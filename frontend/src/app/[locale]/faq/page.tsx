import { getTranslations } from "next-intl/server";

const ITEMS = [1, 2, 3, 4, 5] as const;

export default async function FaqPage() {
  const t = await getTranslations("faq");
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display mb-8 text-center text-4xl">{t("title")}</h1>
      <div className="divide-line border-line bg-card divide-y rounded-xl border">
        {ITEMS.map((n) => (
          <details key={n} className="group p-5">
            <summary className="cursor-pointer list-none font-medium marker:hidden">
              <span className="text-accent mr-2 inline-block transition group-open:rotate-45">
                +
              </span>
              {t(`q${n}`)}
            </summary>
            <p className="text-muted mt-3 pl-5">{t(`a${n}`)}</p>
          </details>
        ))}
      </div>
    </div>
  );
}
