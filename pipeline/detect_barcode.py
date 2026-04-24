"""
Stage 2b of the pipeline — 1D barcode localisation.
Detects EAN-13 / CODE128 / UPC-style barcodes via Sobel gradient density and Hough-based tilt estimation.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — Sobel, morphology, Hough transform
import numpy as np                               # Array math for angles and line coordinates


def detect_barcodes(gray, blurred, binary=None, min_area=2000,
                    morph_ksize=(21, 7), gradient_blur_ksize=(9, 9)):
    """
    Detect 1D barcode regions by finding areas of high horizontal-gradient density.
    Returns a list of candidate detections with bounding box, ROI crop, and estimated tilt angle.
    """
    detections = []                              # Final list of barcode candidates
    intermediates = {}                           # Diagnostic images for the frontend

    # ── 1. Sobel gradients in X and Y ───────────────────────────────────────
    # Sobel_x captures vertical edges (strong for barcodes); Sobel_y captures horizontal edges.
    sobel_x = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)

    # Take absolute values so we can compare magnitudes without sign cancellation.
    sobel_x_abs = cv2.convertScaleAbs(sobel_x)
    sobel_y_abs = cv2.convertScaleAbs(sobel_y)

    # |Sobel_x| − |Sobel_y| isolates regions whose horizontal gradient dominates (i.e. vertical bars).
    gradient = cv2.subtract(sobel_x_abs, sobel_y_abs)
    intermediates['gradient'] = gradient.copy()

    # ── 2. Blur the gradient map to join nearby bar peaks ───────────────────
    blurred_grad = cv2.GaussianBlur(gradient, gradient_blur_ksize, 0)
    intermediates['blurred_gradient'] = blurred_grad.copy()

    # ── 3. Morphological closing to merge bar peaks into a solid region ─────
    # A wide, short kernel (21×7) connects bars horizontally without merging across rows.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, morph_ksize)
    closed = cv2.morphologyEx(blurred_grad, cv2.MORPH_CLOSE, kernel)
    intermediates['morphological_closed'] = closed.copy()

    # Extra erosion + dilation clean up residual noise.
    closed = cv2.erode(closed, None, iterations=4)
    closed = cv2.dilate(closed, None, iterations=4)
    intermediates['cleaned'] = closed.copy()

    # ── 4. Otsu threshold and contour extraction ────────────────────────────
    # Otsu picks an optimal threshold automatically based on the image histogram.
    _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    intermediates['thresholded'] = thresh.copy()

    # External contours only — we don't care about holes inside the barcode mask.
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Early exit if nothing was found.
    if not contours:
        return detections

    # Sort largest-first so the most promising candidates are processed first.
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Cap the candidate list so noisy images don't blow up processing time.
    MAX_CANDIDATES = 10
    for contour in contours[:MAX_CANDIDATES]:
        area = cv2.contourArea(contour)
        # Skip contours that are below the minimum barcode area threshold.
        if area < min_area:
            continue

        # Minimum-area rotated rectangle gives a cleaner bounding box for angled barcodes.
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)                 # Four corner points of the rotated rectangle
        box = np.intp(box)                        # Integer-cast for drawing

        # Axis-aligned bounding rectangle (easier for cropping the ROI).
        x, y, w, h = cv2.boundingRect(contour)

        # A barcode should be clearly wider than tall (or vice versa after rotation).
        aspect = max(w, h) / (min(w, h) + 1e-6)
        if aspect < 1.5:
            continue                              # Too square → probably not a 1D barcode.

        # ── 5. Estimate tilt using Hough line transform ─────────────────────
        angle = _estimate_tilt_hough(gray, x, y, w, h)

        # Crop the region of interest from the original grayscale, with a small pad.
        pad = 10
        y1 = max(0, y - pad)                      # Clamp to image bounds
        y2 = min(gray.shape[0], y + h + pad)
        x1 = max(0, x - pad)
        x2 = min(gray.shape[1], x + w + pad)
        roi = gray[y1:y2, x1:x2]

        # Build a 4-point quad from the axis-aligned rectangle for annotation drawing.
        quad = np.array([
            [x, y], [x + w, y], [x + w, y + h], [x, y + h]
        ], dtype=np.float32)

        # Record the detection.
        detections.append({
            'bbox':          (x, y, w, h),
            'roi':           roi,
            'angle':         angle,
            'contour':       contour,
            'quad':          quad,
            'box':           box,
            'intermediates': intermediates,
        })

    return detections


def _estimate_tilt_hough(gray, x, y, w, h, min_line_length=30):
    """
    Estimate the dominant bar angle within the given bounding box using the Hough line transform.
    Returns the angle in degrees that should be used for rotation correction.
    """
    # Add a small pad around the bounding box so edge pixels aren't clipped.
    pad = 5
    y1 = max(0, y - pad)
    y2 = min(gray.shape[0], y + h + pad)
    x1 = max(0, x - pad)
    x2 = min(gray.shape[1], x + w + pad)
    roi = gray[y1:y2, x1:x2]

    # Guard against empty ROIs.
    if roi.size == 0:
        return 0.0

    # Canny edges inside the ROI — required input for HoughLinesP.
    edges = cv2.Canny(roi, 50, 150)

    # Probabilistic Hough — faster than the standard version and returns line segments.
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,          # Resolution: 1 px, 1 deg
        threshold=30, minLineLength=min_line_length,
        maxLineGap=10                              # Merge collinear segments within 10 px
    )

    # No lines found — assume axis-aligned.
    if lines is None or len(lines) == 0:
        return 0.0

    # Compute the angle of each detected line segment.
    angles = []
    for line in lines:
        x1_l, y1_l, x2_l, y2_l = line[0]
        # arctan2 returns the angle in radians; convert to degrees.
        angle = np.degrees(np.arctan2(y2_l - y1_l, x2_l - x1_l))
        angles.append(angle)

    # Take the median — robust against outliers.
    median_angle = np.median(angles)

    # Normalise the angle into the range that the rotation routine expects.
    if abs(median_angle) < 45:
        return median_angle                       # Mild tilt — return directly
    elif median_angle > 0:
        return median_angle - 90                  # Rotate by 90° if bars are nearly horizontal
    else:
        return median_angle + 90
