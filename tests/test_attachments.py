from unittest.mock import MagicMock, patch
import pytest
from src.core.attachment_parser import parse_pdf_in_memory, parse_excel_in_memory, parse_image_in_memory

@patch("pdfplumber.open")
def test_parse_pdf_in_memory(mock_open):
    """Verify that parse_pdf_in_memory opens a PDF and extracts text from up to 10 pages."""
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "21BCE0001 is shortlisted"
    # Create 12 pages to test the 10-page limit
    mock_pdf.pages = [mock_page] * 12
    
    mock_open.return_value.__enter__.return_value = mock_pdf
    
    text = parse_pdf_in_memory(b"fake_pdf_bytes")
    assert "21BCE0001" in text
    
    # Verify we extracted text from only the first 10 pages
    assert mock_page.extract_text.call_count == 10

@patch("openpyxl.load_workbook")
def test_parse_excel_in_memory(mock_load):
    """Verify that parse_excel_in_memory reads all sheets and formats rows as CSV lines."""
    mock_wb = MagicMock()
    
    mock_sheet1 = MagicMock()
    mock_sheet1.title = "CSE"
    mock_sheet1.iter_rows.return_value = [
        ("Name", "RegNo", "NeoPAT"),
        ("Alice", "21BCE0001", "NP001"),
        (None, None, None) # Empty row should be filtered out
    ]
    
    mock_sheet2 = MagicMock()
    mock_sheet2.title = "ECE"
    mock_sheet2.iter_rows.return_value = [
        ("Bob", "21BEC0002", "NP002")
    ]
    
    mock_wb.worksheets = [mock_sheet1, mock_sheet2]
    mock_load.return_value = mock_wb
    
    text = parse_excel_in_memory(b"fake_excel_bytes")
    assert "Sheet: CSE" in text
    assert "Alice,21BCE0001,NP001" in text
    assert "Sheet: ECE" in text
    assert "Bob,21BEC0002,NP002" in text

@patch("PIL.Image.open")
@patch("pytesseract.image_to_data")
@patch("pytesseract.image_to_string")
def test_parse_image_in_memory(mock_to_string, mock_to_data, mock_img_open):
    """Verify that parse_image_in_memory computes mean OCR confidence and extracts string."""
    mock_img_open.return_value = MagicMock()
    mock_to_data.return_value = {
        "conf": ["-1", "90", "70", "invalid", "80"]
    }
    mock_to_string.return_value = "WhatsApp Screenshot: SDE Shortlist"
    
    text, confidence = parse_image_in_memory(b"fake_image_bytes")
    assert "SDE Shortlist" in text
    # Mean of valid values [90, 70, 80] = 80.0
    assert confidence == 80.0
