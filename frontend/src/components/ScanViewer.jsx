// Scan viewer — shows the selected (or annotated) image plus a toolbar with Scan/Export/Steps/Clear actions.
// During scanning, an animated overlay (corner brackets + scan line) visualises pipeline activity.

import { Scan, X, Download, Layers, RotateCcw } from 'lucide-react';  // Toolbar icons.
import { motion }                               from 'framer-motion'; // Animated scan-line + bracket entrance.

export default function ScanViewer({
  imageUrl,        // Source of the <img>: preview before scanning, annotated PNG after.
  scanning,        // True while /api/scan is in flight; drives the overlay animation.
  annotated,       // True once a scan result is rendered into `imageUrl`.
  onScan,          // Parent callback to POST to /api/scan.
  onReset,         // Parent callback to clear the selected image.
  onExport,        // Parent callback to download annotated PNG + JSON.
  hasResults,      // True if we have a scanResult object in state.
  showSteps,       // True when the "Show Steps" panel is expanded.
  onToggleSteps,   // Parent callback to flip showSteps.
}) {
  return (
    <div className="glass-strong rounded-3xl overflow-hidden">

      {/* ── Top toolbar — status badge on left, action buttons on right ─ */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/5 bg-ink-800/40">

        {/* Fake "window chrome" dots + status label (purely decorative + state indicator). */}
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-accent-rose/80" />
          <div className="w-2.5 h-2.5 rounded-full bg-accent-amber/80" />
          <div className="w-2.5 h-2.5 rounded-full bg-accent-emerald/80" />
          {/* Status badge: scanning / annotated / ready. */}
          <div className="ml-3 px-3 py-1 rounded-md bg-ink-700/60 text-xs font-mono text-white/60 flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${scanning ? 'bg-accent-fuchsia animate-pulse' : annotated ? 'bg-accent-emerald' : 'bg-accent-cyan'}`} />
            {scanning ? 'scanning…' : annotated ? 'annotated' : 'ready'}
          </div>
        </div>

        {/* Right-hand toolbar buttons. */}
        <div className="flex items-center gap-2">
          {/* Toggles the Pipeline Intermediates drawer. */}
          <button
            onClick={onToggleSteps}
            disabled={!hasResults}
            className={`btn-ghost !py-1.5 !px-3 flex items-center gap-1.5 text-sm ${showSteps ? 'bg-white/10 border-white/30' : ''}`}
          >
            <Layers className="w-3.5 h-3.5" />
            Steps
          </button>
          {/* Export annotated PNG + JSON. */}
          <button
            onClick={onExport}
            disabled={!hasResults}
            className="btn-ghost !py-1.5 !px-3 flex items-center gap-1.5 text-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
          {/* Clear the current image and return to the upload zone. */}
          <button
            onClick={onReset}
            className="btn-ghost !py-1.5 !px-3 flex items-center gap-1.5 text-sm"
          >
            <X className="w-3.5 h-3.5" />
            Clear
          </button>
        </div>
      </div>

      {/* ── Viewer area — image + scanning overlay ─────────────────────── */}
      <div className="relative bg-black/40 flex items-center justify-center" style={{ minHeight: '480px' }}>
        {/* Displayed image — flips between preview and annotated result. */}
        <img
          src={imageUrl}
          alt="scan target"
          className="max-w-full max-h-[70vh] object-contain"
        />

        {/* Overlay only visible during the scanning request. */}
        {scanning && (
          <>
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              {/* Horizontal scan line animated top → bottom → top. */}
              <motion.div
                className="absolute left-0 right-0 h-[3px] pointer-events-none"
                style={{
                  background: 'linear-gradient(90deg, transparent 0%, #8b5cf6 20%, #d946ef 50%, #06b6d4 80%, transparent 100%)',
                  boxShadow:  '0 0 20px #d946ef, 0 0 40px #8b5cf6',
                }}
                animate={{ top: ['0%', '100%', '0%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              />

              {/* Four corner brackets — mimic a camera viewfinder. */}
              {[
                { top: '4%',    left: '4%',   rotate: 0   },
                { top: '4%',    right: '4%',  rotate: 90  },
                { bottom: '4%', right: '4%',  rotate: 180 },
                { bottom: '4%', left:  '4%',  rotate: 270 },
              ].map((pos, i) => (
                <motion.div
                  key={i}
                  className="absolute w-12 h-12"
                  style={{ ...pos, transform: `rotate(${pos.rotate}deg)` }}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.1 }}
                >
                  {/* Top edge of the bracket. */}
                  <div className="absolute top-0 left-0 w-full h-[3px] bg-accent-fuchsia shadow-[0_0_10px_rgba(217,70,239,0.8)]" />
                  {/* Left edge of the bracket. */}
                  <div className="absolute top-0 left-0 w-[3px] h-full bg-accent-fuchsia shadow-[0_0_10px_rgba(217,70,239,0.8)]" />
                </motion.div>
              ))}

              {/* Faint grid overlay for a tech/measurement feel. */}
              <div className="absolute inset-0 opacity-20"
                   style={{
                     backgroundImage:
                       'linear-gradient(rgba(139,92,246,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(139,92,246,0.3) 1px, transparent 1px)',
                     backgroundSize: '40px 40px',
                   }} />
            </div>

            {/* Floating status pill showing what's happening. */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-6 left-1/2 -translate-x-1/2 px-5 py-2.5 rounded-full glass-strong flex items-center gap-3"
            >
              {/* Three staggered pulse dots. */}
              <div className="flex items-center gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-accent-fuchsia"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
              <span className="text-sm font-mono text-white/80">
                Running pipeline · 3 scales
              </span>
            </motion.div>
          </>
        )}
      </div>

      {/* ── Bottom action bar — Run scan / Rescan button ──────────────── */}
      <div className="px-5 py-4 flex items-center justify-between bg-ink-800/30 border-t border-white/5">
        <div className="text-xs font-mono text-white/40">
          {annotated ? '✓ pipeline complete' : 'ready for scan'}
        </div>
        <div className="flex items-center gap-2">
          {/* After a scan, show "Rescan"; before, show "Run scan". */}
          {hasResults && (
            <button onClick={onScan} disabled={scanning} className="btn-ghost flex items-center gap-2">
              <RotateCcw className="w-4 h-4" />
              Rescan
            </button>
          )}
          {!hasResults && (
            <button
              onClick={onScan}
              disabled={scanning}
              className="btn-primary flex items-center gap-2"
            >
              <Scan className="w-4 h-4" />
              {scanning ? 'Scanning…' : 'Run scan'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
