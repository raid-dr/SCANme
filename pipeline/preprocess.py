"""
Stage 1 of the pipeline — image preprocessing.
Converts a raw BGR photo into grayscale, smoothed, and binarized variants used by later stages.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — all image operations (blur, threshold, etc.)
import numpy as np                               # Unused here directly, but kept for type safety/future extension


def preprocess(img, gaussian_ksize=(5, 5), gaussian_sigma=1.2,
               use_bilateral=False, bilateral_d=9,
               bilateral_sigma_color=75, bilateral_sigma_space=75,
               adaptive_block_size=11, adaptive_C=2):
    """
    Full preprocessing chain: grayscale → Gaussian blur → (optional bilateral) → adaptive threshold.
    Returns a dictionary containing all intermediate results for later stages and GUI display.
    """
    # Defensive check — a None image would crash cv2.cvtColor.
    if img is None:
        raise ValueError("Input image is None — check file path.")

    # ── 1. Grayscale conversion ─────────────────────────────────────────────
    # Convert BGR → single-channel grayscale using the standard luminance formula.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── 2. Gaussian blur ────────────────────────────────────────────────────
    # Smooth the image to suppress high-frequency noise before edge detection.
    # sigmaX controls the trade-off between noise removal and edge preservation.
    blurred = cv2.GaussianBlur(gray, gaussian_ksize, sigmaX=gaussian_sigma)

    # ── 3. Bilateral filter (optional) ──────────────────────────────────────
    # Bilateral smoothing keeps edges sharp while removing noise — useful for degraded images.
    bilateral = None                             # Initialise to None for consumers who check presence.
    if use_bilateral:
        bilateral = cv2.bilateralFilter(
            gray, d=bilateral_d,                  # Neighborhood diameter
            sigmaColor=bilateral_sigma_color,     # Tolerance in intensity domain
            sigmaSpace=bilateral_sigma_space      # Tolerance in spatial domain
        )

    # ── 4. Adaptive threshold ───────────────────────────────────────────────
    # Choose the cleanest source image: bilateral (if computed) else the Gaussian-blurred one.
    source_for_thresh = bilateral if bilateral is not None else blurred
    # Adaptive thresholding handles uneven lighting by computing a local threshold per pixel.
    binary = cv2.adaptiveThreshold(
        source_for_thresh, 255,                  # Max value for pixels above the threshold
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,          # Weighted Gaussian mean of the neighborhood
        cv2.THRESH_BINARY,                       # Output: 0 or 255
        adaptive_block_size, adaptive_C          # Window size (odd) and constant subtracted from mean
    )

    # Return every intermediate so callers can inspect or display them.
    return {
        'original':  img,                         # The input BGR image (unchanged)
        'gray':      gray,                        # Grayscale
        'blurred':   blurred,                     # Gaussian-smoothed
        'bilateral': bilateral,                   # Edge-preserving smoothed (or None)
        'binary':    binary,                      # Adaptive-thresholded binary image
    }


def preprocess_at_scale(img, scale):
    """
    Run the full preprocessing chain on a resized copy of the image.
    Used by the multi-scale scanner to detect codes of varying sizes.
    """
    # If the scale is essentially 1.0, skip the resize and run on the original.
    if abs(scale - 1.0) < 1e-6:
        return preprocess(img), img

    # Compute new dimensions scaled by the given factor.
    h, w = img.shape[:2]                          # Original height and width
    new_w, new_h = int(w * scale), int(h * scale) # Scaled dimensions (integer pixel counts)
    # INTER_AREA gives the best visual quality for down-scaling.
    scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    # Return the preprocessed dict AND the resized BGR image (for downstream coordinate math).
    return preprocess(scaled), scaled
