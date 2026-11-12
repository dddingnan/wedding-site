// Public schedule shown on the home page (no API call, so the page is fully static).
// Keep in sync with backend/scripts/seed_events.py. Titles/venues are in messages/*.json.
export const SCHEDULE = [
  { slug: "korea", startsAt: "2027-12-26T12:00:00+09:00", timeZone: "Asia/Seoul", mapUrl: null },
  {
    slug: "second",
    startsAt: "2028-01-02T12:00:00-05:00",
    timeZone: "America/New_York",
    mapUrl: null,
  },
] as const satisfies readonly {
  slug: "korea" | "second";
  startsAt: string;
  timeZone: string;
  mapUrl: string | null;
}[];

export const RSVP_DEADLINE = "2027-10-31T23:59:59-04:00";
