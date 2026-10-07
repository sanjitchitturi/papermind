/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Serif for headings and the wordmark gives the academic-journal
        // feel, Inter stays as the body/UI font for readability at small
        // sizes. Both fall back to generic families if the Google Fonts
        // request is blocked for any reason.
        serif: ["Source Serif 4", "Georgia", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
