from __future__ import annotations

from pathlib import Path

from render_ink import (
    group_pages,
    load_fragments,
    render_nbk_all_pages,
    render_nbk_pages,
)


def page_count(nbk_path: Path | str) -> int:
    """Return the number of detected notebook pages from fragment grouping."""
    nbk = Path(nbk_path)
    _symtable, frags = load_fragments(nbk)
    pages = group_pages(frags)
    return len([cfid for cfid in pages if cfid != "_global_"])


__all__ = ["page_count", "render_nbk_pages", "render_nbk_all_pages"]

