import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { locale as rootLocale } from "next/root-params";

import { routing } from "./routing";

export default getRequestConfig(async () => {
  // Read the locale from the `[locale]` root segment via next/root-params.
  // Unlike next-intl's header-based default, this keeps pages statically
  // renderable under Cache Components (no headers() call).
  const requested = await rootLocale();
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    // Fixed so server- and client-rendered dates match. Event times are always
    // formatted in the event's own timezone (see EventCard), not this one.
    timeZone: "America/New_York",
  };
});
