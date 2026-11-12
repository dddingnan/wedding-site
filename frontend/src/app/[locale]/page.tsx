import { getFormatter, getTranslations } from "next-intl/server";

import { Countdown } from "@/components/Countdown";
import { EventCard } from "@/components/EventCard";
import { Link } from "@/i18n/navigation";
import { RSVP_DEADLINE, SCHEDULE } from "@/lib/schedule";

export default async function HomePage() {
  const t = await getTranslations("home");
  const format = await getFormatter();

  return (
    <>
      <section className="mx-auto max-w-3xl px-4 pt-20 pb-12 text-center">
        <p className="text-muted text-xs tracking-[0.3em] uppercase">{t("tagline")}</p>
        <h1 className="font-display mt-4 text-6xl leading-tight sm:text-7xl">{t("names")}</h1>
        <p className="text-muted mx-auto mt-6 max-w-md">{t("intro")}</p>
        <div className="mt-10">
          <Countdown to={SCHEDULE[0].startsAt} />
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 py-10">
        <h2 className="font-display mb-6 text-center text-3xl">{t("eventsTitle")}</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          {SCHEDULE.map((e) => (
            <EventCard
              key={e.slug}
              slug={e.slug}
              startsAt={e.startsAt}
              timeZone={e.timeZone}
              mapUrl={e.mapUrl}
            />
          ))}
        </div>
      </section>

      <section className="px-4 py-12 text-center">
        <Link
          href="/rsvp"
          className="bg-accent text-accent-ink inline-block rounded-full px-8 py-3 font-medium hover:opacity-90"
        >
          {t("rsvpCta")}
        </Link>
        <p className="text-muted mt-3 text-sm">
          {t("rsvpBy", { date: format.dateTime(new Date(RSVP_DEADLINE), { dateStyle: "long" }) })}
        </p>
      </section>
    </>
  );
}
