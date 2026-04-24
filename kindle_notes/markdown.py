from __future__ import annotations

import json
import re
from pathlib import Path

from .classify import classify_notebook, to_dict
from .layout import ensure_output_layout


def _load_transcriptions(layout_root: Path) -> dict[str, str]:
    json_path = layout_root / "json" / "transcriptions.json"
    if not json_path.exists():
        legacy = layout_root / "transcriptions.json"
        if legacy.exists():
            json_path = legacy
        else:
            raise FileNotFoundError(f"Missing transcriptions JSON: {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def _load_classifications(layout_root: Path, transcriptions: dict[str, str]) -> dict[str, dict]:
    p = layout_root / "json" / "classifications.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {uuid: to_dict(classify_notebook(uuid, text)) for uuid, text in transcriptions.items()}


def _sort_key(entry: dict) -> tuple:
    dt = entry.get("detected_date")
    if dt and dt.startswith("--"):
        month, day = dt[2:].split("-")
        return (0, 0, -int(month), -int(day), entry["notebook_uuid"])
    if dt and re.match(r"^\d{4}-\d{2}-\d{2}$", dt):
        y, m, d = dt.split("-")
        return (0, -int(y), -int(m), -int(d), entry["notebook_uuid"])
    return (1, 0, 0, 0, entry["notebook_uuid"])


def build_markdown_report(output_dir: Path | str) -> Path:
    layout = ensure_output_layout(output_dir)
    transcriptions = _load_transcriptions(layout.root)
    classifications = _load_classifications(layout.root, transcriptions)

    entries: list[dict] = []
    for uuid, text in sorted(transcriptions.items()):
        c = classifications.get(uuid) or to_dict(classify_notebook(uuid, text))
        entries.append(
            {
                "uuid": uuid,
                "text": text,
                "topics": c.get("topics", ["Altro"]),
                "confidence": c.get("confidence", {"Altro": 1.0}),
                "detected_date": c.get("detected_date"),
                "title_preview": c.get("title_preview", uuid),
            }
        )
    entries.sort(key=lambda e: _sort_key({"detected_date": e["detected_date"], "notebook_uuid": e["uuid"]}))

    topic_index: dict[str, list[dict]] = {}
    for e in entries:
        for t in e["topics"]:
            topic_index.setdefault(t, []).append(e)

    # Persist classification artifacts so build-markdown can be run on externally
    # provided transcriptions.json and still produce structured outputs.
    by_uuid = {e["uuid"]: classifications.get(e["uuid"], {}) for e in entries}
    by_topic = {topic: sorted([e["uuid"] for e in vals]) for topic, vals in topic_index.items()}
    (layout.json_dir / "classifications.json").write_text(
        json.dumps(by_uuid, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (layout.json_dir / "topics_index.json").write_text(
        json.dumps(by_topic, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (layout.json_dir / "manifest.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "total_notebooks": len(entries),
                "topics": sorted(by_topic.keys()),
                "by_uuid": by_uuid,
                "by_topic": by_topic,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines: list[str] = ["# Kindle Notebooks — Trascrizione Completa\n\n"]
    lines.append("## Indice\n")
    for i, e in enumerate(entries, 1):
        date_str = f" `{e['detected_date']}`" if e["detected_date"] else ""
        topics_str = ", ".join(e["topics"][:2])
        lines.append(f"{i}. [{e['title_preview'][:60]}](#{e['uuid']}) — {topics_str}{date_str}\n")

    lines.append("\n## Raggruppamento per tema\n")
    for topic in sorted(topic_index):
        items = sorted(
            topic_index[topic],
            key=lambda e: _sort_key({"detected_date": e["detected_date"], "notebook_uuid": e["uuid"]}),
        )
        lines.append(f"\n### {topic} ({len(items)} notebook)\n")
        for e in items:
            date_str = f" `{e['detected_date']}`" if e["detected_date"] else ""
            lines.append(f"- [{e['title_preview'][:60]}](#{e['uuid']}){date_str}\n")

    lines.append("\n## Trascrizioni Dettagliate\n")
    for i, e in enumerate(entries, 1):
        lines.append(f"\n### {i}. {e['title_preview'][:70]}\n")
        lines.append(f"<a name=\"{e['uuid']}\"></a>\n")
        date_str = f" | Data: {e['detected_date']}" if e["detected_date"] else ""
        lines.append(f"> **UUID**: `{e['uuid']}`{date_str}  \n")
        lines.append(f"> **Temi**: {' | '.join(e['topics'])}\n\n")
        lines.append("```\n")
        lines.append((e["text"] or "[PAGINA VUOTA]").strip())
        lines.append("\n```\n")

    out_path = layout.markdown_dir / "kindle_notebooks_completo.md"
    out_path.write_text("".join(lines), encoding="utf-8")

    for topic, topic_entries in topic_index.items():
        safe_topic = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_").replace("/", "_")
        tlines = [f"# {topic}\n\n", f"> {len(topic_entries)} notebook\n\n---\n"]
        ordered = sorted(
            topic_entries,
            key=lambda e: _sort_key({"detected_date": e["detected_date"], "notebook_uuid": e["uuid"]}),
        )
        for i, e in enumerate(ordered, 1):
            date_str = f" | {e['detected_date']}" if e["detected_date"] else ""
            tlines.append(f"\n## {i}. {e['title_preview']}{date_str}\n\n")
            tlines.append(f"> UUID: `{e['uuid']}`\n\n")
            tlines.append("```\n")
            tlines.append((e["text"] or "[PAGINA VUOTA]").strip())
            tlines.append("\n```\n")
        (layout.markdown_dir / f"{safe_topic}.md").write_text("".join(tlines), encoding="utf-8")

    return out_path
