"""
Stage 3 of the pipeline — perspective correction.
Straightens detected code regions (perspective warp for QR, affine rotation for barcodes) before decoding.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — homography and affine warp primitives
import numpy as np                               # Array math for geometry computations


def perspective_correct_qr(img, quad):
    """
    Warp a QR code quadrilateral into a front-facing rectangle using a 3×3 homography.
    The destination size is derived from the longer edges of the source quad.
    """
    # Guard against invalid quads (e.g. fewer than 4 corners).
    if quad is None or len(quad) != 4:
        return None

    # Cast to float32 (required by OpenCV's homography functions).
    src_pts = quad.astype(np.float32)

    # Estimate output width using the longest horizontal edge.
    width_top = np.linalg.norm(src_pts[1] - src_pts[0])   # TR − TL
    width_bot = np.linalg.norm(src_pts[2] - src_pts[3])   # BR − BL
    width = int(max(width_top, width_bot))

    # Estimate output height using the longest vertical edge.
    height_left = np.linalg.norm(src_pts[3] - src_pts[0]) # BL − TL
    height_right = np.linalg.norm(src_pts[2] - src_pts[1])# BR − TR
    height = int(max(height_left, height_right))

    # Reject degenerate quads that would produce near-empty output.
    if width < 10 or height < 10:
        return None

    # Destination is an axis-aligned rectangle at the origin.
    dst_pts = np.array([
        [0, 0],                                   # TL
        [width - 1, 0],                           # TR
        [width - 1, height - 1],                  # BR
        [0, height - 1]                           # BL
    ], dtype=np.float32)

    # Compute the 3×3 homography that maps src_pts → dst_pts.
    H = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Apply the warp. The output is the rectified QR patch.
    warped = cv2.warpPerspective(img, H, (width, height))

    return warped


def perspective_correct_barcode(roi, angle_degrees):
    """
    Rotate a barcode ROI by the given angle so the bars become vertical.
    Uses an affine 2D rotation; the output canvas is enlarged to avoid clipping.
    """
    # Handle empty inputs gracefully.
    if roi is None or roi.size == 0:
        return roi

    h, w = roi.shape[:2]                          # Input dimensions
    center = (w // 2, h // 2)                     # Rotate about the image centre

    # Build a 2×3 rotation matrix (no scale change).
    M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)

    # Compute the enlarged bounding box so the rotated content isn't cropped.
    cos_a = abs(M[0, 0])
    sin_a = abs(M[0, 1])
    new_w = int(h * sin_a + w * cos_a)
    new_h = int(h * cos_a + w * sin_a)

    # Shift the transform so the rotated image is centered in the new canvas.
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    # Apply the affine warp with a white border (barcodes sit on white quiet zones).
    rotated = cv2.warpAffine(roi, M, (new_w, new_h), borderValue=255)

    return rotated


def auto_crop_barcode(rotated):
    """
    Tighten the crop around a rotated barcode by removing the white padding added during rotation.
    Returns the rotated image unchanged if it's empty or fully white.
    """
    # Handle empty inputs gracefully.
    if rotated is None or rotated.size == 0:
        return rotated

    # Work on a grayscale copy so thresholding is straightforward.
    if len(rotated.shape) == 3:
        gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
    else:
        gray = rotated

    # Invert and Otsu-threshold so barcode pixels become white.
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)             # Locations of non-zero (barcode) pixels

    # If the image is completely white, don't crop.
    if coords is None:
        return rotated

    # Tight bounding box of the non-zero pixels, plus a small pad.
    x, y, w, h = cv2.boundingRect(coords)
    pad = 10
    y1 = max(0, y - pad)
    y2 = min(gray.shape[0], y + h + pad)
    x1 = max(0, x - pad)
    x2 = min(gray.shape[1], x + w + pad)

    # Return the cropped region from the original (still colour-preserving) input.
    return rotated[y1:y2, x1:x2]
