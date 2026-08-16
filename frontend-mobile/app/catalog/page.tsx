import Link from "next/link";
import { getFacets, listProducts } from "@/lib/catalog";
import { ProductCard } from "@/components/ProductCard";

export const dynamic = "force-dynamic";

// Smaller page than desktop: 18 cards is 9 rows of two, which is about as far
// as anyone thumbs before wanting a page break.
const PAGE_SIZE = 18;

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
    return <p className="text-sm text-hm-red">Could not reach the catalog API — {error}</p>;
  }

  const lastPage = Math.max(1, Math.ceil(result.total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">
          {params.ids ? "Björn's picks" : "Catalog"}
        </h1>
        <p className="text-xs text-hm-muted">{result.total.toLocaleString()} products</p>
      </div>

      {/* Full-width search: on a phone the field and its button stack badly
          side by side, so the button becomes an icon-sized square instead. */}
      <form className="flex gap-2" action="/catalog">
        <input
          name="q"
          defaultValue={params.q ?? ""}
          placeholder="Search products…"
          // 16px minimum keeps iOS Safari from zooming the page on focus.
          className="flex-1 rounded-full border border-hm-line px-4 py-2.5 text-base focus:border-hm-ink focus:outline-none"
        />
        <button
          className="rounded-full bg-hm-ink px-5 text-sm text-white"
          aria-label="Search"
        >
          Go
        </button>
      </form>

      {!params.ids && (
        // Chips scroll sideways rather than wrapping into four rows that would
        // push the products off screen. Negative margin lets them bleed to the
        // screen edge so it reads as a scrollable rail.
        <div className="-mx-4 overflow-x-auto no-scrollbar">
          <div className="flex w-max gap-2 px-4">
            <Link
              href={buildHref(params, { product_group_name: "", page: "" })}
              className={`whitespace-nowrap rounded-full border px-3.5 py-1.5 text-xs ${
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
                className={`whitespace-nowrap rounded-full border px-3.5 py-1.5 text-xs ${
                  params.product_group_name === group
                    ? "border-hm-ink bg-hm-ink text-white"
                    : "border-hm-line"
                }`}
              >
                {group}
              </Link>
            ))}
          </div>
        </div>
      )}

      {result.items.length === 0 ? (
        <p className="py-16 text-center text-sm text-hm-muted">No products matched.</p>
      ) : (
        <div className="grid grid-cols-2 gap-x-3 gap-y-6">
          {result.items.map((product) => (
            <ProductCard key={product.article_id} product={product} />
          ))}
        </div>
      )}

      {!params.ids && lastPage > 1 && (
        <div className="flex items-center justify-between gap-3 pt-2 text-sm">
          {page > 1 ? (
            <Link
              href={buildHref(params, { page: String(page - 1) })}
              className="rounded-full border border-hm-line px-4 py-2"
            >
              Previous
            </Link>
          ) : (
            <span />
          )}
          <span className="text-xs text-hm-muted">
            {page} / {lastPage.toLocaleString()}
          </span>
          {page < lastPage ? (
            <Link
              href={buildHref(params, { page: String(page + 1) })}
              className="rounded-full border border-hm-line px-4 py-2"
            >
              Next
            </Link>
          ) : (
            <span />
          )}
        </div>
      )}
    </div>
  );
}
