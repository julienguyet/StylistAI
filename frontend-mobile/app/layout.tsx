import type { Metadata, Viewport } from "next";
import "./globals.css";
import { StoreProvider } from "@/lib/store-context";
import { ChatProvider } from "@/lib/chat-context";
import { Header } from "@/components/Header";
import { BottomNav } from "@/components/BottomNav";
import { ChatWidget } from "@/components/ChatWidget";
import { CustomerPicker } from "@/components/CustomerPicker";

export const metadata: Metadata = {
  title: "StylistAI — H&M Portugal",
  description: "Shop the H&M catalog with Björn, your AI stylist.",
};

/**
 * `viewport-fit=cover` is what makes env(safe-area-inset-*) report real values
 * on a notched phone; without it the bottom nav sits under the home bar.
 * Zoom stays enabled — disabling it is an accessibility regression, and the
 * layout is already sized for a phone.
 */
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <StoreProvider>
          <ChatProvider>
            {/* The whole app is a single phone-width column. It fills a narrow
                window edge to edge, and centres itself on anything wider so a
                desktop screen recording still frames like a phone. */}
            <div className="relative mx-auto flex min-h-screen w-full max-w-phone flex-col bg-white shadow-xl">
              <Header />

              {/* Bottom padding clears the fixed nav (56px) plus the home bar. */}
              <main className="flex-1 px-4 pb-[calc(4.5rem+var(--safe-bottom))] pt-4">
                {children}
              </main>

              <BottomNav />
              <CustomerPicker />
              <ChatWidget />
            </div>
          </ChatProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
