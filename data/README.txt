================================================================
 ScanMe — Dataset Description
================================================================

This directory contains the test images used to validate the
barcode / QR-code scanning pipeline implemented in
  ../code/scanme_pipeline.ipynb

The dataset is intentionally small (14 images) so that the whole
notebook runs in well under a minute on a laptop with no GPU, yet
still covers the main failure modes a classical CV pipeline must
handle: clean input, rotation, perspective distortion, uneven
lighting, noise, low contrast, small targets, busy backgrounds,
and a negative sample (no codes at all).

----------------------------------------------------------------
 Synthetic images (12 PNGs, 800 x 800)
----------------------------------------------------------------

They were generated with OpenCV + NumPy so that ground truth is
perfectly known.  Each file stresses one specific aspect of the
pipeline:

  #   File                             Scenario tested
  --  -------------------------------  ----------------------------
  01  01_clean_barcode.png             Ideal EAN-13, front-facing.
  02  02_clean_qr.png                  Ideal QR, front-facing.
  03  03_angled_barcode.png            Barcode rotated ~30 deg.
  04  04_angled_qr.png                 QR rotated ~30 deg.
  05  05_multiple_codes.png            One QR + one barcode in
                                       the same frame.
  06  06_uneven_lighting.png           Strong illumination gradient
                                       (tests adaptive threshold).
  07  07_complex_background.png        Busy background with random
                                       shapes around the code.
  08  08_perspective_qr.png            QR seen from an angle
                                       (tests homography warp).
  09  09_small_code_large_image.png    Small code in a big frame
                                       (tests multi-scale loop).
  10  10_noisy_barcode.png             Heavy salt-and-pepper noise
                                       (tests blur + morphology).
  11  11_no_codes.png                  Negative case: the pipeline
                                       must return 0 detections.
  12  12_low_contrast.png              Low-contrast barcode
                                       (tests Otsu / equalisation).

----------------------------------------------------------------
 Real-world samples (2 JPEGs)
----------------------------------------------------------------

  real_sample_01.jpeg   Photograph of a real product barcode.
  real_sample_02.jpeg   Photograph of a printed QR code.

These come from a mobile-phone camera and are useful for the
final end-to-end sanity check — the pipeline is shown to
generalise beyond the synthetic benchmark.

----------------------------------------------------------------
 File format
----------------------------------------------------------------

 * PNGs  : 8-bit RGB, 800 x 800, lossless.
 * JPEGs : 8-bit RGB, camera-resolution, lossy.

All images are read with cv2.imread(), which returns a BGR
uint8 NumPy array.

----------------------------------------------------------------
 Regenerating the synthetic set
----------------------------------------------------------------

The 12 PNGs can be re-created at any time by running the
"Generate synthetic dataset" section inside the notebook, which
uses only OpenCV + NumPy (no external drawing tools).

================================================================
