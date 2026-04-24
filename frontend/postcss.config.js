// PostCSS configuration — Vite runs CSS through PostCSS on every build.
// Chains Tailwind (utility CSS generation) and Autoprefixer (vendor prefixes).

export default {
  plugins: {
    tailwindcss: {},   // Tailwind transforms the @tailwind directives into real CSS.
    autoprefixer: {},  // Autoprefixer adds -webkit-/-moz- prefixes where needed.
  },
};
