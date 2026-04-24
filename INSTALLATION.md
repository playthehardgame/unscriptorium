# 📥 Installation Guide

## System Requirements

```
┌─────────────────────────────────┐
│  MINIMUM                        │
├─────────────────────────────────┤
│  Python:      3.10+             │
│  RAM:         512 MB            │
│  Disk:        200 MB            │
│  OS:          Linux/Mac/Windows │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  RECOMMENDED                    │
├─────────────────────────────────┤
│  Python:      3.11+             │
│  RAM:         2+ GB             │
│  Disk:        1+ GB             │
│  CPU:         4+ cores          │
└─────────────────────────────────┘
```

## Step-by-Step Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-repo/unscriptorium.git
cd unscriptorium
```

### 2. Create Virtual Environment (Recommended)

```bash
# Python venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate      # Windows
```

### 3. Install Package

```bash
# Development mode (editable)
pip install -e .

# Or production
pip install .
```

This installs:
- ✓ amazon.ion (Ion codec for Kindle format)
- ✓ pillow (Image processing)
- ✓ pytest (Testing framework)
- ✓ ruff (Linting)

### 4. Verify Installation

```bash
# Check CLI is available
kindle-notes --help

# Run tests
pytest tests/ -v

# Should see: 17 passed ✓
```

---

## Optional: OCR with Tesseract

For real OCR transcription instead of heuristics:

### Linux (Ubuntu/Debian)

```bash
# Install tesseract system package
sudo apt-get install tesseract-ocr tesseract-ocr-ita

# Install Python wrapper
pip install pytesseract
```

### macOS

```bash
# Install via Homebrew
brew install tesseract tesseract-lang

# Install Python wrapper
pip install pytesseract
```

### Windows

1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location (C:\Program Files\Tesseract-OCR)
3. Add to PATH (automatic in installer)
4. Install Python wrapper:

```bash
pip install pytesseract
```

### Verify Tesseract

```bash
# Check installation
tesseract --version

# Test with CLI
kindle-notes extract ./notebooks-raw \
    --output ./output \
    --vector-render \
    --use-tesseract
```

---

## Troubleshooting Installation

### Error: "python: command not found"

```bash
# Check Python version
python3 --version

# Use python3 instead
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -e .
```

### Error: "pip: command not found"

```bash
# Install pip
python -m ensurepip --upgrade

# Or upgrade pip
python -m pip install --upgrade pip
```

### Error: "amazon.ion not found"

```bash
# Install explicitly
pip install amazon.ion

# Or reinstall package with dependencies
pip install -e . --force-reinstall
```

### Error: "Permission denied" (Linux/Mac)

```bash
# Use user install
pip install --user -e .

# Or use sudo (not recommended for venv)
sudo pip install -e .
```

### Error: "ModuleNotFoundError: kindle_notes"

```bash
# Make sure you're in project directory
cd unscriptorium

# Reinstall in development mode
pip install -e .

# Verify
python -c "import kindle_notes; print('✓ OK')"
```

---

## Development Setup

### Install Development Tools

```bash
pip install -e ".[dev]"  # With dev dependencies

# Or manually
pip install pytest pytest-cov ruff black mypy
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_ocr.py -v

# With coverage
pytest tests/ --cov=kindle_notes --cov-report=html
```

### Linting

```bash
# Check code style
ruff check kindle_notes/ tests/

# Format code
ruff format kindle_notes/ tests/
```

### Type Checking

```bash
mypy kindle_notes/
```

---

## Docker Installation (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/*

# Copy and install
COPY . .
RUN pip install -e .

# CLI entrypoint
ENTRYPOINT ["kindle-notes"]
```

Build:
```bash
docker build -t kindle-notes .
```

Run:
```bash
docker run --rm -v $(pwd):/data kindle-notes \
    extract /data/notebooks-raw \
    --output /data/output \
    --vector-render
```

---

## Uninstall

```bash
# Remove package
pip uninstall kindle-notes

# Remove virtual environment
deactivate
rm -rf venv/

# Or on Windows
deactivate
rmdir /s venv
```

---

<div align="center">

### ✅ Installation Complete!

Next: Read **README.md** for usage guide

</div>
