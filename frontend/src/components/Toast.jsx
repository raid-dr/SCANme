// Transient notification component — floats at the bottom of the screen for a few seconds.
// Supports three visual variants: success (emerald), warn (amber), and error (rose).

import { useEffect }                             from 'react';         // Timer for auto-dismiss.
import { motion }                                from 'framer-motion'; // Spring animation for entrance/exit.
import { CheckCircle2, AlertTriangle, XCircle }  from 'lucide-react';  // One icon per variant.

// Variant lookup — colours + icon component per type.
const VARIANTS = {
  success: {
    icon:   CheckCircle2,
    border: 'border-accent-emerald/40',
    bg:     'bg-accent-emerald/10',
    text:   'text-accent-emerald',
  },
  warn: {
    icon:   AlertTriangle,
    border: 'border-accent-amber/40',
    bg:     'bg-accent-amber/10',
    text:   'text-accent-amber',
  },
  error: {
    icon:   XCircle,
    border: 'border-accent-rose/40',
    bg:     'bg-accent-rose/10',
    text:   'text-accent-rose',
  },
};

export default function Toast({ type = 'success', message, onDone }) {
  // Resolve the variant (fallback to success for unknown types).
  const variant = VARIANTS[type] || VARIANTS.success;
  const Icon    = variant.icon;

  // Auto-dismiss after 3.5 seconds by calling the parent's onDone callback.
  useEffect(() => {
    const t = setTimeout(onDone, 3500);
    return () => clearTimeout(t);                    // Clean up on unmount.
  }, [onDone]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.9 }}    // Slide up and grow in.
      animate={{ opacity: 1, y: 0,  scale: 1   }}
      exit={{    opacity: 0, y: 30, scale: 0.95 }}   // Shrink and slide down on dismiss.
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50"
    >
      <div className={`glass-strong rounded-2xl border ${variant.border} px-5 py-3.5 flex items-center gap-3 shadow-2xl min-w-[320px]`}>
        {/* Coloured icon square. */}
        <div className={`w-9 h-9 rounded-xl ${variant.bg} ${variant.text} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
        {/* Message text. */}
        <div className="flex-1">
          <div className="text-sm font-medium text-white">{message}</div>
        </div>
      </div>
    </motion.div>
  );
}
