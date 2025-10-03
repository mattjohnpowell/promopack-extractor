# Copilot Instructions for Promo Pack Extractor

This repository contains a Python FastAPI application that extracts promotional pack information from PDF documents using Large Language Models (LLMs). The service provides REST API endpoints for PDF processing, health checks, and monitoring.

## Code Style and Standards

- **Python Version**: Use Python 3.12 or later
- **Code Style**: Follow PEP 8 with Black formatter
- **Type Hints**: Use type hints (PEP 484) for all function parameters and return values
- **Imports**: Organize imports with standard library first, then third-party, then local modules
- **Naming**: Use descriptive names; functions and variables in snake_case, classes in PascalCase
- **Docstrings**: Write comprehensive docstrings for all public functions and classes using Google style

## Architecture Overview

**Core Components:**
- `api.py`: FastAPI app with endpoints, middleware, rate limiting, and caching
- `llm_integration.py`: LLM calls with circuit breakers, retries, and model fallback
- `pdf_processing.py`: PDF text extraction and validation
- `config/`: Dynamic environment-specific configuration loading
- `models.py`: SQLAlchemy models for job tracking and audit logs
- `database.py`: Async database session management
- `prompt_engineering.py`: Model selection and prompt versioning
- `cost_tracking.py`: LLM usage monitoring and cost calculation

**Data Flow:** PDF URL → Download → Text Extraction → LLM Processing → Claim Extraction → Response Caching

## Critical Developer Workflows

**Environment Setup:**
```bash
cp .env.example .env  # Configure API keys
make setup-dev        # Install dependencies
```

**Local Development:**
```bash
make run              # Start with auto-reload (uvicorn main:app --reload)
# Or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Testing:**
```bash
make test             # Run all tests
make test-cov         # Run with coverage report
pytest tests/test_api.py  # Run specific test file
```

**Container Development:**
```bash
make podman-build     # Build container image
make podman-run       # Run container (requires .env file)
make podman-logs      # View container logs
make health-check     # Test health endpoint
```

**Code Quality:**
```bash
make lint             # Check formatting and linting
make format           # Auto-format code (black + isort)
make security         # Run security scans
```

## Project-Specific Patterns

**Configuration Management:**
- Environment configs loaded dynamically from `config/{env}.py`
- Use `config.py` module for all settings access
- Environment variables override config file defaults
- Example: `config.rate_limit_requests`, `config.database_url`

**Error Handling:**
- Custom exceptions in `validation.py` and `api.py`
- Consistent HTTP error responses with error codes
- Never expose internal errors - use generic messages
- Log full details with request correlation IDs

**Rate Limiting & Caching:**
- In-memory rate limiting per API key (upgrade to Redis for prod)
- TTL-based response caching (1 hour default)
- Job store for async processing (24 hour TTL)

**LLM Integration:**
- Circuit breaker pattern with configurable failure thresholds
- Model fallback: Gemini Flash → Gemini Pro based on complexity
- Cost tracking with token counting and usage analytics
- Retry logic with exponential backoff

**Database Patterns:**
- Async SQLAlchemy with `aiosqlite` for SQLite, `asyncpg` for PostgreSQL
- Auto-create tables on startup via `init_db()`
- Use `get_db()` dependency for session management
- Models: `Job`, `AuditLog`, `UsageStats`

**Async Processing:**
- Background tasks for large PDF processing
- Job tracking with status updates
- TTL-based job storage (24 hours)

**Logging Conventions:**
- Structured JSON logging with `extra` parameter
- Request correlation IDs in all log entries
- Log levels: DEBUG (dev), INFO (prod)
- Include `request_id`, `endpoint`, `processing_time` in logs

## Integration Points

**External Dependencies:**
- **LLM Service**: Google Gemini via `langextract` library
- **Database**: SQLAlchemy async (SQLite for dev, PostgreSQL for prod)
- **Caching**: Redis support planned (currently in-memory)
- **Monitoring**: Prometheus metrics exposed
- **Container**: Podman/Docker with health checks

**API Authentication:**
- API key authentication via `X-API-Key` header
- Rate limiting applied per API key
- Keys stored in environment variables

## Testing Patterns

**Test Structure:**
- Unit tests in `tests/` directory
- Mock external dependencies (LLM APIs, HTTP calls)
- Use `pytest` with `conftest.py` for fixtures
- Test coverage target: >80%

**Common Test Patterns:**
```python
# Mock LLM responses
@patch('llm_integration.extract_claims_with_fallback')
async def test_api_endpoint(mock_llm, client):
    mock_llm.return_value = [...]
    
# Test database operations
async def test_database_operation(db_session):
    # Use async session fixture
```

## Development Best Practices

**When Adding Features:**
1. Update `production-readiness-todos.md` with new tasks
2. Add comprehensive tests before implementation
3. Include proper logging and error handling
4. Update API documentation if endpoints change
5. Test both success and failure scenarios

**Code Review Checklist:**
- Type hints on all public functions
- Comprehensive docstrings
- Proper error handling with custom exceptions
- Logging for debugging and monitoring
- Unit tests with mocked dependencies
- Security considerations (input validation, rate limiting)

**Performance Considerations:**
- Cache LLM responses for identical content
- Use async/await for all I/O operations
- Implement circuit breakers for external services
- Monitor memory usage for large PDFs
- Rate limiting to prevent abuse

## Key Files to Reference

**Architecture Understanding:**
- `api.py`: Main API endpoints and middleware
- `main.py`: Application entry point
- `config/__init__.py`: Configuration loading system

**Implementation Examples:**
- `llm_integration.py`: Circuit breaker and retry patterns
- `prompt_engineering.py`: Model selection and prompt management
- `database.py`: Async database session management

**Testing Examples:**
- `tests/test_api.py`: API endpoint testing
- `tests/conftest.py`: Test fixtures and setup

Always refer to the `production-readiness-todos.md` file for current development priorities and completed features.
