// Tailwind CSS configuration — defines the design tokens, custom colors, and animations used across the UI.
// Referenced by index.css through the @tailwind directives and loaded by PostCSS at build time.

/** @type {import('tailwindcss').Config} */
export default {
  // Only scan the source files below for class usage (keeps the final CSS bundle small).
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      // Custom font stacks — Inter is the base, Space Grotesk is used for headings/display.
      fontFamily: {
        sans:    ['Inter',        'system-ui',  'sans-serif'],
        display: ['Space Grotesk','Inter',       'sans-serif'],
        mono:    ['JetBrains Mono','monospace'],
      },
      // Custom colour palette tailored to the dark, glassmorphism design.
      colors: {
        // "ink" = dark background shades (deepest → lightest).
        ink: {
          900: '#0a0a14',
          800: '#0f0f1a',
          700: '#13131f',
          600: '#1a1a2e',
          500: '#22223d',
        },
        // Accent colours — used for type badges, hover states, gradients.
        accent: {
          violet:  '#8b5cf6',
          fuchsia: '#d946ef',
          cyan:    '#06b6d4',
          emerald: '#10b981',
          amber:   '#f59e0b',
          rose:    '#f43f5e',
        },
      },
      // Registered animation names — referenced via `animate-<name>` classes.
      animation: {
        'scan-line':    'scanline 2s ease-in-out infinite',
        'pulse-glow':   'pulseGlow 2s ease-in-out infinite',
        'float':        'float 6s ease-in-out infinite',
        'gradient':     'gradient 8s ease infinite',
        'fade-up':      'fadeUp 0.5s ease-out forwards',
      },
      // Keyframe definitions that power the animations above.
      keyframes: {
        scanline: {                                // Vertical sweeping scan line.
          '0%':   { top: '0%',   opacity: '0.8' },
          '50%':  { top: '100%', opacity: '1' },
          '100%': { top: '0%',   opacity: '0.8' },
        },
        pulseGlow: {                               // Soft violet glow pulse.
          '0%, 100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.3)' },
          '50%':      { boxShadow: '0 0 40px rgba(139, 92, 246, 0.8)' },
        },
        float: {                                   // Subtle vertical floating motion.
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-15px)' },
        },
        gradient: {                                // Moving gradient background for text.
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':      { backgroundPosition: '100% 50%' },
        },
        fadeUp: {                                  // Fade+slide entrance for cards.
          '0%':   { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      // Radial-gradient mesh used as the page background.
      backgroundImage: {
        'mesh-gradient':
          'radial-gradient(at 20% 30%, rgba(139,92,246,0.25) 0px, transparent 50%), ' +
          'radial-gradient(at 80% 0%,  rgba(217,70,239,0.2) 0px, transparent 50%), ' +
          'radial-gradient(at 0% 80%,  rgba(6,182,212,0.2)  0px, transparent 50%)',
      },
    },
  },
  plugins: [],                                    // No extra Tailwind plugins are used.
};
