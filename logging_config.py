"""Logging configuration for the PromoPack Claim Extractor."""

import json
import logging
from datetime import datetime

from config import config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if they exist
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "processing_time"):
            log_entry["processing_time"] = record.processing_time
        if hasattr(record, "pdf_url"):
            log_entry["pdf_url"] = record.pdf_url
        if hasattr(record, "file_size"):
            log_entry["file_size"] = record.file_size
        if hasattr(record, "claims_count"):
            log_entry["claims_count"] = record.claims_count
        if hasattr(record, "detected_language"):
            log_entry["detected_language"] = record.detected_language

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging():
    """Setup application logging."""
    logger = logging.getLogger("promopack-extractor")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler (optional, for production)
    if config.log_to_file:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logging()
