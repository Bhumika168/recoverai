import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0D0C0A",
        surface: "#15130F",
        "surface-elevated": "#1C1914",
        "surface-border": "rgba(245, 240, 232, 0.10)",
        primary: {
          DEFAULT: "#D79A43",
          light: "#E5A958",
          dark: "#B87F32",
        },
        ivory: {
          DEFAULT: "#F5F0E8",
          muted: "#9E978C",
          dim: "#6B655C",
        },
        success: {
          DEFAULT: "#2A9D8F",
          muted: "rgba(42, 157, 143, 0.15)",
        },
        warning: {
          DEFAULT: "#E76F51",
          muted: "rgba(231, 111, 81, 0.15)",
        },
        danger: {
          DEFAULT: "#E63946",
          muted: "rgba(230, 57, 70, 0.15)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
        editorial: ["var(--font-editorial)", "Georgia", "serif"],
      },
      boxShadow: {
        gold: "0 0 20px -5px rgba(215, 154, 67, 0.15)",
        "gold-lg": "0 0 30px -5px rgba(215, 154, 67, 0.25)",
        card: "0 4px 20px 0 rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
