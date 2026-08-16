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
      .then((res) =>
        res.ok ? res.json() : Promise.reject(new Error("Catalog API unreachable")),
      )
      .then(setCustomers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [needsPick]);

  if (!needsPick) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/60" />

      {/* Bottom sheet rather than a centred modal: it opens under the thumb,
          and the list scrolls inside the sheet instead of the page behind it. */}
      <div className="fixed bottom-0 left-1/2 z-50 flex max-h-[85vh] w-full max-w-[520px] -translate-x-1/2 flex-col rounded-t-2xl bg-white">
        <div className="flex justify-center pt-2">
          <span className="h-1 w-10 rounded-full bg-neutral-300" />
        </div>

        <div className="px-5 pb-3 pt-3">
          <h2 className="text-base font-semibold">Choose a shopper profile</h2>
          <p className="mt-1 text-sm text-hm-muted">
            This demo has no sign-up. Pick one of these real profiles from the H&amp;M
            dataset — their purchase history drives the recommendations.
          </p>
        </div>

        {loading && <p className="px-5 pb-5 text-sm text-hm-muted">Loading profiles…</p>}
        {error && (
          <p className="px-5 pb-5 text-sm text-hm-red">
            {error}. Is the catalog API running on port 8002?
          </p>
        )}

        <ul className="flex-1 space-y-2 overflow-y-auto px-5 pb-[calc(1.25rem+var(--safe-bottom))]">
          {customers.map((customer) => (
            <li key={customer.customer_id}>
              <button
                onClick={() => setCustomerId(customer.customer_id)}
                className="w-full rounded-xl border border-hm-line px-4 py-3 text-left active:bg-neutral-100"
              >
                <span className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {customer.age ? `${customer.age} years old` : "Age unknown"}
                  </span>
                  <span className="text-xs text-hm-muted">
                    {customer.purchase_count} purchases
                  </span>
                </span>
                <span className="mt-0.5 block text-xs text-hm-muted">
                  {customer.club_member_status ?? "—"}
                </span>
                <span className="mt-0.5 block truncate font-mono text-[11px] text-hm-muted">
                  {customer.customer_id.slice(0, 24)}…
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
