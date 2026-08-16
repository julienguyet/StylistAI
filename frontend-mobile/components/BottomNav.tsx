"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStore } from "@/lib/store-context";
import { useChat } from "@/lib/chat-context";

type Item = { href: string; label: string; icon: string };

const ITEMS: Item[] = [
  { href: "/", label: "Home", icon: "⌂" },
  { href: "/catalog", label: "Catalog", icon: "▤" },
  { href: "/cart", label: "Cart", icon: "▢" },
];

/**
 * Thumb-reachable navigation, pinned to the bottom of the phone column rather
 * than the viewport — `left-1/2 -translate-x-1/2` keeps it aligned with the
 * centred column on a wide screen instead of stretching across it.
 */
export function BottomNav() {
  const pathname = usePathname();
  const { cart } = useStore();
  const { open: openChat } = useChat();

  return (
    <nav className="fixed bottom-0 left-1/2 z-30 w-full max-w-phone -translate-x-1/2 border-t border-hm-line bg-white/95 pb-safe backdrop-blur">
      <div className="flex items-stretch">
        {ITEMS.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const badge = item.href === "/cart" ? cart?.item_count ?? 0 : 0;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] ${
                active ? "text-hm-red" : "text-hm-muted"
              }`}
            >
              <span className="text-lg leading-none">{item.icon}</span>
              {item.label}
              {badge > 0 && (
                <span className="absolute right-[22%] top-1.5 rounded-full bg-hm-red px-1.5 text-[10px] font-semibold leading-4 text-white">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}

        {/* Not a route: the chat is a sheet over whatever page you are on, so
            leaving the catalog behind it is what makes ui_action navigation
            visible while you are still talking. */}
        <button
          onClick={openChat}
          className="flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] text-hm-muted"
        >
          <span className="text-lg leading-none">✦</span>
          Björn
        </button>
      </div>
    </nav>
  );
}
