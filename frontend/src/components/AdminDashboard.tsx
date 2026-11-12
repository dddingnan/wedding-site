"use client";

import { useEffect, useState } from "react";

import { setAdminToken, useAdminToken } from "@/lib/admin-token";
import {
  admin,
  adminLogin,
  ApiError,
  type HouseholdAdmin,
  type Summary,
  type WeddingEvent,
} from "@/lib/api";

const input = "rounded-md border border-line bg-paper px-3 py-2 text-sm";
const button =
  "rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-ink disabled:opacity-60";

type Data = { summary: Summary; events: WeddingEvent[]; households: HouseholdAdmin[] };

export function AdminDashboard() {
  const token = useAdminToken();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Data | null>(null);
  // Bump to refetch after a change (add/delete).
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

  const summary = data?.summary;
  const events = data?.events ?? [];
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
                <h2 className="mb-3 font-medium">{e.slug}</h2>
                <dl className="grid grid-cols-4 gap-2 text-center">
                  {(
                    [
                      ["Invited", e.invited],
                      ["Yes", e.attending],
                      ["No", e.declined],
                      ["Waiting", e.awaiting],
                    ] as const
                  ).map(([label, n]) => (
                    <div key={label}>
                      <dd className="font-display text-3xl tabular-nums">{n}</dd>
                      <dt className="text-muted text-xs">{label}</dt>
                    </div>
                  ))}
                </dl>
                {Object.keys(e.meals).length > 0 && (
                  <p className="text-muted mt-3 text-xs">
                    Meals:{" "}
                    {Object.entries(e.meals)
                      .map(([m, n]) => `${m} ${n}`)
                      .join(" · ")}
                  </p>
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

      <AddHousehold token={token} events={events} onAdded={reload} />

      <section>
        <h2 className="mb-3 font-medium">Invitations ({households.length})</h2>
        <div className="border-line bg-card overflow-x-auto rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead className="border-line text-muted border-b text-xs uppercase">
              <tr>
                <th className="p-3">Household</th>
                <th className="p-3">Code</th>
                <th className="p-3">Lang</th>
                <th className="p-3">Events</th>
                <th className="p-3">Guests</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody className="divide-line divide-y">
              {households.map((h) => (
                <tr key={h.id}>
                  <td className="p-3">
                    {h.name}
                    {h.note && <p className="text-muted mt-1 text-xs italic">“{h.note}”</p>}
                  </td>
                  <td className="p-3 font-mono">{h.invite_code}</td>
                  <td className="p-3">{h.preferred_language}</td>
                  <td className="p-3">{h.events.map((e) => e.slug).join(", ")}</td>
                  <td className="p-3">
                    {h.guests.map((g) => (
                      <div key={g.id}>
                        {g.full_name}{" "}
                        <span className="text-muted text-xs">
                          {h.events
                            .map((ev) => {
                              const r = g.rsvps.find((r) => r.event_id === ev.id);
                              return `${ev.slug}: ${r ? (r.attending ? "✓" : "✗") : "…"}`;
                            })
                            .join("  ")}
                        </span>
                      </div>
                    ))}
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
  events: WeddingEvent[];
  onAdded: () => void;
}) {
  const [name, setName] = useState("");
  const [guests, setGuests] = useState("");
  const [plusOnes, setPlusOnes] = useState(0);
  const [language, setLanguage] = useState<"en" | "zh-TW" | "ko">("en");
  const [slugs, setSlugs] = useState<string[] | null>(null); // null = all events
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = slugs ?? events.map((e) => e.slug);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const names = guests
        .split(/[\n,;]/)
        .map((s) => s.trim())
        .filter(Boolean);
      await admin(token).createHousehold({
        name,
        preferred_language: language,
        event_slugs: selected,
        guests: [
          ...names.map((full_name) => ({ full_name, is_plus_one: false })),
          ...Array.from({ length: plusOnes }, () => ({ full_name: "Guest", is_plus_one: true })),
        ],
      });
      setName("");
      setGuests("");
      setPlusOnes(0);
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
          placeholder="Household (e.g. The Kim Family)"
          className={input}
          required
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
        <textarea
          value={guests}
          onChange={(e) => setGuests(e.target.value)}
          placeholder="Guest names, one per line"
          rows={3}
          className={`${input} sm:col-span-2`}
          required
        />
        <label className="flex items-center gap-2 text-sm">
          Plus-ones
          <input
            type="number"
            min={0}
            max={5}
            value={plusOnes}
            onChange={(e) => setPlusOnes(Number(e.target.value))}
            className={`${input} w-20`}
          />
        </label>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {events.map((ev) => (
            <label key={ev.id} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={selected.includes(ev.slug)}
                onChange={(e) =>
                  setSlugs(
                    e.target.checked
                      ? [...selected, ev.slug]
                      : selected.filter((s) => s !== ev.slug),
                  )
                }
              />
              {ev.slug}
            </label>
          ))}
        </div>
        <div className="sm:col-span-2">
          <button disabled={busy || selected.length === 0} className={button}>
            {busy ? "Adding…" : "Add"}
          </button>
          {error && <span className="text-danger ml-3 text-sm">{error}</span>}
        </div>
      </form>
    </section>
  );
}
