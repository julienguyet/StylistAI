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
      <div className="py-16 text-center">
        <h1 className="text-2xl font-semibold">Your cart is empty</h1>
        <p className="mt-2 text-sm text-hm-muted">
          Browse the catalog, or ask Björn for a recommendation.
        </p>
        <Link
          href="/catalog"
          className="mt-6 inline-block rounded bg-hm-red px-6 py-3 text-sm font-medium text-white hover:bg-red-700"
        >
          Start shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">
          Your cart
          <span className="ml-2 text-sm font-normal text-hm-muted">
            ({cart.item_count} {cart.item_count === 1 ? "item" : "items"})
          </span>
        </h1>
        <button
          onClick={() => void emptyCart()}
          className="text-sm text-hm-muted underline hover:text-hm-red"
        >
          Empty cart
        </button>
      </div>

      <ul className="divide-y divide-hm-line border-y border-hm-line">
        {cart.items.map((item) => (
          <li key={item.article_id} className="flex gap-4 py-4">
            <Link href={`/product/${item.article_id}`} className="shrink-0">
              <ProductImage
                articleId={item.article_id}
                alt={item.prod_name ?? "Product"}
                className="h-32 w-24 bg-neutral-100"
              />
            </Link>

            <div className="flex flex-1 flex-col justify-between">
              <div>
                <Link
                  href={`/product/${item.article_id}`}
                  className="text-sm font-medium hover:text-hm-red"
                >
                  {item.prod_name ?? `Article ${item.article_id}`}
                </Link>
                <p className="text-xs text-hm-muted">{item.product_type_name}</p>
                <p className="mt-1 text-sm">
                  {formatPrice(item.price, cart.currency)}
                </p>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex items-center rounded border border-hm-line">
                  <button
                    onClick={() => void setQuantity(item.article_id, item.quantity - 1)}
                    className="px-3 py-1 text-sm hover:bg-neutral-100"
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span className="w-8 text-center text-sm">{item.quantity}</span>
                  <button
                    onClick={() => void setQuantity(item.article_id, item.quantity + 1)}
                    className="px-3 py-1 text-sm hover:bg-neutral-100"
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
                <button
                  onClick={() => void removeFromCart(item.article_id)}
                  className="text-xs text-hm-muted underline hover:text-hm-red"
                >
                  Remove
                </button>
              </div>
            </div>

            <p className="text-sm font-medium">
              {formatPrice(item.line_total, cart.currency)}
            </p>
          </li>
        ))}
      </ul>

      <div className="flex justify-end">
        <div className="w-full sm:w-80">
          <div className="flex justify-between border-b border-hm-line py-3">
            <span className="text-sm text-hm-muted">Subtotal</span>
            <span className="text-sm font-medium">
              {formatPrice(cart.subtotal, cart.currency)}
            </span>
          </div>
          <button className="mt-4 w-full rounded bg-hm-red py-3 text-sm font-medium text-white hover:bg-red-700">
            Checkout
          </button>
          <p className="mt-2 text-center text-xs text-hm-muted">
            Demo only — checkout is not wired up.
          </p>
        </div>
      </div>
    </div>
  );
}
