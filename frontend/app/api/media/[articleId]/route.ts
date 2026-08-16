import { NextRequest } from "next/server";
import { CATALOG_API_URL } from "@/lib/catalog";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ articleId: string }> },
) {
  const { articleId: raw } = await params;
  const articleId = encodeURIComponent(raw);
  const upstream = await fetch(`${CATALOG_API_URL}/products/${articleId}/image`);

  if (!upstream.ok || !upstream.body) {
    return new Response(null, { status: 404 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "image/jpeg",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
