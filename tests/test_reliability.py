import asyncio
import time
import pytest

from services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed():
    breaker = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_seconds=1.0)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0
    assert breaker.allow_request() is True


@pytest.mark.asyncio
async def test_circuit_breaker_successful_call():
    breaker = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_seconds=1.0)

    async def mock_success():
        return "success"

    result = await breaker.call_async(mock_success)
    assert result == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_retries_and_trips_to_open():
    breaker = CircuitBreaker(
        name="test_cb_retries",
        failure_threshold=2,
        recovery_seconds=0.5,
        max_retries=1,
        backoff_seconds=0.01,
    )

    call_count = 0

    async def mock_failing():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Downstream network failure")

    # First call: attempts = 2 (initial + 1 retry), then raises ConnectionError, recording 1 failure
    with pytest.raises(ConnectionError):
        await breaker.call_async(mock_failing)
    assert breaker.consecutive_failures == 1
    assert breaker.state == CircuitState.CLOSED

    # Second call: attempts = 2, reaches failure_threshold (2), trips circuit breaker to OPEN
    with pytest.raises(ConnectionError):
        await breaker.call_async(mock_failing)
    assert breaker.consecutive_failures == 2
    assert breaker.state == CircuitState.OPEN

    # While OPEN: calls fast-fail immediately with CircuitBreakerOpenError without invoking target
    calls_before = call_count
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call_async(mock_failing)
    assert call_count == calls_before  # Downstream was NOT called


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_via_half_open():
    recovery_delay = 0.1
    breaker = CircuitBreaker(
        name="test_cb_recovery",
        failure_threshold=1,
        recovery_seconds=recovery_delay,
        max_retries=0,
    )

    async def mock_fail():
        raise RuntimeError("Service failure")

    with pytest.raises(RuntimeError):
        await breaker.call_async(mock_fail)

    assert breaker.state == CircuitState.OPEN

    # Wait for recovery window to pass
    await asyncio.sleep(recovery_delay + 0.05)

    # State transitions to HALF_OPEN
    assert breaker.state == CircuitState.HALF_OPEN

    # Successful call in HALF_OPEN recovers circuit to CLOSED
    async def mock_healthy():
        return "recovered"

    result = await breaker.call_async(mock_healthy)
    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_sync_circuit_breaker():
    breaker = CircuitBreaker(
        name="test_cb_sync",
        failure_threshold=2,
        recovery_seconds=1.0,
        max_retries=0,
    )

    def failing_action():
        raise ValueError("Sync error")

    with pytest.raises(ValueError):
        breaker.call_sync(failing_action)
    assert breaker.state == CircuitState.CLOSED

    with pytest.raises(ValueError):
        breaker.call_sync(failing_action)
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenError):
        breaker.call_sync(failing_action)
