import type { Metadata } from "next";

import { AdminDashboard } from "@/components/AdminDashboard";

export const metadata: Metadata = { title: "Admin", robots: { index: false, follow: false } };

// Admin UI is English-only; it's just for the two of us.
export default function AdminPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <AdminDashboard />
    </div>
  );
}
