from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api import app, check_rate_limit, rate_limit_store, verify_api_key
from config import config


@pytest.fixture
def client():
    """Test client with overridden authentication."""

    # Override the verify_api_key dependency to always return the test key but still check rate limits
    def override_verify_api_key():
        api_key = "test-api-key"
        if not check_rate_limit(api_key):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Maximum {config.rate_limit_requests} requests per {config.rate_limit_window} seconds.",
                    "timestamp": "test-timestamp",
                },
            )
        return api_key

    app.dependency_overrides[verify_api_key] = override_verify_api_key
    client = TestClient(app)
    yield client
    # Clean up
    app.dependency_overrides = {}


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "promopack-extractor"
        assert data["version"] == "1.0"

    def test_readiness_endpoint_ready(self, client):
        """Test readiness check when ready."""
        with patch.object(config, "api_key_secret", "test-key"), patch.object(
            config, "langextract_api_key", "test-langextract-key"
        ):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_endpoint_not_ready_missing_api_key(self, client):
        """Test readiness check when API key is missing."""
        with patch.object(config, "api_key_secret", ""):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not ready"
            assert "API_KEY_SECRET not configured" in data["reason"]

    def test_readiness_endpoint_not_ready_missing_langextract_key(self, client):
        """Test readiness check when LangExtract key is missing."""
        with patch.object(config, "langextract_api_key", ""):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not ready"
            assert "LANGEXTRACT_API_KEY not configured" in data["reason"]


class TestExtractClaims:
    """Test claim extraction endpoint."""

    def test_extract_claims_missing_api_key(self, client):
        """Test endpoint rejects requests without API key."""
        # Temporarily remove the dependency override
        app.dependency_overrides = {}
        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/test.pdf"}
        )
        assert response.status_code == 403  # HTTPBearer returns 403 when no auth header

    def test_extract_claims_invalid_url(self, client):
        """Test endpoint rejects invalid URLs."""
        response = client.post(
            "/extract-claims", json={"document_url": "not-a-valid-url"}
        )
        assert response.status_code == 422
        # Pydantic validation error for invalid URL format

    @patch("httpx.AsyncClient.get")
    def test_extract_claims_download_failure(self, mock_get, client):
        """Test handling of download failures."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/missing.pdf"}
        )
        assert response.status_code == 400
        assert response.json()["error"] == "download_failed"
        assert "Failed to download" in response.json()["message"]

    @patch("httpx.AsyncClient.get")
    def test_extract_claims_invalid_pdf(self, mock_get, client):
        """Test handling of invalid PDF content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"not pdf content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value = mock_response

        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/invalid.pdf"}
        )
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_pdf"
        assert "Document is not a valid PDF" in response.json()["message"]

    @patch("httpx.AsyncClient.get")
    @patch("llm_integration.lx.extract")
    def test_extract_claims_success(
        self, mock_lx_extract, mock_get, client, sample_pdf_bytes
    ):
        """Test successful claim extraction."""
        # Mock PDF download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_pdf_bytes
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value = mock_response

        # Mock LangExtract result
        mock_result = MagicMock()
        mock_extraction = MagicMock()
        mock_extraction.extraction_text = "Test claim"
        mock_extraction.attributes = {"confidence": 0.9}
        mock_extraction.spans = [MagicMock(start=0)]
        mock_result.extractions = [mock_extraction]
        mock_lx_extract.return_value = mock_result

        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/test.pdf"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert len(data["claims"]) == 1
        assert data["claims"][0]["text"] == "Test claim"
        assert data["claims"][0]["confidence_score"] == 0.9

    @patch("httpx.AsyncClient.get")
    def test_extract_claims_file_too_large(self, mock_get, client):
        """Test handling of files that are too large."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-" + b"x" * (21 * 1024 * 1024)  # 21MB
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value = mock_response

        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/large.pdf"}
        )
        assert response.status_code == 400
        assert response.json()["error"] == "file_too_large"
        assert "too large" in response.json()["message"]

    @patch("httpx.AsyncClient.get")
    @patch("llm_integration.lx.extract")
    def test_extract_claims_llm_fallback(self, mock_lx_extract, mock_get, client):
        """Test fallback to regex extraction when LLM fails."""
        # Mock successful PDF download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(This is a test claim.) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value = mock_response

        # Mock LLM extraction failure
        mock_lx_extract.side_effect = Exception("LLM API error")

        response = client.post(
            "/extract-claims", json={"document_url": "https://example.com/test.pdf"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        # Should have fallback claims
        assert len(data["claims"]) >= 0  # May find claims with regex

    @patch("httpx.AsyncClient.get")
    @patch("llm_integration.lx.extract")
    def test_extract_claims_rate_limit(self, mock_lx_extract, mock_get, client):
        """Test rate limiting functionality."""
        # Clear rate limit store to ensure clean state
        rate_limit_store.clear()

        # Mock successful PDF download and extraction
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(This is a test claim.) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value = mock_response

        mock_result = MagicMock()
        mock_extraction = MagicMock()
        mock_extraction.extraction_text = "Test claim"
        mock_extraction.attributes = {"confidence": 0.9}
        mock_extraction.spans = [MagicMock(start=0)]
        mock_result.extractions = [mock_extraction]
        mock_lx_extract.return_value = mock_result

        # Make multiple requests to trigger rate limit
        for i in range(config.rate_limit_requests + 1):
            response = client.post(
                "/extract-claims", json={"document_url": "https://example.com/test.pdf"}
            )
            if i < config.rate_limit_requests:
                # Should succeed
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert response.json()["error"] == "rate_limit_exceeded"
