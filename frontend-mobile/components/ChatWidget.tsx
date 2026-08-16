"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "@/lib/store-context";
import { useChat } from "@/lib/chat-context";
import type { UiAction } from "@/lib/types";

type Message = { role: "user" | "assistant"; text: string };

const SUGGESTIONS = [
  "Recommend me a product",
  "Show me a summer dress",
  "Where is the closest H&M store to me?",
];

/**
 * Björn replies in markdown, so the bubbles have to render it rather than
 * print the asterisks. Tailwind's preflight strips list bullets and heading
 * sizes, so every block element needs its styling restated here.
 *
 * Raw HTML is deliberately NOT enabled (no rehype-raw): message text is model
 * output that can quote tool results, so it must never reach the DOM as markup.
 */
const markdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => (
    <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-snug">{children}</li>,
  h1: ({ children }) => <p className="mb-1 mt-3 font-semibold first:mt-0">{children}</p>,
  h2: ({ children }) => <p className="mb-1 mt-3 font-semibold first:mt-0">{children}</p>,
  h3: ({ children }) => <p className="mb-1 mt-3 font-semibold first:mt-0">{children}</p>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2 hover:text-hm-red"
    >
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="rounded bg-black/5 px-1 py-0.5 font-mono text-[0.85em]">
      {children}
    </code>
  ),
  // Reset the nested <code> styling so fenced blocks get one background, not two.
  pre: ({ children }) => (
    <pre className="mb-2 overflow-x-auto rounded bg-black/5 p-2 text-xs last:mb-0 [&_code]:bg-transparent [&_code]:p-0">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mb-2 border-l-2 border-hm-line pl-3 text-hm-muted last:mb-0">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-hm-line" />,
  table: ({ children }) => (
    <div className="mb-2 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-hm-line px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => <td className="border border-hm-line px-2 py-1">{children}</td>,
};

export function ChatWidget() {
  const router = useRouter();
  const { customerId, refreshCart } = useStore();
  const { isOpen, close } = useChat();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, busy, isOpen]);

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionId) return sessionId;
    if (!customerId) return null;

    const id = `s_${Math.random().toString(36).slice(2, 10)}`;
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customerId, sessionId: id }),
    });
    if (!res.ok) {
      const { error } = await res.json().catch(() => ({ error: "Session failed" }));
      setMessages((m) => [...m, { role: "assistant", text: `⚠️ ${error}` }]);
      return null;
    }
    setSessionId(id);
    return id;
  }, [sessionId, customerId]);

  const applyUiActions = useCallback(
    async (actions: UiAction[]) => {
      for (const action of actions) {
        if (action.type === "navigate" && action.path.startsWith("/")) {
          router.push(action.path);
          // On a phone the sheet covers the whole screen, so a navigation the
          // customer cannot see is a navigation that did not happen. Drop the
          // sheet and let them look at what Björn opened.
          close();
        } else if (action.type === "cart_updated") {
          // No close here: the badge behind the sheet updates on its own, and
          // yanking the chat away mid-conversation would break the flow.
          await refreshCart();
        } else if (action.type === "show_products" && action.article_ids.length) {
          router.push(`/catalog?ids=${action.article_ids.join(",")}`);
          close();
        }
      }
    },
    [router, refreshCart, close],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || busy) return;

      setInput("");
      setMessages((m) => [...m, { role: "user", text: trimmed }]);
      setBusy(true);

      try {
        const activeSession = await ensureSession();
        if (!activeSession) return;

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            customerId,
            sessionId: activeSession,
            message: trimmed,
          }),
        });
        const data = await res.json();

        if (!res.ok) {
          setMessages((m) => [
            ...m,
            { role: "assistant", text: `⚠️ ${data.error ?? "Something went wrong."}` },
          ]);
          return;
        }

        setMessages((m) => [...m, { role: "assistant", text: data.text }]);
        await applyUiActions(data.uiActions ?? []);
      } catch (error) {
        setMessages((m) => [
          ...m,
          { role: "assistant", text: `⚠️ ${(error as Error).message}` },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [busy, customerId, ensureSession, applyUiActions],
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop covers the viewport, not just the column, so the page behind
          is dimmed edge to edge on a wide screen. */}
      <button
        aria-label="Close chat"
        onClick={close}
        className="fixed inset-0 z-40 bg-black/40"
      />

      <section className="fixed bottom-0 left-1/2 z-50 flex h-[88vh] w-full max-w-[520px] -translate-x-1/2 flex-col rounded-t-2xl bg-white shadow-2xl">
        {/* Grab handle: signals "drag/tap to dismiss" the way a native sheet does. */}
        <div className="flex justify-center pt-2">
          <span className="h-1 w-10 rounded-full bg-neutral-300" />
        </div>

        <div className="flex items-center justify-between border-b border-hm-line px-4 py-3">
          <div>
            <p className="text-sm font-semibold">Björn</p>
            <p className="text-xs text-hm-muted">Your AI stylist</p>
          </div>
          <button
            onClick={close}
            className="-mr-2 px-2 py-1 text-xl leading-none text-hm-muted"
            aria-label="Close chat"
          >
            ✕
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-hm-muted">
                Hi! Ask me for a recommendation and I&apos;ll open the product for you.
              </p>
              <div className="flex flex-col gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => void send(s)}
                    className="rounded-full border border-hm-line px-4 py-2.5 text-left text-sm active:bg-neutral-100"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, i) => (
            <div
              key={i}
              className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              {message.role === "user" ? (
                // What the customer typed is plain text — render it verbatim so
                // an asterisk or underscore stays an asterisk or underscore.
                <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-hm-ink px-3.5 py-2 text-sm text-white">
                  {message.text}
                </p>
              ) : (
                <div className="max-w-[90%] rounded-2xl bg-neutral-100 px-3.5 py-2 text-sm text-hm-ink">
                  <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {message.text}
                  </Markdown>
                </div>
              )}
            </div>
          ))}

          {busy && <p className="text-xs text-hm-muted">Björn is thinking…</p>}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
          className="flex gap-2 border-t border-hm-line px-3 pb-[calc(0.75rem+var(--safe-bottom))] pt-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask for a recommendation…"
            // text-base is deliberate: iOS Safari zooms the whole page when a
            // focused input renders below 16px.
            className="flex-1 rounded-full border border-hm-line px-4 py-2.5 text-base focus:border-hm-ink focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-full bg-hm-red px-5 text-sm font-medium text-white disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </section>
    </>
  );
}
