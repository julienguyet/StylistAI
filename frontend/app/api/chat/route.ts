import { NextRequest, NextResponse } from "next/server";
import { extractAgentText, extractUiActions } from "@/lib/ui-actions";

const ADK_API_URL = process.env.ADK_API_URL ?? "http://localhost:8015";
const ADK_APP_NAME = process.env.ADK_APP_NAME ?? "stylist_agent";

export const maxDuration = 120;

export async function POST(req: NextRequest) {
  const { customerId, sessionId, message } = await req.json();
  if (!customerId || !sessionId || !message) {
    return NextResponse.json(
      { error: "customerId, sessionId and message are required" },
      { status: 400 },
    );
  }

  const payload = {
    appName: ADK_APP_NAME,
    userId: `u_${customerId.slice(0, 12)}`,
    sessionId,
    newMessage: { role: "user", parts: [{ text: message }] },
  };

  try {
    const res = await fetch(`${ADK_API_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(115_000),
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Agent error (${res.status}): ${await res.text()}` },
        { status: 502 },
      );
    }

    const events = await res.json();
    return NextResponse.json({
      text: extractAgentText(events) || "_(no reply from the stylist)_",
      uiActions: extractUiActions(events),
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Agent unreachable: ${(error as Error).message}` },
      { status: 502 },
    );
  }
}
