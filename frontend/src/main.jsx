// Application bootstrap — the first file executed in the browser after Vite loads index.html.
// Mounts the <App /> component tree into #root and enables StrictMode for development warnings.

import React      from 'react';            // React itself (required by JSX).
import ReactDOM   from 'react-dom/client'; // React 18 client-side renderer (createRoot API).
import App        from './App.jsx';        // Top-level component that composes the whole UI.
import './index.css';                      // Global styles (Tailwind directives, custom classes).

// Find the #root div in index.html and create a React root attached to it.
ReactDOM.createRoot(document.getElementById('root')).render(
  // StrictMode surfaces deprecated patterns and double-invokes effects in dev (no impact in production).
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
