"use client";

import Link from "next/link";
import { useStore } from "@/lib/store-context";

export function Header() {
  const { cart, customerId } = useStore();

  return (
    <header className="sticky top-0 z-30 border-b border-hm-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <Link href="/" className="text-xl font-bold tracking-tight text-hm-red">
          StylistAI
        </Link>

        <nav className="flex items-center gap-6 text-sm">
          <Link href="/catalog" className="hover:text-hm-red">
            Catalog
          </Link>
          <Link href="/cart" className="relative hover:text-hm-red">
            Cart
            {cart && cart.item_count > 0 && (
              <span className="absolute -right-4 -top-2 rounded-full bg-hm-red px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {cart.item_count}
              </span>
            )}
          </Link>
          {customerId && (
            <span
              className="hidden font-mono text-xs text-hm-muted sm:inline"
              title={customerId}
            >
              {customerId.slice(0, 8)}…
            </span>
          )}
        </nav>
      </div>
    </header>
  );
}
