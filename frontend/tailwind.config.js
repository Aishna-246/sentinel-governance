/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: "#1A3C5E",
        "navy-light": "#2E6DA4",
      }
    },
  },
  plugins: [],
}
