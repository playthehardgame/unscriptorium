from __future__ import annotations

from pathlib import Path

from kindle_notes.ink_render import page_count


def test_page_count_existing_notebook() -> None:
    nbk = Path("notebooks-raw") / "0d68df15-0b73-3753-a1cd-8a00dfcc50aa" / "nbk"
    assert page_count(nbk) >= 1


