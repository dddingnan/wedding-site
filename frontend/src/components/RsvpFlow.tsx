"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useEffectEvent, useState } from "react";

import {
  ApiError,
  MEALS,
  lookupInvite,
  submitRsvp,
  type EventResponse,
  type Household,
  type Meal,
  type WeddingEvent,
  type Zodiac,
} from "@/lib/api";

import { EventCard, useEventTitle } from "./EventCard";

// Placeholder icons until we draw our own animal artwork.
const ZODIAC_ICONS: Record<Zodiac, string> = {
  rat: "🐀", ox: "🐂", tiger: "🐅", rabbit: "🐇", dragon: "🐉", snake: "🐍",
  horse: "🐎", goat: "🐐", monkey: "🐒", rooster: "🐓", dog: "🐕", pig: "🐖",
}; // prettier-ignore

/** The household's answer for one event, as edited in the form. */
type Answer = {
  attending?: boolean;
  partySize: number;
  meals: Partial<Record<Meal, number>>;
  zodiacs: Partial<Record<Zodiac, number>>;
  dietary: string;
};
const emptyAnswer: Answer = { partySize: 1, meals: {}, zodiacs: {}, dietary: "" };

/** Pre-fill the form from answers already saved on the server (keyed by event id). */
function answersFrom(h: Household): Record<number, Answer> {
  const answers: Record<number, Answer> = {};
  for (const r of h.rsvps) {
    answers[r.event_id] = {
      attending: r.attending,
      partySize: r.attending ? r.party_size : 1,
      meals: r.meals,
      zodiacs: r.zodiacs,
      dietary: r.dietary ?? "",
    };
  }
  return answers;
}

const total = (counts: Partial<Record<string, number>>) =>
  Object.values(counts).reduce<number>((sum, n) => sum + (n ?? 0), 0);

const inputClass = "w-full rounded-md border border-line bg-paper px-3 py-2 text-sm";

export function RsvpFlow() {
  const t = useTranslations("rsvp");
  const tMeals = useTranslations("meals");
  const tZodiac = useTranslations("zodiac");
  const format = useFormatter();
  const eventTitle = useEventTitle();
  const searchParams = useSearchParams();

  // A QR code on the printed card can link straight to /rsvp?code=AB3K9Q.
  const [codeFromUrl] = useState(() => searchParams.get("code"));
  const [code, setCode] = useState(codeFromUrl ?? "");
  const [household, setHousehold] = useState<Household | null>(null);
  const [answers, setAnswers] = useState<Record<number, Answer>>({});
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
      setHousehold(result.h);
      setAnswers(answersFrom(result.h));
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

  const answerFor = (eventId: number) => answers[eventId] ?? emptyAnswer;

  function update(eventId: number, patch: Partial<Answer>) {
    setAnswers((prev) => ({ ...prev, [eventId]: { ...(prev[eventId] ?? emptyAnswer), ...patch } }));
  }

  function toResponse(ev: WeddingEvent): EventResponse {
    const a = answerFor(ev.id);
    if (!a.attending) {
      return { event_id: ev.id, attending: false, party_size: 0, meals: {}, zodiacs: {} };
    }
    return {
      event_id: ev.id,
      attending: true,
      party_size: a.partySize,
      meals: a.meals,
      // Only the animals this event asks about; never more than the people coming
      // (the party size may have been lowered after picking).
      zodiacs: Object.fromEntries(
        ev.gift_zodiacs.map((z) => [z, Math.min(a.zodiacs[z] ?? 0, a.partySize)]),
      ),
      dietary: a.dietary || null,
    };
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!household) return;

    if (household.events.some((ev) => answerFor(ev.id).attending === undefined)) {
      setError(t("chooseAll"));
      return;
    }
    const mealsOff = household.events.find((ev) => {
      const a = answerFor(ev.id);
      return a.attending && total(a.meals) !== a.partySize;
    });
    if (mealsOff) {
      setError(t("mealsMismatch", { event: eventTitle(mealsOff.slug) }));
      return;
    }

    setError(null);
    setStatus("loading");
    try {
      const saved = await submitRsvp(code, {
        note: note || null,
        responses: household.events.map(toResponse),
      });
      setHousehold(saved);
      setAnswers(answersFrom(saved));
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
  const max = household.max_guests;
  const stepLabels: [string, string] = [t("fewer"), t("more")];

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="text-center">
        <p className="font-display text-2xl">{t("greeting", { name: household.name })}</p>
        <p className="text-muted mt-1 text-sm">{t("intro")}</p>
      </div>

      {household.events.map((ev) => {
        const a = answerFor(ev.id);
        const mealsChosen = total(a.meals);
        return (
          <EventCard
            key={ev.id}
            slug={ev.slug}
            startsAt={ev.starts_at}
            timeZone={ev.timezone}
            mapUrl={ev.map_url}
          >
            <div className="flex flex-wrap gap-2">
              {([true, false] as const).map((value) => (
                <label
                  key={String(value)}
                  className={`cursor-pointer rounded-full border px-5 py-2 transition ${
                    a.attending === value
                      ? "border-accent bg-accent text-accent-ink"
                      : "border-line hover:border-accent"
                  }`}
                >
                  <input
                    type="radio"
                    className="sr-only"
                    name={`attending-${ev.id}`}
                    checked={a.attending === value}
                    onChange={() => update(ev.id, { attending: value })}
                  />
                  {value ? t("attending") : t("declining")}
                </label>
              ))}
            </div>

            {a.attending && (
              <div className="divide-line mt-4 divide-y">
                <Row label={t("partySize")} hint={t("partySizeHint", { max })}>
                  <Stepper
                    value={a.partySize}
                    min={1}
                    max={max}
                    labels={stepLabels}
                    onChange={(partySize) => update(ev.id, { partySize })}
                  />
                </Row>

                <div className="py-4">
                  <p className="font-medium">{t("meals")}</p>
                  <p
                    className={`mb-2 text-sm ${mealsChosen === a.partySize ? "text-muted" : "text-danger"}`}
                  >
                    {t("mealsHint", { chosen: mealsChosen, total: a.partySize })}
                  </p>
                  {MEALS.map((m) => (
                    <Row key={m} label={tMeals(m)} compact>
                      <Stepper
                        value={a.meals[m] ?? 0}
                        min={0}
                        // Can't pick more meals than people (but can always lower one).
                        max={Math.max(
                          a.meals[m] ?? 0,
                          a.partySize - mealsChosen + (a.meals[m] ?? 0),
                        )}
                        labels={stepLabels}
                        onChange={(n) => update(ev.id, { meals: { ...a.meals, [m]: n } })}
                      />
                    </Row>
                  ))}
                </div>

                {ev.gift_zodiacs.length > 0 && (
                  <div className="py-4">
                    <p className="mb-2 font-medium">{t("zodiac")}</p>
                    {ev.gift_zodiacs.map((z) => (
                      <Row
                        key={z}
                        compact
                        label={
                          <>
                            <span aria-hidden className="mr-2 text-2xl">
                              {ZODIAC_ICONS[z]}
                            </span>
                            {tZodiac(z)}
                          </>
                        }
                      >
                        <Stepper
                          value={a.zodiacs[z] ?? 0}
                          min={0}
                          max={Math.max(a.zodiacs[z] ?? 0, a.partySize)}
                          labels={stepLabels}
                          onChange={(n) => update(ev.id, { zodiacs: { ...a.zodiacs, [z]: n } })}
                        />
                      </Row>
                    ))}
                  </div>
                )}

                <label className="block pt-4 text-sm">
                  <span className="text-muted mb-1 block">{t("dietary")}</span>
                  <input
                    value={a.dietary}
                    onChange={(e) => update(ev.id, { dietary: e.target.value })}
                    maxLength={500}
                    className={inputClass}
                  />
                </label>
              </div>
            )}
          </EventCard>
        );
      })}

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

function Row({
  label,
  hint,
  compact,
  children,
}: {
  label: React.ReactNode;
  hint?: string;
  compact?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex items-center justify-between gap-4 ${compact ? "py-1.5" : "py-4"}`}>
      <div>
        <p className={compact ? "" : "font-medium"}>{label}</p>
        {hint && <p className="text-muted text-sm">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

/** Big −/+ buttons: easier than a number field for older guests and on phones. */
function Stepper({
  value,
  min,
  max,
  onChange,
  labels: [fewer, more],
}: {
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
  labels: [string, string];
}) {
  const btn =
    "border-line hover:border-accent flex size-11 items-center justify-center rounded-full border text-xl disabled:opacity-30";
  return (
    <div className="flex shrink-0 items-center gap-3">
      <button
        type="button"
        aria-label={fewer}
        className={btn}
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <span className="w-6 text-center text-lg tabular-nums" aria-live="polite">
        {value}
      </span>
      <button
        type="button"
        aria-label={more}
        className={btn}
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  );
}
