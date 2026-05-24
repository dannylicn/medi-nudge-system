/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        /* ============================================================
           Adheris primary palette
           ============================================================ */
        accent: {
          DEFAULT: "#E85A3C",      // coral — CTA, urgent, links
          container: "#FBE5DD",    // coral-soft — chip bg, soft fills
          hover: "#D04B2E",
        },
        teal: {
          DEFAULT: "#0F4C5C",      // headers, info, charts
          container: "#D9E7EA",
        },
        green: {
          DEFAULT: "#2F7D5B",      // positive, on-track, success
          container: "#DDEDE3",
        },
        gold: {
          DEFAULT: "#C8923E",      // warning, "pending"
          container: "#F5E8D0",
        },
        ink: {
          DEFAULT: "#0E1A2B",      // primary text / button fill
          soft: "#38465A",         // secondary text
        },
        muted: "#7A8595",          // tertiary text, labels, hints

        /* ============================================================
           Legacy tokens — remapped onto Adheris so existing components
           and class names keep working without edits.
           ============================================================ */
        primary: {
          DEFAULT: "#0E1A2B",      // CTAs (ink)
          container: "#38465A",
          fixed: "#E85A3C",        // focus rings → coral
          "fixed-dim": "#F08267",
        },
        secondary: {
          DEFAULT: "#0F4C5C",
          container: "#D9E7EA",
        },
        surface: {
          DEFAULT: "#FAF7F2",                  // app background (warm off-white)
          "container-low": "#F2EDE4",          // sidebar / soft container
          "container-lowest": "#FFFFFF",       // card surface
          "container-highest": "#ECE6DA",      // input surface, contrast container
        },
        "on-surface": "#0E1A2B",
        "tertiary-container": "#DDEDE3",
        "on-tertiary-container": "#2F7D5B",
        error: {
          DEFAULT: "#E85A3C",
          container: "#FBE5DD",
        },
        "on-error-container": "#E85A3C",
        "outline-variant": "#E6DFD2",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Inter Tight", "Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        pill: "9999px",
      },
      boxShadow: {
        ambient: "0 1px 2px rgba(14,26,43,.06), 0 8px 28px rgba(14,26,43,.05)",
        float: "0 24px 60px rgba(14,26,43,.14)",
        soft: "0 1px 2px rgba(14,26,43,.06)",
      },
      letterSpacing: {
        tightish: "-0.015em",
        eyebrow: "0.16em",
      },
    },
  },
  plugins: [],
};
