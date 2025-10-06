# Fix for Empty LLM Response Error

## Problem

The application was encountering errors when the LLM (Language Model) returned empty or malformed responses:

```
ValueError: Source tokens and extraction tokens cannot be empty.
```

This error occurred in the `langextract` library when:
1. The LLM returned an empty response
2. The LLM returned a response that couldn't be properly tokenized/aligned
3. The extraction validation step failed due to missing tokens

## Root Cause

The `langextract` library's internal validation (`validate_prompt_alignment`) expects non-empty token sequences for both the source text and the extracted results. When the LLM fails to return valid extractions, this validation step raises a `ValueError`.

The retry logic was configured to retry ALL exceptions, including `ValueError`, which meant the system would waste time retrying 3 times for each model even when the error was an empty response that wouldn't improve on retry.

## Solution Implemented

### 1. Early Text Validation (api.py)

Added validation to ensure text is not empty BEFORE calling the LLM:

```python
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
```

This prevents wasting API calls when the PDF has no extractable text or when security filtering removes all content.

### 2. Better Error Handling in LLM Integration (llm_integration.py)

**a) Empty Text Check:**
```python
# Validate text is not empty before attempting extraction
if not text or not text.strip():
    logger.error(
        "Empty text provided for extraction",
        extra={"request_id": request_id},
    )
    raise ValueError("Cannot extract claims from empty text")
```

**b) Improved ValueError Handling:**
```python
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
```

**c) Optimized Retry Logic:**

Changed from:
```python
retry=retry_if_exception_type(Exception),
```

To:
```python
retry=retry_if_not_exception_type(ValueError),
```

This means:
- **Network errors, timeouts, etc.** → Retry up to 3 times (helpful)
- **ValueError (empty/malformed responses)** → Fail fast and try the next model (efficient)

### 3. Enhanced Logging

Added debug logging to track LLM responses:

```python
logger.debug(
    f"LLM extraction result from {model_id}",
    extra={
        "request_id": request_id,
        "has_extractions": hasattr(result, "extractions"),
        "extraction_count": len(result.extractions) if hasattr(result, "extractions") else 0,
    },
)
```

Also added success logging after successful extraction:

```python
logger.info(
    f"Successfully extracted {len(extractions)} claims with model {model_id}",
    extra={"request_id": request_id},
)
```

## Impact

### Before:
- Empty LLM responses triggered 3 retry attempts per model (wasting ~30 seconds)
- Both models would retry, totaling 6 failed attempts
- Eventually fell back to regex (which works but is less accurate)
- Poor visibility into what was happening

### After:
- Empty LLM responses fail immediately and try the next model
- Clear logging shows exactly when and why LLMs fail
- Faster fallback to regex when LLMs can't help
- Better error messages for users when PDFs have no extractable text

## Testing Recommendations

1. **Test with empty PDFs**: Verify proper error message
2. **Test with image-only PDFs**: Ensure OCR fallback works
3. **Test with heavily redacted content**: Verify security filtering doesn't leave empty text
4. **Monitor LLM response patterns**: Check if empty responses are common (may indicate prompt issues)

## Future Improvements

1. **Investigate why LLMs return empty responses**: May need prompt tuning
2. **Add metrics tracking**: Count how often each fallback path is used
3. **Implement response caching**: Avoid re-processing identical PDFs that always fail
4. **Consider alternative LLM providers**: If Gemini consistently fails on certain content types
