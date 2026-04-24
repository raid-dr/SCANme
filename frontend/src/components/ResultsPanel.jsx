// Right-hand results panel — displays stats, a list of detection cards, and a pipeline footer.
// Renders skeleton cards while scanning and an empty state when no codes are found.

import { motion, AnimatePresence }                                     from 'framer-motion';
import { QrCode, Barcode, Zap, Copy, Check, Clock, Layers3, Target }   from 'lucide-react';
import { useState }                                                    from 'react';

// Mapping from detection track name → icon + display colour.
const TRACK_INFO = {
  qr:      { icon: QrCode,  color: 'emerald', label: 'QR Code'    },
  barcode: { icon: Barcode, color: 'cyan',    label: '1D Barcode' },
  direct:  { icon: Zap,     color: 'amber',   label: 'Direct'     },
};

// Colour tokens (bg/text/border) keyed by the accent colour names defined in Tailwind config.
const COLORS = {
  emerald: { bg: 'bg-accent-emerald/10', text: 'text-accent-emerald', border: 'border-accent-emerald/30' },
  cyan:    { bg: 'bg-accent-cyan/10',    text: 'text-accent-cyan',    border: 'border-accent-cyan/30'    },
  amber:   { bg: 'bg-accent-amber/10',   text: 'text-accent-amber',   border: 'border-accent-amber/30'   },
};

// ── Individual detection card (one per decoded code) ───────────────────
function DetectionCard({ detection, index }) {
  const [copied, setCopied] = useState(false);      // Tracks the click-to-copy feedback state.
  const info   = TRACK_INFO[detection.track] || TRACK_INFO.direct; // Fallback to "direct" if unknown.
  const colors = COLORS[info.color];                // Resolve accent colour → class strings.
  const Icon   = info.icon;                         // Icon component for this track.

  // Copy the decoded payload to the clipboard and briefly flash the check-mark.
  const handleCopy = async () => {
    await navigator.clipboard.writeText(detection.data);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}                // Card slides up + fades in.
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}           // Stagger multiple cards for a nice effect.
      className={`rounded-2xl glass border ${colors.border} p-4 hover:scale-[1.01] transition-transform`}
    >
      <div className="flex items-start gap-3">
        {/* Icon square (coloured) on the left. */}
        <div className={`w-10 h-10 rounded-xl ${colors.bg} ${colors.text} flex items-center justify-center shrink-0`}>
          <Icon className="w-5 h-5" />
        </div>

        {/* Card content on the right. */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {/* Zero-padded index (#01, #02, ...). */}
            <span className="text-xs text-white/50 font-mono">
              #{String(index + 1).padStart(2, '0')}
            </span>
            {/* Symbology type chip (e.g. EAN13, QRCODE). */}
            <span className={`chip ${colors.bg} ${colors.text}`}>
              {detection.type}
            </span>
            {/* Scale factor at which this detection was found. */}
            <span className="chip bg-white/5 text-white/50">
              {detection.scale}×
            </span>
          </div>

          {/* Payload text — clickable to copy to clipboard. */}
          <div
            className="font-mono text-sm text-white/90 break-all leading-snug cursor-pointer group flex items-start gap-2"
            onClick={handleCopy}
            title="Click to copy"
          >
            <span className="flex-1">{detection.data}</span>
            {/* Swap between copy icon and check icon when copied. */}
            <span className="shrink-0 mt-0.5">
              {copied ? (
                <Check className="w-4 h-4 text-accent-emerald" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-white/30 group-hover:text-white/70" />
              )}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Placeholder card shown while the backend is processing ────────────
function SkeletonCard() {
  return (
    <div className="rounded-2xl glass border border-white/5 p-4 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-white/5 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-white/5 rounded w-1/3" />
          <div className="h-4 bg-white/5 rounded w-full" />
          <div className="h-4 bg-white/5 rounded w-2/3" />
        </div>
      </div>
    </div>
  );
}

// ── Main exported panel component ─────────────────────────────────────
export default function ResultsPanel({ result, scanning, hasImage }) {
  // Extract detections (safe fallback if result is null).
  const detections = result?.detections || [];

  // Summary stats rendered above the list.
  const stats = {
    count:   detections.length,
    qr:      detections.filter((d) => d.track === 'qr').length,
    barcode: detections.filter((d) => d.track === 'barcode').length,
    time:    result?.processing_time || 0,
  };

  return (
    <aside className="glass-strong rounded-3xl flex flex-col"
           style={{ minHeight: '560px', maxHeight: 'calc(100vh - 120px)' }}>
      {/* ── Panel header with title + time chip + stats row ──────────── */}
      <div className="px-5 py-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-display font-bold">Detections</h2>
          {/* Processing-time chip appears only once we have a result. */}
          {result && (
            <span className="chip bg-accent-violet/10 text-accent-violet border border-accent-violet/30">
              <Clock className="w-3 h-3" />
              {stats.time.toFixed(2)}s
            </span>
          )}
        </div>

        {/* Three-stat mini cards (total / QR / barcode). */}
        <div className="grid grid-cols-3 gap-2">
          <StatCard icon={Target}  value={stats.count}   label="Total"   color="violet"  />
          <StatCard icon={QrCode}  value={stats.qr}      label="QR"      color="emerald" />
          <StatCard icon={Barcode} value={stats.barcode} label="Barcode" color="cyan"    />
        </div>
      </div>

      {/* ── Scrollable list of detections / skeleton / empty state ───── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence mode="popLayout">
          {scanning ? (
            // Three skeleton cards while waiting for the backend.
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : detections.length === 0 ? (
            // No results → friendly empty state with contextual message.
            <EmptyState hasImage={hasImage} hasResult={!!result} />
          ) : (
            // One card per detection.
            detections.map((d, i) => (
              <DetectionCard key={`${d.data}-${i}`} detection={d} index={i} />
            ))
          )}
        </AnimatePresence>
      </div>

      {/* ── Bottom footer showing pipeline metadata ──────────────────── */}
      <div className="px-5 py-3 border-t border-white/5 text-xs font-mono text-white/40 flex items-center justify-between">
        <span>pipeline v1.0</span>
        <span className="flex items-center gap-1.5">
          <Layers3 className="w-3 h-3" />
          4 stages · 3 scales
        </span>
      </div>
    </aside>
  );
}

// ── Small stat card used three times in the header ─────────────────
function StatCard({ icon: Icon, value, label, color }) {
  // Colour-class lookup.
  const colors = {
    violet:  'text-accent-violet',
    emerald: 'text-accent-emerald',
    cyan:    'text-accent-cyan',
  };
  return (
    <div className="rounded-xl bg-ink-800/50 px-3 py-2.5 border border-white/5">
      <div className="flex items-center gap-1.5 mb-0.5">
        <Icon className={`w-3 h-3 ${colors[color]}`} />
        <span className="text-[10px] uppercase tracking-wider text-white/40">{label}</span>
      </div>
      <div className="text-xl font-mono font-bold text-white">{value}</div>
    </div>
  );
}

// ── Empty-state illustration + contextual message ─────────────────
function EmptyState({ hasImage, hasResult }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-full text-center py-12"
    >
      {/* Muted target-icon circle. */}
      <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
        <Target className="w-7 h-7 text-white/30" />
      </div>
      {/* Message tailored to the current state. */}
      <p className="text-white/50 text-sm font-medium">
        {hasResult
          ? 'No codes detected in this image'
          : hasImage
          ? 'Click "Run scan" to detect codes'
          : 'Load an image to begin'}
      </p>
      <p className="text-white/30 text-xs mt-2 max-w-[240px]">
        Results will appear here with type, payload, and processing metadata.
      </p>
    </motion.div>
  );
}
