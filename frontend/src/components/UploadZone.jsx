// Image upload zone — a large drag-and-drop target shown when no image is selected yet.
// Uses react-dropzone to accept common image formats and raises a single File via `onSelect`.

import { useDropzone }                       from 'react-dropzone';  // Drag-and-drop + file-picker hook.
import { Upload, ImageIcon }                  from 'lucide-react';    // Icons for the centre illustration and button.
import { motion }                             from 'framer-motion';   // Floating animation for the icon card.

export default function UploadZone({ onSelect }) {
  // react-dropzone wires up the input element and exposes drag state.
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      // Only accept image MIME types; broad file extension support.
      'image/*': ['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.tif'],
    },
    multiple: false,                                // Single-file upload only.
    onDrop: (files) => files[0] && onSelect(files[0]), // Pass the first file back to the parent.
  });

  return (
    // The outer div is the drop target; its class list changes on drag-over.
    <div
      {...getRootProps()}
      className={`
        group relative overflow-hidden rounded-3xl glass-strong
        min-h-[560px] flex items-center justify-center cursor-pointer
        transition-all duration-500 border-2 border-dashed
        ${isDragActive
          ? 'border-accent-fuchsia scale-[1.01] shadow-2xl shadow-accent-fuchsia/30'
          : 'border-white/10 hover:border-accent-violet/60'}
      `}
    >
      {/* Hidden native <input type="file"> — required by react-dropzone. */}
      <input {...getInputProps()} />

      {/* Decorative radial gradient background (non-interactive). */}
      <div className="absolute inset-0 opacity-30 bg-mesh-gradient pointer-events-none" />

      {/* Decorative dot grid pattern overlay. */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
           style={{
             backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
             backgroundSize:  '24px 24px',
           }} />

      {/* Centred content column. */}
      <div className="relative z-10 text-center px-8">

        {/* Floating icon block — bobs up and down continuously, wiggles on drag. */}
        <motion.div
          animate={{
            y: [0, -12, 0],                         // Gentle vertical float loop.
            rotate: isDragActive ? [0, -3, 3, 0] : 0, // Small wiggle when dragging over.
          }}
          transition={{
            y:      { duration: 3,   repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: 0.4 },
          }}
          className="inline-block mb-6"
        >
          <div className="relative">
            {/* Gradient icon container. */}
            <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-accent-violet via-accent-fuchsia to-accent-cyan flex items-center justify-center shadow-2xl shadow-accent-violet/40">
              <Upload className="w-11 h-11 text-white" strokeWidth={2} />
            </div>
            {/* Blurred halo behind the icon — gives the "glowing" effect. */}
            <div className="absolute -inset-2 rounded-3xl bg-gradient-to-br from-accent-violet to-accent-fuchsia blur-2xl opacity-40 -z-10" />
          </div>
        </motion.div>

        {/* Headline changes while dragging for tactile feedback. */}
        <h2 className="text-3xl md:text-4xl font-display font-bold mb-3">
          {isDragActive ? 'Release to scan' : (
            <>Drop your image <span className="text-gradient">here</span></>
          )}
        </h2>

        {/* Sub-description emphasising that everything runs locally. */}
        <p className="text-white/60 mb-8 max-w-md mx-auto">
          Upload a photo containing barcodes or QR codes. The pipeline runs
          locally at <span className="font-mono text-accent-cyan">localhost:5000</span>
          &nbsp;— nothing leaves your machine.
        </p>

        {/* Browse button + supported format list. */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          {/* stopPropagation prevents a second open dialog when the button is clicked. */}
          <button className="btn-primary flex items-center gap-2" onClick={(e) => e.stopPropagation()} type="button">
            <ImageIcon className="w-4 h-4" />
            Browse files
          </button>
          <div className="flex items-center gap-2 text-xs text-white/40 font-mono">
            <span>PNG · JPG · WEBP · BMP · TIFF</span>
          </div>
        </div>

        {/* Three tiny info cards highlighting key pipeline features. */}
        <div className="mt-12 grid grid-cols-3 gap-4 max-w-md mx-auto">
          {[
            { label: 'Multi-scale', desc: '3 scales' },
            { label: 'Pipeline',    desc: '4 stages' },
            { label: 'Local only',  desc: '0 cloud'  },
          ].map((f, i) => (
            <div key={i} className="px-3 py-2 rounded-xl glass text-center">
              <div className="text-[10px] uppercase tracking-wider text-white/40">
                {f.label}
              </div>
              <div className="text-sm font-semibold text-white/90 font-mono">
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
