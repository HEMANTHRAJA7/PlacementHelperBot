import io
import pdfplumber
import openpyxl
from PIL import Image
import pytesseract
from typing import Tuple

def parse_pdf_in_memory(pdf_bytes: bytes) -> str:
    """Extracts plain text from the first 10 pages of a PDF completely in-memory."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # Limit to the first 10 pages
        for page in pdf.pages[:10]:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)

def parse_excel_in_memory(excel_bytes: bytes) -> str:
    """Reads all worksheets and rows of an Excel spreadsheet in-memory, returning comma-separated rows."""
    text_parts = []
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), read_only=True, data_only=True)
    for sheet in wb.worksheets:
        sheet_rows = []
        for row in sheet.iter_rows(values_only=True):
            # Format row values as comma-separated strings, filtering out None values
            row_str = ",".join([str(val) if val is not None else "" for val in row])
            if row_str.strip(", "):
                sheet_rows.append(row_str)
        if sheet_rows:
            text_parts.append(f"Sheet: {sheet.title}\n" + "\n".join(sheet_rows))
    wb.close()
    return "\n\n".join(text_parts)

def parse_image_in_memory(image_bytes: bytes) -> Tuple[str, float]:
    """Runs local Tesseract OCR on in-memory image bytes, returning the extracted text and mean confidence."""
    image = Image.open(io.BytesIO(image_bytes))
    
    # Get word confidences to determine local OCR extraction quality
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = []
    for conf_val in ocr_data.get("conf", []):
        try:
            val = int(conf_val)
            if val != -1:
                confidences.append(val)
        except (ValueError, TypeError):
            continue
            
    mean_confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0
    text = pytesseract.image_to_string(image)
    return text, mean_confidence
