// Top navigation header — renders the "ScanMe" logo/name and a small tech-stack chip.
// Pure presentation: no state, no props.

import { ScanLine, Sparkles } from 'lucide-react'; // Icon components (scan line + sparkle).
import { motion }             from 'framer-motion';// Entrance animations for the header content.

export default function Header() {
  return (
    // Outer <header> acts as the page-wide container; padding sets the safe area.
    <header className="px-4 md:px-8 py-5">
      {/* Inner flex container aligns the logo (left) and status chip (right). */}
      <div className="max-w-[1600px] mx-auto flex items-center justify-between">

        {/* ── Left side: icon + brand name ──────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}           // Start invisible, shifted left.
          animate={{ opacity: 1, x: 0 }}             // Fade in and slide to place.
          transition={{ duration: 0.6 }}
          className="flex items-center gap-3"
        >
          {/* Logo block with the scan icon and a pulsing status dot. */}
          <div className="relative">
            {/* Gradient square containing the scan-line icon. */}
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-accent-violet via-accent-fuchsia to-accent-cyan flex items-center justify-center shadow-lg shadow-accent-violet/30">
              <ScanLine className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            {/* Small emerald dot — signals the app is live; animated via Tailwind keyframe. */}
            <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-accent-emerald animate-pulse-glow" />
          </div>

          {/* Brand name + tagline. */}
          <div>
            {/* "ScanMe" with the "Me" portion rendered using the animated gradient text class. */}
            <h1 className="text-xl font-display font-bold tracking-tight">
              Scan<span className="text-gradient">Me</span>
            </h1>
            {/* Sub-tagline in monospace grey. */}
            <p className="text-xs text-white/50 font-mono">
              Barcode & QR Vision Pipeline
            </p>
          </div>
        </motion.div>

        {/* ── Right side: tech-stack chip (only shown on ≥ md screens) ─── */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}            // Mirror entrance animation from the right.
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }} // Slight stagger after the logo.
          className="flex items-center gap-3"
        >
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs">
            <Sparkles className="w-3.5 h-3.5 text-accent-amber" />
            <span className="text-white/70">OpenCV · pyzbar · React</span>
          </div>
        </motion.div>

      </div>
    </header>
  );
}
