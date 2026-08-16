import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct, listProducts } from "@/lib/catalog";
import { ProductImage } from "@/components/ProductImage";
import { ProductCard } from "@/components/ProductCard";
import { AddToCartButton } from "@/components/AddToCartButton";

export const dynamic = "force-dynamic";

export default async function ProductPage({
  params,
}: {
  params: Promise<{ articleId: string }>;
}) {
  const { articleId } = await params;

  let product;
  try {
    product = await getProduct(articleId);
  } catch {
    notFound();
  }

  const related = product.section_name
    ? await listProducts({ section_name: product.section_name, limit: 4 }).catch(() => null)
    : null;

  return (
    // Extra bottom padding clears the sticky price bar as well as the nav.
    <div className="space-y-8 pb-20">
      {/* Full-bleed image: it breaks out of the page padding so the product
          fills the width of the phone, the way a native shopping app does. */}
      <div className="-mx-4 aspect-[3/4] overflow-hidden bg-neutral-100">
        <ProductImage
          articleId={product.article_id}
          alt={product.prod_name ?? "Product"}
          className="h-full w-full"
        />
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-hm-muted">
            {product.index_name} · {product.section_name}
          </p>
          <h1 className="mt-1.5 text-xl font-semibold leading-snug">{product.prod_name}</h1>
          <p className="mt-1 text-sm text-hm-muted">{product.product_type_name}</p>
        </div>

        {product.detail_desc && (
          <p className="text-sm leading-relaxed text-hm-ink">{product.detail_desc}</p>
        )}

        <dl className="space-y-1.5 border-t border-hm-line pt-4 text-xs text-hm-muted">
          <div className="flex justify-between">
            <dt>Article</dt>
            <dd className="font-mono">{product.article_id}</dd>
          </div>
          <div className="flex justify-between">
            <dt>Department</dt>
            <dd>{product.department_name ?? "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt>Group</dt>
            <dd>{product.product_group_name ?? "—"}</dd>
          </div>
        </dl>
      </div>

      {related && related.items.length > 0 && (
        <section>
          <h2 className="mb-3 text-base font-semibold">
            More from {product.section_name}
          </h2>
          {/* Horizontal rail rather than a grid: keeps the related items one
              swipe away instead of another screen of scrolling. */}
          <div className="-mx-4 overflow-x-auto no-scrollbar">
            <div className="flex w-max gap-3 px-4">
              {related.items
                .filter((item) => item.article_id !== product.article_id)
                .map((item) => (
                  <div key={item.article_id} className="w-36 shrink-0">
                    <ProductCard product={item} />
                  </div>
                ))}
            </div>
          </div>
        </section>
      )}

      <Link href="/catalog" className="inline-block text-sm text-hm-muted">
        ← Back to catalog
      </Link>

      <AddToCartButton
        articleId={product.article_id}
        price={product.price}
        currency={product.currency}
      />
    </div>
  );
}
