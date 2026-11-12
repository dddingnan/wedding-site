import "@fontsource/cormorant-garamond/400.css";
import "@fontsource/cormorant-garamond/600.css";
import "@fontsource-variable/inter";
// CJK fonts use unicode-range, so browsers only download the glyph chunks a page uses.
import "@fontsource/noto-sans-tc/400.css";
import "@fontsource/noto-sans-tc/500.css";
import "@fontsource/noto-sans-kr/400.css";
import "@fontsource/noto-sans-kr/500.css";
import "../globals.css";

import type { Metadata } from "next";
import { locale as rootLocale } from "next/root-params";
import { NextIntlClientProvider } from "next-intl";
import { getTranslations } from "next-intl/server";

import { SiteHeader } from "@/components/SiteHeader";
import { routing } from "@/i18n/routing";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("meta");
  return { title: t("title"), description: t("description") };
}

export default async function LocaleLayout({ children }: LayoutProps<"/[locale]">) {
  const t = await getTranslations("footer");
  return (
    <html lang={await rootLocale()}>
      <body className="flex min-h-dvh flex-col">
        <NextIntlClientProvider>
          <SiteHeader />
          <main className="flex-1">{children}</main>
          <footer className="text-muted py-10 text-center text-sm">{t("madeWith")}</footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
