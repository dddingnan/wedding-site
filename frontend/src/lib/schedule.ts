// Public schedule shown on the home page (no API call, so the page is fully static).
// Keep in sync with backend/scripts/seed_events.py. Titles/venues are in messages/*.json.
export const SCHEDULE = [
  {
    slug: "korea",
    startsAt: "2027-12-26T12:00:00+09:00",
    timeZone: "Asia/Seoul",
    theme: "gold",
    mapUrl:
      "https://www.google.com/maps/search/?api=1&query=The+Westin+Josun+Seoul%2C+106+Sogong-ro%2C+Jung+District%2C+Seoul%2C+South+Korea",
  },
  {
    slug: "taiwan",
    startsAt: "2028-01-02T12:00:00+08:00",
    timeZone: "Asia/Taipei",
    theme: "red",
    mapUrl:
      "https://www.google.com/maps/search/?api=1&query=Mandarin+Oriental%2C+Taipei%2C+No.+158%2C+Dunhua+N.+Rd.%2C+Songshan+District%2C+Taipei+City%2C+Taiwan+10548",
  },
] as const satisfies readonly {
  slug: "korea" | "taiwan";
  startsAt: string;
  timeZone: string;
  theme: "gold" | "red";
  mapUrl: string | null;
}[];

export const RSVP_DEADLINE = "2027-10-31T23:59:59-04:00";
