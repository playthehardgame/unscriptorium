from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kindle_notes.cli import main


def test_cli_extract_invokes_pipeline(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    output = tmp_path / "out"

    captured = {}

    def fake_extract(input_root, output_dir, model, vector_render, render_pages_fn=None, limit=None, use_tesseract=False):
        captured["input_root"] = input_root
        captured["output_dir"] = output_dir
        captured["model"] = model
        captured["vector_render"] = vector_render
        captured["limit"] = limit
        captured["use_tesseract"] = use_tesseract

        return SimpleNamespace(
            processed=0,
            model=model,
            output_file=output_dir / "transcriptions.json",
        )

    monkeypatch.setattr("kindle_notes.cli.extract_notebooks", fake_extract)
    rc = main(
        [
            "extract",
            str(source),
            "--output",
            str(output),
            "--vector-render",
            "--model",
            "claude-opus-4-7",
            "--limit",
            "1",
        ]
    )

    assert rc == 0
    assert captured["input_root"] == source
    assert captured["output_dir"] == output
    assert captured["model"] == "claude-opus-4-7"
    assert captured["vector_render"] is True
    assert captured["limit"] == 1
    assert captured["use_tesseract"] is False


def test_cli_build_markdown_invokes_builder(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()

    captured = {}

    def fake_build(output_dir):
        captured["output_dir"] = output_dir
        return output_dir / "markdown" / "kindle_notebooks_completo.md"

    monkeypatch.setattr("kindle_notes.cli.build_markdown_report", fake_build)
    rc = main(["build-markdown", "--output", str(output)])

    assert rc == 0
    assert captured["output_dir"] == output
