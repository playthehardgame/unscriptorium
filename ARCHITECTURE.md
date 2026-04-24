# 🏗️ Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      KINDLE NOTEBOOK PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   INPUT               PROCESSING              OUTPUT            │
│   ┌──────────┐       ┌──────────┐            ┌──────────┐      │
│   │ .nbk     │       │ Render   │            │ PNG      │      │
│   │ Files    │──────→│ Engine   │───────────→│ Images   │      │
│   │ (SQLite) │       │ (Ion)    │            │          │      │
│   └──────────┘       └──────────┘            └──────────┘      │
│                            ↓                       ↓            │
│                      ┌──────────┐            ┌──────────┐      │
│                      │ OCR      │            │ JSON     │      │
│                      │ Module   │───────────→│ Transcr. │      │
│                      │ (Heur.)  │            │          │      │
│                      └──────────┘            └──────────┘      │
│                            ↓                       ↓            │
│                      ┌──────────┐            ┌──────────┐      │
│                      │ Classify │            │ JSON     │      │
│                      │ Topics   │───────────→│ Classes  │      │
│                      │ (KW)     │            │          │      │
│                      └──────────┘            └──────────┘      │
│                            ↓                       ↓            │
│                      ┌──────────┐            ┌──────────┐      │
│                      │ Markdown │            │ MD Files │      │
│                      │ Builder  │───────────→│ (Grouped)│      │
│                      │ (Group)  │            │          │      │
│                      └──────────┘            └──────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Architecture

### Layer Model

```
┌──────────────────────────────────────┐
│  CLI LAYER (cli.py)                  │
│  ├─ argparse entry points            │
│  ├─ Coordinated command dispatch     │
│  └─ Human-friendly output            │
└───────────────┬──────────────────────┘
                │
┌───────────────▼──────────────────────┐
│  ORCHESTRATION LAYER (extract.py)    │
│  ├─ Discover notebooks               │
│  ├─ Coordinate pipeline stages       │
│  ├─ Manage intermediate results      │
│  ├─ Database tracking ⭐             │
│  └─ Write output artifacts           │
└───────────────┬──────────────────────┘
                │
┌───────────────▼──────────────────────┐
│  DOMAIN LAYER (Business Logic)       │
│  ├─ database.py (History tracking)   │
│  ├─ ocr.py         (Text extraction) │
│  ├─ classify.py    (Topic detection) │
│  ├─ markdown.py    (Report building) │
│  └─ ink_render.py  (Rendering API)   │
└───────────────┬──────────────────────┘
                │
┌───────────────▼──────────────────────┐
│  INFRASTRUCTURE LAYER                │
│  ├─ render_ink.py   (Core decoder)   │
│  ├─ layout.py       (FS structure)   │
│  └─ External libs   (Pillow, ion)    │
└──────────────────────────────────────┘
```

### Dependency Flow

```
cli.py
  └─→ extract.py
       ├─→ layout.py (folder structure)
       ├─→ database.py (tracking) ⭐
       ├─→ ink_render.py (rendering)
       │    └─→ render_ink.py (core decoder)
       ├─→ ocr.py (text extraction)
       │    └─→ PIL (image analysis)
       └─→ classify.py (topic detection)
            └─→ markdown.py (output)
```

### No Circular Dependencies

```
✓ ALLOWED          ✗ NOT ALLOWED
cli.py → extract.py   extract.py → cli.py
extract.py → ocr.py   ocr.py → extract.py
ocr.py → classify.py  classify.py → cli.py
```

---

## Kernel: Coordinate Decoder

### Problem Statement

Kindle stores handwriting as **instruction streams**, not direct coordinates.

```
Format: INSTRUCTION_STREAM with 2ND-ORDER DELTA ENCODING
┌─────────────────────────────────────────────────────────┐
│ Signature  │  01 01                                      │
├─────────────────────────────────────────────────────────┤
│ Count      │  uint32 (e.g., 0x000000C8 = 200 points)   │
├─────────────────────────────────────────────────────────┤
│ Instructions│ Packed nibbles (2 per byte)               │
│            │  Each nibble: delta value (-7 to +8)       │
│            │  Sequence: dx0, dy0, dx1, dy1, ...         │
├─────────────────────────────────────────────────────────┤
│ Payload    │ Variable-length bytes                      │
│            │  Interpreted based on instruction values   │
└─────────────────────────────────────────────────────────┘
```

### Algorithm

```python
def _decode_stroke_values(stream: bytes) -> tuple[list[int], list[int]]:
    """Decode 2nd-order delta instruction stream to coordinates."""
    
    # Parse header
    count = unpack_uint32(stream[0:4])  # Number of points
    instructions = stream[4:4 + count // 2]  # Packed nibbles
    payload_offset = 4 + (count + 1) // 2
    payload = stream[payload_offset:]
    
    # Extract nibble instructions
    nibbles = []
    for byte in instructions:
        nibbles.append(byte & 0x0F)      # Low nibble
        nibbles.append((byte >> 4) & 0x0F)  # High nibble
    nibbles = nibbles[:count]
    
    # Initialize state for 2nd-order integration
    x_values, y_values = [], []
    prev_dx, prev_dy = 0, 0  # 1st-order deltas
    payload_index = 0
    
    for i in range(count):
        instruction = nibbles[i]
        
        # Decode delta from instruction
        d = _decode_delta(instruction, payload, payload_index)
        
        if instruction < 16:  # Direct nibble
            dx = _nibble_to_signed(instruction)
            dy = _nibble_to_signed(nibbles[i+1]) if i+1 < count else 0
            i += 1
        else:  # Extended payload
            dx, dy, payload_index = _decode_extended(payload, payload_index)
        
        # Apply 2nd-order integration
        x = x_values[-1] + prev_dx + dx if x_values else dx
        y = y_values[-1] + prev_dy + dy if y_values else dy
        
        x_values.append(x)
        y_values.append(y)
        
        # Update 1st-order deltas for next iteration
        prev_dx = dx
        prev_dy = dy
    
    return x_values, y_values
```

### Key Points

1. **Packed Nibbles:** 2 instructions per byte (4 bits each)
2. **Signed Values:** Nibbles interpreted as signed (-8 to +7) or as payload pointers
3. **2nd-Order Integration:** Uses previous deltas to predict next point
4. **Payload Extension:** For large jumps, stores full values in payload section

---

## OCR Module Strategy

### Heuristic Approach (Default)

```
Image Analysis Flow:
┌────────────────────┐
│  PIL Image         │
└─────────┬──────────┘
          ↓
┌─────────────────────┐
│ Convert to Grayscale│
└─────────┬──────────┘
          ↓
┌──────────────────────────┐
│ Count dark pixels (<128) │
│ ink_ratio = dark/total   │
└─────────┬────────────────┘
          ↓
┌──────────────────────────┐
│ Classify by Thresholds   │
│ < 0.00001: BLANK         │
│ < 0.005:   SPARSE        │
│ < 0.10:    MODERATE      │
│ ≥ 0.10:    DENSE         │
└──────────────────────────┘
```

**Pros:**
- Fast (O(n) where n = pixel count)
- No external dependencies
- Robust to small noise

**Cons:**
- No actual text content
- Can't distinguish different ink types
- Threshold-dependent

### Tesseract Fallback (Optional)

```
if use_tesseract and pytesseract_available:
    try:
        text = pytesseract.image_to_string(
            image,
            lang='ita+eng'  # Italian + English
        )
        if text.strip():
            return text  # Real OCR output
    except Exception:
        pass  # Fall through to heuristic

# Default: heuristic analysis
return extract_text_from_pages(pages)
```

**When to use:**
- Need actual transcription text
- Tesseract installed on system
- Willing to accept slower processing
- Have computational resources

---

## Database Layer

### Schema

```sql
-- Main extraction history
CREATE TABLE extractions (
    id INTEGER PRIMARY KEY,
    notebook_uuid TEXT UNIQUE NOT NULL,
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    primary_topic TEXT,
    confidence REAL,
    page_count INTEGER,
    text_length INTEGER,
    extracted_date_from_content TEXT,
    model TEXT,
    status TEXT DEFAULT 'completed',  -- completed, failed, skipped
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Topic assignments (supports multiple per notebook)
CREATE TABLE notebook_topics (
    id INTEGER PRIMARY KEY,
    notebook_uuid TEXT NOT NULL,
    topic TEXT NOT NULL,
    score REAL,
    rank INTEGER,
    FOREIGN KEY (notebook_uuid) REFERENCES extractions(notebook_uuid),
    UNIQUE(notebook_uuid, topic)
);

-- Batch processing history
CREATE TABLE batch_runs (
    id INTEGER PRIMARY KEY,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_notebooks INTEGER,
    successful INTEGER,
    failed INTEGER,
    skipped INTEGER,
    model TEXT,
    output_path TEXT,
    duration_seconds REAL,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Statistics cache
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Usage

```python
from kindle_notes import NotebookDatabase

db = NotebookDatabase("./output/notebooks.db")

# Add extraction record
record = ExtractionRecord(
    notebook_uuid="abc-123",
    extraction_date=datetime.now(),
    primary_topic="Data & Analytics",
    confidence=0.92,
    page_count=42,
    text_length=5000,
    extracted_date_from_content="2024-04-15",
    model="claude-opus-4-7",
    status="completed"
)
db.add_extraction(record)

# Add topic assignments
db.add_topics("abc-123", {
    "Data & Analytics": 0.92,
    "AI & Automazione": 0.45
})

# Query operations
all_records = db.get_all_extractions(limit=1000)
data_notebooks = db.get_by_topic("Data & Analytics", limit=100)
stats = db.get_statistics()
batch_runs = db.get_batch_runs(limit=10)

# Export
db.export_json("backup.json")
```

### Lifecycle

```
extract_notebooks()
    │
    ├─ Initialize NotebookDatabase (create tables if needed)
    │
    ├─ For each notebook:
    │  ├─ Render + OCR + Classify
    │  ├─ Add extraction record to DB
    │  └─ Add topic assignments to DB
    │
    └─ Record batch run metadata
```

### Benefits

- **Audit Trail:** Complete history of all extractions
- **Replay:** Re-run specific notebook via UUID lookup
- **Analytics:** Query by topic, date, confidence
- **Incremental:** Skip already-processed notebooks
- **Export:** Backup to JSON for external tools

---

## Classification System

### Taxonomy Structure

```
TOPIC_DEFINITIONS = {
    "AI & Automazione": {
        "primary": ["AI", "ML", "algoritmo", "automazione", ...],
        "secondary": ["intelligenza", "learning", "pattern", ...],
    },
    "Data & Analytics": {
        "primary": ["data", "analytics", "BI", "database", ...],
        "secondary": ["report", "insight", "trend", ...],
    },
    # ... 9 more topics
}
```

### Scoring Algorithm

```python
def classify_notebook(notebook_id: str, text: str) -> Classification:
    """Classify notebook into topic with confidence score."""
    
    scores = {}
    text_lower = text.lower()
    
    for topic, keywords in TOPIC_DEFINITIONS.items():
        primary_hits = sum(
            text_lower.count(kw) 
            for kw in keywords["primary"]
        )
        secondary_hits = sum(
            text_lower.count(kw) 
            for kw in keywords["secondary"]
        )
        
        # Weighted scoring
        score = (primary_hits * 3 + secondary_hits * 1)
        max_possible = len(keywords["primary"]) * 3
        
        scores[topic] = score / max(max_possible, 1)
    
    # Select primary topic
    best_topic = max(scores, key=scores.get)
    confidence = scores[best_topic]
    
    # Fallback if low confidence
    if confidence < 0.40:
        best_topic = "Altro"
        confidence = 0.10
    
    return Classification(
        primary_topic=best_topic,
        topics=[best_topic],  # Could add secondaries
        confidence=confidence,
        extracted_date=extract_date(text),
    )
```

### Confidence Interpretation

```
Confidence Score Meaning:
├─ 0.90-1.00 ✓✓✓ Very confident (primary keywords heavily present)
├─ 0.70-0.89 ✓✓  Confident (good keyword presence)
├─ 0.40-0.69 ✓   Moderate (some keywords, could be mixed)
├─ 0.10-0.39 ?   Low confidence (few keywords, likely "Altro")
└─ < 0.10    ✗   Very low (probably misclassified)
```

---

## Output Schema

### Directory Layout

```
output/
├── json/                          ← Machine-readable data
│   ├── transcriptions.json        ← All extracted text
│   ├── classifications.json       ← Topic + metadata
│   ├── topics_index.json          ← UUID grouped by topic
│   └── manifest.json              ← Version + summary
│
├── markdown/                      ← Human-readable reports
│   ├── kindle_notebooks_completo.md  ← Master file (all topics)
│   ├── topic_ai_automazione.md       ← Topic-specific
│   ├── topic_data_analytics.md
│   └── ... (9 more topics)
│
├── renders/                       ← Visual artifacts
│   ├── {uuid}_p001.png            ← First page
│   ├── {uuid}_p002.png
│   └── ...
│
└── logs/                          ← Processing logs
    ├── extraction.log
    └── errors.log
```

### JSON Schema

```json
{
  "transcriptions.json": {
    "uuid-key": "Text content (OCR or heuristic)",
    ...
  },
  
  "classifications.json": {
    "uuid-key": {
      "primary_topic": "Data & Analytics",
      "topics": ["Data & Analytics", "AI & Automazione"],
      "confidence": 0.85,
      "extracted_date": "2024-04-15",
      "preview": "First 200 chars of transcription...",
      "page_count": 42
    },
    ...
  },
  
  "topics_index.json": {
    "Topic Name": ["uuid1", "uuid2", ...],
    ...
  },
  
  "manifest.json": {
    "version": "1.0",
    "total_notebooks": 105,
    "extraction_model": "claude-opus-4-7",
    "by_topic": { ... },
    "by_uuid": { ... }
  }
}
```

---

## Testing Strategy

### Test Pyramid

```
        ▲
       /│\
      / │ \
     /  │  \        E2E Tests (2)
    /   │   \       └─ Full pipeline on test data
   /    │    \
  /  ───┼───  \     Integration Tests (4)
 /   │  │  │   \    └─ Multi-component flows
/    │  │  │    \
─────┼──┼──┼─────   Unit Tests (11)
     │  │  │        └─ Individual functions
   CLI│OCR│MARKDOWN
```

### Test Organization

```
tests/
├── test_cli.py                (CLI dispatch)
├── test_extract_pipeline.py   (Notebook discovery + extraction)
├── test_classify.py           (Classification logic)
├── test_ocr.py                (OCR module)
├── test_markdown_build.py     (Report generation)
└── test_ink_render_api.py     (Rendering wrapper)

Naming convention:
- test_*() for unit tests
- Fixture-based setup for common data
- Monkeypatch for external dependencies
```

### Mocking Strategy

```python
@pytest.fixture
def fake_render(monkeypatch):
    """Mock rendering to avoid .nbk file dependency."""
    def mock_render(nbk_path):
        return [Image.new("RGB", (800, 1000), color="white")]
    
    monkeypatch.setattr(
        "kindle_notes.extract.render_nbk_pages",
        mock_render
    )
    return mock_render

def test_extract_with_mock_render(fake_render, tmp_path):
    """Test extraction without real notebooks."""
    result = extract_notebooks(
        tmp_path / "notebooks",
        tmp_path / "output",
        ...
    )
    assert result.processed == 1
```

---

## Performance Considerations

### Bottlenecks

```
Operation          Time (per notebook)  Optimization
─────────────────────────────────────────────────────
Read .nbk file:    ~100ms              ✓ Parallelizable
Render to PNG:     ~500ms              ✓ Parallelizable
OCR analysis:      ~50ms               ✓ Parallelizable
Classification:    ~10ms               ✓ Parallelizable
Write JSON:        ~50ms               ✓ Batch write
─────────────────────────────────────────────────────
Total sequential:  ~710ms × 105 ≈ 75s

With parallelization (4 workers):
  Total time: ~20s (4x speedup)
```

### Memory Profile

```
Per-notebook:
├─ Notebook image: 800×1000 RGB ≈ 2.4 MB
├─ Decoded pixels: ≈ 0.8 MB (grayscale analysis)
├─ Text content: ≈ 10 KB (average transcription)
└─ Metadata: ≈ 1 KB

Total per notebook: ~3.2 MB
For 105 notebooks: ~336 MB (comfortable in 1 GB RAM)
```

### Optimization Opportunities

1. **Parallelization:** Use multiprocessing for render/OCR/classify
2. **Streaming:** Process notebooks sequentially, write incrementally
3. **Caching:** Cache rendered PNGs to skip re-rendering
4. **Incremental:** Track processed notebooks, skip already done

---

## Error Handling

### Failure Modes

```
Scenario              Handling              User Impact
────────────────────────────────────────────────────────
Corrupt .nbk:        Skip, log error       Notebook skipped
Invalid PNG decode:  Fallback render      Degraded image
OCR crash:           Use heuristic        Heuristic analysis
Classification fail: Default to "Altro"   Safe classification
────────────────────────────────────────────────────────
```

### Resilience Patterns

```python
# Try OCR, fallback to heuristic
try:
    text = pytesseract.image_to_string(img)
except Exception:
    text = extract_text_from_pages(pages)

# Graceful degradation
try:
    topic = classify_notebook(uuid, text)
except Exception:
    topic = Classification(primary_topic="Altro", confidence=0.0)

# Continue on partial failure
for notebook in notebooks:
    try:
        process_notebook(notebook)
    except Exception as e:
        logger.error(f"Skipped {notebook.uuid}: {e}")
        continue  # Don't stop entire batch
```

---

## Future Architecture

### Planned Evolution

```
v1.0 (Current)
├─ Keyword-based classification
├─ Heuristic OCR (tesseract optional)
└─ Markdown output only

v2.0 (Planned)
├─ ML topic classifier
├─ Handwriting recognition models
├─ Web UI visualization
└─ PDF export

v3.0 (Vision)
├─ Real-time sync with Kindle
├─ Collaborative annotation
├─ Knowledge graph integration
└─ Enterprise deployment
```

---

<div align="center">

### 📚 Architecture Review Checklist

- [ ] Single responsibility per module
- [ ] No circular dependencies
- [ ] Clear error handling
- [ ] Testable design (dependency injection)
- [ ] Documented algorithms
- [ ] Performance bottlenecks identified
- [ ] Scalability path clear

</div>
