from __future__ import annotations

import argparse
from pathlib import Path

from .extract import extract_notebooks
from .markdown import build_markdown_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kindle-notes")
    sub = parser.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="Extract notebook transcriptions")
    ex.add_argument("input_root", help="Directory containing notebook folders")
    ex.add_argument("--output", required=True, help="Output directory")
    ex.add_argument("--model", default="claude-opus-4-7", help="Model label to persist in result")
    ex.add_argument("--vector-render", action="store_true", help="Render vector notebook pages")
    ex.add_argument("--use-tesseract", action="store_true", help="Use tesseract OCR for text extraction")
    ex.add_argument("--limit", type=int, default=None, help="Limit notebooks to process")

    md = sub.add_parser("build-markdown", help="Build markdown report from transcriptions JSON")
    md.add_argument("--output", required=True, help="Output directory containing JSON artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        result = extract_notebooks(
            input_root=Path(args.input_root),
            output_dir=Path(args.output),
            model=args.model,
            vector_render=args.vector_render,
            limit=args.limit,
            use_tesseract=args.use_tesseract,
        )
        print(
            f"Processed {result.processed} notebooks with model '{result.model}'. "
            f"Output: {result.output_file}"
        )
        return 0
    if args.command == "build-markdown":
        md_path = build_markdown_report(Path(args.output))
        print(f"Markdown report generated: {md_path}")
        return 0

    parser.print_help()
    return 1


def main_cli() -> None:
    raise SystemExit(main())
