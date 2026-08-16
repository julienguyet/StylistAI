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
    },
  },
  plugins: [],
};

export default config;
