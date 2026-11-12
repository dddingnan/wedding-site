import type { routing } from "@/i18n/routing";
import type messages from "../messages/en.json";

// Makes useTranslations()/getTranslations() keys type-checked against en.json,
// so a typo or a key missing from the English file fails `npm run build`.
declare module "next-intl" {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof messages;
  }
}
