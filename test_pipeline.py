#!/usr/bin/env python3
"""
CLI validation script — runs the full pipeline on every image in ./test_images.
Prints a per-image detection summary and writes annotated PNGs to ./outputs for visual review.
"""

# ── Imports ─────────────────────────────────────────────────────────────────
import sys                                       # Adjusts the module search path
import os                                        # Filesystem helpers
import glob                                      # Wildcard file matching
import cv2                                       # OpenCV — used only to write annotated images

# Make the project root importable so "from pipeline.scanner import scan" resolves.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.scanner import scan                # The public pipeline entry point.


def run_tests():
    """Iterate over every PNG in test_images/, run scan(), and report results."""
    # Compute absolute paths so the script works from any current directory.
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_images')
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
    os.makedirs(output_dir, exist_ok=True)       # Create the outputs directory if needed.

    # Deterministic ordering via sorted().
    images = sorted(glob.glob(os.path.join(test_dir, '*.png')))
    if not images:
        print("No test images found!")
        return

    print(f"Testing pipeline on {len(images)} images")
    print("=" * 70)

    # Aggregate counters for the final summary.
    total_detections = 0
    results_summary = []

    for img_path in images:
        name = os.path.basename(img_path)        # Short filename for display.
        print(f"\n{'─' * 60}")
        print(f"  Image: {name}")

        try:
            # Run the pipeline on this image.
            result = scan(image_path=img_path)
            detections = result['detections']
            t = result['processing_time']

            print(f"  Time:  {t:.3f}s")
            print(f"  Found: {len(detections)} code(s)")

            # One-line per detection: index, type, truncated payload, and track.
            for i, det in enumerate(detections):
                print(f"    [{i+1}] {det['type']}: {det['data'][:50]} (track: {det['track']})")

            # Save the annotated image alongside its test counterpart.
            out_name = name.replace('.png', '_result.png')
            cv2.imwrite(os.path.join(output_dir, out_name), result['annotated'])

            total_detections += len(detections)
            # Keep a record for the final summary table.
            results_summary.append({
                'image': name,
                'detections': len(detections),
                'time': t,
                'details': [
                    {'type': d['type'], 'data': d['data'], 'track': d['track']}
                    for d in detections
                ],
            })

        except Exception as e:
            # A crash on one image shouldn't stop the entire test run.
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                'image': name,
                'detections': 0,
                'time': 0,
                'error': str(e),
            })

    # ── Summary table ──────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total images tested: {len(images)}")
    print(f"Total detections:    {total_detections}")
    print()

    print(f"{'Image':<40} {'Detections':>12} {'Time (s)':>10}")
    print(f"{'─' * 40} {'─' * 12} {'─' * 10}")
    for r in results_summary:
        det_str = str(r['detections']) if 'error' not in r else 'ERROR'
        time_str = f"{r['time']:.3f}" if 'error' not in r else '—'
        print(f"{r['image']:<40} {det_str:>12} {time_str:>10}")

    print(f"\nAnnotated results saved to: {output_dir}/")


# Standard entry-point guard.
if __name__ == '__main__':
    run_tests()
