import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { RsvpFlow } from "@/components/RsvpFlow";

// The URL holds the household's secret token: keep it out of search engines, and don't
// send it as the Referer when guests tap out to Google Maps or a hotel site.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

// Every invitation URL is unique, so there's no shell worth prerendering (the header's
// language switcher also needs the real path). Render each request on the server.
export const instant = false;

// Opened from the link / QR code on the printed invitation: /invite/<token>.
// (The locale prefix is added by the proxy from the browser language.)
// Later: the envelope/card animation (Phase 3) lives here.
export default async function InvitePage({ params }: PageProps<"/[locale]/invite/[token]">) {
  const [{ token }, t] = await Promise.all([params, getTranslations("rsvp")]);
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display mb-8 text-center text-4xl">{t("title")}</h1>
      <RsvpFlow token={token} />
    </div>
  );
}
