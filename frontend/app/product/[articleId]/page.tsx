import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct, listProducts } from "@/lib/catalog";
import { formatPrice } from "@/lib/format";
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
    ? await listProducts({ section_name: product.section_name, limit: 4 }).catch(
        () => null,
      )
    : null;

  return (
    <div className="space-y-16">
      <div className="grid gap-8 md:grid-cols-2">
        <div className="aspect-[2/3] w-full overflow-hidden bg-neutral-100">
          <ProductImage
            articleId={product.article_id}
            alt={product.prod_name ?? "Product"}
            className="h-full w-full"
          />
        </div>

        <div className="space-y-6">
          <div>
            <p className="text-xs uppercase tracking-wide text-hm-muted">
              {product.index_name} · {product.section_name}
            </p>
            <h1 className="mt-2 text-3xl font-semibold">{product.prod_name}</h1>
            <p className="mt-1 text-sm text-hm-muted">{product.product_type_name}</p>
            <p className="mt-4 text-2xl">
              {formatPrice(product.price, product.currency)}
            </p>
          </div>

          {product.detail_desc && (
            <p className="text-sm leading-relaxed text-hm-ink">{product.detail_desc}</p>
          )}

          <AddToCartButton articleId={product.article_id} />

          <dl className="space-y-1 border-t border-hm-line pt-4 text-xs text-hm-muted">
            <div className="flex gap-2">
              <dt>Article</dt>
              <dd className="font-mono">{product.article_id}</dd>
            </div>
            <div className="flex gap-2">
              <dt>Department</dt>
              <dd>{product.department_name ?? "—"}</dd>
            </div>
            <div className="flex gap-2">
              <dt>Group</dt>
              <dd>{product.product_group_name ?? "—"}</dd>
            </div>
          </dl>
        </div>
      </div>

      {related && related.items.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold">More from {product.section_name}</h2>
          <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-4">
            {related.items
              .filter((item) => item.article_id !== product.article_id)
              .map((item) => (
                <ProductCard key={item.article_id} product={item} />
              ))}
          </div>
        </section>
      )}

      <Link href="/catalog" className="inline-block text-sm text-hm-muted hover:text-hm-ink">
        ← Back to catalog
      </Link>
    </div>
  );
}
