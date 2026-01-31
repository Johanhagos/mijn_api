/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1F2937',    // Dark gray/brand primary
        secondary: '#3B82F6',  // Blue accent
        accent: '#FBBF24',     // Optional gold/yellow
        background: '#F9FAFB', // Light background
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'], // Match your site
      },
    },
  },
  plugins: [],
}
