"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

function partsUntil(target: number) {
  const ms = Math.max(0, target - Date.now());
  return {
    days: Math.floor(ms / 86_400_000),
    hours: Math.floor(ms / 3_600_000) % 24,
    minutes: Math.floor(ms / 60_000) % 60,
    seconds: Math.floor(ms / 1000) % 60,
  };
}

export function Countdown({ to }: { to: string }) {
  const t = useTranslations("home");
  // Start empty and fill in after mount: the server's "now" differs from the
  // browser's, so rendering numbers on the server would cause a hydration mismatch.
  const [parts, setParts] = useState<ReturnType<typeof partsUntil> | null>(null);

  useEffect(() => {
    const target = new Date(to).getTime();
    const tick = () => setParts(partsUntil(target));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [to]);

  const units = ["days", "hours", "minutes", "seconds"] as const;
  return (
    <div aria-live="off">
      <p className="text-muted mb-3 text-xs tracking-[0.25em] uppercase">{t("countdownLabel")}</p>
      <div className="flex justify-center gap-3 sm:gap-6">
        {units.map((u) => (
          <div key={u} className="border-line bg-card min-w-16 rounded-lg border px-3 py-3">
            <div className="font-display text-3xl tabular-nums sm:text-4xl">
              {parts ? parts[u] : "–"}
            </div>
            <div className="text-muted text-xs">{t(u)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
