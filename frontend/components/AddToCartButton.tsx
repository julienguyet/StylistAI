"use client";

import { useState } from "react";
import { useStore } from "@/lib/store-context";

export function AddToCartButton({ articleId }: { articleId: string }) {
  const { addToCart, customerId } = useStore();
  const [state, setState] = useState<"idle" | "adding" | "added">("idle");

  async function handleClick() {
    setState("adding");
    await addToCart(articleId);
    setState("added");
    setTimeout(() => setState("idle"), 2000);
  }

  return (
    <button
      onClick={handleClick}
      disabled={!customerId || state === "adding"}
      className="w-full rounded bg-hm-ink py-3 text-sm font-medium text-white hover:bg-black disabled:opacity-50 sm:w-64"
    >
      {state === "added" ? "Added to cart ✓" : state === "adding" ? "Adding…" : "Add to cart"}
    </button>
  );
}
