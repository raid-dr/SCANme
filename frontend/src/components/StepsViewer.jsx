// Horizontal carousel that shows every intermediate pipeline stage as a small thumbnail.
// Receives `steps` — a dict of stage-name → base64 PNG — from the backend's /api/scan response.

import { motion }        from 'framer-motion';  // Slide-in animation per thumbnail.
import { ChevronRight }  from 'lucide-react';   // Arrow separator between stages.

// Human-readable labels for the keys returned by the backend.
const STEP_LABELS = {
  gray:                 'Grayscale',
  blurred:              'Gaussian Blur',
  bilateral:            'Bilateral Filter',
  binary:               'Adaptive Threshold',
  canny_edges:          'Canny Edges',
  harris:               'Harris Corners',
  gradient:             'Sobel Gradient',
  morphological_closed: 'Morph. Closing',
  thresholded:          'Otsu Threshold',
  corrected_patch:      'Corrected Patch',
};

// Preferred display order — matches the pipeline execution order.
const STEP_ORDER = [
  'gray', 'blurred', 'bilateral', 'binary',
  'canny_edges', 'harris',
  'gradient', 'morphological_closed', 'thresholded',
  'corrected_patch',
];

export default function StepsViewer({ steps }) {
  // Keep only steps that are actually present in the backend response.
  const available = STEP_ORDER.filter((k) => steps[k]);

  // Nothing to show — render nothing rather than an empty box.
  if (!available.length) return null;

  return (
    <div className="glass-strong rounded-3xl overflow-hidden">

      {/* Header with stage count and a scroll hint. */}
      <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Small vertical gradient bar accent. */}
          <div className="w-1 h-5 rounded-full bg-gradient-to-b from-accent-violet to-accent-fuchsia" />
          <h3 className="font-display font-semibold">Pipeline Intermediates</h3>
          <span className="chip bg-white/5 text-white/50">
            {available.length} stages
          </span>
        </div>
        <div className="text-xs font-mono text-white/40 hidden md:block">
          scroll horizontally →
        </div>
      </div>

      {/* Horizontally scrolling row of stage thumbnails. */}
      <div className="overflow-x-auto p-5">
        <div className="flex gap-3 items-start">
          {available.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, x: 20 }}          // Each thumbnail slides in from the right.
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}          // Staggered for a waterfall effect.
              className="shrink-0 flex items-center gap-2"
            >
              {/* One thumbnail card. */}
              <div className="w-44 rounded-xl overflow-hidden glass border border-white/5 hover:border-accent-violet/40 transition-colors group">
                <div className="aspect-[4/3] bg-black/40 flex items-center justify-center overflow-hidden">
                  {/* Base64-decoded image returned by the backend. */}
                  <img
                    src={`data:image/png;base64,${steps[key]}`}
                    alt={STEP_LABELS[key]}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-500"
                  />
                </div>
                {/* Label under the thumbnail. */}
                <div className="px-3 py-2 border-t border-white/5">
                  <div className="text-[10px] uppercase tracking-wider text-white/40 font-mono">
                    stage {String(i + 1).padStart(2, '0')}
                  </div>
                  <div className="text-sm font-semibold text-white/90 truncate">
                    {STEP_LABELS[key]}
                  </div>
                </div>
              </div>

              {/* Arrow between thumbnails (not after the last one). */}
              {i < available.length - 1 && (
                <ChevronRight className="w-4 h-4 text-white/20 shrink-0" />
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
