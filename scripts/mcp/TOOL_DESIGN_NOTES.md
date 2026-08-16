# MCP Tool Design Notes — Storefront Control

The storefront (`/workspace/frontend`) and the Catalog & Cart API
(`/workspace/scripts/catalog_api`) are built and verified. The tools that let Björn
*drive* that storefront are deliberately left for you to design.

This document is the reference material you need: what the API can do, the one contract
the frontend enforces, and the decisions worth thinking through. It intentionally does
not give you tool names, signatures, or finished code.

---

## 1. What already exists

```
Browser ──► Next.js storefront :3000 ──► Catalog & Cart API :8002 ──► Mongo
   │                  ▲
   │ chat             │ ui_action (navigate / refresh cart)
   ▼                  │
ADK agent :8015 ──► MCP server :8001 ──┘
                         │
                         └──► Recommender API :8000  (already wired: `recommender_tool`)
```

Today `recommender_tool` returns article IDs as text. The customer then has to find the
product themselves. Your new tools close that loop.

## 2. Catalog & Cart API reference

Base URL from inside the Docker network: `http://stylistai-catalog:8002`
(follow the pattern of the existing `RECOMMENDER_URL` constant in `main.py`).

Interactive docs are available at `http://localhost:8002/docs` once the service runs.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/products` | Query: `q`, `product_group_name`, `section_name`, `index_name`, `article_ids` (comma-separated, preserves order), `limit` (≤100), `offset`. Returns `{items, total, limit, offset}` |
| `GET` | `/products/{article_id}` | Full product. `404` if unknown |
| `GET` | `/products/{article_id}/image` | JPEG bytes |
| `GET` | `/products/facets` | Distinct `product_group_name` / `section_name` / `index_name` — useful for validating a filter before querying |
| `GET` | `/customers/sample?n=&min_purchases=` | Random demo profiles |
| `GET` | `/cart/{customer_id}` | Current cart |
| `POST` | `/cart/{customer_id}/items` | Body `{article_id, quantity}`. Adding an article already in the cart **increments** it. `404` if the article doesn't exist |
| `PATCH` | `/cart/{customer_id}/items/{article_id}` | Body `{quantity}`. `0` removes the line. `404` if not in cart |
| `DELETE` | `/cart/{customer_id}/items/{article_id}` | Remove one line |
| `DELETE` | `/cart/{customer_id}` | Empty the cart |

Every cart endpoint returns the **whole cart** after the change:

```json
{"customer_id": "...", "items": [{"article_id": "108775015", "quantity": 2,
  "prod_name": "Strap top", "price": 31.94, "line_total": 63.88,
  "image_url": "/products/108775015/image"}],
 "item_count": 2, "subtotal": 63.88, "currency": "EUR", "updated_at": "..."}
```

**Article ID formats are interchangeable.** `"0108775015"`, `"108775015"` and `108775015`
all resolve to the same product, so you do not need to normalise what the recommender or
the vector search hands you.

**Prices are synthetic.** The H&M dataset has no price column; the API derives a stable
per-article value (see `catalog_api/pricing.py`). Fine for a demo — just don't present it
as real H&M pricing.

## 3. The `ui_action` contract — the one thing that is fixed

The frontend inspects **every** MCP tool response for a key named `ui_action`. Anything
it finds, it executes. This is what makes the store navigate itself.

Three action shapes are understood (`frontend/lib/types.ts`):

```jsonc
{"ui_action": {"type": "navigate", "path": "/product/108775015"}}  // route the browser
{"ui_action": {"type": "cart_updated"}}                            // refetch cart + badge
{"ui_action": {"type": "show_products", "article_ids": ["1087750
15", "110065001"]}}                                                // grid of specific items
```

Rules that are already enforced for you:

- **Nesting doesn't matter.** The extractor walks the whole ADK event payload, parses
  JSON-encoded strings along the way, and collects any `ui_action` it finds — so it works
  whether FastMCP returns your dict directly, wraps it under `result`, or serialises it
  into a text content block.
- `navigate` paths must start with `/`; anything else is ignored (open-redirect guard).
- Unknown `type` values are ignored rather than throwing.
- You may return a **list** under `ui_action` to trigger several actions at once.
- Returning no `ui_action` is always safe — the tool just behaves like a normal one.

Valid routes to navigate to: `/`, `/catalog`, `/catalog?q=…`, `/product/{article_id}`,
`/cart`.

After changing your tools, check your payload shape still parses:

```bash
cd frontend && npm run verify:ui-actions
```

Add a case to `frontend/scripts/verify-ui-actions.ts` matching the exact JSON your tool
returns — that file is where the contract is pinned down.

## 4. Decisions to make

These are genuinely open. There's a defensible answer either way; think about which fits
the conversation you want Björn to have.

**Granularity.** Does one tool both fetch a product *and* navigate to it, or is navigation
its own tool the model calls deliberately? Bundling means fewer round trips and the model
can't "forget" to navigate; separating means the model can look something up without
yanking the customer's screen around mid-sentence.

**Where `customer_id` comes from.** The frontend seeds ADK session state with
`{"customer_id": ...}` when the chat session is created, so it is available server-side
without the customer ever typing a 64-character hash. Decide whether to surface it to the
model via a `{customer_id}` placeholder in `system_prompt.txt`, or keep it a tool-side
concern. Consider what happens if the model passes the wrong ID — should the tool trust it?

**Cart semantics.** `POST /items` increments on repeat calls. Is that what you want when a
customer says "add it to my cart" twice — two items, or a correction? What should the tool
return when the article doesn't exist, or the cart API is down? The existing tools in
`main.py` all return `{"error": "..."}` rather than raising; matching that keeps the agent
able to recover and apologise instead of the turn failing.

**Confirmation before mutating.** Adding to someone's cart is a side effect. Should the
tool do it immediately, or should the prompt require Björn to confirm first? Your system
prompt already forbids fabricating stock and addresses — cart writes deserve similar
thought.

**How much to build now.** The core loop the user asked for — *"recommend me a product" →
product page opens → "add it to cart"* — needs surprisingly little: something that turns a
recommendation into a navigation, and something that writes to the cart. Broader browsing
tools (filtered catalog searches, "show me these four side by side" via `show_products`)
are worth adding only once the core loop feels right.

**Prompt work is part of the design.** New tools are invisible to Björn unless
`system_prompt.txt` tells it when to reach for them. The existing "Tool Usage Rules"
section is where that belongs.

## 5. House style in `scripts/mcp/main.py`

Worth matching, since the docstring *is* the instruction the LLM reads:

- Sphinx-style docstrings (`:param:` / `:type:` / `:return:` / `:rtype:`) with a plain-English
  first line saying **when** to use the tool, not just what it does.
- Service URLs as module constants (`RECOMMENDER_URL`, `QDRANT_URL`, …).
- `try/except` returning `{"error": f"..."}` instead of raising.
- `mongo_to_dict()` if you ever return raw Mongo documents (`ObjectId` isn't JSON-serialisable).
- Note `requests` is sync and `search_catalog` is `async` with `httpx` — either works;
  FastMCP handles both.

## 6. Trying it end to end

1. Start Mongo, the catalog API (`:8002`), and the storefront (`:3000`).
2. Add your tools, restart the MCP server (`:8001`), restart the agent (`:8015`).
3. Open `http://localhost:3000`, pick a demo shopper, open the chat, say
   *"recommend me a product"*.
4. If the reply reads correctly but nothing moves, your `ui_action` isn't reaching the
   frontend — check the browser Network tab on `POST /api/chat` and confirm `uiActions` is
   non-empty in the JSON response.
