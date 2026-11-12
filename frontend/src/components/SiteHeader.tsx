import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

import { LanguageSwitcher } from "./LanguageSwitcher";

export async function SiteHeader() {
  const t = await getTranslations("nav");
  return (
    <header className="border-line bg-paper/90 sticky top-0 z-10 border-b backdrop-blur">
      <nav className="mx-auto flex max-w-4xl items-center gap-5 px-4 py-3 text-sm">
        <Link href="/" className="font-display text-xl tracking-wide">
          D <span className="text-accent">&amp;</span> H
        </Link>
        <div className="ml-auto flex items-center gap-5">
          <Link href="/rsvp" className="hover:text-accent">
            {t("rsvp")}
          </Link>
          <Link href="/faq" className="hover:text-accent">
            {t("faq")}
          </Link>
          <LanguageSwitcher />
        </div>
      </nav>
    </header>
  );
}
