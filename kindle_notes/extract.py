from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image

from .classify import classify_notebook, to_dict
from .database import ExtractionRecord, NotebookDatabase
from .ink_render import render_nbk_pages
from .layout import ensure_output_layout
from .ocr import extract_text_from_images_with_fallback


@dataclass(frozen=True)
class ExtractionResult:
    processed: int
    output_file: Path
    model: str


def discover_notebooks(input_root: Path | str) -> list[Path]:
    root = Path(input_root)
    return sorted(
        [p for p in root.iterdir() if p.is_dir() and (p / "nbk").is_file()],
        key=lambda p: p.name,
    )


def _ink_ratio(page: Image.Image, threshold: int = 220) -> float:
    gray = page.convert("L")
    hist = gray.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    dark = sum(hist[:threshold])
    return dark / total


def summarize_notebook_text(notebook_id: str, pages: list[Image.Image]) -> str:
    if not pages:
        return "[PAGINA VUOTA]"

    ratios = [_ink_ratio(img) for img in pages]
    non_empty = [r for r in ratios if r >= 0.002]
    if not non_empty:
        return "[PAGINA VUOTA]"

    return (
        f"Notebook {notebook_id}: {len(non_empty)}/{len(pages)} pagine con inchiostro. "
        "[ILLEGGIBILE]"
    )


def extract_notebooks(
    input_root: Path | str,
    output_dir: Path | str,
    model: str,
    vector_render: bool,
    render_pages_fn: Callable[[Path], list[Image.Image]] | None = None,
    limit: int | None = None,
    use_tesseract: bool = False,
    track_db: bool = True,
) -> ExtractionResult:
    start_time = time.time()
    source = Path(input_root)
    layout = ensure_output_layout(output_dir)

    # Initialize database for tracking
    db = None
    if track_db:
        db_path = layout.root / "notebooks.db"
        db = NotebookDatabase(db_path)

    notebooks = discover_notebooks(source)
    if limit is not None and limit > 0:
        notebooks = notebooks[:limit]

    renderer = render_pages_fn or render_nbk_pages
    transcriptions: dict[str, str] = {}
    classifications: dict[str, dict] = {}
    successful, failed = 0, 0

    for nb_dir in notebooks:
        nbk_path = nb_dir / "nbk"
        try:
            if vector_render:
                pages = renderer(nbk_path)
                # Use OCR module for real text extraction instead of placeholder
                text = extract_text_from_images_with_fallback(
                    pages, use_tesseract=use_tesseract
                )
            else:
                text = f"Notebook {nb_dir.name}: estrazione senza vector render. [ILLEGGIBILE]"

            transcriptions[nb_dir.name] = text
            classification = classify_notebook(nb_dir.name, text)
            classifications[nb_dir.name] = to_dict(classification)

            # Track in database
            if db:
                record = ExtractionRecord(
                    notebook_uuid=nb_dir.name,
                    extraction_date=datetime.now(),
                    primary_topic=classification.primary_topic,
                    confidence=classification.confidence,
                    page_count=len(pages) if vector_render else 0,
                    text_length=len(text),
                    extracted_date_from_content=classification.extracted_date,
                    model=model,
                    status="completed",
                )
                db.add_extraction(record)
                db.add_topics(
                    nb_dir.name,
                    {t: classification.confidence for t in classification.topics},
                )

            successful += 1
        except Exception as e:
            failed += 1
            if db:
                record = ExtractionRecord(
                    notebook_uuid=nb_dir.name,
                    extraction_date=datetime.now(),
                    primary_topic="error",
                    confidence=0.0,
                    page_count=0,
                    text_length=0,
                    model=model,
                    status=f"failed: {str(e)[:100]}",
                )
                db.add_extraction(record)

    output_file = layout.json_dir / "transcriptions.json"
    output_file.write_text(
        json.dumps(transcriptions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Backward-compatible flat path used in earlier scripts.
    (layout.root / "transcriptions.json").write_text(
        json.dumps(transcriptions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (layout.json_dir / "classifications.json").write_text(
        json.dumps(classifications, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_topic: dict[str, list[str]] = {}
    for uuid, c in classifications.items():
        for t in c["topics"]:
            by_topic.setdefault(t, []).append(uuid)
    for topic in by_topic:
        by_topic[topic] = sorted(by_topic[topic])
    (layout.json_dir / "topics_index.json").write_text(
        json.dumps(by_topic, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "version": "1.0",
        "total_notebooks": len(transcriptions),
        "extraction_model": model,
        "by_uuid": classifications,
        "by_topic": by_topic,
    }
    (layout.json_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Record batch run in database
    if db:
        duration = time.time() - start_time
        db.add_batch_run(
            total=len(notebooks),
            successful=successful,
            failed=failed,
            skipped=len(notebooks) - successful - failed,
            model=model,
            output_path=str(layout.root),
            duration_seconds=duration,
        )

    return ExtractionResult(processed=len(transcriptions), output_file=output_file, model=model)
