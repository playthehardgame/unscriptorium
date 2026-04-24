"""SQLite database for tracking notebook extraction history."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ExtractionRecord:
    """Single extraction record."""

    notebook_uuid: str
    extraction_date: datetime
    primary_topic: str
    confidence: float
    page_count: int
    text_length: int
    extracted_date_from_content: Optional[str] = None
    model: str = "unknown"
    status: str = "completed"  # completed, failed, skipped


class NotebookDatabase:
    """SQLite database for extraction history."""

    def __init__(self, db_path: Path | str):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main extraction history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_uuid TEXT UNIQUE NOT NULL,
                    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    primary_topic TEXT,
                    confidence REAL,
                    page_count INTEGER,
                    text_length INTEGER,
                    extracted_date_from_content TEXT,
                    model TEXT,
                    status TEXT DEFAULT 'completed',
                    
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Topic assignments (supports multiple topics per notebook)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notebook_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_uuid TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    score REAL,
                    rank INTEGER,
                    
                    FOREIGN KEY (notebook_uuid) REFERENCES extractions(notebook_uuid),
                    UNIQUE(notebook_uuid, topic)
                )
                """
            )

            # Batch processing records
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_notebooks INTEGER,
                    successful INTEGER,
                    failed INTEGER,
                    skipped INTEGER,
                    model TEXT,
                    output_path TEXT,
                    duration_seconds REAL,
                    
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Statistics cache
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    def add_extraction(self, record: ExtractionRecord) -> int:
        """Add extraction record to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO extractions (
                        notebook_uuid,
                        extraction_date,
                        primary_topic,
                        confidence,
                        page_count,
                        text_length,
                        extracted_date_from_content,
                        model,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.notebook_uuid,
                        record.extraction_date,
                        record.primary_topic,
                        record.confidence,
                        record.page_count,
                        record.text_length,
                        record.extracted_date_from_content,
                        record.model,
                        record.status,
                    ),
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                raise ValueError(f"Failed to insert extraction: {e}") from e

    def add_topics(
        self, notebook_uuid: str, topics: dict[str, float]
    ) -> None:
        """Add topic assignments for notebook."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sort by score (highest first)
            sorted_topics = sorted(
                topics.items(), key=lambda x: x[1], reverse=True
            )

            for rank, (topic, score) in enumerate(sorted_topics, 1):
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO notebook_topics (
                            notebook_uuid,
                            topic,
                            score,
                            rank
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (notebook_uuid, topic, score, rank),
                    )
                except sqlite3.Error as e:
                    print(f"Warning: Failed to add topic {topic}: {e}")

            conn.commit()

    def get_extraction(self, notebook_uuid: str) -> Optional[ExtractionRecord]:
        """Retrieve extraction record by UUID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    notebook_uuid,
                    extraction_date,
                    primary_topic,
                    confidence,
                    page_count,
                    text_length,
                    extracted_date_from_content,
                    model,
                    status
                FROM extractions
                WHERE notebook_uuid = ?
                """,
                (notebook_uuid,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return ExtractionRecord(
                notebook_uuid=row[0],
                extraction_date=datetime.fromisoformat(row[1]),
                primary_topic=row[2],
                confidence=row[3],
                page_count=row[4],
                text_length=row[5],
                extracted_date_from_content=row[6],
                model=row[7],
                status=row[8],
            )

    def get_all_extractions(self, limit: int = 1000) -> list[ExtractionRecord]:
        """Get all extraction records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    notebook_uuid,
                    extraction_date,
                    primary_topic,
                    confidence,
                    page_count,
                    text_length,
                    extracted_date_from_content,
                    model,
                    status
                FROM extractions
                ORDER BY extraction_date DESC
                LIMIT ?
                """,
                (limit,),
            )

            records = []
            for row in cursor.fetchall():
                records.append(
                    ExtractionRecord(
                        notebook_uuid=row[0],
                        extraction_date=datetime.fromisoformat(row[1]),
                        primary_topic=row[2],
                        confidence=row[3],
                        page_count=row[4],
                        text_length=row[5],
                        extracted_date_from_content=row[6],
                        model=row[7],
                        status=row[8],
                    )
                )

            return records

    def get_by_topic(self, topic: str, limit: int = 100) -> list[str]:
        """Get all notebook UUIDs for a topic."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT notebook_uuid
                FROM notebook_topics
                WHERE topic = ?
                ORDER BY rank
                LIMIT ?
                """,
                (topic, limit),
            )
            return [row[0] for row in cursor.fetchall()]

    def get_statistics(self) -> dict[str, int]:
        """Get overall statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM extractions")
            total = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT primary_topic) FROM extractions"
            )
            topics = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM extractions WHERE status = 'failed'"
            )
            failed = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(confidence) FROM extractions")
            avg_confidence = cursor.fetchone()[0] or 0.0

            return {
                "total_notebooks": total,
                "unique_topics": topics,
                "failed": failed,
                "avg_confidence": round(avg_confidence, 3),
            }

    def add_batch_run(
        self,
        total: int,
        successful: int,
        failed: int,
        skipped: int,
        model: str,
        output_path: str,
        duration_seconds: float,
    ) -> int:
        """Record a batch processing run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO batch_runs (
                    total_notebooks,
                    successful,
                    failed,
                    skipped,
                    model,
                    output_path,
                    duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (total, successful, failed, skipped, model, output_path, duration_seconds),
            )
            conn.commit()
            return cursor.lastrowid

    def get_batch_runs(self, limit: int = 10) -> list[dict]:
        """Get recent batch runs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    run_date,
                    total_notebooks,
                    successful,
                    failed,
                    skipped,
                    model,
                    output_path,
                    duration_seconds
                FROM batch_runs
                ORDER BY run_date DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [
                {
                    "id": row[0],
                    "run_date": row[1],
                    "total": row[2],
                    "successful": row[3],
                    "failed": row[4],
                    "skipped": row[5],
                    "model": row[6],
                    "output_path": row[7],
                    "duration_seconds": row[8],
                }
                for row in cursor.fetchall()
            ]

    def export_json(self, output_file: Path | str) -> None:
        """Export all extraction records to JSON."""
        records = self.get_all_extractions(limit=10000)
        data = [
            {
                "notebook_uuid": r.notebook_uuid,
                "extraction_date": r.extraction_date.isoformat(),
                "primary_topic": r.primary_topic,
                "confidence": r.confidence,
                "page_count": r.page_count,
                "text_length": r.text_length,
                "extracted_date_from_content": r.extracted_date_from_content,
                "model": r.model,
                "status": r.status,
            }
            for r in records
        ]

        Path(output_file).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def clear(self) -> None:
        """Clear all records (use with caution!)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notebook_topics")
            cursor.execute("DELETE FROM extractions")
            cursor.execute("DELETE FROM batch_runs")
            conn.commit()
