import Link from "next/link";
import { listProducts } from "@/lib/catalog";
import { ProductCard } from "@/components/ProductCard";
import { AskBjornButton } from "@/components/AskBjornButton";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let trending: Awaited<ReturnType<typeof listProducts>>["items"] = [];
  let error: string | null = null;

  try {
    const page = await listProducts({ index_name: "Ladieswear", limit: 6, offset: 40 });
    trending = page.items;
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <div className="space-y-8">
      {/* Compact hero: on a phone the fold is expensive, so the trending rail
          has to start above it rather than sit under a full-height banner. */}
      <section className="rounded-2xl bg-neutral-100 px-5 py-8 text-center">
        <h1 className="text-2xl font-bold leading-tight tracking-tight">
          Shop by talking,
          <br />
          not clicking
        </h1>
        <p className="mx-auto mt-3 text-sm text-hm-muted">
          Ask Björn for a recommendation and watch the store navigate itself.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <AskBjornButton className="w-full rounded-full bg-hm-red py-3 text-sm font-medium text-white active:bg-red-700" />
          <Link
            href="/catalog"
            className="w-full rounded-full border border-hm-ink py-3 text-sm font-medium active:bg-neutral-200"
          >
            Browse the catalog
          </Link>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold">Trending now</h2>
        {error ? (
          <p className="text-sm text-hm-red">Could not reach the catalog API — {error}</p>
        ) : (
          <div className="grid grid-cols-2 gap-x-3 gap-y-6">
            {trending.map((product) => (
              <ProductCard key={product.article_id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
