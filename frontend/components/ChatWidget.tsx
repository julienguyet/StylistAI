"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "@/lib/store-context";
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
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  /**
   * Scrolling to the bottom drops the reader at the *end* of a long reply,
   * which then has to be scrolled back up to be read at all. Pin the top of a
   * new assistant message to the top of the scroll area instead, so it starts
   * on its first line. User messages still go to the bottom, which is where
   * the eye expects your own message to land.
   */
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const target = lastMessageRef.current;
    const lastIsAssistant = messages[messages.length - 1]?.role === "assistant";

    if (lastIsAssistant && target) {
      // getBoundingClientRect rather than offsetTop: the bubble's offsetParent
      // is not guaranteed to be the scroll container.
      const delta =
        target.getBoundingClientRect().top - container.getBoundingClientRect().top;
      // scrollTop clamps itself, so a reply too short to reach the top simply
      // settles at the bottom with the whole message visible anyway.
      container.scrollTo({ top: container.scrollTop + delta - 8, behavior: "smooth" });
    } else {
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    }
  }, [messages, busy]);

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
        } else if (action.type === "cart_updated") {
          await refreshCart();
        } else if (action.type === "show_products" && action.article_ids.length) {
          router.push(`/catalog?ids=${action.article_ids.join(",")}`);
        }
      }
    },
    [router, refreshCart],
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

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-hm-red px-5 py-3 text-sm font-medium text-white shadow-lg hover:bg-red-700"
      >
        Ask Björn
      </button>
    );
  }

  return (
    // Width steps up with the viewport so a desktop screen recording gets a
    // panel that reads clearly on LinkedIn, without covering the product page
    // on smaller laptops.
    <aside className="fixed bottom-0 right-0 z-40 flex h-[70vh] w-full flex-col border-l border-t border-hm-line bg-white shadow-2xl sm:bottom-6 sm:right-6 sm:h-[620px] sm:w-[440px] sm:rounded-lg sm:border md:w-[520px] lg:w-[620px]">
      <div className="flex items-center justify-between border-b border-hm-line px-4 py-3">
        <div>
          <p className="text-sm font-semibold">Björn</p>
          <p className="text-xs text-hm-muted">Your AI stylist</p>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="text-hm-muted hover:text-hm-ink"
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
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="rounded-full border border-hm-line px-3 py-1 text-xs hover:border-hm-ink"
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
            ref={i === messages.length - 1 ? lastMessageRef : undefined}
            className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            {message.role === "user" ? (
              // What the customer typed is plain text — render it verbatim so
              // an asterisk or underscore stays an asterisk or underscore.
              <p className="max-w-[85%] whitespace-pre-wrap rounded-lg bg-hm-ink px-3 py-2 text-sm text-white">
                {message.text}
              </p>
            ) : (
              <div className="max-w-[90%] rounded-lg bg-neutral-100 px-3 py-2 text-sm text-hm-ink">
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
        className="flex gap-2 border-t border-hm-line p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask for a recommendation…"
          className="flex-1 rounded border border-hm-line px-3 py-2 text-sm focus:border-hm-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded bg-hm-red px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </aside>
  );
}
