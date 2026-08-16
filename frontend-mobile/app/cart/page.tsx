"use client";

import Link from "next/link";
import { formatPrice } from "@/lib/format";
import { useStore } from "@/lib/store-context";
import { ProductImage } from "@/components/ProductImage";

export default function CartPage() {
  const { cart, setQuantity, removeFromCart, emptyCart, ready, customerId } = useStore();

  if (!ready || (customerId && !cart)) {
    return <p className="text-sm text-hm-muted">Loading your cart…</p>;
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="py-20 text-center">
        <h1 className="text-xl font-semibold">Your cart is empty</h1>
        <p className="mt-2 text-sm text-hm-muted">
          Browse the catalog, or ask Björn for a recommendation.
        </p>
        <Link
          href="/catalog"
          className="mt-6 inline-block rounded-full bg-hm-red px-6 py-3 text-sm font-medium text-white"
        >
          Start shopping
        </Link>
      </div>
    );
  }

  return (
    // Padding clears the sticky subtotal bar as well as the nav.
    <div className="space-y-5 pb-32">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">
          Your cart
          <span className="ml-2 text-sm font-normal text-hm-muted">
            ({cart.item_count})
          </span>
        </h1>
        <button
          onClick={() => void emptyCart()}
          className="text-xs text-hm-muted underline"
        >
          Empty cart
        </button>
      </div>

      <ul className="divide-y divide-hm-line border-y border-hm-line">
        {cart.items.map((item) => (
          <li key={item.article_id} className="flex gap-3 py-3">
            <Link href={`/product/${item.article_id}`} className="shrink-0">
              <ProductImage
                articleId={item.article_id}
                alt={item.prod_name ?? "Product"}
                className="h-28 w-20 bg-neutral-100"
              />
            </Link>

            <div className="flex min-w-0 flex-1 flex-col justify-between">
              <div className="min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    href={`/product/${item.article_id}`}
                    className="truncate text-sm font-medium"
                  >
                    {item.prod_name ?? `Article ${item.article_id}`}
                  </Link>
                  {/* Line total moves up beside the name: on a narrow screen a
                      third column would squeeze the title to a few characters. */}
                  <span className="shrink-0 text-sm font-medium">
                    {formatPrice(item.line_total, cart.currency)}
                  </span>
                </div>
                <p className="truncate text-xs text-hm-muted">{item.product_type_name}</p>
                <p className="mt-0.5 text-xs text-hm-muted">
                  {formatPrice(item.price, cart.currency)} each
                </p>
              </div>

              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center rounded-full border border-hm-line">
                  <button
                    onClick={() => void setQuantity(item.article_id, item.quantity - 1)}
                    // 44px targets: anything smaller is a miss on a real thumb.
                    className="h-9 w-11 text-base active:bg-neutral-100"
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span className="w-6 text-center text-sm">{item.quantity}</span>
                  <button
                    onClick={() => void setQuantity(item.article_id, item.quantity + 1)}
                    className="h-9 w-11 text-base active:bg-neutral-100"
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
                <button
                  onClick={() => void removeFromCart(item.article_id)}
                  className="text-xs text-hm-muted underline"
                >
                  Remove
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="fixed bottom-[calc(3.5rem+var(--safe-bottom))] left-1/2 z-20 w-full max-w-phone -translate-x-1/2 border-t border-hm-line bg-white/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between pb-2">
          <span className="text-sm text-hm-muted">Subtotal</span>
          <span className="text-base font-semibold">
            {formatPrice(cart.subtotal, cart.currency)}
          </span>
        </div>
        <button className="w-full rounded-full bg-hm-red py-3 text-sm font-medium text-white">
          Checkout
        </button>
        <p className="mt-1.5 text-center text-[11px] text-hm-muted">
          Demo only — checkout is not wired up.
        </p>
      </div>
    </div>
  );
}
