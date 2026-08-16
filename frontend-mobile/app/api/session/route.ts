import { NextRequest, NextResponse } from "next/server";

const ADK_API_URL = process.env.ADK_API_URL ?? "http://localhost:8015";
const ADK_APP_NAME = process.env.ADK_APP_NAME ?? "stylist_agent";

export async function POST(req: NextRequest) {
  const { customerId, sessionId } = await req.json();
  if (!customerId || !sessionId) {
    return NextResponse.json(
      { error: "customerId and sessionId are required" },
      { status: 400 },
    );
  }

  const userId = `u_${customerId.slice(0, 12)}`;
  // Post to the collection endpoint, not /sessions/{id}. The latter is
  // deprecated in ADK and binds the *entire* request body to its `state`
  // argument, so {state: {...}} would land in session state as a nested
  // {state: {...}} and `{customer_id}` in system_prompt.txt would not resolve.
  const url = `${ADK_API_URL}/apps/${ADK_APP_NAME}/users/${userId}/sessions`;

  try {
    // Seeding state here is what lets tools resolve the shopper without the
    // agent having to ask for a 64-char customer id in conversation.
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        state: { customer_id: customerId },
      }),
    });

    // A reused session id is not an error — the state was seeded on creation.
    if (res.status === 409) {
      return NextResponse.json({ sessionId, userId });
    }

    if (!res.ok) {
      return NextResponse.json(
        { error: `Agent session failed (${res.status}): ${await res.text()}` },
        { status: 502 },
      );
    }
    return NextResponse.json({ sessionId, userId });
  } catch (error) {
    return NextResponse.json(
      { error: `Agent unreachable: ${(error as Error).message}` },
      { status: 502 },
    );
  }
}
