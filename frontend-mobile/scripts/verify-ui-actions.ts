import { extractUiActions, extractAgentText } from "../lib/ui-actions";

const cases: [string, unknown, number][] = [
  // 1. structured dict straight on the functionResponse
  ["plain response", [{ content: { role: "model", parts: [
    { functionResponse: { name: "open_product", response: { ui_action: { type: "navigate", path: "/product/123" } } } }
  ] } }], 1],
  // 2. FastMCP wraps structured returns under `result`
  ["nested under result", [{ content: { role: "model", parts: [
    { functionResponse: { name: "open_product", response: { result: { ui_action: { type: "navigate", path: "/product/1" } } } } }
  ] } }], 1],
  // 3. MCP text content block carrying JSON as a string
  ["json string in content block", [{ content: { role: "model", parts: [
    { functionResponse: { name: "add", response: { result: { content: [
      { type: "text", text: JSON.stringify({ ok: true, ui_action: { type: "cart_updated" } }) }
    ] } } } }
  ] } }], 1],
  // 4. multiple actions across several tool calls
  ["multiple", [
    { content: { role: "model", parts: [{ functionResponse: { response: { ui_action: { type: "navigate", path: "/a" } } } }] } },
    { content: { role: "model", parts: [{ functionResponse: { response: { ui_action: { type: "cart_updated" } } } }] } },
  ], 2],
  // 5. array of actions
  ["array of actions", [{ content: { parts: [{ functionResponse: { response: {
    ui_action: [{ type: "navigate", path: "/x" }, { type: "cart_updated" }] } } }] } }], 2],
  // 6. must NOT fire on unrelated objects that merely have a `type` key
  ["no false positive", [{ content: { role: "model", parts: [
    { functionResponse: { response: { result: { content: [{ type: "text", text: "just prose" }] } } } }
  ] } }], 0],
  // 7. bad json string must not throw
  ["malformed json", [{ content: { parts: [{ functionResponse: { response: "{not json" } }] } }], 0],
  // 8. unknown action type ignored
  ["unknown type", [{ content: { parts: [{ functionResponse: { response: { ui_action: { type: "explode" } } } }] } }], 0],
  // 9. cycles / deep nesting must not hang
  ["depth cap: 30 levels is ignored", { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { a: { ui_action: { type: "cart_updated" } } } } } } } } } } } } } } } } } } } } } } } } } } } } } } } }, 0],
  ["9-level payload still found", { a: { b: { c: { d: { e: { f: { g: { h: { ui_action: { type: "cart_updated" } } } } } } } } } }, 1],
];

// --- Live payloads from scripts/mcp/main.py -------------------------------
// Captured verbatim from the running Catalog API, so these break if a tool's
// return shape drifts. Regenerate by calling the tool and pasting the JSON.

const OPEN_PRODUCT_OK = {
  status: "success",
  product: {
    article_id: "108775015",
    prod_name: "Strap top",
    product_type_name: "Vest top",
    section_name: "Womens Everyday Basics",
    price: 31.94,
    currency: "EUR",
    detail_desc: "Jersey top with narrow shoulder straps.",
  },
  ui_action: { type: "navigate", path: "/product/108775015" },
  agent_next_action:
    "The product page is now open on the customer's screen. Describe the item briefly using the details above and ask what they think.",
};

// The 400/404 branch: no ui_action, so the customer's screen must not move.
const OPEN_PRODUCT_ERR = {
  status: "error",
  agent_next_action:
    "There is no article 999999999 in the catalog. Do not retry with this id and do not describe this product to the customer. Search the catalog to get a valid article id instead.",
};

const ADD_TO_CART_OK = {
  status: "success",
  quantity_in_cart: 1,
  item_count: 1,
  subtotal: 31.94,
  currency: "EUR",
  ui_action: { type: "cart_updated" },
  agent_next_action:
    "The item is in the cart. Confirm to the customer using the quantity and totals above, then ask if there is anything else they need. Do not call this tool again for the same item.",
};

const ADD_TO_CART_ERR = {
  status: "error",
  agent_next_action:
    "There is no article 999999999 in the catalog, so nothing was added. Do not tell the customer it was added. Search the catalog for a valid article and confirm with them before retrying.",
};

/** Wrap a tool return the way FastMCP does for a structured dict. */
const structured = (name: string, response: unknown) => ({
  content: { role: "model", parts: [{ functionResponse: { name, response: { result: response } } }] },
});

/** Wrap a tool return the way MCP does when it serialises to a text block. */
const asTextBlock = (name: string, response: unknown) => ({
  content: {
    role: "model",
    parts: [
      {
        functionResponse: {
          name,
          response: { result: { content: [{ type: "text", text: JSON.stringify(response) }] } },
        },
      },
    ],
  },
});

cases.push(
  ["open_product_page: success navigates", [structured("open_product_page", OPEN_PRODUCT_OK)], 1],
  ["open_product_page: success as text block", [asTextBlock("open_product_page", OPEN_PRODUCT_OK)], 1],
  ["open_product_page: error does not move the screen", [structured("open_product_page", OPEN_PRODUCT_ERR)], 0],
  ["add_to_cart: success refreshes the cart", [structured("add_to_cart", ADD_TO_CART_OK)], 1],
  ["add_to_cart: success as text block", [asTextBlock("add_to_cart", ADD_TO_CART_OK)], 1],
  ["add_to_cart: error does not refresh the cart", [structured("add_to_cart", ADD_TO_CART_ERR)], 0],
  // The core loop in one turn: recommend -> open the page -> add it.
  [
    "full loop: open then add in a single turn",
    [structured("open_product_page", OPEN_PRODUCT_OK), structured("add_to_cart", ADD_TO_CART_OK)],
    2,
  ],
);

let failed = 0;
for (const [name, payload, expected] of cases) {
  const got = extractUiActions(payload).length;
  const ok = got === expected;
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}: expected ${expected}, got ${got}`);
}

// Counting actions is not enough for navigate: ChatWidget only routes when the
// path starts with "/", so a tool emitting a bare or absolute-URL path would be
// silently dropped at runtime. Pin the actual value.
const navAction = extractUiActions([structured("open_product_page", OPEN_PRODUCT_OK)])[0];
const navOk =
  navAction?.type === "navigate" &&
  navAction.path === "/product/108775015" &&
  navAction.path.startsWith("/");
if (!navOk) failed++;
console.log(`${navOk ? "PASS" : "FAIL"}  navigate path is routable: ${JSON.stringify(navAction)}`);

const text = extractAgentText([
  { content: { role: "user", parts: [{ text: "hi" }] } },
  { content: { role: "model", parts: [{ functionCall: { name: "x" } }] } },
  { content: { role: "model", parts: [{ text: "Here are my picks." }] } },
]);
const textOk = text === "Here are my picks.";
if (!textOk) failed++;
console.log(`${textOk ? "PASS" : "FAIL"}  agent text extraction: ${JSON.stringify(text)}`);

console.log(failed === 0 ? "\nALL PASS" : `\n${failed} FAILED`);
