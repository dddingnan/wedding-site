import type { components } from "./api-types";

// Types are generated from the FastAPI OpenAPI schema: `npm run gen:api`.
type Schemas = components["schemas"];
export type Household = Schemas["HouseholdOut"];
export type HouseholdAdmin = Schemas["HouseholdAdminOut"];
export type HouseholdCreate = Schemas["HouseholdCreate"];
export type HouseholdUpdate = Schemas["HouseholdUpdate"];
export type WeddingEvent = Schemas["EventOut"];
export type WeddingEventAdmin = Schemas["EventAdminOut"];
export type Rsvp = Schemas["RsvpOut"];
export type RsvpSubmit = Schemas["RsvpSubmit"];
export type EventResponse = Schemas["EventResponse"];
export type Summary = Schemas["Summary"];
export type Zodiac = WeddingEvent["gift_zodiacs"][number];

// Keep in sync with `Meal` in backend/app/schemas.py (labels: messages "meals.*").
export const MEALS = ["beef", "fish", "vegetarian", "kids"] as const;
export type Meal = (typeof MEALS)[number];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const { token, headers, ...rest } = init;
  const res = await fetch(`${API_URL}/api${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

// ---------- Guests ----------

export const lookupInvite = (code: string) =>
  request<Household>("/invites/lookup", { method: "POST", body: JSON.stringify({ code }) });

export const submitRsvp = (code: string, body: RsvpSubmit) =>
  request<Household>(`/invites/${encodeURIComponent(code)}/rsvp`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

// ---------- Admin ----------

export const adminLogin = (password: string) =>
  request<{ access_token: string }>("/admin/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });

export const admin = (token: string) => ({
  summary: () => request<Summary>("/admin/summary", { token }),
  events: () => request<WeddingEventAdmin[]>("/admin/events", { token }),
  households: () => request<HouseholdAdmin[]>("/admin/households", { token }),
  createHousehold: (body: HouseholdCreate) =>
    request<HouseholdAdmin>("/admin/households", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),
  updateHousehold: (id: number, body: HouseholdUpdate) =>
    request<HouseholdAdmin>(`/admin/households/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      token,
    }),
  deleteHousehold: (id: number) =>
    request<void>(`/admin/households/${id}`, { method: "DELETE", token }),
  exportCsv: async () => {
    const res = await fetch(`${API_URL}/api/admin/export.csv`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    return res.blob();
  },
});
