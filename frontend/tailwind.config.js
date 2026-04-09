/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#006565",
          container: "#008080",
          fixed: "#93f2f2",
          "fixed-dim": "#76d5d5",
        },
        secondary: {
          DEFAULT: "#206393",
          container: "#90c9ff",
        },
        surface: {
          DEFAULT: "#f7fafc",
          "container-low": "#f1f4f6",
          "container-lowest": "#ffffff",
          "container-highest": "#e0e3e5",
        },
        "on-surface": "#181c1e",
        "tertiary-container": "#338236",
        "on-tertiary-container": "#ffffff",
        error: {
          DEFAULT: "#ba1a1a",
          container: "#ffdad6",
        },
        "on-error-container": "#410002",
        "outline-variant": "#bdc9c8",
      },
      fontFamily: {
        display: ["Manrope", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        pill: "9999px",
      },
      boxShadow: {
        ambient: "0 4px 24px rgba(24,28,30,0.04)",
        float: "0 4px 24px rgba(24,28,30,0.08)",
      },
    },
  },
  plugins: [],
}

