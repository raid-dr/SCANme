"""
Stage 2a of the pipeline — QR code localisation.
Finds candidate QR codes by detecting the three finder patterns (concentric squares) and their right-angle geometry.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import cv2                                       # OpenCV — edge detection, contour analysis, Harris corners
import numpy as np                               # Array math — point coordinates, norms, dot products
from itertools import combinations               # Generates (A,B,C) triplets from the candidate list


def detect_qr_codes(gray, blurred, binary, original_img=None):
    """
    Detect QR code regions and return a list of bounding quadrilaterals.
    Each detection includes diagnostic intermediates used by the GUI "Steps" panel.
    """
    detections = []                              # List of final QR detections to return
    intermediates = {}                           # Diagnostic images used by the frontend

    # ── 1. Canny edge detection ─────────────────────────────────────────────
    # Canny returns a thin edge map; thresholds 50 (low) / 150 (high) are a safe default.
    edges = cv2.Canny(blurred, 50, 150)
    intermediates['canny_edges'] = edges.copy()  # Save for the GUI visualisation.

    # ── 2. Contour extraction with full hierarchy ───────────────────────────
    # RETR_TREE preserves parent-child relationships — we need nesting to find finder patterns.
    contours, hierarchy = cv2.findContours(
        edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    # If no contours were found, there's nothing to detect.
    if hierarchy is None or len(contours) == 0:
        return detections

    # hierarchy is shaped (1, N, 4); unwrap the outer dimension.
    hierarchy = hierarchy[0]                      # Now shape (N, 4) — [next, prev, child, parent]

    # ── 3. Find finder-pattern candidates (nested squares) ──────────────────
    finder_candidates = _find_finder_pattern_candidates(contours, hierarchy)
    intermediates['finder_candidates_count'] = len(finder_candidates)

    # Overlay candidate centres on the original image (purely for visualisation).
    if original_img is not None:
        candidates_vis = original_img.copy()
        for fc in finder_candidates:
            center = fc['center']                 # Candidate centre (cx, cy)
            # Draw a red circle at the centre for clarity.
            cv2.circle(candidates_vis, (int(center[0]), int(center[1])), 10,
                       (0, 0, 255), 2)
            # Draw the candidate contour itself in green.
            cv2.drawContours(candidates_vis, [fc['contour']], -1, (0, 255, 0), 2)
        intermediates['candidates_vis'] = candidates_vis

    # ── 4. Confirm candidates with Harris corner response ───────────────────
    # Harris strongly responds at corners; finder-pattern corners should light up.
    harris = cv2.cornerHarris(gray.astype(np.float32), blockSize=2, ksize=3, k=0.04)
    # Normalize so we can apply an absolute threshold on a 0–255 scale.
    harris_norm = cv2.normalize(harris, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    intermediates['harris'] = harris_norm.copy()

    # First attempt: strict threshold.
    confirmed = _confirm_with_harris(finder_candidates, harris_norm, threshold=100)

    # If not enough confirmed, relax the threshold.
    if len(confirmed) < 3:
        confirmed = _confirm_with_harris(finder_candidates, harris_norm, threshold=50)

    # Last-resort fallback: use the raw candidates if we have at least 3.
    if len(confirmed) < 3:
        if len(finder_candidates) >= 3:
            confirmed = finder_candidates[:min(len(finder_candidates), 6)]

    intermediates['confirmed_count'] = len(confirmed)

    # Need at least 3 finder patterns to form a QR code.
    if len(confirmed) < 3:
        return detections

    # ── 5. Geometric verification: right-angle triangle check ───────────────
    # Three QR finder patterns always form an L-shape (right angle at the top-left corner).
    triplets = _find_right_angle_triplets(confirmed)

    # ── 6. For each valid triplet, compute the fourth corner and save the detection.
    for triplet in triplets:
        quad = _estimate_quad(triplet)           # Parallelogram completion
        if quad is not None:
            # Keep the three centres alongside for diagnostics.
            centers = [c['center'] for c in triplet]
            detections.append({
                'quad':           quad,
                'finder_centers': centers,
                'intermediates':  intermediates,
            })

    return detections


def _find_finder_pattern_candidates(contours, hierarchy, min_area=150):
    """
    Filter the contour list to those that look like QR finder patterns.
    Criteria: minimum area, 4–6 polygon vertices, near-1 aspect ratio, convex shape, and nested children.
    """
    candidates = []                               # Accumulator for valid candidates

    # Walk every contour alongside its hierarchy record.
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)           # Signed area of the polygon
        # Reject tiny contours — they're almost certainly noise.
        if area < min_area:
            continue

        # Approximate the contour with a polygon (Douglas-Peucker).
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

        # A finder pattern should approximate to a square-ish polygon (4 verts, sometimes 5–6).
        if len(approx) < 4 or len(approx) > 6:
            continue

        # Axis-aligned bounding box (used for aspect-ratio filter).
        x, y, w, h = cv2.boundingRect(contour)
        aspect = w / (h + 1e-6)                   # Add epsilon to avoid zero-division
        # Reject heavily elongated shapes.
        if aspect < 0.6 or aspect > 1.6:
            continue

        # Convexity filter: the contour should closely match its convex hull.
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area < 1:                         # Degenerate hull — skip.
            continue
        solidity = area / hull_area               # 1.0 = perfect convex
        if solidity < 0.7:
            continue

        # Count how deeply this contour is nested — QR finder patterns have concentric children.
        nesting_level = _count_nesting(i, hierarchy)
        if nesting_level >= 2:                    # Require at least 2 levels of nesting
            # Compute centre from the bounding box.
            cx = x + w // 2
            cy = y + h // 2
            # Record all the information we'll need later.
            candidates.append({
                'index':    i,
                'contour':  contour,
                'center':   (cx, cy),
                'area':     area,
                'bbox':     (x, y, w, h),
                'nesting':  nesting_level,
                'approx':   approx,
            })

    # Remove candidates that are essentially duplicates (same centre from different nesting levels).
    candidates = _deduplicate_candidates(candidates, min_dist=20)

    return candidates


def _count_nesting(idx, hierarchy):
    """Count how many nested child levels a contour has (finder patterns should have ≥2)."""
    depth = 0                                     # Track how many levels deep we've gone
    child = hierarchy[idx][2]                     # Index of the first child (-1 if none)
    # Walk down the child chain.
    while child != -1:
        depth += 1                                # Count this level
        # Among siblings at this level, prefer one that has its own children (deeper nesting).
        sibling = hierarchy[child][0]             # Next sibling index
        while sibling != -1:
            if hierarchy[sibling][2] != -1:       # This sibling has a child of its own
                child = sibling                   # Switch to the deeper branch
                break
            sibling = hierarchy[sibling][0]
        child = hierarchy[child][2]               # Descend one more level
    return depth


def _deduplicate_candidates(candidates, min_dist=20):
    """Collapse candidates whose centres are within `min_dist` pixels of each other."""
    # If there's only one (or none), nothing to dedupe.
    if len(candidates) <= 1:
        return candidates

    # Prefer candidates with the deepest nesting; they are most likely to be the true finder pattern.
    candidates.sort(key=lambda c: c['nesting'], reverse=True)
    kept = []                                     # Unique candidates we've accepted so far
    for cand in candidates:
        cx, cy = cand['center']
        too_close = False                         # Flag: does this candidate duplicate a kept one?
        for k in kept:
            kx, ky = k['center']
            # Euclidean distance between the two centres.
            if np.sqrt((cx - kx) ** 2 + (cy - ky) ** 2) < min_dist:
                too_close = True
                break
        if not too_close:
            kept.append(cand)
    return kept


def _confirm_with_harris(candidates, harris_norm, threshold=100):
    """Drop candidates whose Harris corner response is below `threshold` (likely false positives)."""
    confirmed = []
    for cand in candidates:
        cx, cy = cand['center']
        x, y, w, h = cand['bbox']

        # Inspect a window sized to the candidate's bounding box plus a few pixels of margin.
        pad = max(w, h) // 2 + 5
        y1 = max(0, cy - pad)                     # Clamp to image bounds (top)
        y2 = min(harris_norm.shape[0], cy + pad)
        x1 = max(0, cx - pad)
        x2 = min(harris_norm.shape[1], cx + pad)

        region = harris_norm[y1:y2, x1:x2]        # Extract the window of Harris responses
        if region.size == 0:                      # Empty region — skip.
            continue

        # Peak response within the window.
        max_response = region.max()
        if max_response >= threshold:             # Accept if the corner is strong enough.
            cand['harris_response'] = max_response
            confirmed.append(cand)

    return confirmed


def _find_right_angle_triplets(candidates, angle_tolerance=0.3):
    """Return triplets of candidates that form a right-angled triangle (with B as the corner)."""
    triplets = []

    # Enumerate every unique 3-element combination of candidate indices.
    for combo in combinations(range(len(candidates)), 3):
        # Retrieve the three centre points as float arrays for vector math.
        A = np.array(candidates[combo[0]]['center'], dtype=np.float64)
        B = np.array(candidates[combo[1]]['center'], dtype=np.float64)
        C = np.array(candidates[combo[2]]['center'], dtype=np.float64)

        # Test each of the three points as a potential right-angle vertex.
        for vertex_idx, (P, Q, R) in enumerate([
            (A, B, C),                            # Vertex = A
            (B, A, C),                            # Vertex = B
            (C, A, B),                            # Vertex = C
        ]):
            v1 = Q - P                            # Vector from the vertex to one other point
            v2 = R - P                            # Vector from the vertex to the third point
            norm1 = np.linalg.norm(v1)            # Length of v1
            norm2 = np.linalg.norm(v2)            # Length of v2
            # Reject degenerate (near-zero-length) vectors.
            if norm1 < 1 or norm2 < 1:
                continue

            # Cosine of the angle — 0 means perpendicular.
            cos_angle = abs(np.dot(v1, v2) / (norm1 * norm2))
            if cos_angle < angle_tolerance:
                # Reorder the triplet so the right-angle vertex is at index 0.
                indices = list(combo)
                right_angle_cand = candidates[indices[vertex_idx]]
                others = [candidates[indices[j]] for j in range(3) if j != vertex_idx]
                triplets.append([right_angle_cand] + others)
                break                             # One valid configuration is enough per triplet.

    return triplets


def _estimate_quad(triplet):
    """Given 3 finder centres, estimate the fourth corner via parallelogram completion."""
    # Unpack the three centres; triplet[0] is the right-angle vertex.
    right_angle = np.array(triplet[0]['center'], dtype=np.float32)
    p1 = np.array(triplet[1]['center'], dtype=np.float32)
    p2 = np.array(triplet[2]['center'], dtype=np.float32)

    # Fourth corner is obtained by vector addition: p4 = p1 + p2 − right_angle.
    p4 = p1 + p2 - right_angle

    # Stack the four points and sort them into a consistent [TL, TR, BR, BL] order.
    points = np.array([right_angle, p1, p2, p4], dtype=np.float32)
    quad = _order_points(points)

    # Guard against invalid point sets.
    if quad is None:
        return None

    # Expand the quad slightly so the crop includes a small margin around the QR code.
    center = np.mean(quad, axis=0)               # Centroid of the quad
    margin = 1.1                                 # 10 % expansion factor
    expanded = center + margin * (quad - center) # Scale vectors outward from the centroid

    return expanded.astype(np.float32)


def _order_points(pts):
    """Sort four points into [top-left, top-right, bottom-right, bottom-left] order."""
    # Must receive exactly four points.
    if len(pts) != 4:
        return None

    s = pts.sum(axis=1)                           # Sum (x+y) — TL has min, BR has max.
    d = np.diff(pts, axis=1).flatten()            # y−x — TR has min, BL has max.

    # Pre-allocate the ordered array.
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]                # Top-left (smallest x+y)
    ordered[2] = pts[np.argmax(s)]                # Bottom-right (largest x+y)
    ordered[1] = pts[np.argmin(d)]                # Top-right (smallest y−x)
    ordered[3] = pts[np.argmax(d)]                # Bottom-left (largest y−x)

    return ordered
