#!/usr/bin/env python3
"""
Flask REST API backend for the ScanMe barcode/QR code scanner.
Exposes the OpenCV pipeline (in ./pipeline) as JSON endpoints consumed by the React frontend.
"""

# ── Standard library imports ────────────────────────────────────────────────
import os                                        # File path utilities (static folder, env vars)
import sys                                       # Used to insert project root into import path
import base64                                    # Encodes annotated images as text for JSON transport

# ── Third-party imports ─────────────────────────────────────────────────────
import cv2                                       # OpenCV — decodes uploaded image bytes, encodes PNGs
import numpy as np                               # Converts raw bytes into a NumPy image array
from flask import Flask, request, jsonify, send_from_directory  # Flask web-server primitives
from flask_cors import CORS                      # Enables cross-origin calls from the React dev server

# Make sure the project root is on the Python path so "from pipeline.scanner import scan" works.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Project imports ─────────────────────────────────────────────────────────
from pipeline.scanner import scan                # Full scanning pipeline (preprocess → detect → decode)


# Absolute path to the built React bundle; served in production mode.
FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),  # <project>/
    'frontend', 'dist'                           # <project>/frontend/dist (Vite build output)
)

# Create the Flask application; static_folder points to the React build output.
app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path='')

# Allow cross-origin requests — needed when running Vite (5173) and Flask (5000) separately.
CORS(app)


def _encode_image_base64(img):
    """
    Convert a NumPy image array to a base64-encoded PNG string.
    Returns None if the image is empty or cannot be encoded.
    """
    # Guard against None or non-array inputs so the endpoint never crashes.
    if img is None or not isinstance(img, np.ndarray):
        return None
    # Encode the NumPy array as PNG bytes in memory; `ok` is True on success.
    ok, buf = cv2.imencode('.png', img)
    # If encoding fails (unlikely for valid arrays), return None.
    if not ok:
        return None
    # Convert the PNG bytes to a plain ASCII base64 string safe for JSON.
    return base64.b64encode(buf.tobytes()).decode('utf-8')


@app.route('/api/health', methods=['GET'])
def health():
    """Simple liveness endpoint — the frontend can ping this to verify the server is up."""
    # Return a static JSON payload; no computation required.
    return jsonify({'status': 'ok', 'service': 'scanme-backend'})


@app.route('/api/scan', methods=['POST'])
def scan_endpoint():
    """
    Main endpoint: receives an uploaded image, runs the pipeline,
    and returns detections + annotated image + intermediate processing steps.
    """
    # Ensure the request contains a file under the 'image' form-data key.
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    # Retrieve the FileStorage object from the request.
    file = request.files['image']
    # Reject empty file uploads (e.g. when users submit without selecting a file).
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # Read the raw bytes of the uploaded image into memory.
    img_bytes = file.read()
    # Wrap the bytes in a NumPy uint8 buffer for OpenCV to decode.
    nparr = np.frombuffer(img_bytes, np.uint8)
    # Decode the buffer into a BGR image; returns None for invalid/corrupt files.
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Validate the decoded image.
    if img is None:
        return jsonify({'error': 'Could not decode image'}), 400

    # Run the full pipeline; catch any unexpected exception so the client gets a clean error.
    try:
        result = scan(img=img)
    except Exception as e:
        return jsonify({'error': f'Pipeline failed: {str(e)}'}), 500

    # Encode the final annotated image (with colored bounding rectangles) as base64.
    annotated_b64 = _encode_image_base64(result['annotated'])

    # Collect intermediate images produced during preprocessing (for the GUI "Steps" view).
    steps = {}
    prep = result.get('preprocessing')              # May be None if scan failed early.
    if prep:
        # These four are standard for every scan (grayscale → Gaussian → bilateral → binary).
        for key in ('gray', 'blurred', 'bilateral', 'binary'):
            img_step = prep.get(key)                 # Look up the NumPy array by name.
            if img_step is not None:                 # Skip missing/optional steps (bilateral is optional).
                encoded = _encode_image_base64(img_step)
                if encoded:
                    steps[key] = encoded             # Add to the response dict keyed by step name.

    # If the pipeline produced any detections, include each detection's diagnostic intermediates.
    if result['detections']:
        first = result['detections'][0]              # Take the first detection's intermediates only.
        inter = first.get('intermediates', {})       # Empty dict if the detection has none.
        # Canny edges, Harris corners, Sobel gradient, morphology stages — all optional.
        for key in ('canny_edges', 'harris', 'gradient',
                    'morphological_closed', 'thresholded'):
            img_step = inter.get(key)
            if img_step is not None:
                encoded = _encode_image_base64(img_step)
                if encoded:
                    steps[key] = encoded

        # The perspective-corrected patch that was fed to pyzbar, if available.
        warped = first.get('warped')
        if warped is not None:
            encoded = _encode_image_base64(warped)
            if encoded:
                steps['corrected_patch'] = encoded

    # Serialize detections into a plain list of dicts (no NumPy arrays allowed in JSON).
    detections = []
    for d in result['detections']:
        quad = d.get('quad')                        # Bounding quadrilateral (4×2 float array).
        if isinstance(quad, np.ndarray):
            quad = quad.tolist()                    # Convert to plain Python list for JSON.
        # Build a clean, JSON-safe record for this detection.
        detections.append({
            'type':  d.get('type'),                 # e.g. 'QRCODE', 'EAN13', 'CODE128'
            'data':  d.get('data'),                 # Decoded string payload
            'track': d.get('track'),                # 'qr' | 'barcode' | 'direct'
            'scale': float(d.get('scale', 1.0)),    # Scale factor at which it was detected
            'quad':  quad,                          # Polygon points for frontend overlay
        })

    # Return the full scan response as JSON.
    return jsonify({
        'detections':      detections,              # All decoded codes
        'annotated':       annotated_b64,           # PNG of the original with colored rectangles
        'steps':           steps,                   # Intermediate pipeline images
        'processing_time': result['processing_time'],  # Total pipeline runtime in seconds
    })


# ── Serve the React frontend (production build) ─────────────────────────────
@app.route('/', defaults={'path': ''})               # Root URL → index.html
@app.route('/<path:path>')                           # Any other path → matching static file
def serve_frontend(path):
    """Serve files from frontend/dist; fall back to index.html so React Router (if added) keeps working."""
    # If no build exists yet, return a helpful error message instead of 404.
    if not os.path.exists(FRONTEND_DIST):
        return jsonify({
            'error': 'Frontend not built.',
            'hint':  'Run: cd frontend && npm install && npm run build'
        }), 503

    # If the requested path maps to an existing asset (JS/CSS/img), serve it directly.
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    # Otherwise serve the SPA entry point.
    return send_from_directory(FRONTEND_DIST, 'index.html')


# Standard Python entry-point guard — only run the server when invoked directly.
if __name__ == '__main__':
    # Allow the port to be overridden via environment variable (defaults to 5000).
    port = int(os.environ.get('PORT', 5000))
    # Print a friendly banner so users can see where to point their browser.
    print(f"\n  ScanMe API running on http://localhost:{port}")
    print(f"  Health check:  http://localhost:{port}/api/health\n")
    # Run the Flask development server; debug=True enables hot-reload on file changes.
    app.run(host='0.0.0.0', port=port, debug=True)
