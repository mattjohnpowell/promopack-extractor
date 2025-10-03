import os

import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Valid API key for testing."""
    return "test-api-key"


@pytest.fixture
def auth_headers(api_key):
    """Authorization headers for testing."""
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["API_KEY_SECRET"] = "test-api-key"
    os.environ["LANGEXTRACT_API_KEY"] = "test-langextract-key"
    os.environ["LOG_TO_FILE"] = "false"
    yield
    # Cleanup if needed


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF bytes for testing."""
    # Create a minimal valid PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"
    return pdf_content
