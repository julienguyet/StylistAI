import Link from "next/link";
import { formatPrice } from "@/lib/format";
import type { ProductSummary } from "@/lib/types";
import { ProductImage } from "./ProductImage";

export function ProductCard({ product }: { product: ProductSummary }) {
  return (
    <Link
      href={`/product/${product.article_id}`}
      className="group block focus:outline-none focus:ring-2 focus:ring-hm-red"
    >
      <div className="aspect-[2/3] w-full overflow-hidden bg-neutral-100">
        <ProductImage
          articleId={product.article_id}
          alt={product.prod_name ?? "Product"}
          className="h-full w-full transition-transform duration-300 group-hover:scale-105"
        />
      </div>
      <div className="mt-2 space-y-0.5">
        <p className="truncate text-sm font-medium">{product.prod_name}</p>
        <p className="truncate text-xs text-hm-muted">{product.product_type_name}</p>
        <p className="text-sm">{formatPrice(product.price, product.currency)}</p>
      </div>
    </Link>
  );
}
