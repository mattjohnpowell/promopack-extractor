"""Tests for LLM integration with focus on error handling."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from llm_integration import extract_claims_with_fallback


class TestEmptyResponseHandling:
    """Test handling of empty LLM responses."""

    def test_empty_text_falls_back_to_regex(self):
        """Test that empty text triggers regex fallback (graceful handling)."""
        result, method = extract_claims_with_fallback("", "test-request-id")
        
        # Should fall back to regex
        assert method == "regex_fallback"
        assert isinstance(result, list)
        # Empty text should result in no claims
        assert len(result) == 0

    def test_whitespace_only_text_falls_back_to_regex(self):
        """Test that whitespace-only text triggers regex fallback."""
        result, method = extract_claims_with_fallback("   \n\t  ", "test-request-id")
        
        # Should fall back to regex
        assert method == "regex_fallback"
        assert isinstance(result, list)
        # Whitespace only should result in no claims
        assert len(result) == 0

    @patch("llm_integration.lx.extract")
    def test_empty_llm_response_triggers_fallback(self, mock_extract):
        """Test that empty LLM responses trigger model fallback."""
        # Simulate langextract ValueError for empty tokens
        mock_extract.side_effect = ValueError(
            "Source tokens and extraction tokens cannot be empty."
        )

        text = "This is a valid test claim about efficacy."
        result, method = extract_claims_with_fallback(text, "test-request-id")

        # Should fall back to regex extraction
        assert method == "regex_fallback"
        assert isinstance(result, list)

    @patch("llm_integration.lx.extract")
    def test_malformed_llm_response_triggers_fallback(self, mock_extract):
        """Test that malformed LLM responses trigger model fallback."""
        # Simulate various langextract errors
        mock_extract.side_effect = ValueError("Alignment validation failed")

        text = "This drug demonstrates superior efficacy in clinical trials."
        result, method = extract_claims_with_fallback(text, "test-request-id")

        # Should fall back to regex extraction
        assert method == "regex_fallback"
        assert isinstance(result, list)

    @patch("llm_integration.lx.extract")
    def test_successful_extraction_after_first_model_fails(self, mock_extract):
        """Test successful extraction with second model after first fails."""

        # Create a mock extraction result
        class MockExtraction:
            def __init__(self):
                self.extraction_text = "Reduces risk by 50%"
                self.attributes = {"confidence": 0.9}
                self.spans = []

        class MockResult:
            def __init__(self):
                self.extractions = [MockExtraction()]

        # First call (flash model) fails, second call (pro model) succeeds
        mock_extract.side_effect = [
            ValueError("Source tokens and extraction tokens cannot be empty."),
            MockResult(),
        ]

        text = "This drug reduces cardiovascular risk by 50% compared to placebo."
        result, method = extract_claims_with_fallback(text, "test-request-id")

        # Should succeed with second model
        assert method.startswith("llm_")
        assert len(result) == 1
        assert result[0].extraction_text == "Reduces risk by 50%"

    @patch("llm_integration.lx.extract")
    @patch("llm_integration.cost_tracker.record_usage")
    def test_cost_tracking_on_successful_extraction(
        self, mock_cost_tracker, mock_extract
    ):
        """Test that cost tracking is called on successful extraction."""

        class MockExtraction:
            def __init__(self):
                self.extraction_text = "Test claim"
                self.attributes = {"confidence": 0.9}
                self.spans = []

        class MockResult:
            def __init__(self):
                self.extractions = [MockExtraction()]

        mock_extract.return_value = MockResult()

        text = "This drug shows significant improvement in patient outcomes."
        result, method = extract_claims_with_fallback(text, "test-request-id")

        # Cost tracking should be called once
        assert mock_cost_tracker.call_count == 1

    @patch("llm_integration.lx.extract")
    def test_all_models_fail_uses_regex_fallback(self, mock_extract):
        """Test that regex fallback is used when all LLM models fail."""
        # All LLM calls fail with ValueError
        mock_extract.side_effect = ValueError(
            "Source tokens and extraction tokens cannot be empty."
        )

        text = "Demonstrated efficacy in reducing symptoms compared to placebo."
        result, method = extract_claims_with_fallback(text, "test-request-id")

        # Should use regex fallback
        assert method == "regex_fallback"
        assert isinstance(result, list)
        # Extract should have been called twice (flash + pro)
        assert mock_extract.call_count == 2


class TestRegexFallback:
    """Test regex-based fallback extraction."""

    @patch("llm_integration.lx.extract")
    def test_regex_fallback_finds_efficacy_claims(self, mock_extract):
        """Test that regex fallback can find basic efficacy claims."""
        mock_extract.side_effect = ValueError("LLM failed")

        text = """
        This medication demonstrated superior efficacy in clinical trials.
        Patients showed significant improvement in symptoms.
        The treatment is proven effective for reducing cardiovascular risk.
        """

        result, method = extract_claims_with_fallback(text, "test-request-id")

        assert method == "regex_fallback"
        # Should find at least one claim
        assert len(result) > 0

    @patch("llm_integration.lx.extract")
    def test_regex_fallback_finds_safety_claims(self, mock_extract):
        """Test that regex fallback can find safety claims."""
        mock_extract.side_effect = ValueError("LLM failed")

        text = """
        The safety profile of this medication is well-established.
        Adverse events were minimal in clinical trials.
        This treatment is generally well-tolerated by patients.
        """

        result, method = extract_claims_with_fallback(text, "test-request-id")

        assert method == "regex_fallback"
        # Should find at least one claim
        assert len(result) > 0

    @patch("llm_integration.lx.extract")
    def test_regex_fallback_with_no_claims(self, mock_extract):
        """Test regex fallback with text containing no claims."""
        mock_extract.side_effect = ValueError("LLM failed")

        text = "This is just regular text with no medical claims whatsoever."

        result, method = extract_claims_with_fallback(text, "test-request-id")

        assert method == "regex_fallback"
        # May return empty list or few results
        assert isinstance(result, list)
