from validation import validate_pdf_content, validate_url


class TestValidation:
    """Test input validation functions."""

    def test_validate_url_valid(self):
        """Test valid URLs are accepted."""
        assert validate_url("https://example.com/document.pdf") is True
        assert validate_url("http://example.com/document.pdf") is True

    def test_validate_url_invalid(self):
        """Test invalid URLs are rejected."""
        assert validate_url("ftp://example.com/document.pdf") is False
        assert validate_url("javascript:alert('xss')") is False
        assert validate_url("localhost/document.pdf") is False
        assert validate_url("127.0.0.1/document.pdf") is False
        assert validate_url("192.168.1.1/document.pdf") is False
        assert validate_url("10.0.0.1/document.pdf") is False
        assert validate_url("172.16.0.1/document.pdf") is False

    def test_validate_url_malformed(self):
        """Test malformed URLs are rejected."""
        assert validate_url("not-a-url") is False
        assert validate_url("") is False
        assert validate_url("http://") is False

    def test_validate_pdf_content_valid(self):
        """Test valid PDF content is accepted."""
        pdf_header = b"%PDF-1.4\n"
        assert validate_pdf_content(pdf_header) is True

    def test_validate_pdf_content_invalid(self):
        """Test invalid content is rejected."""
        assert validate_pdf_content(b"not pdf content") is False
        assert validate_pdf_content(b"") is False
        assert validate_pdf_content(b"short") is False
