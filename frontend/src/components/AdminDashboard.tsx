"use client";

import { useEffect, useState } from "react";

import { setAdminToken, useAdminToken } from "@/lib/admin-token";
import {
  admin,
  adminLogin,
  ApiError,
  type HouseholdAdmin,
  type Summary,
  type WeddingEventAdmin,
} from "@/lib/api";

const input = "rounded-md border border-line bg-paper px-3 py-2 text-sm";
const button =
  "rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-ink disabled:opacity-60";

type Data = { summary: Summary; events: WeddingEventAdmin[]; households: HouseholdAdmin[] };

const counts = (c: Record<string, number>) =>
  Object.entries(c)
    .map(([k, n]) => `${k} ${n}`)
    .join(" · ");

export function AdminDashboard() {
  const token = useAdminToken();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Data | null>(null);
  // Bump to refetch after a change (add/edit/delete).
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const api = admin(token);
    Promise.all([api.summary(), api.events(), api.households()]).then(
      ([summary, events, households]) => {
        if (!cancelled) setData({ summary, events, households });
      },
      (err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401)
          setAdminToken(null); // expired
        else setError(String(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [token, version]);

  const logout = () => {
    setAdminToken(null);
    setData(null);
  };

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { access_token } = await adminLogin(password);
      setAdminToken(access_token);
      setPassword("");
    } catch {
      setError("Wrong password");
    }
  }

  async function downloadCsv() {
    if (!token) return;
    const url = URL.createObjectURL(await admin(token).exportCsv());
    const a = Object.assign(document.createElement("a"), { href: url, download: "rsvps.csv" });
    a.click();
    URL.revokeObjectURL(url);
  }

  async function remove(h: HouseholdAdmin) {
    if (!token || !confirm(`Delete "${h.name}" and all their RSVPs?`)) return;
    await admin(token).deleteHousehold(h.id);
    reload();
  }

  async function setMax(h: HouseholdAdmin, max: number) {
    if (!token || max === h.max_guests || !(max >= 1)) return;
    setError(null);
    try {
      await admin(token).updateHousehold(h.id, { max_guests: max });
    } catch (err) {
      setError(`${h.name}: ${err instanceof ApiError ? err.message : String(err)}`);
    }
    reload();
  }

  const summary = data?.summary;
  const events = data?.events ?? [];
  const upcoming = events.filter((e) => e.kind === "upcoming");
  const households = data?.households ?? [];

  if (!token) {
    return (
      <form onSubmit={login} className="mx-auto flex max-w-xs flex-col gap-3">
        <h1 className="font-display text-3xl">Admin</h1>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className={input}
          required
        />
        <button className={button}>Sign in</button>
        {error && <p className="text-danger text-sm">{error}</p>}
      </form>
    );
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl">Admin</h1>
        <div className="ml-auto flex gap-2">
          <button onClick={downloadCsv} className={button}>
            Export CSV
          </button>
          <button onClick={logout} className="border-line rounded-md border px-4 py-2 text-sm">
            Sign out
          </button>
        </div>
      </div>

      {summary && (
        <section>
          <p className="text-muted mb-3 text-sm">
            {summary.households_responded} of {summary.households} invitations answered
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {summary.events.map((e) => (
              <div key={e.event_id} className="border-line bg-card rounded-xl border p-5">
                <h2 className="font-medium">{e.slug}</h2>
                <p className="text-muted mb-3 text-xs">
                  Seats given out: {e.reserved}
                  {e.capacity ? ` of ${e.capacity}` : " (no capacity set)"}
                </p>
                <dl className="grid grid-cols-4 gap-2 text-center">
                  {(
                    [
                      ["People coming", e.people_attending],
                      ["Households yes", e.households_attending],
                      ["No", e.households_declined],
                      ["Waiting", e.households_awaiting],
                    ] as const
                  ).map(([label, n]) => (
                    <div key={label}>
                      <dd className="font-display text-3xl tabular-nums">{n}</dd>
                      <dt className="text-muted text-xs">{label}</dt>
                    </div>
                  ))}
                </dl>
                {Object.keys(e.meals).length > 0 && (
                  <p className="text-muted mt-3 text-xs">Meals: {counts(e.meals)}</p>
                )}
                {Object.keys(e.zodiacs).length > 0 && (
                  <p className="text-muted mt-1 text-xs">Zodiac gifts: {counts(e.zodiacs)}</p>
                )}
              </div>
            ))}
          </div>
          {events.length === 0 && (
            <p className="text-danger text-sm">
              No events yet. Run `uv run python -m scripts.seed_events` in backend/.
            </p>
          )}
        </section>
      )}

      <AddHousehold token={token} events={upcoming} onAdded={reload} />

      <section>
        <h2 className="mb-3 font-medium">Invitations ({households.length})</h2>
        {error && <p className="text-danger mb-3 text-sm">{error}</p>}
        <div className="border-line bg-card overflow-x-auto rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead className="border-line text-muted border-b text-xs uppercase">
              <tr>
                <th className="p-3">Household</th>
                <th className="p-3">Code</th>
                <th className="p-3">Lang</th>
                <th className="p-3">Max</th>
                <th className="p-3">RSVP (★ = main event)</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody className="divide-line divide-y">
              {households.map((h) => (
                <tr key={h.id}>
                  <td className="p-3">
                    {h.name}
                    {(h.contact_first_name || h.contact_last_name) && (
                      <p className="text-muted text-xs">
                        {[h.contact_first_name, h.contact_last_name].filter(Boolean).join(" ")}
                      </p>
                    )}
                    {h.note && <p className="text-muted mt-1 text-xs italic">“{h.note}”</p>}
                  </td>
                  <td className="p-3 font-mono">{h.invite_code}</td>
                  <td className="p-3">{h.preferred_language}</td>
                  <td className="p-3">
                    <input
                      // Remount after a save/reload so a rejected value snaps back.
                      key={`${h.id}-${h.max_guests}-${version}`}
                      type="number"
                      min={1}
                      max={50}
                      defaultValue={h.max_guests}
                      onBlur={(e) => setMax(h, Number(e.target.value))}
                      onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                      className={`${input} w-16`}
                      aria-label={`Max people for ${h.name}`}
                    />
                  </td>
                  <td className="p-3">
                    {h.events.map((ev) => {
                      const r = h.rsvps.find((r) => r.event_id === ev.id);
                      const answer = !r ? "…" : r.attending ? `✓ ${r.party_size}` : "✗";
                      return (
                        <div key={ev.id}>
                          {ev.id === h.primary_event_id && "★ "}
                          {ev.slug}: {answer}
                          {r && Object.keys(r.zodiacs).length > 0 && (
                            <span className="text-muted text-xs"> ({counts(r.zodiacs)})</span>
                          )}
                        </div>
                      );
                    })}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => remove(h)}
                      className="text-danger text-xs hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function AddHousehold({
  token,
  events,
  onAdded,
}: {
  token: string;
  events: WeddingEventAdmin[];
  onAdded: () => void;
}) {
  const [name, setName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [maxGuests, setMaxGuests] = useState(1);
  const [language, setLanguage] = useState<"en" | "zh-TW" | "ko">("en");
  const [primary, setPrimary] = useState<string | null>(null); // null = first event
  const [others, setOthers] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const main = primary ?? events[0]?.slug ?? "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await admin(token).createHousehold({
        name,
        contact_first_name: firstName || null,
        contact_last_name: lastName || null,
        preferred_language: language,
        max_guests: maxGuests,
        primary_event: main,
        other_events: others.filter((s) => s !== main),
      });
      setName("");
      setFirstName("");
      setLastName("");
      setMaxGuests(1);
      setOthers([]);
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h2 className="mb-3 font-medium">Add invitation</h2>
      <form
        onSubmit={submit}
        className="border-line bg-card grid gap-3 rounded-xl border p-5 sm:grid-cols-2"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Household (e.g. Hsu Family)"
          className={`${input} sm:col-span-2`}
          required
        />
        <input
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="Contact first name"
          className={input}
        />
        <input
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          placeholder="Contact last name"
          className={input}
        />
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as typeof language)}
          className={input}
        >
          <option value="en">English</option>
          <option value="zh-TW">繁體中文</option>
          <option value="ko">한국어</option>
        </select>
        <label className="flex items-center gap-2 text-sm">
          Max people
          <input
            type="number"
            min={1}
            max={50}
            value={maxGuests}
            onChange={(e) => setMaxGuests(Number(e.target.value))}
            className={`${input} w-20`}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          Main event
          <select value={main} onChange={(e) => setPrimary(e.target.value)} className={input}>
            {events.map((ev) => (
              <option key={ev.id} value={ev.slug}>
                {ev.slug}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          Also invite to:
          {events
            .filter((ev) => ev.slug !== main)
            .map((ev) => (
              <label key={ev.id} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={others.includes(ev.slug)}
                  onChange={(e) =>
                    setOthers(
                      e.target.checked ? [...others, ev.slug] : others.filter((s) => s !== ev.slug),
                    )
                  }
                />
                {ev.slug}
              </label>
            ))}
        </div>
        <div className="sm:col-span-2">
          <button disabled={busy || !main} className={button}>
            {busy ? "Adding…" : "Add"}
          </button>
          {error && <span className="text-danger ml-3 text-sm">{error}</span>}
        </div>
      </form>
    </section>
  );
}
