/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0A09",
        "background-secondary": "#11110F",
        card: "#151513",
        "card-elevated": "#1A1A18",
        border: "rgba(255, 255, 255, 0.09)",
        "border-subtle": "rgba(255, 255, 255, 0.05)",
        "border-gold": "rgba(217, 164, 65, 0.25)",
        primary: {
          DEFAULT: "#D9A441",
          highlight: "#F0B84B",
          dark: "#B3822B",
          muted: "rgba(217, 164, 65, 0.12)",
        },
        ivory: {
          DEFAULT: "#F5F1E8",
          secondary: "#918D84",
          muted: "#66625B",
          dim: "#403D37",
        },
        success: {
          DEFAULT: "#36C9A5",
          muted: "rgba(54, 201, 165, 0.12)",
          border: "rgba(54, 201, 165, 0.30)",
        },
        warning: {
          DEFAULT: "#E5A958",
          muted: "rgba(229, 169, 88, 0.12)",
          border: "rgba(229, 169, 88, 0.30)",
        },
        danger: {
          DEFAULT: "#E56B6F",
          muted: "rgba(229, 107, 111, 0.12)",
          border: "rgba(229, 107, 111, 0.30)",
        },
      },
      fontFamily: {
        serif: ["'Instrument Serif'", "'Playfair Display'", "Georgia", "serif"],
        sans: ["'Inter'", "-apple-system", "BlinkMacSystemFont", "'Segoe UI'", "Roboto", "sans-serif"],
        mono: ["'JetBrains Mono'", "'SF Mono'", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        gold: "0 0 24px -4px rgba(217, 164, 65, 0.18)",
        "gold-sm": "0 0 12px -2px rgba(217, 164, 65, 0.12)",
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
        card: "0 4px 20px -2px rgba(0, 0, 0, 0.5)",
      },
      letterSpacing: {
        tighter: "-0.04em",
        tight: "-0.02em",
        widest: "0.15em",
        ultra: "0.2em",
      },
    },
  },
  plugins: [],
};
