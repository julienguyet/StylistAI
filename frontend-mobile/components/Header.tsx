"use client";

import Link from "next/link";
import { useStore } from "@/lib/store-context";

/**
 * Slim top bar. Navigation lives in the BottomNav where a thumb can reach it,
 * so this only carries identity and the profile chip.
 */
export function Header() {
  const { customerId } = useStore();

  return (
    <header className="sticky top-0 z-30 border-b border-hm-line bg-white/95 pt-safe backdrop-blur">
      <div className="flex items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight text-hm-red">
          StylistAI
        </Link>

        {customerId && (
          <span
            className="rounded-full bg-neutral-100 px-2.5 py-1 font-mono text-[11px] text-hm-muted"
            title={customerId}
          >
            {customerId.slice(0, 8)}…
          </span>
        )}
      </div>
    </header>
  );
}
