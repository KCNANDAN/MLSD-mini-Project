
"""Deterministic LLM stub for repeatable load testing."""

import asyncio
import json
from typing import Any


class StubLLMService:
    """Simulate LLM responses without contacting an external provider."""

    def __init__(self, latency_ms: int = 100) -> None:
        self.provider = "stub"
        self.model = "deterministic-stub"
        self.latency_ms = max(0, latency_ms)

    async def _simulate_latency(self) -> None:
        """Simulate configurable model response latency."""
        if self.latency_ms:
            await asyncio.sleep(self.latency_ms / 1000)

    async def generate(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 2048,
    ) -> str:
        """Return a deterministic verification response."""

        if not messages:
            raise ValueError("Messages cannot be empty")

        await self._simulate_latency()

        return json.dumps({
            "verification_passed": False,
            "claims_supported": False,
            "missing_provisions": [
                "Official regulatory evidence requires verification."
            ],
            "conflicts_detected": False,
            "committee_discretion": False,
            "unsupported_claims": [],
            "reasoning": (
                "Stub verification: no regulatory evidence "
                "has been independently established."
            ),
            "recommendation_supported": False,
            "verified_recommendation": "refer-to-committee",
        })

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
    ) -> dict[str, Any]:
        """Simulate research-agent tool selection and final response."""

        if not messages:
            raise ValueError("Messages cannot be empty")

        if not tools:
            raise ValueError("At least one tool must be provided")

        await self._simulate_latency()

        tool_results_received = any(
            message.get("role") == "tool"
            for message in messages
        )

        if tool_results_received:
            return {
                "role": "assistant",
                "content": json.dumps({
                    "petition_category": "attendance",
                    "classification_confidence": 0.95,
                    "research_query": (
                        "attendance requirements and condonation "
                        "on medical grounds"
                    ),
                    "findings": (
                        "Stub research completed. Actual regulatory "
                        "evidence must determine eligibility."
                    ),
                    "citations": [],
                    "proposed_recommendation": "refer-to-committee",
                    "missing_evidence": [
                        "Verified university regulation provisions"
                    ],
                }),
            }

        available_tools = {
            item.get("function", {}).get("name")
            for item in tools
        }

        requested_tools = [
            (
                "search_regulation_provisions",
                {
                    "query": (
                        "minimum attendance requirement and "
                        "attendance eligibility"
                    )
                },
            ),
            (
                "search_condonation_provisions",
                {
                    "topic": (
                        "attendance condonation for medical grounds"
                    )
                },
            ),
        ]

        tool_calls = []

        for tool_name, arguments in requested_tools:
            if tool_name not in available_tools:
                continue

            tool_calls.append({
                "id": f"stub_call_{len(tool_calls) + 1}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments),
                },
            })

        if not tool_calls:
            return {
                "role": "assistant",
                "content": json.dumps({
                    "petition_category": "attendance",
                    "classification_confidence": 0.0,
                    "research_query": "",
                    "findings": "No compatible retrieval tools available.",
                    "citations": [],
                    "proposed_recommendation": "refer-to-committee",
                    "missing_evidence": ["Retrieval tools unavailable"],
                }),
            }

        return {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        }
