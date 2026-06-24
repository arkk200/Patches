from typing import TYPE_CHECKING

import cv2
import numpy as np
import pytesseract

from app.services.patch_detect import PatchSegment

if TYPE_CHECKING:
    import easyocr


# ── OCR related constants ───────────────────────────────────────────────────
SAT_UPSCALE_FACTOR = 5
OCR_OPEN_KERNEL_SIZE = 2
MAX_PIECE_SIZE = 99   # Upper bound for valid puzzle piece count (0-99)
_OCR_PSM = 8          # Tesseract PSM 8 (single word) for thresholded images
_OCR_CFG = f"--psm {_OCR_PSM} -c tessedit_char_whitelist=0123456789"


def _ocr_single(src: np.ndarray, threshold_type: int) -> int | None:
    _, bin_img = cv2.threshold(src, 0, 255, threshold_type + cv2.THRESH_OTSU)
    big = cv2.resize(bin_img, None, fx=SAT_UPSCALE_FACTOR, fy=SAT_UPSCALE_FACTOR,
                     interpolation=cv2.INTER_NEAREST)
    text = pytesseract.image_to_string(big, config=_OCR_CFG).strip()
    try:
        return int(text) if text else None
    except ValueError:
        return None


def _sat_ocr(cell_image: np.ndarray) -> int | None:
    sat = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)[:, :, 1]
    return _ocr_single(sat, cv2.THRESH_BINARY_INV)


def _hole_ocr(cell_image: np.ndarray) -> set[int]:
    """Extract text via contour hole-filling.

    Otsu on saturation → piece=white, text+bg=black.
    Fill piece contour → XOR with original → holes (text) only.

    Returns results from PSM 8 (single word) and PSM 7 (single line).
    PSM 7 captures 2-digit numbers better; PSM 8 handles single digits.
    """
    sat = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)[:, :, 1]
    _, otsu = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return set()

    filled = np.zeros_like(otsu)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    holes = cv2.bitwise_xor(filled, otsu)

    cleaned = cv2.morphologyEx(holes, cv2.MORPH_OPEN,
                               np.ones((OCR_OPEN_KERNEL_SIZE, OCR_OPEN_KERNEL_SIZE), np.uint8))
    big = cv2.resize(cleaned, None, fx=SAT_UPSCALE_FACTOR, fy=SAT_UPSCALE_FACTOR,
                     interpolation=cv2.INTER_NEAREST)

    def _read(psm: int) -> int | None:
        cfg = f"--psm {psm} -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(big, config=cfg).strip()
        try:
            return int(text) if text else None
        except ValueError:
            return None

    vals: set[int] = set()
    for v in (_read(8), _read(7)):
        if v is not None:
            vals.add(v)
    return vals


def _pick_best_ocr_result(results: set[int], easy_val: int | None = None) -> int | None:
    if not results:
        return None
    candidates = [r for r in results if 1 <= r <= MAX_PIECE_SIZE]
    if not candidates:
        return None

    # Prefer 2-digit values — PSM 8 often misses tens digit
    two_digit = [r for r in candidates if r >= 10]
    if two_digit:
        return max(two_digit)

    # Single-digit conflict: EasyOCR is most reliable tiebreaker
    if easy_val is not None and easy_val in candidates:
        return easy_val

    # All agree or no tiebreaker: pick smallest
    return min(candidates)


# ── EasyOCR (3rd voter) ────────────────────────────────────────────────────

_EASYOCR_READER: "easyocr.Reader | None" = None  # lazy-init singleton


def _easy_ocr(cell_image: np.ndarray) -> int | None:
    """Extract digit via EasyOCR. Lazy-init reader on first call."""
    global _EASYOCR_READER
    try:
        import easyocr
    except ImportError:
        return None

    if _EASYOCR_READER is None:
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False, verbose=False)

    try:
        results = _EASYOCR_READER.readtext(cell_image, allowlist="0123456789", paragraph=False)
    except (ValueError, TypeError, AttributeError):
        return None

    digits = [(int(t.strip()), c) for _, t, c in results if t.strip().isdigit()]
    if not digits:
        return None
    digits.sort(key=lambda x: -x[1])
    return digits[0][0]


def _extract_patch_size(cell_image: np.ndarray) -> int | None:
    results: set[int] = set()

    sat_val = _sat_ocr(cell_image)
    if sat_val is not None:
        results.add(sat_val)

    results.update(_hole_ocr(cell_image))

    easy_val = _easy_ocr(cell_image)
    if easy_val is not None:
        results.add(easy_val)

    return _pick_best_ocr_result(results, easy_val)


def extract_patch_sizes(cells: list[PatchSegment]) -> list[PatchSegment]:
    return [
        PatchSegment(
            row=c.row,
            col=c.col,
            cell_image=c.cell_image,
            shape=c.shape,
            size=_extract_patch_size(c.cell_image),
        )
        for c in cells
    ]
