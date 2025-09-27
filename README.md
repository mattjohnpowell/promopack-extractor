# PromoPack Claim Extractor

A FastAPI-based microservice for extracting claims from PDF documents.

## Features

- Extracts key phrases (claims) from PDF documents
- RESTful API with authentication
- Docker containerized
- Asynchronous PDF download and processing

## API Specification

### Endpoint: `POST /extract-claims`

**Authentication:** Include `X-API-Key` header with your secret key.

**Request Body:**
```json
{
  "document_url": "https://example.com/path/to/document.pdf"
}
```

**Response:**
```json
{
  "claims": [
    {
      "text": "Drug X was shown to reduce Y by Z%",
      "page": 1,
      "confidence_score": 0.92
    }
  ]
}
```

## Running Locally

### With Podman/Docker

1. Build the image:
   ```bash
   podman build -t promopack-extractor .
   ```

2. Run the container:
   ```bash
   podman run -d -p 8000:8000 -e API_KEY_SECRET=your-secret-key promopack-extractor
   ```

3. Access the API documentation at `http://localhost:8000/docs`

### Environment Variables

- `API_KEY_SECRET`: Secret key for API authentication (required)
- `LANGEXTRACT_API_KEY`: API key for Google Gemini (required for claim extraction)

## Deployment

Deploy as a container on serverless platforms like Google Cloud Run or AWS Fargate.

## Development

Install dependencies:
```bash
pip install -r requirements.txt
```

Run locally:
```bash
uvicorn main:app --reload
```