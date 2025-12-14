/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'eve-red': '#dc2626',
        'eve-yellow': '#fbbf24',
        'eve-blue': '#3b82f6',
      },
    },
  },
  plugins: [],
}
