import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <h1 className="text-2xl font-semibold">Product not found</h1>
      <p className="mt-2 text-sm text-hm-muted">
        That article isn&apos;t in the catalog.
      </p>
      <Link
        href="/catalog"
        className="mt-6 inline-block rounded bg-hm-ink px-6 py-3 text-sm text-white"
      >
        Back to catalog
      </Link>
    </div>
  );
}
