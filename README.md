# ScanMe — Barcode & QR Code Scanner

A local-first barcode and QR code scanner built on a classical computer-vision
pipeline (OpenCV + pyzbar) with a modern React frontend. Upload an image, and
the backend runs a multi-stage pipeline to locate, rectify, and decode every
1-D barcode and 2-D QR code it can find. Intermediate stages are returned so
the pipeline's behaviour is fully transparent and auditable.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Running the Project](#running-the-project)
7. [How the Pipeline Works](#how-the-pipeline-works)
8. [API Reference](#api-reference)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Features

- **Multi-scale detection** — the pipeline runs at 3 scales (0.5×, 1.0×, 2.0×)
  so both very small and very large codes are detected reliably.
- **QR + barcode support** — EAN-13, CODE128, CODE39, QR, DataMatrix, and more
  (whatever `pyzbar` and OpenCV's `QRCodeDetector` can decode).
- **Perspective correction** — angled / skewed codes are rectified before
  decoding using a 4-point perspective warp.
- **Pipeline inspector** — every intermediate image (grayscale, blur, threshold,
  Canny, Harris corners, Sobel gradient, morphological closing, corrected
  patches) is returned to the UI for debugging and teaching.
- **Annotated output** — the result image shows a coloured rectangle per
  detection: green for QR, blue for barcode, yellow for direct decode.
- **100% local** — no image ever leaves your machine; the frontend talks only
  to `localhost:5000`.
- **Modern UI** — React 18 + Tailwind + Framer Motion, with a glassmorphism
  dark theme, drag-and-drop upload, live scanning overlay, and one-click
  PNG + JSON export.

---

## Architecture

```
┌──────────────────────┐        HTTP POST /api/scan        ┌────────────────────────┐
│  React frontend      │ ─────────────────────────────────▶│  Flask API (server.py) │
│  (Vite, port 5173)   │                                   │  (port 5000)           │
│                      │◀──── JSON: detections + PNGs ─────│                        │
└──────────────────────┘                                   └──────────┬─────────────┘
                                                                      │
                                                                      ▼
                                                     ┌────────────────────────────────┐
                                                     │  pipeline/scanner.py           │
                                                     │  ├── preprocess.py             │
                                                     │  ├── detect_qr.py              │
                                                     │  ├── detect_barcode.py         │
                                                     │  ├── perspective.py            │
                                                     │  └── decoder.py (pyzbar + cv2) │
                                                     └────────────────────────────────┘
```

---

## Project Structure

```
barcode_scanner/
├── README.md                  ← you are here
├── requirements.txt           ← Python dependencies
├── server.py                  ← Flask REST API
├── generate_test_images.py    ← creates 12 synthetic test images
├── test_pipeline.py           ← batch-runs the pipeline over test_images/
│
├── pipeline/                  ← pure-Python, no web code
│   ├── __init__.py
│   ├── preprocess.py          ← grayscale, blur, adaptive threshold
│   ├── detect_qr.py           ← finder-pattern detection + Harris corners
│   ├── detect_barcode.py      ← Sobel gradient + morphology + Hough
│   ├── perspective.py         ← 4-point warp / rectification
│   ├── decoder.py             ← pyzbar + cv2.QRCodeDetector wrappers
│   └── scanner.py             ← orchestrator: multi-scale + all tracks
│
├── test_images/               ← 12 generated test PNGs
│
└── frontend/                  ← React + Vite + Tailwind
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        └── components/
            ├── Header.jsx
            ├── UploadZone.jsx
            ├── ScanViewer.jsx
            ├── ResultsPanel.jsx
            ├── StepsViewer.jsx
            └── Toast.jsx
```

---

## Prerequisites

| Tool        | Version       | Used for                         |
| ----------- | ------------- | -------------------------------- |
| Python      | 3.9 or higher | Backend + pipeline               |
| Node.js     | 18 or higher  | Frontend build                   |
| npm         | 9 or higher   | Installing JS dependencies       |
| `zbar` DLL  | latest        | Required by `pyzbar` on Windows  |

> **Windows users:** `pyzbar` requires the native `libzbar` DLL. If you get a
> `FileNotFoundError` on import, install the Visual C++ Redistributable or
> download the DLL from <https://sourceforge.net/projects/zbar/>.

---

## Installation

### 1. Clone / open the project

```bash
cd f:/PROJECT/barcode_scanner
```

### 2. Install Python dependencies

```bash
![alt text](image.png)
```

This installs OpenCV, NumPy, pyzbar, Pillow, Flask, and Flask-CORS.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

This downloads React, Vite, Tailwind, Framer Motion, Lucide icons, and
react-dropzone into `frontend/node_modules/`.

---

## Running the Project

There are two ways to run ScanMe: **development mode** (hot-reload frontend)
or **production mode** (single server serving a built bundle).

### Option A — Development mode (recommended while editing)

Open **two terminals**:

**Terminal 1 — backend**
```bash
python server.py
```
The Flask API starts on <http://localhost:5000>.

**Terminal 2 — frontend**
```bash
cd frontend
npm run dev
```
The Vite dev server starts on <http://localhost:5173>. Open that URL in your
browser. The frontend will proxy `/api/*` calls to Flask on port 5000.

### Option B — Production mode (single server)

Build the frontend once:
```bash
cd frontend
npm run build
cd ..
```

Then launch the backend — it will serve both the API and the built React app:
```bash
python server.py
```

Open <http://localhost:5000> in your browser.

### Option C — Command-line / batch mode (no browser)

Generate the 12 synthetic test images:
```bash
python generate_test_images.py
```

Run the pipeline on every test image and print detections:
```bash
python test_pipeline.py
```

---

## How the Pipeline Works

Every uploaded image goes through the following stages (see `pipeline/scanner.py`):

1. **Multi-scale loop** — the image is re-run at scales **0.5×, 1.0×, 2.0×**.
   Detections from all scales are collected, then de-duplicated by payload.

2. **Preprocessing** (`preprocess.py`)
   - Grayscale conversion
   - Gaussian blur (noise reduction)
   - Bilateral filter (edge-preserving smoothing)
   - Adaptive thresholding (handles uneven lighting)

3. **QR track** (`detect_qr.py`)
   - Find candidate finder patterns via contour nesting analysis
   - Refine corners using Harris corner detection
   - Produce 4-point polygons for each candidate region

4. **Barcode track** (`detect_barcode.py`)
   - Compute Sobel gradient magnitude (bars have strong directional gradients)
   - Morphological closing to connect bar regions
   - Find bounding contours and rotate to rectangular candidates

5. **Perspective correction** (`perspective.py`)
   - For every candidate polygon, warp to a normalised rectangle using
     `cv2.getPerspectiveTransform` + `cv2.warpPerspective`.

6. **Decoding** (`decoder.py`)
   - Try `pyzbar.decode` on the rectified patch.
   - Fall back to `cv2.QRCodeDetector` for QR codes.
   - If both fail, try a "direct" decode on the whole frame as a last resort.

7. **Annotation** — each successful detection is drawn onto the original
   image with a coloured rectangle and its decoded payload.

---

## API Reference

### `GET /api/health`
Simple health check.

**Response**
```json
{ "status": "ok", "service": "ScanMe API" }
```

### `POST /api/scan`
Run the full pipeline on an uploaded image.

**Request** — `multipart/form-data` with a single field:
| Field   | Type | Description                      |
| ------- | ---- | -------------------------------- |
| `image` | File | PNG / JPG / BMP / WEBP / TIFF    |

**Response** (JSON)
```jsonc
{
  "detections": [
    {
      "data":  "4006381333931",        // decoded payload
      "type":  "EAN13",                // symbology
      "track": "barcode",              // "qr" | "barcode" | "direct"
      "scale": 1.0,                    // scale at which it was found
      "polygon": [[x, y], ...]         // 4-point polygon in original image
    }
  ],
  "annotated_image": "iVBORw0KGgo...", // base64 PNG
  "steps": {                           // all intermediate stages, base64 PNG
    "gray":                 "...",
    "blurred":              "...",
    "bilateral":            "...",
    "binary":               "...",
    "canny_edges":          "...",
    "harris":               "...",
    "gradient":             "...",
    "morphological_closed": "...",
    "thresholded":          "...",
    "corrected_patch":      "..."
  },
  "processing_time": 0.42              // seconds
}
```

---

## Testing

### Synthetic test images

`generate_test_images.py` produces 12 PNGs covering common scenarios:

| #   | File                              | Scenario                           |
| --- | --------------------------------- | ---------------------------------- |
| 01  | `01_clean_barcode.png`            | Ideal barcode                      |
| 02  | `02_clean_qr.png`                 | Ideal QR                           |
| 03  | `03_angled_barcode.png`           | Rotated barcode                    |
| 04  | `04_angled_qr.png`                | Rotated QR                         |
| 05  | `05_multiple_codes.png`           | Multiple codes in one image        |
| 06  | `06_uneven_lighting.png`          | Strong lighting gradient           |
| 07  | `07_complex_background.png`       | Busy / noisy background            |
| 08  | `08_perspective_qr.png`           | Perspective-distorted QR           |
| 09  | `09_small_code_large_image.png`   | Very small code in big frame       |
| 10  | `10_noisy_barcode.png`            | Heavy salt-and-pepper noise        |
| 11  | `11_no_codes.png`                 | Negative case — no codes           |
| 12  | `12_low_contrast.png`             | Low-contrast barcode               |

### Batch run

```bash
python test_pipeline.py
```
Prints a summary table of detections per image.

---

## Troubleshooting

| Symptom                                           | Fix                                                                 |
| ------------------------------------------------- | ------------------------------------------------------------------- |
| `ImportError: Unable to find zbar shared library` | Install the zbar DLL (Windows) or `libzbar0` (Debian/Ubuntu).       |
| Frontend shows `ECONNREFUSED` to port 5000        | Start the backend with `python server.py` before loading the page.  |
| `npm run dev` shows a blank page                  | Check the browser console; verify Vite is reachable on port 5173.   |
| `cv2.error: (-215:Assertion failed)`              | The uploaded image failed to decode — try a different file/format.  |
| Codes detected at low quality are mis-decoded     | Re-run with a higher resolution scan or better lighting.            |

---


