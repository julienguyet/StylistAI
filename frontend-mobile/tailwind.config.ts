import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        hm: {
          red: "#e50010",
          ink: "#101010",
          muted: "#6b6b6b",
          line: "#e5e5e5",
        },
      },
      maxWidth: {
        /**
         * The width of the phone column, in CSS pixels. This is the single
         * knob for how large the app renders: everything inside is sized
         * relative to it, so lowering it makes the whole UI proportionally
         * bigger for a given capture width.
         *
         * 430px is the CSS viewport of an iPhone 15/16 Pro Max, so a recording
         * framed to this column has the same text-to-width ratio the customer
         * sees on a real handset. Drop to 390px to match a standard iPhone.
         */
        phone: "430px",
      },
    },
  },
  plugins: [],
};

export default config;
