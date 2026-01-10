/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Intrace Design System colors
        neutral: {
          50: "#fafafa",
          100: "#f5f5f5",
          400: "#a3a3a3",
          500: "#737373",
          600: "#525252",
          700: "#404040",
          800: "#262626",
          900: "#171717",
          950: "#0a0a0a",
        },
        error: {
          600: "#dc2626",
          700: "#b91c1c",
          800: "#991b1b",
        },
        success: {
          700: "#15803d",
        },
        warning: {
          700: "#a16207",
        },
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px",
      },
      boxShadow: {
        xs: "0px 1px 2px rgba(23, 23, 23, 0.06)",
        sm: "0px 2px 4px rgba(23, 23, 23, 0.06)",
        md: "0px 3px 6px rgba(23, 23, 23, 0.07)",
        lg: "0px 10px 15px -3px rgba(23, 23, 23, 0.1)",
        xl: "0px 20px 24px -4px rgba(23, 23, 23, 0.1)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["SF Mono", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1.125rem" }], // 12px / 18px
        sm: ["0.875rem", { lineHeight: "1.25rem" }], // 14px / 20px
        base: ["1rem", { lineHeight: "1.5rem" }], // 16px / 24px
        lg: ["1.125rem", { lineHeight: "1.75rem" }], // 18px / 28px
      },
      letterSpacing: {
        tight: "-0.02em",
      },
      transitionDuration: {
        DEFAULT: "100ms",
      },
      transitionTimingFunction: {
        DEFAULT: "ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
