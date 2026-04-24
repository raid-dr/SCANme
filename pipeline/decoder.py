"""
Stage 4 of the pipeline — payload decoding.
Uses pyzbar as the primary decoder, with OpenCV's QRCodeDetector and several preprocessing variants as fallbacks.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — used for fallback QR decoder and preprocessing
import numpy as np                               # Array math (only for shape checks)
from pyzbar.pyzbar import decode as pyzbar_decode  # pyzbar handles EAN-13, CODE128, QR, etc.


def decode_patch(warped_img, code_type='any'):
    """
    Try to decode a perspective-corrected image patch.
    Uses pyzbar, then OpenCV's QRCodeDetector, then preprocessing variants, and returns a list of results.
    """
    # Empty or malformed patches cannot produce a decode result.
    if warped_img is None or warped_img.size == 0:
        return []

    results = []                                 # Accumulator for decoded detections

    # ── Attempt 1: pyzbar directly on the patch ──────────────────────────────
    try:
        pyzbar_results = pyzbar_decode(warped_img)
        for obj in pyzbar_results:
            # Convert the pyzbar result into our standard dict shape.
            results.append({
                'type':    obj.type,             # e.g. 'QRCODE', 'EAN13'
                'data':    obj.data.decode('utf-8', errors='replace'),  # Decoded payload
                'polygon': [(p.x, p.y) for p in obj.polygon] if obj.polygon else [],
                'rect':    (obj.rect.left, obj.rect.top,
                            obj.rect.width, obj.rect.height),
            })
    except Exception:
        # pyzbar can throw on unusual inputs; treat as "no decode".
        pass

    # ── Attempt 2: OpenCV's built-in QR decoder (QR-only) ───────────────────
    if not results and code_type in ('qr', 'any'):
        results = _try_opencv_qr_detector(warped_img)

    # ── Attempt 3: try different preprocessing variants ─────────────────────
    if not results:
        results = _try_with_preprocessing(warped_img)

    return results


def _try_opencv_qr_detector(img):
    """Fallback QR decoder using OpenCV's built-in QRCodeDetector."""
    results = []
    try:
        detector = cv2.QRCodeDetector()
        # detectAndDecode returns (decoded_text, corner_points, rectified_image).
        data, points, _ = detector.detectAndDecode(img)
        if data:                                  # Non-empty string means success.
            results.append({
                'type':    'QRCODE',
                'data':    data,
                'polygon': points.tolist() if points is not None else [],
                'rect':    (0, 0, img.shape[1], img.shape[0]),
            })
    except Exception:
        pass
    return results


def _try_with_preprocessing(img):
    """
    Try three preprocessing variants sequentially, stopping at the first successful decode:
      1) Histogram equalization · 2) Otsu binarization · 3) Colour inversion.
    """
    results = []

    # Ensure we're working in grayscale.
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # ── Variant 1: histogram equalization ───────────────────────────────────
    equalized = cv2.equalizeHist(gray)
    try:
        decoded = pyzbar_decode(equalized)
        for obj in decoded:
            results.append({
                'type': obj.type,
                'data': obj.data.decode('utf-8', errors='replace'),
                'polygon': [(p.x, p.y) for p in obj.polygon] if obj.polygon else [],
                'rect': (obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height),
            })
        if results:
            return results                        # Stop at first success.
    except Exception:
        pass

    # ── Variant 2: Otsu threshold ───────────────────────────────────────────
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    try:
        decoded = pyzbar_decode(binary)
        for obj in decoded:
            results.append({
                'type': obj.type,
                'data': obj.data.decode('utf-8', errors='replace'),
                'polygon': [(p.x, p.y) for p in obj.polygon] if obj.polygon else [],
                'rect': (obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height),
            })
        if results:
            return results
    except Exception:
        pass

    # ── Variant 3: colour inversion ─────────────────────────────────────────
    inverted = cv2.bitwise_not(gray)
    try:
        decoded = pyzbar_decode(inverted)
        for obj in decoded:
            results.append({
                'type': obj.type,
                'data': obj.data.decode('utf-8', errors='replace'),
                'polygon': [(p.x, p.y) for p in obj.polygon] if obj.polygon else [],
                'rect': (obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height),
            })
    except Exception:
        pass

    return results


def decode_full_image(img):
    """
    Run pyzbar on the entire image as a supplementary pass.
    Catches codes whose localisation was missed by the earlier pipeline stages.
    """
    results = []

    # Use grayscale for maximum pyzbar compatibility.
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Run pyzbar on the full image.
    try:
        decoded = pyzbar_decode(gray)
        for obj in decoded:
            polygon = [(p.x, p.y) for p in obj.polygon] if obj.polygon else []
            results.append({
                'type':    obj.type,
                'data':    obj.data.decode('utf-8', errors='replace'),
                'polygon': polygon,
                'rect':    (obj.rect.left, obj.rect.top,
                            obj.rect.width, obj.rect.height),
                'source':  'direct_pyzbar',       # Marker for the scanner aggregator.
            })
    except Exception:
        pass

    return results
