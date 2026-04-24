// Vite build-tool configuration for the ScanMe React frontend.
// Proxies /api requests to the Flask backend during development.

import { defineConfig } from 'vite';              // Vite's config helper for IDE type hints.
import react from '@vitejs/plugin-react';         // Official React plugin — enables JSX/Fast Refresh.

// Default export consumed by the Vite CLI when running `npm run dev` / `npm run build`.
export default defineConfig({
  plugins: [react()],                             // Register the React plugin.
  server: {                                       // Dev-server settings for `npm run dev`.
    port: 5173,                                   // Standard Vite port.
    proxy: {                                      // Forward backend calls so they appear same-origin.
      '/api': {
        target: 'http://localhost:5000',          // Flask server URL.
        changeOrigin: true,                       // Rewrite the Host header for the proxied request.
      },
    },
  },
  build: {                                        // Production build settings.
    outDir: 'dist',                               // Output directory consumed by Flask in production.
  },
});
