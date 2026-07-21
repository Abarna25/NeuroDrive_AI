/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0F172A',
        card: '#1E293B',
        safe: '#22C55E',
        caution: '#F59E0B',
        danger: '#EF4444',
        textmain: '#F1F5F9',
        accent: '#3B82F6',
      },
    },
  },
  plugins: [],
};
