/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        asa: {
          primary: '#6366f1',
          secondary: '#8b5cf6',
          accent: '#06b6d4',
          success: '#22c55e',
          warning: '#f59e0b',
          danger: '#ef4444',
          muted: '#64748b',
        },
      },
    },
  },
  plugins: [],
}
