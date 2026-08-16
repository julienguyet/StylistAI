import type { Metadata } from "next";
import "./globals.css";
import { StoreProvider } from "@/lib/store-context";
import { Header } from "@/components/Header";
import { ChatWidget } from "@/components/ChatWidget";
import { CustomerPicker } from "@/components/CustomerPicker";

export const metadata: Metadata = {
  title: "StylistAI — H&M Portugal",
  description: "Shop the H&M catalog with Björn, your AI stylist.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <StoreProvider>
          <Header />
          <main className="mx-auto min-h-[70vh] max-w-7xl px-4 py-8">{children}</main>
          <footer className="border-t border-hm-line py-8 text-center text-xs text-hm-muted">
            Portfolio demo · H&amp;M Kaggle dataset · prices are synthetic
          </footer>
          <CustomerPicker />
          <ChatWidget />
        </StoreProvider>
      </body>
    </html>
  );
}
