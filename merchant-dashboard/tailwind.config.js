/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        // Invoicing Merchant (green on white) theme
        primary: '#10B981',    // green (emerald-500)
        secondary: '#065F46',  // dark green
        accent: '#A3E635',     // brighter lime accent for CTAs
        background: '#FFFFFF', // white page background
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'], // Match your site
      },
    },
  },
  plugins: [],
}
