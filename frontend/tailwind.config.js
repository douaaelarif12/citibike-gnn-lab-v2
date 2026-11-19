/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {
    colors: { graphite: '#0B1115', panel: '#1A292C', emerald: '#10B981', mint: '#75E3CF', ink: '#EFFCF7' },
    fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
    boxShadow: { glow: '0 0 40px rgba(16,185,129,.12)' },
  }},
  plugins: [],
}
