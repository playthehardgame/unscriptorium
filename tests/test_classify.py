from __future__ import annotations

from kindle_notes.classify import classify_notebook, detect_topics, extract_date


def test_detect_topics_data_analytics() -> None:
    topics, conf = detect_topics("dbt staging marts data mesh kpi")
    assert "Data & Analytics" in topics
    assert conf["Data & Analytics"] > 0


def test_detect_topics_fallback_altro() -> None:
    topics, conf = detect_topics("qwerty zxcv lorem ipsum")
    assert topics == ["Altro"]
    assert conf["Altro"] == 1.0


def test_extract_date_iso_conversion() -> None:
    assert extract_date("Riunione 25/03/2026") == "2026-03-25"


def test_classify_notebook_has_preview() -> None:
    c = classify_notebook("abc", "DBT rollout 25/03/2026")
    assert c.notebook_uuid == "abc"
    assert c.title_preview
    assert c.topics

