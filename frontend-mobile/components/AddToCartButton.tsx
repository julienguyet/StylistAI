"use client";

import { useState } from "react";
import { useStore } from "@/lib/store-context";
import { formatPrice } from "@/lib/format";

/**
 * Sticky call to action, the standard mobile commerce pattern: the price and
 * the button stay reachable however far down the description you have scrolled.
 *
 * It sits directly above the BottomNav (3.5rem) rather than at the bottom of
 * the viewport, and is width-matched to the phone column so it lines up with
 * the nav underneath it on a wide screen.
 */
export function AddToCartButton({
  articleId,
  price,
  currency,
}: {
  articleId: string;
  price: number;
  currency: string;
}) {
  const { addToCart, customerId } = useStore();
  const [state, setState] = useState<"idle" | "adding" | "added">("idle");

  async function handleClick() {
    setState("adding");
    await addToCart(articleId);
    setState("added");
    setTimeout(() => setState("idle"), 2000);
  }

  return (
    <div className="fixed bottom-[calc(3.5rem+var(--safe-bottom))] left-1/2 z-20 w-full max-w-phone -translate-x-1/2 border-t border-hm-line bg-white/95 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="text-lg font-semibold">{formatPrice(price, currency)}</span>
        <button
          onClick={handleClick}
          disabled={!customerId || state === "adding"}
          className="flex-1 rounded-full bg-hm-ink py-3 text-sm font-medium text-white active:bg-black disabled:opacity-50"
        >
          {state === "added"
            ? "Added to cart ✓"
            : state === "adding"
              ? "Adding…"
              : "Add to cart"}
        </button>
      </div>
    </div>
  );
}
