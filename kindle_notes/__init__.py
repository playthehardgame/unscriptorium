"""Native package interface for Kindle notebook extraction."""

from .database import ExtractionRecord, NotebookDatabase
from .extract import extract_notebooks
from .ink_render import page_count, render_nbk_pages
from .ocr import detect_text_from_image, extract_text_from_images_with_fallback

__all__ = [
    "extract_notebooks",
    "page_count",
    "render_nbk_pages",
    "detect_text_from_image",
    "extract_text_from_images_with_fallback",
    "ExtractionRecord",
    "NotebookDatabase",
]

