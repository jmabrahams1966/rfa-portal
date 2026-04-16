/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#E8EBF0',
          100: '#C5CBD8',
          200: '#9BA6BD',
          300: '#7181A2',
          400: '#4D6187',
          500: '#2A416C',
          600: '#1A3058',
          700: '#0F2044',
          800: '#0A1730',
          900: '#050E1D',
        },
        accent: {
          50: '#EBF0FF',
          100: '#D6E0FF',
          200: '#ADC1FF',
          300: '#85A2FF',
          400: '#5C83FF',
          500: '#1D4ED8',
          600: '#1A45C2',
          700: '#163BAB',
          800: '#123295',
          900: '#0E287E',
        },
      },
    },
  },
  plugins: [],
};
