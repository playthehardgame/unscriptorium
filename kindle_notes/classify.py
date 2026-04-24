from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b")

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Assicurazioni": (
        "assicur",
        "polizza",
        "polizze",
        "ramo",
        "ggs",
        "premio",
        "sinistro",
        "compagn",
        "iassicur",
        "dslip",
    ),
    "Data & Analytics": (
        "dbt",
        "databricks",
        "snowflake",
        "data mesh",
        "kpi",
        "normalizzaz",
        "mappatura dati",
        "bi",
        "etl",
        "staging",
    ),
    "CRM & Vendite": (
        "crm",
        "cribus",
        "cerved",
        "b2b",
        "b2g",
        "crosselling",
        "portafoglio",
        "key account",
        "upsell",
    ),
    "AI & Automazione": (
        "claude",
        "llm",
        "agent",
        "chatbot",
        "ai",
        "bot",
        "embeddings",
        "automation",
        "automaz",
    ),
    "Meeting & Riunioni": ("riunione", "meeting", "agenda", "kickoff", "verbale"),
    "HR & People": ("hr", "ferie", "hiring", "onboarding", "team", "persone", "leadership"),
    "Tecnico / Dev": (
        "api",
        "gcp",
        "aws",
        "docker",
        "python",
        "github",
        "sql",
        "microservizi",
        "deploy",
    ),
    "Personale": ("trasloco", "casa", "fibra", "gas", "famiglia", "personale"),
    "Sicurezza": ("vuln", "penetration", "zero trust", "sicurezza", "gdpr", "compliance"),
    "Finanza / Mercati": ("s&p500", "faang", "dax", "investimenti", "mercati", "trading"),
}


@dataclass(frozen=True)
class NotebookClassification:
    notebook_uuid: str
    topics: list[str]
    confidence: dict[str, float]
    detected_date: str | None
    title_preview: str
    transcription_preview: str
    metadata: dict[str, Any]


def extract_date(text: str) -> str | None:
    m = DATE_RE.search(text or "")
    if not m:
        return None
    day_s, month_s, year_s = m.groups()
    day = int(day_s)
    month = int(month_s)
    if year_s is None:
        return f"--{month:02d}-{day:02d}"
    year = int(year_s)
    if year < 100:
        year += 2000
    return f"{year:04d}-{month:02d}-{day:02d}"


def title_preview(text: str, max_len: int = 80) -> str:
    raw = (text or "").strip()
    if not raw or raw in ("[PAGINA VUOTA]", "[ILLEGGIBILE]"):
        return "[PAGINA VUOTA]"
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("[")
    ]
    src = lines[0] if lines else raw
    return src[:max_len] + ("..." if len(src) > max_len else "")


def detect_topics(text: str) -> tuple[list[str], dict[str, float]]:
    text_l = (text or "").lower()
    tokens = set(re.findall(r"[a-z0-9_+&./-]+", text_l))
    scores: dict[str, float] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = 0
        for kw in keywords:
            kw_l = kw.lower()
            if " " in kw_l or "/" in kw_l:
                if kw_l in text_l:
                    hits += 1
                continue
            if len(kw_l) <= 2:
                if kw_l in tokens:
                    hits += 1
                continue
            if re.search(rf"\b{re.escape(kw_l)}\w*", text_l):
                hits += 1
        if hits > 0:
            scores[topic] = round(min(1.0, hits / max(3, len(keywords) / 2)), 4)
    if not scores:
        return (["Altro"], {"Altro": 1.0})
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    topics = [ordered[0][0]]
    if len(ordered) > 1 and ordered[1][1] >= max(0.4, ordered[0][1] * 0.7):
        topics.append(ordered[1][0])
    return (topics, {k: v for k, v in ordered})


def classify_notebook(uuid: str, text: str, metadata: dict[str, Any] | None = None) -> NotebookClassification:
    topics, confidence = detect_topics(text)
    return NotebookClassification(
        notebook_uuid=uuid,
        topics=topics,
        confidence=confidence,
        detected_date=extract_date(text),
        title_preview=title_preview(text),
        transcription_preview=(text or "").strip()[:200],
        metadata=metadata or {},
    )


def to_dict(c: NotebookClassification) -> dict[str, Any]:
    return asdict(c)
