import re
from pathlib import Path
import fitz

MAX_WORDS = 180


def _split_text(text, max_words=MAX_WORDS):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words) if words[i:i + max_words]]


def _ocr_blocks(page):
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("This PDF appears scanned. Install the OCR extra and the Tesseract executable.") from exc
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    grouped = {}
    for i, token in enumerate(data["text"]):
        token = token.strip()
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1
        if not token or confidence < 20:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y = data["left"][i] / 2, data["top"][i] / 2
        w, h = data["width"][i] / 2, data["height"][i] / 2
        row = grouped.setdefault(key, {"words": [], "x0": x, "y0": y, "x1": x + w, "y1": y + h})
        row["words"].append(token)
        row["x0"] = min(row["x0"], x); row["y0"] = min(row["y0"], y)
        row["x1"] = max(row["x1"], x + w); row["y1"] = max(row["y1"], y + h)
    return [{"text": " ".join(row["words"]), "bbox": [row["x0"], row["y0"], row["x1"], row["y1"]]} for row in grouped.values()]


def extract_pdf(path: Path):
    pages = []
    with fitz.open(path) as pdf:
        for page_index, page in enumerate(pdf):
            blocks = []
            for block in page.get_text("blocks", sort=True):
                text = re.sub(r"\s+", " ", block[4]).strip()
                if text:
                    blocks.append({"text": text, "bbox": [round(float(v), 2) for v in block[:4]]})
            if not blocks:
                blocks = _ocr_blocks(page)
            chunks = []
            for block in blocks:
                for part in _split_text(block["text"]):
                    chunks.append({"page_number": page_index + 1, "text": part, "bbox": block["bbox"]})
            pages.append({"page_number": page_index + 1, "chunks": chunks})
    if not any(page["chunks"] for page in pages):
        raise ValueError("No readable text found. Check the PDF or install Tesseract OCR for scanned files.")
    return pages