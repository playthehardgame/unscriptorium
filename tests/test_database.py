"""Test database module."""

from datetime import datetime
from pathlib import Path

from kindle_notes.database import ExtractionRecord, NotebookDatabase


def test_database_init(tmp_path: Path) -> None:
    """Test database initialization creates schema."""
    db_path = tmp_path / "test.db"
    db = NotebookDatabase(db_path)

    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_add_and_retrieve_extraction(tmp_path: Path) -> None:
    """Test adding and retrieving extraction record."""
    db = NotebookDatabase(tmp_path / "test.db")

    record = ExtractionRecord(
        notebook_uuid="test-uuid-123",
        extraction_date=datetime.now(),
        primary_topic="Data & Analytics",
        confidence=0.92,
        page_count=42,
        text_length=5000,
        extracted_date_from_content="2024-04-15",
        model="test-model",
        status="completed",
    )

    record_id = db.add_extraction(record)
    assert record_id > 0

    retrieved = db.get_extraction("test-uuid-123")
    assert retrieved is not None
    assert retrieved.notebook_uuid == "test-uuid-123"
    assert retrieved.primary_topic == "Data & Analytics"
    assert retrieved.confidence == 0.92


def test_add_topics(tmp_path: Path) -> None:
    """Test adding multiple topics for notebook."""
    db = NotebookDatabase(tmp_path / "test.db")

    # Add extraction first
    record = ExtractionRecord(
        notebook_uuid="test-uuid-456",
        extraction_date=datetime.now(),
        primary_topic="AI & Automazione",
        confidence=0.85,
        page_count=10,
        text_length=2000,
    )
    db.add_extraction(record)

    # Add multiple topics
    topics = {
        "AI & Automazione": 0.85,
        "Data & Analytics": 0.45,
        "Tecnico & Dev": 0.30,
    }
    db.add_topics("test-uuid-456", topics)

    # Verify by-topic query
    uuids = db.get_by_topic("AI & Automazione")
    assert "test-uuid-456" in uuids


def test_get_statistics(tmp_path: Path) -> None:
    """Test statistics aggregation."""
    db = NotebookDatabase(tmp_path / "test.db")

    # Add multiple records
    for i in range(3):
        record = ExtractionRecord(
            notebook_uuid=f"uuid-{i}",
            extraction_date=datetime.now(),
            primary_topic=f"Topic {i % 2}",
            confidence=0.8 + (i * 0.05),
            page_count=10 + i,
            text_length=1000 + i * 100,
        )
        db.add_extraction(record)

    stats = db.get_statistics()
    assert stats["total_notebooks"] == 3
    assert stats["unique_topics"] >= 1
    assert stats["failed"] == 0
    assert stats["avg_confidence"] > 0


def test_batch_run_tracking(tmp_path: Path) -> None:
    """Test batch run recording."""
    db = NotebookDatabase(tmp_path / "test.db")

    run_id = db.add_batch_run(
        total=100,
        successful=95,
        failed=2,
        skipped=3,
        model="claude-opus",
        output_path="./output",
        duration_seconds=120.5,
    )

    assert run_id > 0

    runs = db.get_batch_runs(limit=10)
    assert len(runs) >= 1
    assert runs[0]["total"] == 100
    assert runs[0]["successful"] == 95


def test_export_json(tmp_path: Path) -> None:
    """Test JSON export."""
    db = NotebookDatabase(tmp_path / "test.db")

    # Add records
    for i in range(2):
        record = ExtractionRecord(
            notebook_uuid=f"uuid-export-{i}",
            extraction_date=datetime.now(),
            primary_topic="Test Topic",
            confidence=0.9,
            page_count=5,
            text_length=500,
        )
        db.add_extraction(record)

    # Export
    export_file = tmp_path / "export.json"
    db.export_json(export_file)

    assert export_file.exists()
    content = export_file.read_text(encoding="utf-8")
    assert "uuid-export-0" in content
    assert "Test Topic" in content
