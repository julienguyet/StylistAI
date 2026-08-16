# StylistAI Storefront — Mobile

A vertical, phone-shaped version of the storefront in `../frontend`. It is a separate Next.js app so the desktop one keeps working exactly as it does today. Both talk to the same Catalog API and the same agent, so you can run them side by side.

## What is different

The data layer is untouched. The API route handlers, `lib/catalog.ts`, `lib/store-context.tsx`, `lib/types.ts` and `lib/ui-actions.ts` are identical to the desktop app, so the `ui_action` contract behaves the same way and no MCP tool needs to change.

Only the presentation differs:

| | Desktop | Mobile |
|---|---|---|
| Shell | full width, `max-w-7xl` | one phone column, `max-w-[520px]`, centred |
| Navigation | links in the header | fixed bottom nav with the cart badge |
| Chat | floating panel in the corner | full-height sheet over the page |
| Product page | two columns | stacked, with a sticky price and add-to-cart bar |
| Related items | grid | horizontal rail you swipe |
| Filters | wrapping chips | one scrolling row |

Two mobile behaviours are worth knowing about. The chat sheet **closes itself** when Björn returns a `navigate` or `show_products` action, because on a phone the sheet covers the whole screen and a navigation you cannot see is a navigation that did not happen. It stays open on `cart_updated`, since the badge behind it refreshes on its own. And every text input is set to 16px, as iOS Safari zooms the entire page when a focused field renders any smaller.

## Running it locally

```bash
cd frontend-mobile
cp .env.local.example .env.local
npm install
npm run dev
```

The app is then available on `http://localhost:3001`. Port 3001 is deliberate so it does not clash with the desktop storefront on 3000.

## Building the container

```bash
docker build -t stylistai-frontend-mobile ./frontend-mobile
```

```powershell
docker run -d --name stylistai-frontend-mobile --network stylistai-net -p 3001:3001 --restart always `
  -e CATALOG_API_URL=http://stylistai-catalog:8002 `
  -e ADK_API_URL=http://stylist-agent:8015 `
  stylistai-frontend-mobile
```

Run the build from the repository root. The same rule as the desktop app applies here: the front end is compiled at image build time, so any code change needs a new `docker build`.

## Recording a vertical demo

The layout fills the window up to 520px and centres itself beyond that, so you have two options.

The simplest one is to open Chrome DevTools, turn on the device toolbar and pick an iPhone. You then record that region directly and get a real 9:16 frame with the safe area insets applied.

The other is to resize the browser window to roughly 500px wide and as tall as your screen. The app fills it edge to edge, with no visible margins, which is usually what you want for a screen recording that will be cropped to portrait.

If you record on a screen wider than 520px, the column centres itself and the grey body shows on either side. That is intentional and looks like a device on a stage, but it is not a full-bleed vertical video.
