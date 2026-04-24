from __future__ import annotations

import json
from pathlib import Path

from kindle_notes.markdown import build_markdown_report


def test_build_markdown_report_creates_expected_sections(tmp_path: Path) -> None:
    out = tmp_path / "test_output"
    (out / "json").mkdir(parents=True)
    transcriptions = {
        "book-a": "DBT KPI data mesh 25/03/2026",
        "book-b": "[PAGINA VUOTA]",
    }
    (out / "json" / "transcriptions.json").write_text(
        json.dumps(transcriptions, ensure_ascii=False),
        encoding="utf-8",
    )

    md_path = build_markdown_report(out)
    text = md_path.read_text(encoding="utf-8")

    assert md_path == out / "markdown" / "kindle_notebooks_completo.md"
    assert "## Indice" in text
    assert "## Raggruppamento per tema" in text
    assert "## Trascrizioni Dettagliate" in text
    assert "book-a" in text
    assert "book-b" in text
    assert "Data & Analytics" in text
