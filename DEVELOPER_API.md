# PromoPack Claim Extractor - Developer API Documentation

## Overview

The PromoPack Claim Extractor is a REST API service that automatically extracts key claims from PDF documents using advanced language processing. This service is designed for pharmaceutical companies to streamline the creation of reference packs for promotional materials.

## Interactive API Documentation

When the service is running, comprehensive API documentation is automatically available at:

- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation with try-it functionality
- **ReDoc**: `http://localhost:8000/redoc` - Alternative documentation view

## Quick Start

### Prerequisites

- Python 3.12+ (for local development)
- Podman or Docker (for containerized deployment)
- API keys for authentication and LLM services

### Installation & Setup

#### Option 1: Podman/Docker (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd promopack-extractor

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual API keys

# 3. Build the container image
podman build -t promopack-extractor:latest .

# 4. Run the container
podman run -d --name promopack-extractor \
  -p 8000:8000 \
  -e API_KEY_SECRET=your-api-key-here \
  -e LANGEXTRACT_API_KEY=your-langextract-key-here \
  -e DATABASE_URL=sqlite:///./dev.db \
  -e ENV=dev \
  promopack-extractor:latest

# 5. Verify the deployment
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"promopack-extractor","version":"1.0"}

# 6. Access API documentation
open http://localhost:8000/docs
```

#### Option 2: Local Development

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd promopack-extractor
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Set environment variables
# For Windows PowerShell:
$env:API_KEY_SECRET="your-dev-api-key"
$env:LANGEXTRACT_API_KEY="your-dev-langextract-key"

# For Linux/macOS:
export API_KEY_SECRET="your-dev-api-key"
export LANGEXTRACT_API_KEY="your-dev-langextract-key"

# 3. Run the service
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. Run tests (in another terminal)
pytest
```

### Environment Configuration

**Required Environment Variables:**
- `API_KEY_SECRET`: Your API authentication key
- `LANGEXTRACT_API_KEY`: Google Gemini API key for claim extraction

**Optional Environment Variables:**
- `ENV`: Environment mode (`dev` or `prod`, default: `dev`)
- `DATABASE_URL`: Database connection string (default: SQLite)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `RATE_LIMIT_REQUESTS`: API rate limit (default: 100 for dev, 10 for prod)
- `MAX_FILE_SIZE`: Maximum PDF size in bytes (default: 10MB dev, 20MB prod)

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Extract claims from a PDF (replace with real URL)
curl -X POST "http://localhost:8000/extract-claims" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"document_url": "https://example.com/sample.pdf"}'

# View all available endpoints
open http://localhost:8000/docs
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY_SECRET` | Yes | Secret key for API authentication |
| `LANGEXTRACT_API_KEY` | Yes | Google Gemini API key for claim extraction |
| `LOG_TO_FILE` | No | Set to "true" to enable file logging (default: false) |

## Authentication

All API requests require authentication using an API key. Include the key in the `Authorization` header:

```
Authorization: Bearer your-api-key-here
```

**Rate Limits:** 10 requests per minute per API key.

## API Endpoints

### POST /extract-claims

Extracts key claims from a PDF document accessible via URL.

#### Request

```http
POST /extract-claims
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "document_url": "https://example.com/path/to/document.pdf"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_url` | string (URL) | Yes | HTTPS URL to the PDF document to analyze |
| `prompt_version` | string | No | Prompt version to use: `v1_basic`, `v2_enhanced`, `v3_context_aware`. Auto-selected if not specified |
| `force_model` | string | No | Force specific LLM model: `gemini-1.5-flash`, `gemini-1.5-pro`. Auto-selected based on content if not specified |

#### Response (Success - 200)

```json
{
  "claims": [
    {
      "text": "The study showed that Drug X reduced symptoms by 50% compared to placebo.",
      "page": 3,
      "confidence_score": 0.95
    },
    {
      "text": "Patients treated with the new therapy had a 30% improvement in quality of life.",
      "page": 7,
      "confidence_score": 0.92
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `claims` | array | List of extracted claims |
| `claims[].text` | string | The exact text of the claim |
| `claims[].page` | integer | Page number where the claim appears (1-indexed) |
| `claims[].confidence_score` | float | Confidence score (0.0-1.0) of the extraction |

### GET /health

Basic health check endpoint for load balancers and monitoring systems.

#### Request

```http
GET /health
```

#### Response (Success - 200)

```json
{
  "status": "healthy",
  "service": "promopack-extractor",
  "version": "1.0"
}
```

### GET /ready

Readiness probe for container orchestration. Checks if the service can handle requests.

#### Request

```http
GET /ready
```

#### Response (Ready - 200)

```json
{
  "status": "ready",
  "service": "promopack-extractor",
  "version": "1.0"
}
```

#### Response (Not Ready - 503)

```json
{
  "status": "not ready",
  "reason": "LANGEXTRACT_API_KEY not configured"
}
```

### POST /extract-claims/async

Starts asynchronous claim extraction from a PDF document. Suitable for large documents that may take time to process.

#### Request

```http
POST /extract-claims/async
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "document_url": "https://example.com/path/to/document.pdf",
  "prompt_version": "v3_context_aware",
  "force_model": "gemini-1.5-pro"
}
```

#### Response (Accepted - 202)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "accepted",
  "message": "Processing started"
}
```

### GET /job/{job_id}

Retrieves the status and result of an asynchronous extraction job.

#### Request

```http
GET /job/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer your-api-key
```

#### Response (Processing - 200)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "created_at": "2024-01-01T12:00:00.000000Z"
}
```

#### Response (Completed - 200)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "created_at": "2024-01-01T12:00:00.000000Z",
  "completed_at": "2024-01-01T12:05:00.000000Z",
  "result": {
    "claims": [
      {
        "text": "The study showed that Drug X reduced symptoms by 50% compared to placebo.",
        "page": 3,
        "confidence_score": 0.95
      }
    ],
    "request_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

#### Response (Failed - 200)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "failed",
  "created_at": "2024-01-01T12:00:00.000000Z",
  "completed_at": "2024-01-01T12:01:00.000000Z",
  "error": "Failed to download document"
}
```

## Error Handling

All error responses follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "request_id": "unique-request-identifier",
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### Error Codes

| Code | HTTP Status | Description | Troubleshooting |
|------|-------------|-------------|----------------|
| `invalid_api_key` | 401 | Invalid or missing API key | Check your Authorization header format: `Bearer your-key` |
| `rate_limit_exceeded` | 429 | Too many requests | Wait before retrying. Limit: 10 requests/minute |
| `invalid_url` | 400 | Malformed or insecure URL | Ensure URL is valid HTTPS and not localhost/private IP |
| `download_failed` | 400 | Could not download the PDF | Check URL accessibility and file availability |
| `invalid_pdf` | 422 | File is not a valid PDF | Verify the document is a properly formatted PDF |
| `empty_pdf` | 422 | PDF has no pages | Check that the PDF contains content |
| `too_many_pages` | 400 | PDF exceeds 1000 pages | Split large documents or contact support |
| `file_too_large` | 400 | PDF exceeds 20MB limit | Compress the PDF or use a smaller document |
| `pdf_read_error` | 422 | Error reading PDF content | Check PDF is not corrupted or password-protected |
| `internal_server_error` | 500 | Unexpected server error | Retry the request. Contact support if persistent |

## Code Examples

### Python

```python
import requests

# Configuration
API_URL = "https://your-api-endpoint.com"
API_KEY = "your-api-key"

# Extract claims from a PDF
def extract_claims(pdf_url):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "document_url": pdf_url
    }

    response = requests.post(f"{API_URL}/extract-claims", json=data, headers=headers)
    response.raise_for_status()

    return response.json()

# Usage
result = extract_claims("https://example.com/research-paper.pdf")
for claim in result["claims"]:
    print(f"Page {claim['page']}: {claim['text']} (confidence: {claim['confidence_score']})")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'https://your-api-endpoint.com';
const API_KEY = 'your-api-key';

async function extractClaims(pdfUrl) {
    try {
        const response = await axios.post(`${API_URL}/extract-claims`, {
            document_url: pdfUrl
        }, {
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        return response.data;
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
        throw error;
    }
}

// Usage
extractClaims('https://example.com/research-paper.pdf')
    .then(result => {
        result.claims.forEach(claim => {
            console.log(`Page ${claim.page}: ${claim.text} (confidence: ${claim.confidence_score})`);
        });
    });
```

### cURL

```bash
# Extract claims
curl -X POST "https://your-api-endpoint.com/extract-claims" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"document_url": "https://example.com/research-paper.pdf"}'

# Health check
curl "https://your-api-endpoint.com/health"

# Readiness check
curl "https://your-api-endpoint.com/ready"
```

### PHP

```php
<?php

$apiUrl = 'https://your-api-endpoint.com';
$apiKey = 'your-api-key';

function extractClaims($pdfUrl) {
    $ch = curl_init();

    curl_setopt($ch, CURLOPT_URL, $apiUrl . '/extract-claims');
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'document_url' => $pdfUrl
    ]));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . $apiKey,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    curl_close($ch);

    if ($httpCode !== 200) {
        throw new Exception("API request failed with status $httpCode: $response");
    }

    return json_decode($response, true);
}

// Usage
try {
    $result = extractClaims('https://example.com/research-paper.pdf');
    foreach ($result['claims'] as $claim) {
        echo "Page {$claim['page']}: {$claim['text']} (confidence: {$claim['confidence_score']})\n";
    }
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
```

## Best Practices

### PDF Preparation

- Ensure PDFs are text-based (not image-only)
- Remove password protection
- Keep file size under 20MB
- Use standard PDF format (avoid unusual encodings)

### Error Handling

- Always check HTTP status codes
- Implement exponential backoff for retries
- Log request IDs for debugging
- Handle rate limiting gracefully

### Performance

- Process documents during off-peak hours
- Cache results for repeated URLs
- Monitor confidence scores for quality control

## Support

For technical support or questions:

- Check the troubleshooting section above
- Review the error codes and their solutions
- Contact support@promopack-extractor.com with your request ID

## Changelog

### Version 1.0
- Initial release
- Claim extraction from PDF URLs
- REST API with authentication
- Health and readiness endpoints
- Rate limiting and comprehensive logging</content>
<parameter name="filePath">c:\Users\mattj\Development\promopack-extractor\DEVELOPER_API.md