import { NextRequest, NextResponse } from "next/server";
import { sampleCustomers } from "@/lib/catalog";

export async function GET(req: NextRequest) {
  const n = Number(req.nextUrl.searchParams.get("n") ?? 8);
  try {
    return NextResponse.json(await sampleCustomers(n));
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 502 },
    );
  }
}
