"""PDF processing functions with OCR support."""

import io
from typing import List, Optional, Tuple

import fitz
import pytesseract
from PIL import Image

from config import config
from logging_config import logger


def detect_text_quality(text: str, num_pages: int) -> float:
    """Detect text quality score (0.0-1.0). Higher is better."""
    if not text.strip():
        return 0.0

    # Simple heuristics: text length per page
    avg_chars_per_page = len(text) / max(num_pages, 1)

    # Normalize to 0-1 (assuming 1000 chars/page is good)
    quality = min(avg_chars_per_page / 1000.0, 1.0)

    # Check for common OCR artifacts
    ocr_artifacts = ["\n\n", "\f", "\x0c"]  # page breaks, form feeds
    artifact_count = sum(text.count(artifact) for artifact in ocr_artifacts)
    if artifact_count > num_pages:
        quality *= 0.5  # Penalize excessive artifacts

    return quality


def extract_text_with_ocr(pdf_bytes: bytes, lang: str = "eng") -> str:
    """Extract text from PDF using OCR for image-based pages."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ocr_text = []

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Get page as image
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # OCR the image
            page_text = pytesseract.image_to_string(img, lang=lang)
            ocr_text.append(page_text)

        doc.close()
        return "\n".join(ocr_text)
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        doc.close()
        return ""


def extract_text_from_pdf(pdf_bytes: bytes, request_id: Optional[str] = None) -> str:
    """Extract text from PDF bytes. Used for testing."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if not doc:
        raise ValueError("Invalid PDF document")

    pages_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        pages_text.append(text)

    doc.close()
    return "\n".join(pages_text)


def extract_pages_from_pdf(
    pdf_bytes: bytes, request_id: str
) -> Tuple[str, List[Tuple[int, str]]]:
    """Extract text from PDF and return full text and page details."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if not doc:
        logger.error("Invalid PDF document", extra={"request_id": request_id})
        raise ValueError("Invalid PDF document")

    total_pages = len(doc)

    # Validate PDF has content
    if total_pages == 0:
        doc.close()
        logger.warning("PDF has no pages", extra={"request_id": request_id})
        raise ValueError("PDF document has no pages")

    # Check for reasonable page count (prevent abuse)
    if total_pages > config.max_pages:
        doc.close()
        logger.warning(
            "PDF has too many pages",
            extra={"request_id": request_id, "total_pages": total_pages},
        )
        raise ValueError(f"PDF has too many pages (max {config.max_pages})")

    pages_text = []

    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            text = page.get_text()
            # Validate page has some content
            if not text.strip():
                logger.warning(
                    f"Page {page_num + 1} is empty or has no extractable text",
                    extra={"request_id": request_id, "page_num": page_num + 1},
                )
            pages_text.append((page_num + 1, text))  # page numbers start from 1
        except Exception:
            doc.close()
            logger.error(
                f"Error reading page {page_num + 1}",
                exc_info=True,
                extra={"request_id": request_id, "page_num": page_num + 1},
            )
            raise ValueError(f"Error reading PDF page {page_num + 1}")

    doc.close()

    # Prepare full text
    full_text = "\n".join(text for _, text in pages_text)

    # Check text quality and attempt OCR if needed
    quality_score = detect_text_quality(full_text, total_pages)
    logger.info(
        "Text quality analysis",
        extra={
            "request_id": request_id,
            "quality_score": quality_score,
            "total_pages": total_pages,
        },
    )

    if quality_score < 0.3:  # Low quality threshold
        logger.info(
            "Text quality low, attempting OCR extraction",
            extra={"request_id": request_id},
        )
        try:
            ocr_text = extract_text_with_ocr(pdf_bytes)
            if ocr_text and len(ocr_text.strip()) > len(full_text.strip()):
                logger.info(
                    "OCR extraction successful, using OCR text",
                    extra={"request_id": request_id},
                )
                full_text = ocr_text
                # Re-split into pages (approximate)
                ocr_pages = ocr_text.split("\n\n")  # Simple page splitting
                pages_text = [(i + 1, page) for i, page in enumerate(ocr_pages)]
            else:
                logger.info(
                    "OCR extraction failed or produced shorter text",
                    extra={"request_id": request_id},
                )
        except Exception as e:
            logger.warning(
                f"OCR fallback failed: {e}", extra={"request_id": request_id}
            )

    logger.info(
        "Text extraction completed",
        extra={
            "request_id": request_id,
            "total_pages": total_pages,
            "total_text_length": len(full_text),
        },
    )

    return full_text, pages_text
