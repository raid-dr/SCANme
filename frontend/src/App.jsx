// Top-level React component — owns the application state and wires the UI components together.
// Handles image selection, scan requests to the Flask backend, export, and toast notifications.

import { useState, useCallback }     from 'react';       // React hooks for local state and memoized callbacks.
import { AnimatePresence, motion }   from 'framer-motion';// Mount/unmount animations for UI panels.

// ── Child components — each lives in ./components/ ────────────────────────
import Header        from './components/Header.jsx';
import UploadZone    from './components/UploadZone.jsx';
import ScanViewer    from './components/ScanViewer.jsx';
import ResultsPanel  from './components/ResultsPanel.jsx';
import StepsViewer   from './components/StepsViewer.jsx';
import Toast         from './components/Toast.jsx';

export default function App() {
  // Currently selected image file (Blob from the upload input).
  const [imageFile, setImageFile]       = useState(null);
  // Data-URL preview of the selected image (shown before scanning).
  const [imagePreview, setImagePreview] = useState(null);
  // Response object from the /api/scan endpoint (detections, annotated, steps, ...).
  const [scanResult, setScanResult]     = useState(null);
  // Boolean toggled while the backend is processing the request.
  const [scanning, setScanning]         = useState(false);
  // Controls the visibility of the intermediate-steps panel.
  const [showSteps, setShowSteps]       = useState(false);
  // Transient toast notification ({ type, message }) or null when hidden.
  const [toast, setToast]               = useState(null);

  // ── Handler: user picked a new image (via drop or file picker) ─────────
  const handleImageSelect = useCallback((file) => {
    setImageFile(file);                          // Store the raw file for later upload.
    setScanResult(null);                         // Clear any stale results from a previous scan.
    // Read the image as a data URL so <img src="..."> can render it instantly.
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  }, []);

  // ── Handler: run the scan by POSTing the image to /api/scan ────────────
  const handleScan = useCallback(async () => {
    if (!imageFile) return;                      // Nothing to scan yet.
    setScanning(true);                           // Flip the loading flag (triggers overlay UI).
    setScanResult(null);                         // Clear previous results.

    // Multipart form body — Flask reads this as request.files['image'].
    const formData = new FormData();
    formData.append('image', imageFile);

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        body: formData,
      });

      // Non-2xx response → surface the error message (if present).
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      // Parse the JSON response and store it in state.
      const data = await res.json();
      setScanResult(data);

      // Build a friendly toast message based on the outcome.
      setToast({
        type: data.detections.length ? 'success' : 'warn',
        message: data.detections.length
          ? `Decoded ${data.detections.length} code${data.detections.length > 1 ? 's' : ''} in ${data.processing_time.toFixed(2)}s`
          : 'No codes detected.',
      });
    } catch (e) {
      // Network / parse / backend error — show it as a red toast.
      setToast({ type: 'error', message: e.message });
    } finally {
      setScanning(false);                        // Always clear the loading flag.
    }
  }, [imageFile]);

  // ── Handler: user wants to start over with a new image ─────────────────
  const handleReset = useCallback(() => {
    setImageFile(null);
    setImagePreview(null);
    setScanResult(null);
  }, []);

  // ── Handler: download the annotated PNG and a JSON report ──────────────
  const handleExport = useCallback(() => {
    if (!scanResult) return;                     // Nothing to export.

    // Trigger browser download of the annotated PNG.
    const annotatedUrl = `data:image/png;base64,${scanResult.annotated}`;
    const a = document.createElement('a');
    a.href = annotatedUrl;
    a.download = `scan_annotated_${Date.now()}.png`;
    a.click();

    // Build and trigger download of a JSON report of detections.
    const json = JSON.stringify(
      {
        scan_time:       new Date().toISOString(),
        processing_time: scanResult.processing_time,
        detections:      scanResult.detections,
      },
      null,
      2
    );
    const jsonBlob = new Blob([json], { type: 'application/json' });
    const jsonUrl  = URL.createObjectURL(jsonBlob);
    const b = document.createElement('a');
    b.href = jsonUrl;
    b.download = `scan_results_${Date.now()}.json`;
    b.click();
    URL.revokeObjectURL(jsonUrl);                // Free the blob URL now that download has started.

    // Notify the user that the export succeeded.
    setToast({ type: 'success', message: 'Exported PNG + JSON to Downloads' });
  }, [scanResult]);

  // ── Rendered layout ────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top navigation header with the ScanMe logo. */}
      <Header />

      {/* Main content grid: viewer on the left, results on the right. */}
      <main className="flex-1 px-4 md:px-8 pb-8">
        <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-5">
          {/* Left column: upload zone OR image viewer, plus optional steps panel. */}
          <div className="flex flex-col gap-5">
            <AnimatePresence mode="wait">
              {!imagePreview ? (
                // Upload zone is shown when no image has been selected yet.
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4 }}
                >
                  <UploadZone onSelect={handleImageSelect} />
                </motion.div>
              ) : (
                // Once an image is selected, show the viewer with toolbar controls.
                <motion.div
                  key="viewer"
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  <ScanViewer
                    imageUrl={
                      // Prefer annotated image once the scan is complete.
                      scanResult?.annotated
                        ? `data:image/png;base64,${scanResult.annotated}`
                        : imagePreview
                    }
                    scanning={scanning}
                    annotated={!!scanResult?.annotated}
                    onScan={handleScan}
                    onReset={handleReset}
                    onExport={handleExport}
                    hasResults={!!scanResult}
                    showSteps={showSteps}
                    onToggleSteps={() => setShowSteps((s) => !s)}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Collapsible panel showing intermediate pipeline images. */}
            <AnimatePresence>
              {showSteps && scanResult?.steps && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <StepsViewer steps={scanResult.steps} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right column: detections list + stats. */}
          <ResultsPanel
            result={scanResult}
            scanning={scanning}
            hasImage={!!imagePreview}
          />
        </div>
      </main>

      {/* Bottom-centred toast notification (auto-dismisses after ~3.5s). */}
      <AnimatePresence>
        {toast && (
          <Toast
            key={toast.message}
            type={toast.type}
            message={toast.message}
            onDone={() => setToast(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
