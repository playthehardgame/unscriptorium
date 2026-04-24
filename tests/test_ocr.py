"""Test OCR and text extraction functionality."""

from PIL import Image, ImageDraw

from kindle_notes.ocr import detect_text_from_image, extract_text_from_pages


def test_detect_blank_page() -> None:
    """Test detection of completely blank page."""
    img = Image.new("RGB", (800, 1000), color="white")
    result = detect_text_from_image(img)
    assert "[PAGINA VUOTA]" in result


def test_detect_sparse_content() -> None:
    """Test detection of page with minimal content."""
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    # Draw minimal sparse content (50 pixels = 0.00625% of 800x1000)
    for i in range(50):
        draw.point((i * 10, i * 5), fill="black")
    
    result = detect_text_from_image(img)
    assert "pochi segni" in result or "sparso" in result


def test_detect_dense_content() -> None:
    """Test detection of page with significant content."""
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    # Fill 20% of the page with dark pixels
    draw.rectangle([(0, 0), (400, 200)], fill="black")
    
    result = detect_text_from_image(img)
    assert "denso" in result


def test_extract_text_from_empty_list() -> None:
    """Test handling of empty page list."""
    result = extract_text_from_pages([])
    assert "[PAGINA VUOTA]" in result


def test_extract_text_aggregates_descriptions() -> None:
    """Test that extract_text_from_pages combines multiple page descriptions."""
    blank = Image.new("RGB", (800, 1000), color="white")
    dense = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(dense)
    draw.rectangle([(0, 0), (400, 500)], fill="black")
    
    result = extract_text_from_pages([blank, dense])
    assert "Pagina 1:" in result
    assert "Pagina 2:" in result
    assert "Notebook: 1/2 pagine" in result
