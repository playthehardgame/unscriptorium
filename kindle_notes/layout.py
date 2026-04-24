from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputLayout:
    root: Path
    json_dir: Path
    markdown_dir: Path
    renders_dir: Path
    logs_dir: Path


def ensure_output_layout(output_dir: Path | str) -> OutputLayout:
    root = Path(output_dir)
    layout = OutputLayout(
        root=root,
        json_dir=root / "json",
        markdown_dir=root / "markdown",
        renders_dir=root / "renders",
        logs_dir=root / "logs",
    )
    layout.json_dir.mkdir(parents=True, exist_ok=True)
    layout.markdown_dir.mkdir(parents=True, exist_ok=True)
    layout.renders_dir.mkdir(parents=True, exist_ok=True)
    layout.logs_dir.mkdir(parents=True, exist_ok=True)
    return layout

