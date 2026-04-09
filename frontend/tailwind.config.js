/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Cormorant Garamond", "serif"],
        mono: ["DM Mono", "monospace"],
      },
      colors: {
        "space-dark": "#010310",
        "space-gray": "#0a0a1a",
        gold: "#c09850",
        "gold-light": "#d4b06d",
      },
    },
  },
  plugins: [],
};
