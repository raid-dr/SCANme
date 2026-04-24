"""
Top-level pipeline orchestrator — combines preprocessing, detection, correction, and decoding.
Exposes `scan()` (the public API) and `draw_annotations()` (used to render detection overlays).
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — used for final annotation drawing
import numpy as np                               # Array math for bounding-box drawing
import time                                      # Measures total pipeline runtime

# ── Internal pipeline imports ───────────────────────────────────────────────
from pipeline.preprocess    import preprocess, preprocess_at_scale
from pipeline.detect_qr     import detect_qr_codes
from pipeline.detect_barcode import detect_barcodes
from pipeline.perspective   import (
    perspective_correct_qr,
    perspective_correct_barcode,
    auto_crop_barcode,
)
from pipeline.decoder       import decode_patch, decode_full_image


def scan(image_path=None, img=None, scales=(1.0, 0.5, 2.0)):
    """
    Run the complete barcode/QR scanning pipeline at multiple scales.
    Accepts either a file path or a preloaded BGR image; returns detections, annotated image, and timing info.
    """
    t_start = time.time()                         # Start timer for processing_time measurement

    # ── Load or use the provided image ──────────────────────────────────────
    if img is None:
        # Must have at least one source of image data.
        if image_path is None:
            raise ValueError("Provide image_path or img.")
        # Decode the image from disk (BGR by default).
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

    all_detections = []                           # Aggregated list of detections from all scales
    prep_at_1x = None                             # Preprocessing dict at scale 1.0 (saved for the frontend)
    seen_data = set()                             # Deduplication key set: (type, data)

    # ── Multi-scale loop ────────────────────────────────────────────────────
    for scale in scales:
        # Preprocess (and resize) the image for this scale.
        prep, scaled_img = preprocess_at_scale(img, scale)

        # Remember the 1x preprocessing outputs so the GUI can display them.
        if abs(scale - 1.0) < 1e-6:
            prep_at_1x = prep

        # Unpack the intermediates for the detectors.
        gray    = prep['gray']
        blurred = prep['blurred']
        binary  = prep['binary']

        # ── QR detection track ─────────────────────────────────────────────
        qr_detections = detect_qr_codes(gray, blurred, binary, scaled_img)

        for qr_det in qr_detections:
            quad = qr_det['quad']                 # 4×2 float quadrilateral

            # Convert quad back to original-image coordinates if we scaled.
            if abs(scale - 1.0) > 1e-6:
                quad = quad / scale

            # Perspective-correct the QR region on the ORIGINAL image (not the scaled copy).
            warped = perspective_correct_qr(img, quad)
            if warped is None:
                continue                          # Skip degenerate quads

            # Attempt to decode the rectified QR patch.
            decoded = decode_patch(warped, code_type='qr')

            # Save each successful decode (deduped by type/data).
            for d in decoded:
                key = (d['type'], d['data'])
                if key in seen_data:
                    continue
                seen_data.add(key)
                all_detections.append({
                    'type':          d['type'],
                    'data':          d['data'],
                    'quad':          quad,
                    'scale':         scale,
                    'track':         'qr',
                    'warped':        warped,
                    'intermediates': qr_det.get('intermediates', {}),
                })

        # ── Barcode detection track ────────────────────────────────────────
        bc_detections = detect_barcodes(gray, blurred, binary)

        for bc_det in bc_detections:
            roi   = bc_det['roi']                 # Grayscale crop of the barcode region
            angle = bc_det['angle']               # Estimated tilt angle

            # Rotate the ROI to align bars vertically, then tighten the crop.
            corrected = perspective_correct_barcode(roi, angle)
            corrected = auto_crop_barcode(corrected)

            # Skip empty outputs.
            if corrected is None or corrected.size == 0:
                continue

            # Upscale small crops — pyzbar needs a minimum resolution to decode reliably.
            if corrected.shape[0] < 100 or corrected.shape[1] < 200:
                upscale = max(2, 200 // max(corrected.shape[1], 1))
                corrected = cv2.resize(
                    corrected, None, fx=upscale, fy=upscale,
                    interpolation=cv2.INTER_CUBIC
                )

            # Attempt to decode the corrected patch.
            decoded = decode_patch(corrected, code_type='barcode')

            # Convert quad coordinates back to the original image space.
            quad = bc_det['quad'].copy()
            if abs(scale - 1.0) > 1e-6:
                quad = quad / scale

            # Save each successful decode (deduped).
            for d in decoded:
                key = (d['type'], d['data'])
                if key in seen_data:
                    continue
                seen_data.add(key)
                all_detections.append({
                    'type':          d['type'],
                    'data':          d['data'],
                    'quad':          quad,
                    'scale':         scale,
                    'track':         'barcode',
                    'warped':        corrected,
                    'intermediates': bc_det.get('intermediates', {}),
                })

    # ── Fallback pass: pyzbar on the full original image ────────────────────
    direct_results = decode_full_image(img)
    for d in direct_results:
        key = (d['type'], d['data'])
        if key in seen_data:
            continue                              # Skip duplicates already found by detectors
        seen_data.add(key)

        # Build a quad from the pyzbar polygon (4 points) or fall back to the bbox corners.
        if d['polygon'] and len(d['polygon']) >= 4:
            quad = np.array(d['polygon'][:4], dtype=np.float32)
        else:
            rx, ry, rw, rh = d['rect']
            quad = np.array([
                [rx, ry], [rx + rw, ry],
                [rx + rw, ry + rh], [rx, ry + rh]
            ], dtype=np.float32)

        all_detections.append({
            'type':          d['type'],
            'data':          d['data'],
            'quad':          quad,
            'scale':         1.0,
            'track':         'direct',
            'warped':        None,
            'intermediates': {},
        })

    # ── Render the annotated result image ───────────────────────────────────
    annotated = draw_annotations(img, all_detections)

    t_end = time.time()                           # Stop timer

    # Return the full result object — consumed by server.py and callers.
    return {
        'detections':      all_detections,
        'annotated':       annotated,
        'preprocessing':   prep_at_1x,
        'processing_time': t_end - t_start,
    }


def draw_annotations(img, detections):
    """
    Overlay coloured bounding quadrilaterals and decoded-data labels on the input image.
    Each track has its own colour: QR = green, barcode = blue, direct decode = yellow.
    """
    overlay = img.copy()                          # Work on a copy so the caller's image is untouched.

    for det in detections:
        quad = det.get('quad')
        if quad is None:
            continue                              # Skip detections without geometry.

        pts = np.array(quad, dtype=np.int32)      # Integer points required by cv2.polylines.

        # Choose colour by track: green for QR, blue for barcode, yellow for direct.
        color = (0, 255, 0)                       # Default = green (QR)
        if det['track'] == 'barcode':
            color = (255, 0, 0)                   # Pure blue in BGR
        elif det['track'] == 'direct':
            color = (0, 255, 255)                 # Yellow in BGR

        # Draw the quadrilateral outline.
        cv2.polylines(overlay, [pts], isClosed=True, color=color, thickness=3)

        # Compose the label text (truncated to 30 chars).
        label = f"{det['type']}: {det['data'][:30]}"
        label_pos = tuple(pts[0])                 # Draw near the top-left corner of the quad.

        # Measure the label so we can draw a filled background rectangle.
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        # Filled rectangle behind the label for readability.
        cv2.rectangle(
            overlay,
            (label_pos[0], label_pos[1] - text_h - 10),
            (label_pos[0] + text_w, label_pos[1]),
            color, -1
        )
        # Black label text on top of the coloured rectangle.
        cv2.putText(
            overlay, label, (label_pos[0], label_pos[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
        )

    return overlay
