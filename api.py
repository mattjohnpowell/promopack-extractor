"""FastAPI application and routes."""

import hashlib
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from cachetools import TTLCache
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Request,
                     Response)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Histogram,
                               generate_latest)
from pydantic import BaseModel, HttpUrl

from claim_validation import claim_validator, ClaimType
from config import config
from cost_tracking import cost_tracker
from llm_integration import (audit_data_source_language,
                             extract_claims_with_fallback)
from logging_config import logger
from pdf_processing import extract_pages_from_pdf
from prompt_engineering import ModelType, PromptVersion
from security import scan_and_filter_content
from validation import validate_pdf_content, validate_url

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)
CLAIM_EXTRACTION_COUNT = Counter(
    "claim_extractions_total", "Total claim extractions", ["method"]
)
PDF_PROCESSING_DURATION = Histogram(
    "pdf_processing_duration_seconds", "PDF processing duration"
)
LLM_REQUEST_COUNT = Counter(
    "llm_requests_total", "Total LLM requests", ["model", "status"]
)


# Rate limiting storage (in production, use Redis)
rate_limit_store = defaultdict(list)

# Response caching (TTL: 1 hour, max 100 entries)
response_cache = TTLCache(maxsize=100, ttl=3600)

# Job storage for async processing (TTL: 24 hours)
job_store = TTLCache(maxsize=1000, ttl=86400)


def check_rate_limit(api_key: str) -> bool:
    """Check if API key is within rate limits. Returns True if allowed, False if rate limited."""
    current_time = time.time()

    # Get request timestamps for this API key
    timestamps = rate_limit_store[api_key]

    # Remove timestamps older than the window
    timestamps[:] = [
        t for t in timestamps if current_time - t < config.rate_limit_window
    ]

    # Check if under limit
    if len(timestamps) < config.rate_limit_requests:
        timestamps.append(current_time)
        return True
    else:
        return False


# FastAPI app
app = FastAPI(
    title=config.service_name,
    version=config.version,
    description="REST API service that automatically extracts key claims from PDF documents using advanced language processing. Designed for pharmaceutical companies to streamline the creation of reference packs for promotional materials.",
    contact={
        "name": "PromoPack Extractor Support",
        "url": "https://github.com/your-org/promopack-extractor",
    },
    license_info={
        "name": "MIT",
    },
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Log incoming request
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "endpoint": f"{request.method} {request.url.path}",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    start_time = datetime.utcnow()

    try:
        response = await call_next(request)

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Log successful response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "endpoint": f"{request.method} {request.url.path}",
                "status_code": response.status_code,
                "processing_time": processing_time,
            },
        )

        # Update metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method, endpoint=request.url.path
        ).observe(processing_time)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        # Calculate processing time for errors
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Log error
        logger.error(
            "Request failed",
            exc_info=True,
            extra={
                "request_id": request_id,
                "endpoint": f"{request.method} {request.url.path}",
                "processing_time": processing_time,
                "error_type": type(e).__name__,
            },
        )

        # Update metrics for failed requests
        REQUEST_COUNT.labels(
            method=request.method, endpoint=request.url.path, status="500"
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method, endpoint=request.url.path
        ).observe(processing_time)

        raise


# Models
class ExtractClaimsRequest(BaseModel):
    document_url: HttpUrl
    prompt_version: Optional[str] = (
        None  # "v1_basic", "v2_enhanced", "v3_context_aware", "v4_regulatory"
    )
    force_model: Optional[str] = None  # "gemini-2.5-flash", "gemini-2.5-pro"


class ClaimContext(BaseModel):
    """Context surrounding a claim for better understanding."""

    preceding: Optional[str] = None  # Text before the claim
    following: Optional[str] = None  # Text after the claim


class Claim(BaseModel):
    """Enhanced claim model with regulatory validation metadata."""

    text: str
    page: int
    confidence: float  # Renamed from confidence_score for consistency

    # Claim classification
    suggested_type: Optional[str] = None  # EFFICACY, SAFETY, INDICATION, etc.
    reasoning: Optional[str] = None  # Explanation of classification

    # Context and location
    context: Optional[ClaimContext] = None
    section: Optional[str] = None  # Document section name

    # Regulatory flags
    is_comparative: bool = False  # Contains comparative language
    contains_statistics: bool = False  # Has statistical evidence
    citation_present: bool = False  # Has references

    # Quality warnings
    warnings: Optional[List[str]] = None  # Validation warnings if any


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""

    total_claims_extracted: int
    high_confidence_claims: int  # >= 0.8
    medium_confidence_claims: int  # >= 0.5 and < 0.8
    low_confidence_claims: int  # < 0.5
    processing_time_ms: int
    model_version: str
    prompt_version: str
    sections_analyzed: Optional[List[str]] = None


class ExtractClaimsResponse(BaseModel):
    claims: List[Claim]
    metadata: Optional[ExtractionMetadata] = None
    request_id: Optional[str] = None
    security_info: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[ExtractClaimsResponse] = None
    error: Optional[str] = None


class AsyncExtractClaimsRequest(BaseModel):
    document_url: HttpUrl
    prompt_version: Optional[str] = (
        None  # "v1_basic", "v2_enhanced", "v3_context_aware", "v4_regulatory"
    )
    force_model: Optional[str] = None  # "gemini-2.5-flash", "gemini-2.5-pro"


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str
    timestamp: str


# Helper functions
def validate_and_enhance_claim(
    claim_text: str, confidence: float, llm_attributes: Dict[str, Any], request_id: str
) -> Optional[Dict[str, Any]]:
    """
    Validate and enhance a claim with regulatory metadata.

    Args:
        claim_text: The extracted claim text
        confidence: LLM confidence score
        llm_attributes: Attributes from LLM extraction
        request_id: Request ID for logging

    Returns:
        Enhanced claim dict if valid, None if rejected
    """
    # Validate using regulatory rules (pattern-based, no spacy required)
    validation_result = claim_validator.validate_claim(claim_text, request_id)

    # Reject invalid claims
    if not validation_result.is_valid:
        logger.info(
            "Claim rejected by validator",
            extra={
                "request_id": request_id,
                "claim_preview": claim_text[:100],
                "reasoning": validation_result.reasoning,
                "warnings": [w.value for w in validation_result.warnings],
            },
        )
        return None

    # Adjust confidence based on validation
    adjusted_confidence = max(
        0.0, min(1.0, confidence + validation_result.confidence_adjustment)
    )

    # Classify claim type
    claim_type = claim_validator.classify_claim_type(claim_text)
    suggested_type = claim_type.value if claim_type else llm_attributes.get("claim_type")

    # Check for comparative and statistical evidence
    is_comparative = claim_validator.is_comparative_claim(claim_text)
    has_statistics = claim_validator.has_statistical_evidence(claim_text)

    # Convert warnings to strings
    warnings_list = (
        [w.value for w in validation_result.warnings] if validation_result.warnings else None
    )

    # Return enhanced claim
    return {
        "text": claim_text,
        "confidence": adjusted_confidence,
        "suggested_type": suggested_type,
        "reasoning": validation_result.reasoning,
        "is_comparative": is_comparative,
        "contains_statistics": has_statistics,
        "warnings": warnings_list if warnings_list else None,
    }


# Security
security = HTTPBearer()


# Authentication dependency
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    if api_key != config.api_key_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check rate limit
    if not check_rate_limit(api_key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Maximum {config.rate_limit_requests} requests per {config.rate_limit_window} seconds.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

    return api_key


async def process_pdf_extraction(
    job_id: str,
    pdf_url: str,
    api_key: str,
    prompt_version: Optional[str] = None,
    force_model: Optional[str] = None,
):
    """Background task to process PDF extraction."""
    try:
        # Update job status to processing
        job = job_store[job_id]
        job.status = "processing"
        job_store[job_id] = job

        request_id = job_id  # Use job_id as request_id for logging

        logger.info(
            "Starting async PDF extraction",
            extra={"request_id": request_id, "job_id": job_id, "pdf_url": pdf_url},
        )

        # Validate URL
        if not validate_url(pdf_url):
            raise HTTPException(
                status_code=400, detail="Invalid URL format or security violation"
            )

        # Download PDF
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(config.request_timeout, connect=10.0)
        ) as client:
            response = await client.get(pdf_url)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to download document"
                )

            pdf_bytes = response.content
            file_size = len(pdf_bytes)

            # Validate PDF
            if not validate_pdf_content(pdf_bytes):
                raise HTTPException(
                    status_code=422, detail="Document is not a valid PDF"
                )

            if file_size > config.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document too large (max {config.max_file_size} bytes)",
                )

            # Check cache
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
            cache_key = f"{pdf_url}:{pdf_hash}"

            if cache_key in response_cache:
                logger.info(
                    "Using cached result for async job", extra={"job_id": job_id}
                )
                cached_response = response_cache[cache_key]
                result = ExtractClaimsResponse(
                    claims=cached_response.claims, request_id=request_id
                )
            else:
                # Process PDF
                full_text, pages_text = extract_pages_from_pdf(pdf_bytes, request_id)
                detected_language = audit_data_source_language(full_text, request_id)

                # Log language audit results
                logger.info(
                    "Data source audit completed",
                    extra={
                        "request_id": request_id,
                        "detected_language": detected_language,
                        "text_length": len(full_text),
                    },
                )

                # Prepare text with page markers
                page_texts = []
                char_offset = 0
                page_offsets = []

                for page_num, text in pages_text:
                    page_offsets.append(
                        (page_num, char_offset, char_offset + len(text))
                    )
                    page_texts.append(text)
                    char_offset += len(text) + 1

                full_text = "\n".join(page_texts)

                # Security scanning and content filtering
                processed_text, security_result, compliance_result = (
                    scan_and_filter_content(full_text, request_id)
                )

                # Validate processed text is not empty
                if not processed_text or not processed_text.strip():
                    logger.error(
                        "Processed text is empty after security filtering",
                        extra={
                            "request_id": request_id,
                            "original_text_length": len(full_text),
                        },
                    )
                    raise HTTPException(
                        status_code=422,
                        detail="Document contains no extractable text after security filtering",
                    )

                # Parse prompt engineering parameters
                pv = None
                fm = None
                if prompt_version:
                    try:
                        pv = PromptVersion(prompt_version)
                    except ValueError:
                        logger.warning(
                            "Invalid prompt version for async job",
                            extra={"job_id": job_id, "prompt_version": prompt_version},
                        )
                if force_model:
                    try:
                        fm = ModelType(force_model)
                    except ValueError:
                        logger.warning(
                            "Invalid model for async job",
                            extra={"job_id": job_id, "force_model": force_model},
                        )

                extractions, extraction_method = extract_claims_with_fallback(
                    processed_text, request_id, pv, fm
                )

                # Process extractions with validation
                claims = []
                rejected_count = 0
                
                for extraction in extractions:
                    claim_text = extraction.extraction_text
                    confidence = extraction.attributes.get("confidence", 0.9)
                    llm_attributes = extraction.attributes or {}

                    # Validate and enhance claim
                    enhanced_claim_data = validate_and_enhance_claim(
                        claim_text, confidence, llm_attributes, request_id
                    )

                    # Skip invalid claims
                    if enhanced_claim_data is None:
                        rejected_count += 1
                        continue

                    # Find page number
                    page_num = None
                    if hasattr(extraction, "spans") and extraction.spans:
                        span_start = extraction.spans[0].start
                        for p_num, start_offset, end_offset in page_offsets:
                            if start_offset <= span_start < end_offset:
                                page_num = p_num
                                break

                    if page_num is None:
                        for p_num, p_text in pages_text:
                            if claim_text in p_text:
                                page_num = p_num
                                break

                    if page_num:
                        claims.append(
                            Claim(
                                page=page_num,
                                **enhanced_claim_data
                            )
                        )

                logger.info(
                    "Claim validation completed",
                    extra={
                        "request_id": request_id,
                        "total_extracted": len(extractions),
                        "valid_claims": len(claims),
                        "rejected_claims": rejected_count,
                    },
                )

                result = ExtractClaimsResponse(
                    claims=claims,
                    request_id=request_id,
                    security_info={
                        "risk_level": security_result.risk_level,
                        "has_sensitive_content": security_result.has_sensitive_content,
                        "detected_entities_count": len(
                            security_result.detected_entities
                        ),
                        "compliance_warnings": compliance_result["issues"],
                        "compliance_severity": compliance_result["severity"],
                    },
                )

                # Cache the result
                response_cache[cache_key] = result

        # Update job as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow().isoformat() + "Z"
        job.result = result
        job_store[job_id] = job

        logger.info(
            "Async PDF extraction completed",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "claims_count": len(result.claims),
            },
        )

    except Exception as e:
        # Update job as failed
        job = job_store[job_id]
        job.status = "failed"
        job.completed_at = datetime.utcnow().isoformat() + "Z"
        job.error = str(e)
        job_store[job_id] = job

        logger.error(
            "Async PDF extraction failed",
            exc_info=True,
            extra={"request_id": job_id, "job_id": job_id, "error": str(e)},
        )


@app.post(
    "/extract-claims", response_model=ExtractClaimsResponse, tags=["Claim Extraction"]
)
async def extract_claims(
    request: ExtractClaimsRequest, req: Request, api_key: str = Depends(verify_api_key)
):
    request_id = req.state.request_id

    logger.info(
        "Starting claim extraction",
        extra={
            "request_id": request_id,
            "pdf_url": str(request.document_url),
            "endpoint": "/extract-claims",
        },
    )

    try:
        start_time = time.time()

        # Validate URL
        if not validate_url(str(request.document_url)):
            logger.warning(
                "Invalid URL provided",
                extra={"request_id": request_id, "pdf_url": str(request.document_url)},
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_url",
                    "message": "Invalid URL format or security violation",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

        # Download PDF
        logger.info(
            "Downloading PDF",
            extra={"request_id": request_id, "pdf_url": str(request.document_url)},
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(config.request_timeout, connect=10.0)
        ) as client:
            response = await client.get(str(request.document_url))
            if response.status_code != 200:
                logger.warning(
                    "PDF download failed",
                    extra={
                        "request_id": request_id,
                        "pdf_url": str(request.document_url),
                        "status_code": response.status_code,
                    },
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "download_failed",
                        "message": "Failed to download document",
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                )

            pdf_bytes = response.content
            file_size = len(pdf_bytes)

            # Validate content type from response headers
            content_type = response.headers.get("content-type", "").lower()
            if not validate_pdf_content(pdf_bytes):
                logger.warning(
                    "Invalid PDF content",
                    extra={
                        "request_id": request_id,
                        "content_type": content_type,
                        "pdf_url": str(request.document_url),
                    },
                )
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_pdf",
                        "message": "Document is not a valid PDF",
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                )

            logger.info(
                "PDF downloaded successfully",
                extra={
                    "request_id": request_id,
                    "file_size": file_size,
                    "content_type": content_type,
                    "pdf_url": str(request.document_url),
                },
            )

            if file_size > config.max_file_size:
                logger.warning(
                    "PDF file too large",
                    extra={
                        "request_id": request_id,
                        "file_size": file_size,
                        "pdf_url": str(request.document_url),
                    },
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "file_too_large",
                        "message": f"Document too large (max {config.max_file_size} bytes)",
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                )

            # Check cache using PDF content hash
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
            cache_key = f"{str(request.document_url)}:{pdf_hash}"

            if cache_key in response_cache:
                logger.info(
                    "Returning cached response",
                    extra={
                        "request_id": request_id,
                        "cache_key": cache_key,
                        "pdf_url": str(request.document_url),
                    },
                )
                cached_response = response_cache[cache_key]
                # Return new response with current request ID
                return ExtractClaimsResponse(
                    claims=cached_response.claims, request_id=request_id
                )

        # Extract text from PDF
        logger.info(
            "Extracting text from PDF",
            extra={"request_id": request_id, "file_size": file_size},
        )

        full_text, pages_text = extract_pages_from_pdf(pdf_bytes, request_id)

        pdf_processing_time = time.time() - start_time
        PDF_PROCESSING_DURATION.observe(pdf_processing_time)

        # Audit data source language
        detected_language = audit_data_source_language(full_text, request_id)

        # Log language audit results
        logger.info(
            "Data source audit completed",
            extra={
                "request_id": request_id,
                "detected_language": detected_language,
                "text_length": len(full_text),
            },
        )

        # Prepare text with page markers for source grounding
        page_texts = []
        char_offset = 0
        page_offsets = []

        for page_num, text in pages_text:
            page_offsets.append((page_num, char_offset, char_offset + len(text)))
            page_texts.append(text)
            char_offset += len(text) + 1  # +1 for newline

        full_text = "\n".join(page_texts)

        # Security scanning and content filtering
        logger.info(
            "Performing security scan on extracted text",
            extra={"request_id": request_id},
        )

        processed_text, security_result, compliance_result = scan_and_filter_content(
            full_text, request_id
        )

        # Validate processed text is not empty
        if not processed_text or not processed_text.strip():
            logger.error(
                "Processed text is empty after security filtering",
                extra={
                    "request_id": request_id,
                    "original_text_length": len(full_text),
                },
            )
            raise HTTPException(
                status_code=422,
                detail="Document contains no extractable text after security filtering",
            )

        # Log security scan results
        if security_result.has_sensitive_content:
            logger.warning(
                "Sensitive content detected and redacted",
                extra={
                    "request_id": request_id,
                    "risk_level": security_result.risk_level,
                    "detected_entities": len(security_result.detected_entities),
                    "compliance_warnings": len(security_result.compliance_warnings),
                },
            )

        if not compliance_result["compliant"]:
            logger.warning(
                "Medical compliance issues detected",
                extra={
                    "request_id": request_id,
                    "compliance_issues": len(compliance_result["issues"]),
                    "severity": compliance_result["severity"],
                },
            )

        # Extract claims
        # Parse prompt engineering parameters
        prompt_version = None
        force_model = None

        if request.prompt_version:
            try:
                prompt_version = PromptVersion(request.prompt_version)
            except ValueError:
                logger.warning(
                    "Invalid prompt version specified",
                    extra={
                        "request_id": request_id,
                        "prompt_version": request.prompt_version,
                    },
                )

        if request.force_model:
            try:
                force_model = ModelType(request.force_model)
            except ValueError:
                logger.warning(
                    "Invalid model specified",
                    extra={
                        "request_id": request_id,
                        "force_model": request.force_model,
                    },
                )

        extractions, extraction_method = extract_claims_with_fallback(
            processed_text, request_id, prompt_version, force_model
        )

        # Process extractions with validation
        claims = []
        rejected_count = 0
        
        for extraction in extractions:
            claim_text = extraction.extraction_text
            confidence = extraction.attributes.get("confidence", 0.9)
            llm_attributes = extraction.attributes or {}

            # Validate and enhance claim
            enhanced_claim_data = validate_and_enhance_claim(
                claim_text, confidence, llm_attributes, request_id
            )

            # Skip invalid claims
            if enhanced_claim_data is None:
                rejected_count += 1
                continue

            # Log extraction details for debugging
            logger.debug(
                "Processing extraction",
                extra={
                    "request_id": request_id,
                    "claim_text": claim_text[:100],  # Truncate for logging
                    "has_spans": hasattr(extraction, "spans"),
                    "extraction_attrs": (
                        list(extraction.attributes.keys())
                        if hasattr(extraction, "attributes")
                        else []
                    ),
                },
            )

            # Use LangExtract's source grounding to find the page
            page_num = None
            if hasattr(extraction, "spans") and extraction.spans:
                # Use the first span to determine page
                span_start = extraction.spans[0].start
                for p_num, start_offset, end_offset in page_offsets:
                    if start_offset <= span_start < end_offset:
                        page_num = p_num
                        break
                logger.debug(
                    "Found page via spans",
                    extra={
                        "request_id": request_id,
                        "span_start": span_start,
                        "page_num": page_num,
                    },
                )

            # Fallback to text search if spans not available or didn't find page
            if page_num is None:
                for p_num, p_text in pages_text:
                    if claim_text in p_text:
                        page_num = p_num
                        break
                logger.debug(
                    "Found page via text search fallback",
                    extra={"request_id": request_id, "page_num": page_num},
                )

            if page_num:
                claims.append(
                    Claim(
                        page=page_num,
                        **enhanced_claim_data
                    )
                )
            else:
                logger.warning(
                    "Could not determine page for claim",
                    extra={"request_id": request_id, "claim_text": claim_text[:100]},
                )

        logger.info(
            "Claim extraction and validation completed successfully",
            extra={
                "request_id": request_id,
                "total_extracted": len(extractions),
                "valid_claims": len(claims),
                "rejected_claims": rejected_count,
                "extraction_method": extraction_method,
                "pdf_url": str(request.document_url),
                "detected_language": detected_language,
            },
        )

        # Update metrics
        CLAIM_EXTRACTION_COUNT.labels(method=extraction_method).inc()

        response = ExtractClaimsResponse(
            claims=claims,
            request_id=request_id,
            security_info={
                "risk_level": security_result.risk_level,
                "has_sensitive_content": security_result.has_sensitive_content,
                "detected_entities_count": len(security_result.detected_entities),
                "compliance_warnings": compliance_result["issues"],
                "compliance_severity": compliance_result["severity"],
            },
        )

        # Cache the response
        response_cache[cache_key] = response
        logger.info(
            "Response cached",
            extra={
                "request_id": request_id,
                "cache_key": cache_key,
                "claims_count": len(claims),
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during claim extraction",
            exc_info=True,
            extra={
                "request_id": request_id,
                "pdf_url": str(request.document_url),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred during claim extraction",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )


@app.post(
    "/extract-claims/async", response_model=Dict[str, str], tags=["Claim Extraction"]
)
async def extract_claims_async(
    request: AsyncExtractClaimsRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    api_key: str = Depends(verify_api_key),
):
    """Start asynchronous claim extraction from a PDF document."""
    request_id = req.state.request_id

    logger.info(
        "Starting async claim extraction request",
        extra={"request_id": request_id, "pdf_url": str(request.document_url)},
    )

    # Check rate limit
    if not check_rate_limit(api_key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Maximum {config.rate_limit_requests} requests per {config.rate_limit_window} seconds.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

    # Create job
    job_id = str(uuid.uuid4())
    job = JobStatus(
        job_id=job_id, status="pending", created_at=datetime.utcnow().isoformat() + "Z"
    )
    job_store[job_id] = job

    # Start background processing
    background_tasks.add_task(
        process_pdf_extraction,
        job_id=job_id,
        pdf_url=str(request.document_url),
        api_key=api_key,
        prompt_version=request.prompt_version,
        force_model=request.force_model,
    )

    logger.info(
        "Async job created",
        extra={
            "request_id": request_id,
            "job_id": job_id,
            "pdf_url": str(request.document_url),
        },
    )

    return {"job_id": job_id, "status": "accepted", "message": "Processing started"}


@app.get("/job/{job_id}", response_model=JobStatus, tags=["Job Management"])
async def get_job_status(
    job_id: str, req: Request, api_key: str = Depends(verify_api_key)
):
    """Get the status of an async extraction job."""
    request_id = req.state.request_id

    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]

    logger.info(
        "Job status requested",
        extra={"request_id": request_id, "job_id": job_id, "status": job.status},
    )

    return job


@app.get("/", response_class=HTMLResponse, tags=["Homepage"])
async def homepage():
    """Homepage for PromoPack Extractor service."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PromoPack Extractor - AI-Powered PDF Processing</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .hero {
                text-align: center;
                padding: 100px 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin-bottom: 50px;
                backdrop-filter: blur(10px);
            }
            .hero h1 {
                font-size: 3em;
                margin-bottom: 20px;
                color: white;
            }
            .hero p {
                font-size: 1.5em;
                margin-bottom: 30px;
                color: #f0f0f0;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 50px;
            }
            .feature {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            .feature h3 {
                color: #667eea;
                margin-bottom: 15px;
            }
            .cta {
                text-align: center;
                padding: 50px 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            .cta h2 {
                color: white;
                margin-bottom: 20px;
            }
            .cta p {
                color: #f0f0f0;
                margin-bottom: 30px;
            }
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                transition: background 0.3s;
            }
            .btn:hover {
                background: #5a6fd8;
            }
            footer {
                text-align: center;
                padding: 20px;
                color: #f0f0f0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <section class="hero">
                <h1>Welcome to PromoPack Extractor</h1>
                <p>Revolutionize your promotional material processing with AI-powered PDF analysis</p>
            </section>
            
            <section class="features">
                <div class="feature">
                    <h3>🚀 Fast Processing</h3>
                    <p>Extract key claims from PDF documents in seconds using advanced language models.</p>
                </div>
                <div class="feature">
                    <h3>🎯 High Accuracy</h3>
                    <p>Leverage Google Gemini AI for precise identification and extraction of promotional claims.</p>
                </div>
                <div class="feature">
                    <h3>🔧 API Integration</h3>
                    <p>Seamlessly integrate with your existing workflows via our REST API.</p>
                </div>
                <div class="feature">
                    <h3>📊 Cost Tracking</h3>
                    <p>Monitor usage and costs with built-in analytics and reporting.</p>
                </div>
                <div class="feature">
                    <h3>🔒 Secure & Reliable</h3>
                    <p>Enterprise-grade security with rate limiting, authentication, and monitoring.</p>
                </div>
                <div class="feature">
                    <h3>📈 Scalable</h3>
                    <p>Handle large volumes of documents with our robust async processing system.</p>
                </div>
            </section>
            
            <section class="cta">
                <h2>Ready to Get Started?</h2>
                <p>Join pharmaceutical companies worldwide in streamlining their promotional material workflows.</p>
                <a href="/docs" class="btn">View API Documentation</a>
            </section>
        </div>
        
        <footer>
            <p>&copy; 2025 PromoPack Extractor. Built for the pharmaceutical industry.</p>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["Health & Monitoring"])
async def health_check():
    """Basic health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": config.service_name,
        "version": config.version,
    }


@app.get("/cost-analytics", tags=["Analytics & Cost Tracking"])
async def get_cost_analytics(req: Request, api_key: str = Depends(verify_api_key)):
    """Get cost and usage analytics for LLM calls."""
    request_id = req.state.request_id

    logger.info("Cost analytics requested", extra={"request_id": request_id})

    stats = cost_tracker.get_usage_stats()

    return {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cost_analytics": stats,
    }


@app.get("/ready", tags=["Health & Monitoring"])
async def readiness_check():
    """Readiness probe for container orchestration - checks if service can handle requests."""
    try:
        # Check if API key is configured
        if not config.api_key_secret:
            return {"status": "not ready", "reason": "API_KEY_SECRET not configured"}

        # Check if LangExtract API key is configured
        if not config.langextract_api_key:
            return {
                "status": "not ready",
                "reason": "LANGEXTRACT_API_KEY not configured",
            }

        # Could add more checks here (database connectivity, etc.)

        return {
            "status": "ready",
            "service": config.service_name,
            "version": config.version,
        }
    except Exception as e:
        logger.error("Readiness check failed", exc_info=True)
        return {"status": "not ready", "reason": str(e)}


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")

    # If detail is already a dict (like rate limit), use it
    if isinstance(exc.detail, dict):
        response_content = {
            **exc.detail,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    else:
        # Map status codes to error codes
        error_codes = {
            400: "bad_request",
            401: "invalid_api_key",
            403: "forbidden",
            404: "not_found",
            422: "unprocessable_entity",
            429: "rate_limit_exceeded",
            500: "internal_server_error",
        }
        error_code = error_codes.get(exc.status_code, "http_error")

        response_content = {
            "error": error_code,
            "message": exc.detail,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return JSONResponse(
        status_code=exc.status_code, content=response_content, headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    # Log the error (middleware already logs, but ensure it's captured)
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "request_id": request_id,
            "error_type": type(exc).__name__,
            "endpoint": f"{request.method} {request.url.path}",
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )
