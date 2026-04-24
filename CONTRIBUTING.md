# 🤝 Contributing Guide

Welcome! We're excited to have you contribute to the Kindle Notebook Transcriber project.

```
╔════════════════════════════════════════════════════╗
║                                                    ║
║  🎨 CODE  →  ✅ TEST  →  📝 DOCS  →  🚀 SHIP    ║
║                                                    ║
║           TDD-First Development Culture           ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

## Core Principles

1. **Test-Driven Development (TDD)**
   - Write failing test first
   - Implement code to pass test
   - Refactor with confidence

2. **Maintainability Over Cleverness**
   - Code clarity is priority
   - Explicit > implicit
   - Comment complex logic only

3. **Privacy & Security First**
   - No hardcoded secrets
   - Sanitize personal data
   - Audit sensitive operations

4. **Cross-Platform Compatibility**
   - Test on Linux, Mac, Windows
   - Use relative paths
   - Handle edge cases

---

## Getting Started

### 1. Fork & Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/unscriptorium.git
cd unscriptorium
```

### 2. Create Branch

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bugfix branch
git checkout -b fix/issue-description

# Naming convention:
# feature/*, bugfix/*, docs/*, refactor/*
```

### 3. Set Up Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 4. Make Changes

```bash
# Edit files in your favorite editor
# Then run tests
pytest tests/ -v

# Format code
ruff format kindle_notes/ tests/

# Lint
ruff check kindle_notes/ tests/
```

---

## Development Workflow

### TDD Process (Required)

```
1. RED: Write failing test
   └─ pytest tests/test_feature.py::test_name
      FAILED ✗

2. GREEN: Implement code
   └─ pytest tests/test_feature.py::test_name
      PASSED ✓

3. REFACTOR: Clean up
   └─ Maintain green state
   └─ Improve readability
```

Example:

```python
# tests/test_feature.py
def test_new_feature_returns_uppercase():
    from kindle_notes.feature import process
    
    result = process("hello")
    assert result == "HELLO"

# Step 1: Run (FAILS)
# $ pytest tests/test_feature.py::test_new_feature_returns_uppercase
# FAILED: NameError: process not defined

# Step 2: Implement
# kindle_notes/feature.py
def process(text):
    return text.upper()

# Step 3: Run (PASSES)
# $ pytest tests/test_feature.py::test_new_feature_returns_uppercase
# PASSED ✓

# Step 4: Refactor if needed (maintain PASSED)
```

### Code Style

```python
# ✓ GOOD
def extract_text_from_image(img: Image) -> str:
    """Extract text description from notebook page."""
    gray = img.convert("L")
    pixels = list(gray.getdata())
    dark_count = sum(1 for p in pixels if p < 128)
    ink_ratio = dark_count / len(pixels)
    
    if ink_ratio < 0.0001:
        return "[PAGINA VUOTA]"
    return "[Pagina con contenuto]"

# ✗ BAD
def extract_text_from_image(img):
    # Funzione per estrarre testo
    g = img.convert("L")
    p = list(g.getdata())
    d = sum(1 for x in p if x<128)
    r = d/len(p)
    if r<0.0001: return "[PAGINA VUOTA]"
    return "[Pagina con contenuto]"
```

Guidelines:
- Use type hints (Python 3.10+)
- Docstrings for public functions
- Max line length: 88 chars
- Use f-strings for formatting
- Avoid global state

---

## Testing Guidelines

### Unit Tests (Per-function)

```python
# tests/test_ocr.py
def test_detect_blank_page():
    """Test blank page detection."""
    img = Image.new("RGB", (800, 1000), color="white")
    result = detect_text_from_image(img)
    assert "[PAGINA VUOTA]" in result

def test_detect_dense_content():
    """Test dense content detection."""
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (400, 500)], fill="black")
    result = detect_text_from_image(img)
    assert "denso" in result
```

### Integration Tests (Multi-component)

```python
# tests/test_extract_pipeline.py
def test_extract_notebooks_writes_json(tmp_path):
    """Test full extraction pipeline."""
    # Setup
    source = tmp_path / "notebooks"
    source.mkdir()
    # Create test notebook...
    
    # Execute
    result = extract_notebooks(source, ...)
    
    # Verify
    assert result.processed == 1
    assert (tmp_path / "output" / "transcriptions.json").exists()
```

### Coverage Goals

```
Minimum: 70% coverage
Target:  85%+

Run:     pytest tests/ --cov=kindle_notes
Report:  pytest tests/ --cov=kindle_notes --cov-report=html
```

---

## Commit Messages

```
Format: <type>: <subject>

<body>

<footer>

Example:
  fix: correct coordinate decoder for edge case
  
  The 2nd-order delta integration wasn't handling
  negative deltas > 127 correctly. Added proper
  sign-extension logic.
  
  Fixes #42
  Tested on 3 edge case notebooks.

Types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation only
  style:    Code formatting
  refactor: Logic reorganization
  perf:     Performance improvement
  test:     Test additions/changes
  chore:    Dependencies, CI, etc.
```

Keep commits focused:
- One logical change per commit
- Failing tests → passing implementation
- Include test updates

---

## Pull Request Process

### 1. Before Submitting PR

```bash
# Update branch with main
git fetch origin
git rebase origin/main

# Run full test suite
pytest tests/ -v

# Check code quality
ruff check kindle_notes/ tests/
ruff format kindle_notes/ tests/

# Verify no test files committed
git diff --cached tests/
```

### 2. Create Pull Request

**Title:** Clear and descriptive
```
✓ feat: add pytesseract fallback for OCR
✗ update stuff
```

**Description:**
```markdown
## What does this PR do?
Brief explanation of changes.

## Why?
Problem statement or feature request #123.

## How was this tested?
- [ ] Unit tests added
- [ ] Integration tests pass
- [ ] Manual testing: [describe]

## Checklist
- [ ] Tests pass (pytest tests/ -v)
- [ ] Code formatted (ruff format)
- [ ] Lints pass (ruff check)
- [ ] No hardcoded secrets
- [ ] Documentation updated
- [ ] Commits are logical and clean
```

### 3. Review Process

Maintainers will:
1. Review code style and logic
2. Request changes if needed
3. Verify tests pass
4. Approve and merge

Your PR might get requests like:
- "Can you add a test for edge case X?"
- "This variable name could be clearer"
- "Need to update docs here"

**This is normal and helps maintain quality!**

---

## Areas for Contribution

### 🎯 High Priority

- [ ] ML-based topic classifier (replace keywords)
- [ ] Handwriting OCR models
- [ ] Performance optimization for large batches
- [ ] Database backend support

### 📝 Medium Priority

- [ ] Additional language support
- [ ] Export to PDF
- [ ] Web UI prototype
- [ ] API documentation

### 🎨 Low Priority (But Welcome!)

- [ ] Visual redesigns
- [ ] Additional export formats
- [ ] Example notebooks
- [ ] Community templates

---

## Reporting Issues

Found a bug? Have a feature request?

### Bug Report

```markdown
## Description
Brief explanation of the issue.

## Steps to Reproduce
1. Run `kindle-notes extract ...`
2. Process notebook with X pages
3. See error: ...

## Expected Behavior
Should have produced Y, not Z.

## Actual Behavior
Error message / wrong output.

## Environment
- OS: Ubuntu 20.04
- Python: 3.10.5
- Package version: 1.0

## Logs
[paste error output]
```

### Feature Request

```markdown
## Description
What would you like to add?

## Use Case
Why do you need this?

## Proposed Solution
How would you implement it?

## Alternatives Considered
Other approaches?
```

---

## Questions?

- 📖 Read README.md for overview
- 🔧 Check INSTALLATION.md for setup
- 📚 Review existing code and tests
- 💬 Open a Discussion for questions

---

<div align="center">

### 🙏 Thank You!

Every contribution makes this project better.

Together, we're making Kindle Scribe notebooks more useful.

```
  ╔═══════════════════════════════╗
  ║  Contributors Welcome Here 🎉 ║
  ╚═══════════════════════════════╝
```

</div>
