"""Cost optimization and usage tracking for LLM calls."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from logging_config import logger


@dataclass
class TokenUsage:
    """Token usage information for an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class CostMetrics:
    """Cost metrics for LLM usage."""

    total_cost: float = 0.0
    total_tokens: int = 0
    total_requests: int = 0
    model_costs: Dict[str, float] = field(default_factory=dict)
    model_tokens: Dict[str, int] = field(default_factory=dict)
    model_requests: Dict[str, int] = field(default_factory=dict)


class CostTracker:
    """Tracks costs and usage for LLM calls."""

    # Cost per 1K tokens (as of 2024, approximate)
    MODEL_COSTS = {
        "gemini-1.5-flash": {
            "input": 0.000075,  # $0.075 per 1M tokens
            "output": 0.0003,  # $0.30 per 1M tokens
        },
        "gemini-1.5-pro": {
            "input": 0.00125,  # $1.25 per 1M tokens
            "output": 0.005,  # $5.00 per 1M tokens
        },
    }

    def __init__(self):
        self._lock = threading.Lock()
        self.metrics = CostMetrics()
        self.recent_usage: Dict[str, list] = defaultdict(
            list
        )  # request_id -> [TokenUsage]

    def estimate_tokens(self, text: str, model: str) -> int:
        """Estimate token count for text using simple heuristics."""
        # Rough estimation: ~4 characters per token for English text
        # This is approximate and should be replaced with actual token counting
        char_count = len(text)
        estimated_tokens = max(1, char_count // 4)

        # Adjust for model-specific tokenization differences
        if "gemini" in model:
            # Gemini models tend to have slightly different tokenization
            estimated_tokens = int(estimated_tokens * 1.1)

        return estimated_tokens

    def calculate_cost(self, usage: TokenUsage) -> float:
        """Calculate cost for token usage."""
        if usage.model not in self.MODEL_COSTS:
            logger.warning(f"Unknown model for cost calculation: {usage.model}")
            return 0.0

        costs = self.MODEL_COSTS[usage.model]
        input_cost = (usage.prompt_tokens / 1000) * costs["input"]
        output_cost = (usage.completion_tokens / 1000) * costs["output"]

        return input_cost + output_cost

    def record_usage(
        self,
        request_id: str,
        prompt_text: str,
        model: str,
        completion_tokens: Optional[int] = None,
    ) -> TokenUsage:
        """Record token usage for an LLM call."""
        prompt_tokens = self.estimate_tokens(prompt_text, model)

        # Estimate completion tokens if not provided (rough heuristic)
        if completion_tokens is None:
            # Assume completion is roughly 1/3 the size of prompt for extraction tasks
            completion_tokens = max(50, prompt_tokens // 3)

        total_tokens = prompt_tokens + completion_tokens

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
        )

        cost = self.calculate_cost(usage)

        with self._lock:
            self.metrics.total_cost += cost
            self.metrics.total_tokens += total_tokens
            self.metrics.total_requests += 1

            self.metrics.model_costs[model] = (
                self.metrics.model_costs.get(model, 0) + cost
            )
            self.metrics.model_tokens[model] = (
                self.metrics.model_tokens.get(model, 0) + total_tokens
            )
            self.metrics.model_requests[model] = (
                self.metrics.model_requests.get(model, 0) + 1
            )

            # Keep recent usage for analytics (last 1000 entries per request)
            if len(self.recent_usage[request_id]) >= 1000:
                self.recent_usage[request_id].pop(0)
            self.recent_usage[request_id].append(usage)

        logger.info(
            "Token usage recorded",
            extra={
                "request_id": request_id,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": cost,
            },
        )

        return usage

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        with self._lock:
            return {
                "total_cost": self.metrics.total_cost,
                "total_tokens": self.metrics.total_tokens,
                "total_requests": self.metrics.total_requests,
                "model_breakdown": {
                    model: {
                        "cost": self.metrics.model_costs.get(model, 0),
                        "tokens": self.metrics.model_tokens.get(model, 0),
                        "requests": self.metrics.model_requests.get(model, 0),
                        "avg_cost_per_request": (
                            self.metrics.model_costs.get(model, 0)
                            / max(1, self.metrics.model_requests.get(model, 0))
                        ),
                        "avg_tokens_per_request": (
                            self.metrics.model_tokens.get(model, 0)
                            / max(1, self.metrics.model_requests.get(model, 0))
                        ),
                    }
                    for model in set(self.metrics.model_costs.keys())
                    | set(self.metrics.model_tokens.keys())
                },
                "cost_per_token": (
                    self.metrics.total_cost / max(1, self.metrics.total_tokens)
                ),
            }

    def get_request_usage(self, request_id: str) -> list:
        """Get usage history for a specific request."""
        with self._lock:
            return self.recent_usage.get(request_id, []).copy()

    def reset_metrics(self):
        """Reset all metrics (for testing)."""
        with self._lock:
            self.metrics = CostMetrics()
            self.recent_usage.clear()


# Global cost tracker instance
cost_tracker = CostTracker()
