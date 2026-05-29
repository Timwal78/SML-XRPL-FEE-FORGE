/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        neon: {
          cyan:    '#00FFFF',
          green:   '#00FF41',
          magenta: '#FF00FF',
          amber:   '#FFB800',
          red:     '#FF0040',
          blue:    '#0080FF',
        },
        terminal: {
          bg:      '#000000',
          surface: '#080808',
          panel:   '#0d0d0d',
          border:  '#1a1a1a',
          muted:   '#2a2a2a',
          text:    '#e0e0e0',
          dim:     '#666666',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-neon': 'pulseNeon 2s ease-in-out infinite',
        'slide-in':   'slideIn 0.2s ease-out',
        'blink':      'blink 1s step-start infinite',
        'scan':       'scan 4s linear infinite',
      },
      keyframes: {
        pulseNeon: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.5' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateY(-4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
        scan: {
          '0%':   { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '0 100%' },
        },
      },
      boxShadow: {
        'neon-cyan':    '0 0 10px #00FFFF, 0 0 20px #00FFFF40',
        'neon-green':   '0 0 10px #00FF41, 0 0 20px #00FF4140',
        'neon-magenta': '0 0 10px #FF00FF, 0 0 20px #FF00FF40',
        'neon-amber':   '0 0 10px #FFB800, 0 0 20px #FFB80040',
        'neon-red':     '0 0 10px #FF0040, 0 0 20px #FF004040',
      },
    },
  },
  plugins: [],
}
