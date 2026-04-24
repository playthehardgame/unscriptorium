from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from kindle_notes.extract import (
    discover_notebooks,
    extract_notebooks,
    summarize_notebook_text,
)


def _mk_notebook(root: Path, name: str) -> Path:
    nb_dir = root / name
    nb_dir.mkdir(parents=True)
    (nb_dir / "nbk").write_bytes(b"NBK")
    return nb_dir


def _blank_page() -> Image.Image:
    return Image.new("RGB", (32, 32), color=(255, 255, 255))


def _ink_page() -> Image.Image:
    img = _blank_page()
    draw = ImageDraw.Draw(img)
    draw.line((3, 3, 28, 28), fill=(0, 0, 0), width=2)
    return img


def test_discover_notebooks_only_dirs_with_nbk(tmp_path: Path) -> None:
    _mk_notebook(tmp_path, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    (tmp_path / "no_nbk").mkdir()
    (tmp_path / "just_file").write_text("x", encoding="utf-8")

    found = discover_notebooks(tmp_path)
    assert [p.name for p in found] == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]


def test_summarize_notebook_text_blank() -> None:
    text = summarize_notebook_text("book-1", [_blank_page(), _blank_page()])
    assert text.startswith("[PAGINA VUOTA]")


def test_summarize_notebook_text_non_blank() -> None:
    # summarize_notebook_text is legacy function; kept for backward compat
    text = summarize_notebook_text("book-2", [_ink_page(), _blank_page()])
    assert "[ILLEGGIBILE]" in text
    assert "book-2" in text


def test_extract_notebooks_writes_transcriptions_json(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    _mk_notebook(source, "book-a")
    _mk_notebook(source, "book-b")
    output_dir = tmp_path / "out"

    def fake_render(_nbk: Path):
        return [_ink_page(), _blank_page()]

    result = extract_notebooks(
        source,
        output_dir,
        model="claude-opus-4-7",
        vector_render=True,
        render_pages_fn=fake_render,
        limit=1,
    )

    out_file = output_dir / "transcriptions.json"
    assert out_file.exists()
    assert (output_dir / "json" / "classifications.json").exists()
    assert (output_dir / "json" / "topics_index.json").exists()
    assert (output_dir / "json" / "manifest.json").exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert set(data) == {"book-a"}
    # Now expects real OCR text instead of placeholder
    assert "Notebook:" in data["book-a"] or "Pagina" in data["book-a"]

    assert result.processed == 1
    assert result.model == "claude-opus-4-7"
