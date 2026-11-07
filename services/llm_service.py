
import time
from typing import Any

import httpx
from load_testing.stub_llm import StubLLMService
from config.settings import get_settings
from observability.cost_tracker import cost_tracker, LLMUsage
from observability.metrics import record_llm_usage
from observability.tracing import trace_span


settings = get_settings()

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class LLMServiceError(Exception):
    """Raised when an LLM request fails."""


class LLMService:
    """Asynchronous service for communicating with an LLM provider."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout_seconds

        self.api_key = (
            settings.llm_api_key.get_secret_value()
            if settings.llm_api_key
            else None
        )

        self.base_url = (
            settings.llm_base_url.rstrip("/")
            if settings.llm_base_url
            else DEFAULT_GROQ_BASE_URL
        )

        if not self.api_key:
            raise LLMServiceError("LLM API key is not configured")

        if self.provider != "groq":
            raise LLMServiceError(
                f"Unsupported LLM provider: {self.provider}"
            )

    def _record_successful_request(
        self,
        response_data: dict[str, Any],
    ) -> None:
        """Record actual token usage returned by the provider."""

        usage = response_data.get("usage") or {}

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        if not isinstance(prompt_tokens, int) or prompt_tokens < 0:
            prompt_tokens = 0

        if not isinstance(completion_tokens, int) or completion_tokens < 0:
            completion_tokens = 0

        cost_tracker.record_usage(
            LLMUsage(
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
    ) -> str:
        """Generate a response from the configured LLM."""

        if not messages:
            raise ValueError("Messages cannot be empty")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        status = "failed"

        with trace_span(
            "llm.generate",
            {
                "llm.provider": self.provider,
                "llm.model": self.model,
            },
        ) as span:

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout
                ) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]

                if not isinstance(content, str) or not content.strip():
                    raise LLMServiceError(
                        "LLM returned an empty response"
                    )

                self._record_successful_request(data)
                status = "success"

                return content.strip()

            except httpx.TimeoutException as exc:
                raise LLMServiceError(
                    "LLM request timed out"
                ) from exc

            except httpx.HTTPStatusError as exc:
                raise LLMServiceError(
                    f"LLM provider returned HTTP {exc.response.status_code}"
                ) from exc

            except httpx.RequestError as exc:
                raise LLMServiceError(
                    "Could not connect to the LLM provider"
                ) from exc

            except (KeyError, IndexError, TypeError, ValueError) as exc:
                if isinstance(exc, LLMServiceError):
                    raise

                raise LLMServiceError(
                    "Invalid response received from LLM provider"
                ) from exc

            finally:
                duration = time.perf_counter() - start_time

                if status == "failed":
                    record_llm_usage(
                        provider=self.provider,
                        model=self.model,
                        status="failed",
                    )

                span.set_attribute("llm.status", status)
                span.set_attribute("llm.duration_seconds", duration)

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
    ) -> dict[str, Any]:
        """Generate an LLM response with native function-calling support."""

        if not messages:
            raise ValueError("Messages cannot be empty")

        if not tools:
            raise ValueError("At least one tool must be provided")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": self.temperature,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        status = "failed"

        with trace_span(
            "llm.generate_with_tools",
            {
                "llm.provider": self.provider,
                "llm.model": self.model,
            },
        ) as span:

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout
                ) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                    response.raise_for_status()
                    data = response.json()

                message = data["choices"][0]["message"]

                if not isinstance(message, dict):
                    raise LLMServiceError(
                        "Invalid LLM message response"
                    )

                self._record_successful_request(data)
                status = "success"

                return message

            except httpx.TimeoutException as exc:
                raise LLMServiceError(
                    "LLM request timed out"
                ) from exc

            except httpx.HTTPStatusError as exc:
                raise LLMServiceError(
                    f"LLM provider returned HTTP {exc.response.status_code}"
                ) from exc

            except httpx.RequestError as exc:
                raise LLMServiceError(
                    "Could not connect to the LLM provider"
                ) from exc

            except (KeyError, IndexError, TypeError, ValueError) as exc:
                if isinstance(exc, LLMServiceError):
                    raise

                raise LLMServiceError(
                    "Invalid response received from LLM provider"
                ) from exc

            finally:
                duration = time.perf_counter() - start_time

                if status == "failed":
                    record_llm_usage(
                        provider=self.provider,
                        model=self.model,
                        status="failed",
                    )

                span.set_attribute("llm.status", status)
                span.set_attribute("llm.duration_seconds", duration)


class InstrumentedStubLLMService:
    """Add tracing and Prometheus metrics to the deterministic stub."""

    def __init__(self) -> None:
        self.stub = StubLLMService(
            latency_ms=settings.stub_llm_latency_ms
        )
        self.provider = self.stub.provider
        self.model = self.stub.model

    async def generate(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 2048,
    ) -> str:
        start_time = time.perf_counter()
        status = "failed"

        with trace_span(
            "llm.generate",
            {
                "llm.provider": self.provider,
                "llm.model": self.model,
            },
        ) as span:
            try:
                result = await self.stub.generate(messages, max_tokens)
                status = "success"
                return result
            finally:
                span.set_attribute("llm.status", status)
                span.set_attribute(
                    "llm.duration_seconds",
                    time.perf_counter() - start_time,
                )
                record_llm_usage(
                    provider=self.provider,
                    model=self.model,
                    status=status,
                )

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        status = "failed"

        with trace_span(
            "llm.generate_with_tools",
            {
                "llm.provider": self.provider,
                "llm.model": self.model,
            },
        ) as span:
            try:
                result = await self.stub.generate_with_tools(
                    messages,
                    tools,
                    tool_choice,
                )
                status = "success"
                return result
            finally:
                span.set_attribute("llm.status", status)
                span.set_attribute(
                    "llm.duration_seconds",
                    time.perf_counter() - start_time,
                )
                record_llm_usage(
                    provider=self.provider,
                    model=self.model,
                    status=status,
                )


_llm_service: Any = None


def get_llm_service() -> Any:
    """Return the configured, shared LLM service instance."""

    global _llm_service

    if _llm_service is None:
        if settings.use_stub_llm:
            _llm_service = InstrumentedStubLLMService()
        else:
            _llm_service = LLMService()

    return _llm_service
