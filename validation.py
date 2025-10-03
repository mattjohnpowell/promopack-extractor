"""Input validation functions."""

import re
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Validate URL format and security."""
    try:
        parsed = urlparse(url)
        # Check scheme
        if parsed.scheme not in ["http", "https"]:
            return False
        # Check netloc exists
        if not parsed.netloc:
            return False
        # Basic security checks - prevent localhost/private IPs
        if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
            return False
        # Check for private IP ranges (basic check)
        if parsed.hostname and re.match(
            r"^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)", parsed.hostname
        ):
            return False
        return True
    except Exception:
        return False


def validate_pdf_content(pdf_bytes: bytes) -> bool:
    """Validate that the content is actually a PDF."""
    if len(pdf_bytes) < 4:
        return False
    # Check PDF header
    return pdf_bytes.startswith(b"%PDF-")
