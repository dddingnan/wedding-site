import { getTranslations } from "next-intl/server";

import { RsvpFlow } from "@/components/RsvpFlow";

export default async function RsvpPage() {
  const t = await getTranslations("rsvp");
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display mb-8 text-center text-4xl">{t("title")}</h1>
      {/* Typed-code fallback. Links/QR codes open /invite/<token> instead. */}
      <RsvpFlow />
    </div>
  );
}
