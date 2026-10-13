/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#10263F',
        ocean: '#0E6B70',
        mint: '#DDF1EC',
        paper: '#F7F6F1',
        coral: '#D86E53',
      },
      boxShadow: {
        '2xs': '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
        xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        soft: '0 20px 60px rgba(16, 38, 63, 0.09)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Georgia', 'Cambria', 'serif'],
      },
    },
  },
  plugins: [],
}

