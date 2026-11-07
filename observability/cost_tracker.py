
from dataclasses import dataclass

from observability.metrics import record_llm_usage


@dataclass
class LLMUsage:
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ModelPricing:
    """Cost per one million tokens, expressed in USD."""

    prompt_cost_per_million: float
    completion_cost_per_million: float


class CostTracker:
    """Tracks token consumption and estimated LLM costs."""

    def __init__(self) -> None:
        self._pricing: dict[str, ModelPricing] = {}

    def register_pricing(
        self,
        provider: str,
        model: str,
        prompt_cost_per_million: float,
        completion_cost_per_million: float,
    ) -> None:
        if prompt_cost_per_million < 0 or completion_cost_per_million < 0:
            raise ValueError("Token pricing cannot be negative.")

        self._pricing[f"{provider}:{model}"] = ModelPricing(
            prompt_cost_per_million=prompt_cost_per_million,
            completion_cost_per_million=completion_cost_per_million,
        )

    def estimate_cost(self, usage: LLMUsage) -> float | None:
        pricing = self._pricing.get(
            f"{usage.provider}:{usage.model}"
        )

        if pricing is None:
            return None

        prompt_cost = (
            usage.prompt_tokens
            / 1_000_000
            * pricing.prompt_cost_per_million
        )

        completion_cost = (
            usage.completion_tokens
            / 1_000_000
            * pricing.completion_cost_per_million
        )

        return prompt_cost + completion_cost

    def record_usage(self, usage: LLMUsage) -> float | None:
        estimated_cost = self.estimate_cost(usage)

        record_llm_usage(
            provider=usage.provider,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            estimated_cost_usd=estimated_cost or 0.0,
        )

        return estimated_cost


cost_tracker = CostTracker()
