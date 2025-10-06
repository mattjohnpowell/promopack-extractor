"""LLM integration and fallback functions."""

import re
import textwrap
import time
from typing import Any, List, Optional, Tuple

import langextract as lx
from langdetect import LangDetectException, detect
from tenacity import (retry, retry_if_exception_type, retry_if_not_exception_type,
                      stop_after_attempt, wait_exponential)

from cost_tracking import cost_tracker
from logging_config import logger
from prompt_engineering import ModelType, PromptVersion, prompt_manager


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise e


# Global circuit breaker for LLM calls
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=3, recovery_timeout=300
)  # 5 minutes


def audit_data_source_language(text: str, request_id: str) -> str:
    """Audit the data source by detecting the language of the text.

    Args:
        text: The text content to analyze
        request_id: Request ID for logging

    Returns:
        Detected language code (e.g., 'en', 'fr', 'de')
    """
    try:
        # Sample the text for language detection (first 1000 characters should be sufficient)
        sample_text = text[:1000].strip()
        if not sample_text:
            logger.warning(
                "Empty text sample for language detection",
                extra={"request_id": request_id},
            )
            return "unknown"

        detected_lang = detect(sample_text)
        logger.info(
            "Language detection completed",
            extra={
                "request_id": request_id,
                "detected_language": detected_lang,
                "sample_length": len(sample_text),
            },
        )
        return detected_lang

    except LangDetectException as e:
        logger.warning(
            "Language detection failed",
            extra={"request_id": request_id, "error": str(e)},
        )
        return "unknown"
    except Exception as e:
        logger.error(
            "Unexpected error during language detection",
            exc_info=True,
            extra={"request_id": request_id, "error_type": type(e).__name__},
        )
        return "unknown"


def extract_claims_with_langextract(text: str) -> List[dict]:
    """Extract claims using LangExtract. Used for testing."""
    try:
        prompt = textwrap.dedent(
            """\
            Extract key claims from the document. A claim is a significant statement that asserts facts about results, efficacy, or findings.
            Extract the exact text of the claim without paraphrasing."""
        )

        examples = [
            lx.data.ExampleData(
                text="The study showed that Drug X reduced symptoms by 50% compared to placebo.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="claim",
                        extraction_text="The study showed that Drug X reduced symptoms by 50% compared to placebo",
                        attributes={"confidence": 0.95},
                    )
                ],
            ),
            lx.data.ExampleData(
                text="Patients treated with the new therapy had a 30% improvement in quality of life.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="claim",
                        extraction_text="Patients treated with the new therapy had a 30% improvement in quality of life",
                        attributes={"confidence": 0.92},
                    )
                ],
            ),
        ]

        # Use circuit breaker and retry logic
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type(Exception),
        )
        def _extract_with_retry():
            return lx.extract(
                text_or_documents=text,
                prompt_description=prompt,
                examples=examples,
                model_id="gemini-1.5-flash",
            )

        result = llm_circuit_breaker.call(_extract_with_retry)

        claims = []
        if hasattr(result, "extractions"):
            for extraction in result.extractions:
                claim_text = extraction.extraction_text
                confidence = extraction.attributes.get("confidence", 0.9)
                claims.append(
                    {
                        "text": claim_text,
                        "confidence_score": confidence,
                        "source_text": text,
                    }
                )

        return claims
    except Exception:
        # Return empty list on error for graceful degradation
        return []


def fallback_claim_search(text: str) -> List[dict]:
    """Fallback claim search using regex patterns. Used for testing."""
    # Simple regex patterns for common claim indicators
    claim_patterns = [
        r"(?:reduced?|decreased?|improved?|increased?|effective).*?(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:times?|fold))",
        r"(?:study|trial|research).*?(?:showed|demonstrated|found|revealed)",
        r"(?:patients?|subjects?).*?(?:experienced?|achieved?|reported)",
    ]

    claims = []
    for pattern in claim_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            claim_text = match.group(0).strip()
            if len(claim_text) > 20:  # Only include substantial matches
                claims.append(
                    {
                        "text": claim_text,
                        "confidence_score": 0.7,  # Lower confidence for regex fallback
                        "source_text": text,
                    }
                )

    return claims


def extract_claims_with_fallback(
    text: str,
    request_id: str,
    prompt_version: Optional[PromptVersion] = None,
    force_model: Optional[ModelType] = None,
) -> Tuple[List[Any], str]:
    """Extract claims using LLM with model fallback and regex fallback."""
    extractions = []
    extraction_method = "llm"

    # Get optimal prompt configuration based on content analysis
    prompt, examples, selected_model = prompt_manager.get_prompt_config(
        text, request_id, prompt_version, force_model
    )

    logger.info(
        "Starting LLM claim extraction with model fallback",
        extra={
            "request_id": request_id,
            "text_length": len(text),
            "initial_model": selected_model,
            "prompt_version": prompt_version.value if prompt_version else "auto",
        },
    )

    # Model fallback hierarchy: try selected model first, then fallback model, then regex
    models_to_try = [selected_model]
    if selected_model == ModelType.GEMINI_PRO.value:
        models_to_try.append(ModelType.GEMINI_FLASH.value)
    else:
        models_to_try.append(ModelType.GEMINI_PRO.value)

    successful_model = None

    for model_id in models_to_try:
        try:
            logger.info(
                f"Attempting extraction with model: {model_id}",
                extra={"request_id": request_id},
            )

            # Validate text is not empty before attempting extraction
            if not text or not text.strip():
                logger.error(
                    "Empty text provided for extraction",
                    extra={"request_id": request_id},
                )
                raise ValueError("Cannot extract claims from empty text")

            # Use circuit breaker and retry logic
            # Don't retry on ValueError (empty responses) - fail fast and try next model
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_not_exception_type(ValueError),
            )
            def _extract_with_retry():
                try:
                    result = lx.extract(
                        text_or_documents=text,
                        prompt_description=prompt,
                        examples=examples,
                        model_id=model_id,
                        max_char_buffer=50000,  # Larger chunks for pharmaceutical documents
                        max_workers=20,  # Parallel processing for speed
                    )
                    
                    # Log successful result for debugging
                    logger.debug(
                        f"LLM extraction result from {model_id}",
                        extra={
                            "request_id": request_id,
                            "has_extractions": hasattr(result, "extractions"),
                            "extraction_count": len(result.extractions) if hasattr(result, "extractions") else 0,
                        },
                    )
                    
                    return result
                    
                except ValueError as ve:
                    # langextract raises ValueError for empty tokens or alignment issues
                    error_msg = str(ve).lower()
                    if "empty" in error_msg or "token" in error_msg:
                        logger.warning(
                            f"LLM returned empty or malformed response for model {model_id}",
                            extra={
                                "request_id": request_id,
                                "error": str(ve),
                                "text_length": len(text),
                                "text_preview": text[:200] if text else "",
                            },
                        )
                        # Don't retry for empty responses - fail fast and try next model
                        raise ValueError(f"Empty LLM response from {model_id}") from ve
                    raise
                except Exception as e:
                    logger.error(
                        f"Unexpected error during extraction with {model_id}",
                        exc_info=True,
                        extra={
                            "request_id": request_id,
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

            result = llm_circuit_breaker.call(_extract_with_retry)

            if hasattr(result, "extractions") and result.extractions:
                extractions = result.extractions
                successful_model = model_id
                extraction_method = f"llm_{model_id.replace('gemini-1.5-', '')}"

                # Record cost and usage
                cost_tracker.record_usage(
                    request_id=request_id, prompt_text=prompt, model=model_id
                )

                logger.info(
                    f"Successfully extracted {len(extractions)} claims with model {model_id}",
                    extra={"request_id": request_id},
                )

                break  # Success, stop trying other models

        except Exception as e:
            logger.warning(
                f"LLM extraction failed with model {model_id}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "model": model_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            continue  # Try next model

    # If all LLM models failed, fall back to regex
    if not extractions:
        logger.warning(
            "All LLM models failed, falling back to regex-based extraction",
            extra={"request_id": request_id},
        )

        extraction_method = "regex_fallback"
        fallback_claims = fallback_claim_search(text)

        # Convert fallback results to extraction-like objects
        for claim in fallback_claims:
            # Create a mock extraction object
            class MockExtraction:
                def __init__(self, text, confidence):
                    self.extraction_text = text
                    self.attributes = {"confidence": confidence}
                    self.spans = None  # No spans for regex fallback

            extractions.append(MockExtraction(claim["text"], claim["confidence_score"]))

        logger.info(
            "Regex fallback extraction completed",
            extra={"request_id": request_id, "extractions_found": len(extractions)},
        )
    else:
        logger.info(
            "LLM extraction completed successfully",
            extra={
                "request_id": request_id,
                "successful_model": successful_model,
                "extractions_found": len(extractions),
            },
        )

    return extractions, extraction_method
