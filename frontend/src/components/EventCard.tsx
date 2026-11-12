"use client";

import { useFormatter, useTranslations } from "next-intl";

type Props = {
  slug: string;
  startsAt: string;
  timeZone: string;
  mapUrl?: string | null;
  children?: React.ReactNode;
};

/** Event title from translations, time shown in the event's own local time zone. */
export function useEventTitle() {
  const t = useTranslations("events");
  return (slug: string) => {
    const key = `${slug}.title` as "korea.title";
    return t.has(key) ? t(key) : slug;
  };
}

export function EventCard({ slug, startsAt, timeZone, mapUrl, children }: Props) {
  const t = useTranslations("events");
  const format = useFormatter();
  const title = useEventTitle();
  const date = new Date(startsAt);
  const placeKey = `${slug}.place` as "korea.place";

  return (
    <section className="border-line bg-card rounded-xl border p-6">
      <h3 className="font-display text-2xl">{title(slug)}</h3>
      <p className="text-muted mt-1 text-sm">
        {t("time", {
          date: format.dateTime(date, { dateStyle: "full", timeZone }),
          time: format.dateTime(date, { timeStyle: "short", timeZone }),
        })}
      </p>
      {t.has(placeKey) && <p className="mt-1 text-sm">{t(placeKey)}</p>}
      {mapUrl && (
        <a
          href={mapUrl}
          target="_blank"
          rel="noreferrer"
          className="text-accent mt-2 inline-block text-sm underline"
        >
          {t("map")}
        </a>
      )}
      {children && <div className="mt-5">{children}</div>}
    </section>
  );
}
