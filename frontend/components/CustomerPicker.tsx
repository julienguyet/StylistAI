"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/lib/store-context";
import type { CustomerSummary } from "@/lib/types";

export function CustomerPicker() {
  const { customerId, setCustomerId, ready } = useStore();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const needsPick = ready && !customerId;

  useEffect(() => {
    if (!needsPick) return;
    setLoading(true);
    fetch("/api/customers?n=6")
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Catalog API unreachable"))))
      .then(setCustomers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [needsPick]);

  if (!needsPick) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Choose a shopper profile</h2>
        <p className="mt-1 text-sm text-hm-muted">
          This demo has no sign-up. Pick one of these real profiles from the H&amp;M
          dataset — their purchase history drives the recommendations.
        </p>

        {loading && <p className="mt-6 text-sm text-hm-muted">Loading profiles…</p>}
        {error && (
          <p className="mt-6 text-sm text-hm-red">
            {error}. Is the catalog API running on port 8002?
          </p>
        )}

        <ul className="mt-4 space-y-2">
          {customers.map((customer) => (
            <li key={customer.customer_id}>
              <button
                onClick={() => setCustomerId(customer.customer_id)}
                className="flex w-full items-center justify-between rounded border border-hm-line px-4 py-3 text-left hover:border-hm-ink"
              >
                <span>
                  <span className="block text-sm font-medium">
                    {customer.age ? `${customer.age} years old` : "Age unknown"} ·{" "}
                    {customer.club_member_status ?? "—"}
                  </span>
                  <span className="block font-mono text-xs text-hm-muted">
                    {customer.customer_id.slice(0, 16)}…
                  </span>
                </span>
                <span className="text-xs text-hm-muted">
                  {customer.purchase_count} purchases
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
