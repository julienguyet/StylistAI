import Link from "next/link";
import { listProducts } from "@/lib/catalog";
import { ProductCard } from "@/components/ProductCard";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let trending: Awaited<ReturnType<typeof listProducts>>["items"] = [];
  let error: string | null = null;

  try {
    const page = await listProducts({ index_name: "Ladieswear", limit: 8, offset: 40 });
    trending = page.items;
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <div className="space-y-12">
      <section className="rounded-lg bg-neutral-100 px-8 py-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Shop by talking, not clicking
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-hm-muted">
          Ask Björn for a recommendation and watch the store navigate itself — straight
          to the product, straight into your cart.
        </p>
        <Link
          href="/catalog"
          className="mt-8 inline-block rounded bg-hm-red px-6 py-3 text-sm font-medium text-white hover:bg-red-700"
        >
          Browse the catalog
        </Link>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Trending now</h2>
        {error ? (
          <p className="text-sm text-hm-red">
            Could not reach the catalog API — {error}
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
            {trending.map((product) => (
              <ProductCard key={product.article_id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
