"use client";

import { useChat } from "@/lib/chat-context";

/**
 * Lets server-rendered pages open the chat sheet without becoming client
 * components themselves.
 */
export function AskBjornButton({ className = "" }: { className?: string }) {
  const { open } = useChat();

  return (
    <button onClick={open} className={className}>
      Ask Björn
    </button>
  );
}
