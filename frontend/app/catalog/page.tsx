import Link from "next/link";
import { getFacets, listProducts } from "@/lib/catalog";
import { ProductCard } from "@/components/ProductCard";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 24;

type SearchParams = {
  q?: string;
  product_group_name?: string;
  index_name?: string;
  ids?: string;
  page?: string;
};

function buildHref(params: SearchParams, overrides: Partial<SearchParams>): string {
  const merged = { ...params, ...overrides };
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(merged)) {
    if (value) search.set(key, value);
  }
  const qs = search.toString();
  return qs ? `/catalog?${qs}` : "/catalog";
}

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? 1));

  let result;
  let facets;
  let error: string | null = null;

  try {
    [result, facets] = await Promise.all([
      listProducts({
        q: params.q,
        product_group_name: params.product_group_name,
        index_name: params.index_name,
        article_ids: params.ids,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
      getFacets(),
    ]);
  } catch (e) {
    error = (e as Error).message;
  }

  if (error || !result || !facets) {
    return (
      <p className="text-sm text-hm-red">Could not reach the catalog API — {error}</p>
    );
  }

  const lastPage = Math.max(1, Math.ceil(result.total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {params.ids ? "Björn's picks" : "Catalog"}
          </h1>
          <p className="text-sm text-hm-muted">
            {result.total.toLocaleString()} products
          </p>
        </div>

        <form className="flex gap-2" action="/catalog">
          <input
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search products…"
            className="rounded border border-hm-line px-3 py-2 text-sm focus:border-hm-ink focus:outline-none"
          />
          <button className="rounded bg-hm-ink px-4 py-2 text-sm text-white">
            Search
          </button>
        </form>
      </div>

      {!params.ids && (
        <div className="flex flex-wrap gap-2">
          <Link
            href={buildHref(params, { product_group_name: "", page: "" })}
            className={`rounded-full border px-3 py-1 text-xs ${
              params.product_group_name
                ? "border-hm-line"
                : "border-hm-ink bg-hm-ink text-white"
            }`}
          >
            All
          </Link>
          {facets.product_group_name.map((group) => (
            <Link
              key={group}
              href={buildHref(params, { product_group_name: group, page: "" })}
              className={`rounded-full border px-3 py-1 text-xs ${
                params.product_group_name === group
                  ? "border-hm-ink bg-hm-ink text-white"
                  : "border-hm-line hover:border-hm-ink"
              }`}
            >
              {group}
            </Link>
          ))}
        </div>
      )}

      {result.items.length === 0 ? (
        <p className="py-16 text-center text-sm text-hm-muted">
          No products matched.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
          {result.items.map((product) => (
            <ProductCard key={product.article_id} product={product} />
          ))}
        </div>
      )}

      {!params.ids && lastPage > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4 text-sm">
          {page > 1 && (
            <Link
              href={buildHref(params, { page: String(page - 1) })}
              className="rounded border border-hm-line px-4 py-2 hover:border-hm-ink"
            >
              Previous
            </Link>
          )}
          <span className="text-hm-muted">
            Page {page} of {lastPage.toLocaleString()}
          </span>
          {page < lastPage && (
            <Link
              href={buildHref(params, { page: String(page + 1) })}
              className="rounded border border-hm-line px-4 py-2 hover:border-hm-ink"
            >
              Next
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
