import asyncio
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Callable, TypeVar

from config.logging_config import get_logger
from config.settings import get_settings
from observability.metrics import record_agent_retry

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while the circuit is open."""


class CircuitBreaker:
    """
    Three-state circuit breaker protecting external calls (LLM, queue, services).

    - CLOSED: Normal operation. Requests pass through.
    - OPEN: Threshold exceeded. Fast failure without calling downstream service.
    - HALF_OPEN: Recovery testing window. Allows a test request to probe health.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int | None = None,
        recovery_seconds: float | None = None,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else settings.circuit_breaker_failure_threshold
        )
        self.recovery_seconds = (
            recovery_seconds
            if recovery_seconds is not None
            else float(settings.circuit_breaker_recovery_seconds)
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else settings.max_agent_retries
        )
        self.backoff_seconds = (
            backoff_seconds
            if backoff_seconds is not None
            else settings.retry_backoff_seconds
        )

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0
        self._success_count: int = 0
        self._total_requests: int = 0
        self._rejected_requests: int = 0

    @property
    def state(self) -> CircuitState:
        """Evaluate and return the current circuit state, checking recovery window."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_seconds:
                logger.info(
                    "circuit_breaker_transition",
                    circuit=self.name,
                    from_state=CircuitState.OPEN.value,
                    to_state=CircuitState.HALF_OPEN.value,
                    elapsed_seconds=round(elapsed, 2),
                )
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def reset(self) -> None:
        """Reset the breaker to its initial CLOSED state."""
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = 0.0
        self._success_count = 0

    def record_success(self) -> None:
        """Handle a successful downstream response."""
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker_recovered",
                circuit=self.name,
                from_state=CircuitState.HALF_OPEN.value,
                to_state=CircuitState.CLOSED.value,
            )
            self.reset()
        else:
            self._consecutive_failures = 0

    def record_failure(self, error: Exception) -> None:
        """Handle a failed downstream response."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        logger.warning(
            "circuit_breaker_failure_recorded",
            circuit=self.name,
            failures=self._consecutive_failures,
            threshold=self.failure_threshold,
            error=str(error),
        )

        if self._consecutive_failures >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.error(
                    "circuit_breaker_tripped",
                    circuit=self.name,
                    from_state=self._state.value,
                    to_state=CircuitState.OPEN.value,
                    failures=self._consecutive_failures,
                )
            self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check whether a request is allowed through."""
        current_state = self.state
        if current_state == CircuitState.OPEN:
            self._rejected_requests += 1
            return False
        return True

    async def call_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Execute an asynchronous function with circuit breaking and retries.
        """
        self._total_requests += 1

        if not self.allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Fast failing request."
            )

        attempts = 0
        max_attempts = 1 + (self.max_retries if retry else 0)

        last_exception: Exception | None = None

        while attempts < max_attempts:
            attempts += 1
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self.record_success()
                return result

            except Exception as exc:
                last_exception = exc
                if attempts < max_attempts:
                    record_agent_retry(self.name)
                    sleep_time = self.backoff_seconds * (2 ** (attempts - 1))
                    logger.warning(
                        "circuit_breaker_retry",
                        circuit=self.name,
                        attempt=attempts,
                        max_attempts=max_attempts,
                        backoff=sleep_time,
                        error=str(exc),
                    )
                    await asyncio.sleep(sleep_time)

        self.record_failure(last_exception)
        raise last_exception

    def call_sync(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a synchronous function with circuit breaking and retries.
        """
        self._total_requests += 1

        if not self.allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Fast failing request."
            )

        attempts = 0
        max_attempts = 1 + (self.max_retries if retry else 0)
        last_exception: Exception | None = None

        while attempts < max_attempts:
            attempts += 1
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result

            except Exception as exc:
                last_exception = exc
                if attempts < max_attempts:
                    record_agent_retry(self.name)
                    sleep_time = self.backoff_seconds * (2 ** (attempts - 1))
                    logger.warning(
                        "circuit_breaker_retry_sync",
                        circuit=self.name,
                        attempt=attempts,
                        max_attempts=max_attempts,
                        backoff=sleep_time,
                        error=str(exc),
                    )
                    time.sleep(sleep_time)

        self.record_failure(last_exception)
        raise last_exception


# Global registry of circuit breakers by name
_CIRCUIT_BREAKERS: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str = "llm_service") -> CircuitBreaker:
    """Return a shared named circuit breaker instance."""
    if name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[name] = CircuitBreaker(name=name)
    return _CIRCUIT_BREAKERS[name]
