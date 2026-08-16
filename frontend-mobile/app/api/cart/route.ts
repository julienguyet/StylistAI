import { NextRequest, NextResponse } from "next/server";
import {
  addCartItem,
  clearCart,
  getCart,
  removeCartItem,
  updateCartItem,
} from "@/lib/catalog";

function customerIdFrom(req: NextRequest): string | null {
  return (
    req.nextUrl.searchParams.get("customer_id") ??
    req.cookies.get("stylistai_customer_id")?.value ??
    null
  );
}

function proxy<T>(work: () => Promise<T>) {
  return work()
    .then((data) => NextResponse.json(data))
    .catch((error: Error) =>
      NextResponse.json({ error: error.message }, { status: 502 }),
    );
}

export async function GET(req: NextRequest) {
  const customerId = customerIdFrom(req);
  if (!customerId) return NextResponse.json({ error: "No customer selected" }, { status: 400 });
  return proxy(() => getCart(customerId));
}

export async function POST(req: NextRequest) {
  const customerId = customerIdFrom(req);
  if (!customerId) return NextResponse.json({ error: "No customer selected" }, { status: 400 });
  const body = await req.json();
  return proxy(() => addCartItem(customerId, body.article_id, body.quantity ?? 1));
}

export async function PATCH(req: NextRequest) {
  const customerId = customerIdFrom(req);
  if (!customerId) return NextResponse.json({ error: "No customer selected" }, { status: 400 });
  const body = await req.json();
  return proxy(() => updateCartItem(customerId, body.article_id, body.quantity));
}

export async function DELETE(req: NextRequest) {
  const customerId = customerIdFrom(req);
  if (!customerId) return NextResponse.json({ error: "No customer selected" }, { status: 400 });
  const articleId = req.nextUrl.searchParams.get("article_id");
  return proxy(() =>
    articleId ? removeCartItem(customerId, articleId) : clearCart(customerId),
  );
}
