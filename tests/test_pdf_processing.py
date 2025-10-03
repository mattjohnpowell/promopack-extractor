from unittest.mock import MagicMock, patch

import fitz
import pytest
from langdetect import LangDetectException

from llm_integration import (audit_data_source_language,
                             extract_claims_with_langextract,
                             fallback_claim_search)
from pdf_processing import extract_text_from_pdf


class TestPDFProcessing:
    """Test PDF processing functions."""

    @patch("fitz.open")
    def test_extract_text_from_pdf_success(self, mock_fitz_open):
        """Test successful PDF text extraction."""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page 2 content"
        mock_doc.load_page.side_effect = [mock_page1, mock_page2]
        mock_doc.__len__.return_value = 2
        mock_fitz_open.return_value = mock_doc

        result = extract_text_from_pdf(b"fake pdf content")

        assert "Page 1 content" in result
        assert "Page 2 content" in result
        mock_doc.close.assert_called_once()

    @patch("fitz.open")
    def test_extract_text_from_pdf_empty(self, mock_fitz_open):
        """Test PDF with no text."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_fitz_open.return_value = mock_doc

        result = extract_text_from_pdf(b"fake pdf content")

        assert result == ""
        mock_doc.close.assert_called_once()

    @patch("fitz.open")
    def test_extract_text_from_pdf_error(self, mock_fitz_open):
        """Test PDF processing error."""
        mock_fitz_open.side_effect = Exception("PDF error")

        with pytest.raises(Exception, match="PDF error"):
            extract_text_from_pdf(b"fake pdf content")


class TestLangExtractIntegration:
    """Test LangExtract integration."""

    @patch("llm_integration.lx.extract")
    def test_langextract_extraction_success(self, mock_lx_extract):
        """Test successful LangExtract extraction."""
        # Mock LangExtract result
        mock_result = MagicMock()
        mock_extraction = MagicMock()
        mock_extraction.extraction_text = "Sample claim"
        mock_extraction.attributes = {"confidence": 0.85}
        mock_extraction.spans = [MagicMock(start=0, end=12)]
        mock_result.extractions = [mock_extraction]
        mock_lx_extract.return_value = mock_result

        text = "This document contains a sample claim."
        result = extract_claims_with_langextract(text)

        assert len(result) == 1
        assert result[0]["text"] == "Sample claim"
        assert result[0]["confidence_score"] == 0.85
        assert "source_text" in result[0]

    @patch("llm_integration.lx.extract")
    def test_langextract_extraction_no_results(self, mock_lx_extract):
        """Test LangExtract with no extractions found."""
        mock_result = MagicMock()
        mock_result.extractions = []
        mock_lx_extract.return_value = mock_result

        text = "Document with no claims"
        result = extract_claims_with_langextract(text)

        assert result == []

    @patch("llm_integration.lx.extract")
    def test_langextract_extraction_error(self, mock_lx_extract):
        """Test LangExtract error handling."""
        mock_lx_extract.side_effect = Exception("LangExtract error")

        text = "Document text"
        result = extract_claims_with_langextract(text)
        assert result == []


class TestFallbackSearch:
    """Test regex fallback search."""

    def test_fallback_claim_search_success(self):
        """Test successful regex claim extraction."""
        text = "The product claims to reduce wrinkles by 50%."
        result = fallback_claim_search(text)

        assert len(result) == 1
        assert "reduce wrinkles by 50%" in result[0]["text"]

    def test_fallback_claim_search_no_matches(self):
        """Test no claims found."""
        text = "This is just regular text with no claims."
        result = fallback_claim_search(text)

        assert result == []


class TestDataSourceAudit:
    """Test data source language auditing."""

    @patch("llm_integration.detect")
    def test_audit_data_source_language_success(self, mock_detect):
        """Test successful language detection."""
        mock_detect.return_value = "en"
        text = "This is English text."
        request_id = "test-request-123"

        result = audit_data_source_language(text, request_id)

        assert result == "en"
        mock_detect.assert_called_once_with(text)

    @patch("llm_integration.detect")
    def test_audit_data_source_language_detection_error(self, mock_detect):
        """Test language detection error handling."""
        mock_detect.side_effect = LangDetectException(1, "Detection failed")
        text = "Short"
        request_id = "test-request-123"

        result = audit_data_source_language(text, request_id)

        assert result == "unknown"

    @patch("llm_integration.detect")
    def test_audit_data_source_language_empty_text(self, mock_detect):
        """Test language detection with empty text."""
        text = ""
        request_id = "test-request-123"

        result = audit_data_source_language(text, request_id)

        assert result == "unknown"

    @patch("llm_integration.detect")
    def test_audit_data_source_language_unexpected_error(self, mock_detect):
        """Test unexpected error in language detection."""
        mock_detect.side_effect = Exception("Unexpected error")
        text = "Sample text"
        request_id = "test-request-123"

        result = audit_data_source_language(text, request_id)

        assert result == "unknown"
