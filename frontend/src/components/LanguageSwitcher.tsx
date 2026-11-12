"use client";

import { useLocale, useTranslations } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";

// Each language labelled in its own script, so guests can find theirs.
const LABELS: Record<Locale, string> = { en: "English", "zh-TW": "繁體中文", ko: "한국어" };

export function LanguageSwitcher() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <label className="flex items-center gap-1">
      <span className="sr-only">{t("language")}</span>
      <select
        value={locale}
        onChange={(e) => router.replace(pathname, { locale: e.target.value as Locale })}
        className="border-line bg-card rounded-md border px-2 py-1 text-sm"
      >
        {routing.locales.map((l) => (
          <option key={l} value={l}>
            {LABELS[l]}
          </option>
        ))}
      </select>
    </label>
  );
}
