"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useEffectEvent, useState } from "react";

import { ApiError, MEALS, lookupInvite, submitRsvp, type Household, type Meal } from "@/lib/api";

import { EventCard } from "./EventCard";

type Answer = { attending?: boolean; meal?: Meal | null; dietary?: string | null };
type AnswerKey = `${number}:${number}`; // guestId:eventId
const key = (guestId: number, eventId: number): AnswerKey => `${guestId}:${eventId}`;

/** Pre-fill the form from answers already saved on the server. */
function answersFrom(h: Household) {
  const answers: Record<AnswerKey, Answer> = {};
  const names: Record<number, string> = {};
  for (const g of h.guests) {
    if (g.is_plus_one && g.full_name !== "Guest") names[g.id] = g.full_name;
    for (const r of g.rsvps) answers[key(g.id, r.event_id)] = r;
  }
  return { answers, names };
}

const inputClass = "w-full rounded-md border border-line bg-paper px-3 py-2 text-sm";

export function RsvpFlow() {
  const t = useTranslations("rsvp");
  const tMeals = useTranslations("meals");
  const format = useFormatter();
  const searchParams = useSearchParams();

  // A QR code on the printed card can link straight to /rsvp?code=AB3K9Q.
  const [codeFromUrl] = useState(() => searchParams.get("code"));
  const [code, setCode] = useState(codeFromUrl ?? "");
  const [household, setHousehold] = useState<Household | null>(null);
  const [answers, setAnswers] = useState<Record<AnswerKey, Answer>>({});
  const [names, setNames] = useState<Record<number, string>>({});
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "saved">(
    codeFromUrl ? "loading" : "idle",
  );
  const [error, setError] = useState<string | null>(null);

  const errorMessage = (e: unknown) =>
    e instanceof ApiError && e.status === 404
      ? t("notFound")
      : e instanceof ApiError && e.status === 429
        ? t("tooMany")
        : t("error");

  // Applies a lookup result. Called from async callbacks only, never
  // synchronously in an effect body (which would cause cascading renders).
  const onLookupResult = (result: { h: Household } | { err: unknown }) => {
    if ("h" in result) {
      const prefill = answersFrom(result.h);
      setHousehold(result.h);
      setAnswers(prefill.answers);
      setNames(prefill.names);
      setNote(result.h.note ?? "");
    } else {
      setError(errorMessage(result.err));
    }
    setStatus("idle");
  };
  // Effect Events read the latest props/state without being effect dependencies.
  const onAutoLookupResult = useEffectEvent(onLookupResult);

  function find() {
    setError(null);
    setStatus("loading");
    lookupInvite(code).then(
      (h) => onLookupResult({ h }),
      (err) => onLookupResult({ err }),
    );
  }

  useEffect(() => {
    if (!codeFromUrl) return;
    let cancelled = false;
    lookupInvite(codeFromUrl).then(
      (h) => !cancelled && onAutoLookupResult({ h }),
      (err) => !cancelled && onAutoLookupResult({ err }),
    );
    return () => {
      cancelled = true;
    };
  }, [codeFromUrl]);

  function update(guestId: number, eventId: number, patch: Answer) {
    setAnswers((prev) => ({
      ...prev,
      [key(guestId, eventId)]: { ...prev[key(guestId, eventId)], ...patch },
    }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!household) return;

    const pairs = household.events.flatMap((ev) => household.guests.map((g) => ({ g, ev })));
    if (pairs.some(({ g, ev }) => answers[key(g.id, ev.id)]?.attending === undefined)) {
      setError(t("chooseAll"));
      return;
    }

    setError(null);
    setStatus("loading");
    try {
      const saved = await submitRsvp(code, {
        note: note || null,
        responses: pairs.map(({ g, ev }) => {
          const a = answers[key(g.id, ev.id)];
          return {
            guest_id: g.id,
            event_id: ev.id,
            attending: a.attending!,
            meal: a.meal || null,
            dietary: a.dietary || null,
            full_name: g.is_plus_one ? names[g.id] || null : null,
          };
        }),
      });
      setHousehold(saved);
      setStatus("saved");
    } catch (err) {
      setError(errorMessage(err));
      setStatus("idle");
    }
  }

  // ---------- Step 1: enter code ----------
  if (!household) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          find();
        }}
        className="border-line bg-card mx-auto max-w-sm rounded-xl border p-6 text-center"
      >
        <p className="text-muted mb-4 text-sm">{t("codePrompt")}</p>
        <label className="sr-only" htmlFor="code">
          {t("codeLabel")}
        </label>
        <input
          id="code"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder={t("codePlaceholder")}
          autoComplete="off"
          autoCapitalize="characters"
          className={`${inputClass} text-center font-mono text-lg tracking-[0.3em]`}
          required
        />
        <button
          disabled={status === "loading"}
          className="bg-accent text-accent-ink mt-4 w-full rounded-full py-2.5 font-medium disabled:opacity-60"
        >
          {status === "loading" ? t("finding") : t("find")}
        </button>
        {error && <p className="text-danger mt-3 text-sm">{error}</p>}
      </form>
    );
  }

  // ---------- Step 3: thank you ----------
  if (status === "saved") {
    return (
      <div className="border-line bg-card rounded-xl border p-8 text-center">
        <p className="font-display text-3xl">{t("thanks")}</p>
        <p className="text-muted mt-3 text-sm">{t("thanksDetail")}</p>
        {household.responded_at && (
          <p className="text-muted mt-2 text-xs">
            {t("lastUpdated", {
              date: format.dateTime(new Date(household.responded_at), {
                dateStyle: "medium",
                timeStyle: "short",
              }),
            })}
          </p>
        )}
        <button onClick={() => setStatus("idle")} className="text-accent mt-6 text-sm underline">
          {t("edit")}
        </button>
      </div>
    );
  }

  // ---------- Step 2: the form ----------
  const plusOnes = household.guests.filter((g) => g.is_plus_one);
  const displayName = (id: number, fallback: string) => names[id] || fallback;

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="text-center">
        <p className="font-display text-2xl">{t("greeting", { name: household.name })}</p>
        <p className="text-muted mt-1 text-sm">{t("intro")}</p>
      </div>

      {plusOnes.map((g) => (
        <label key={g.id} className="border-line bg-card block rounded-xl border p-5">
          <span className="mb-2 block text-sm font-medium">{t("plusOneName")}</span>
          <input
            value={names[g.id] ?? ""}
            onChange={(e) => setNames((n) => ({ ...n, [g.id]: e.target.value }))}
            placeholder={t("plusOnePlaceholder")}
            className={inputClass}
          />
        </label>
      ))}

      {household.events.map((ev) => (
        <EventCard
          key={ev.id}
          slug={ev.slug}
          startsAt={ev.starts_at}
          timeZone={ev.timezone}
          mapUrl={ev.map_url}
        >
          <div className="divide-line divide-y">
            {household.guests.map((g) => {
              const a = answers[key(g.id, ev.id)] ?? {};
              return (
                <fieldset key={g.id} className="py-4 first:pt-0 last:pb-0">
                  <legend className="mb-2 font-medium">{displayName(g.id, g.full_name)}</legend>
                  <div className="flex flex-wrap gap-2">
                    {([true, false] as const).map((value) => (
                      <label
                        key={String(value)}
                        className={`cursor-pointer rounded-full border px-4 py-1.5 text-sm transition ${
                          a.attending === value
                            ? "border-accent bg-accent text-accent-ink"
                            : "border-line hover:border-accent"
                        }`}
                      >
                        <input
                          type="radio"
                          className="sr-only"
                          name={key(g.id, ev.id)}
                          checked={a.attending === value}
                          onChange={() => update(g.id, ev.id, { attending: value })}
                        />
                        {value ? t("attending") : t("declining")}
                      </label>
                    ))}
                  </div>

                  {a.attending && (
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className="text-sm">
                        <span className="text-muted mb-1 block">{t("meal")}</span>
                        <select
                          value={a.meal ?? ""}
                          onChange={(e) =>
                            update(g.id, ev.id, { meal: (e.target.value || null) as Meal | null })
                          }
                          className={inputClass}
                        >
                          <option value="">{t("mealPlaceholder")}</option>
                          {MEALS.map((m) => (
                            <option key={m} value={m}>
                              {tMeals(m)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm">
                        <span className="text-muted mb-1 block">{t("dietary")}</span>
                        <input
                          value={a.dietary ?? ""}
                          onChange={(e) => update(g.id, ev.id, { dietary: e.target.value })}
                          maxLength={500}
                          className={inputClass}
                        />
                      </label>
                    </div>
                  )}
                </fieldset>
              );
            })}
          </div>
        </EventCard>
      ))}

      <label className="border-line bg-card block rounded-xl border p-5">
        <span className="mb-2 block text-sm font-medium">{t("note")}</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          maxLength={2000}
          className={inputClass}
        />
      </label>

      {error && <p className="text-danger text-center text-sm">{error}</p>}

      <div className="text-center">
        <button
          disabled={status === "loading"}
          className="bg-accent text-accent-ink rounded-full px-10 py-3 font-medium disabled:opacity-60"
        >
          {status === "loading" ? t("submitting") : t("submit")}
        </button>
      </div>
    </form>
  );
}
