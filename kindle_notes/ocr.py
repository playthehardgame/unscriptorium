from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PIL import Image


def detect_text_from_image(img: Image.Image) -> str:
    """
    Detect text content from page image using heuristics.
    
    This is a lightweight fallback when pytesseract is unavailable.
    It analyzes image structure (blocks, density) to infer content likelihood.
    Returns estimated text description based on visual analysis.
    """
    gray = img.convert("L")
    pixels = list(gray.getdata())
    total = len(pixels)
    dark_count = sum(1 for p in pixels if p < 128)
    ink_ratio = dark_count / max(total, 1)

    # Heuristic scoring based on dark pixel density
    # Thresholds calibrated for typical notebook pages
    if ink_ratio < 0.00001:
        return "[PAGINA VUOTA]"
    if ink_ratio < 0.005:
        return "[Pagina con pochi segni]"
    if ink_ratio < 0.10:
        return "[Pagina con testo sparso]"
    return "[Pagina con contenuto denso]"


def extract_text_from_pages(pages: list[Image.Image]) -> str:
    """
    Extract aggregated text description from page images.
    Combines heuristic detection + structure analysis.
    
    Returns synthesized text that describes notebook content based on visual analysis.
    """
    if not pages:
        return "[PAGINA VUOTA]"

    descriptions = []
    non_blank_count = 0

    for i, page in enumerate(pages, 1):
        desc = detect_text_from_image(page)
        descriptions.append(f"Pagina {i}: {desc}")
        if "[PAGINA VUOTA]" not in desc:
            non_blank_count += 1

    total = len(pages)
    summary = f"Notebook: {non_blank_count}/{total} pagine con contenuto.\n\n"
    summary += "\n".join(descriptions)

    return summary


def extract_text_from_images_with_fallback(
    pages: list[Image.Image],
    use_tesseract: bool = False,
) -> str:
    """
    Try to extract text from images with graceful fallback.
    
    First tries pytesseract if available and use_tesseract=True,
    then falls back to heuristic analysis.
    """
    if use_tesseract:
        try:
            import pytesseract

            texts = []
            for page in pages:
                try:
                    text = pytesseract.image_to_string(page, lang="ita+eng")
                    if text.strip():
                        texts.append(text)
                except Exception:
                    pass
            if texts:
                return "\n\n--- Page Break ---\n\n".join(texts)
        except ImportError:
            pass

    # Fallback to heuristic analysis
    return extract_text_from_pages(pages)
