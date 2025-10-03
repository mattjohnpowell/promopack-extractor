"""Tests for cost tracking and optimization."""

from cost_tracking import CostTracker, TokenUsage


class TestCostTracker:
    """Test cost tracking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = CostTracker()
        self.tracker.reset_metrics()  # Start clean

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test sentence with some words."
        tokens = self.tracker.estimate_tokens(text, "gemini-1.5-flash")

        # Should be roughly len(text) // 4
        expected_min = len(text) // 5  # Allow some variance
        expected_max = len(text) // 3
        assert expected_min <= tokens <= expected_max

    def test_calculate_cost_flash(self):
        """Test cost calculation for Flash model."""
        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            model="gemini-1.5-flash",
        )

        cost = self.tracker.calculate_cost(usage)
        expected_cost = (1000 / 1000 * 0.000075) + (
            500 / 1000 * 0.0003
        )  # Convert to per 1K tokens
        assert abs(cost - expected_cost) < 0.000001

    def test_calculate_cost_pro(self):
        """Test cost calculation for Pro model."""
        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            model="gemini-1.5-pro",
        )

        cost = self.tracker.calculate_cost(usage)
        expected_cost = (1000 / 1000 * 0.00125) + (500 / 1000 * 0.005)
        assert abs(cost - expected_cost) < 0.000001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model."""
        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            model="unknown-model",
        )

        cost = self.tracker.calculate_cost(usage)
        assert cost == 0.0

    def test_record_usage(self):
        """Test recording usage."""
        request_id = "test-request"
        usage = self.tracker.record_usage(
            request_id=request_id, prompt_text="Test prompt", model="gemini-1.5-flash"
        )

        assert usage.prompt_tokens > 0
        assert usage.completion_tokens > 0
        assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens
        assert usage.model == "gemini-1.5-flash"

        # Check metrics
        stats = self.tracker.get_usage_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] > 0
        assert stats["total_cost"] > 0
        assert "gemini-1.5-flash" in stats["model_breakdown"]

    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        # Record some usage
        self.tracker.record_usage("req1", "prompt1", "gemini-1.5-flash")
        self.tracker.record_usage("req2", "prompt2", "gemini-1.5-pro")

        stats = self.tracker.get_usage_stats()

        assert stats["total_requests"] == 2
        assert stats["total_tokens"] > 0
        assert stats["total_cost"] > 0
        assert len(stats["model_breakdown"]) == 2
        assert "gemini-1.5-flash" in stats["model_breakdown"]
        assert "gemini-1.5-pro" in stats["model_breakdown"]

    def test_get_request_usage(self):
        """Test getting usage for specific request."""
        request_id = "test-request"
        self.tracker.record_usage(request_id, "prompt1", "gemini-1.5-flash")
        self.tracker.record_usage(request_id, "prompt2", "gemini-1.5-flash")

        usage_history = self.tracker.get_request_usage(request_id)
        assert len(usage_history) == 2

        # Check another request has no history
        other_usage = self.tracker.get_request_usage("other-request")
        assert len(other_usage) == 0

    def test_cost_optimization_logic(self):
        """Test that cost tracking supports optimization decisions."""
        # Record usage for both models
        self.tracker.record_usage("req1", "short prompt", "gemini-1.5-flash")
        self.tracker.record_usage("req2", "long complex prompt", "gemini-1.5-pro")

        stats = self.tracker.get_usage_stats()

        flash_stats = stats["model_breakdown"]["gemini-1.5-flash"]
        pro_stats = stats["model_breakdown"]["gemini-1.5-pro"]

        # Flash should be cheaper per token
        assert flash_stats["avg_cost_per_request"] < pro_stats["avg_cost_per_request"]

        # Both should have reasonable costs
        assert flash_stats["cost"] > 0
        assert pro_stats["cost"] > 0
