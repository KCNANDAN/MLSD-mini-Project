
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    multiprocess,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# --------------------------------------------------
# Petition processing metrics
# --------------------------------------------------

PETITIONS_TOTAL = Counter(
    "petitions_total",
    "Total number of petitions processed",
    ["status"],
)

PETITION_PROCESSING_DURATION = Histogram(
    "petition_processing_duration_seconds",
    "Total petition processing duration",
    buckets=(1, 2, 5, 10, 20, 30, 60, 90, 120),
)


# --------------------------------------------------
# Agent execution metrics
# --------------------------------------------------

AGENT_EXECUTIONS_TOTAL = Counter(
    "agent_executions_total",
    "Total agent executions",
    ["agent_name", "status"],
)

AGENT_EXECUTION_DURATION = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution duration",
    ["agent_name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "agent_tool_calls_total",
    "Total tool calls made by agents",
    ["agent_name", "tool_name", "status"],
)

AGENT_RETRIES_TOTAL = Counter(
    "agent_retries_total",
    "Total agent retries",
    ["agent_name"],
)


# --------------------------------------------------
# Worker metrics
# --------------------------------------------------

ACTIVE_WORKERS = Gauge(
    "active_workers",
    "Number of active petition workers",
    multiprocess_mode="livesum",
)


# --------------------------------------------------
# LLM usage metrics
# --------------------------------------------------

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "token_type"],
)

LLM_ESTIMATED_COST_USD = Counter(
    "llm_estimated_cost_usd_total",
    "Estimated cumulative LLM cost in USD",
    ["provider", "model"],
)


# --------------------------------------------------
# Metrics helpers
# --------------------------------------------------

def record_petition(status: str, duration: float) -> None:
    """Record petition processing outcome and duration."""
    PETITIONS_TOTAL.labels(status=status).inc()
    PETITION_PROCESSING_DURATION.observe(max(duration, 0))


def record_agent_execution(
    agent_name: str,
    status: str,
    duration: float,
) -> None:
    """Record an agent execution."""
    AGENT_EXECUTIONS_TOTAL.labels(
        agent_name=agent_name,
        status=status,
    ).inc()

    AGENT_EXECUTION_DURATION.labels(
        agent_name=agent_name,
    ).observe(max(duration, 0))


def record_tool_call(
    agent_name: str,
    tool_name: str,
    status: str,
) -> None:
    """Record an agent tool invocation."""
    AGENT_TOOL_CALLS_TOTAL.labels(
        agent_name=agent_name,
        tool_name=tool_name,
        status=status,
    ).inc()


def record_agent_retry(agent_name: str) -> None:
    """Record an agent retry."""
    AGENT_RETRIES_TOTAL.labels(
        agent_name=agent_name,
    ).inc()


def record_llm_usage(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    status: str = "success",
) -> None:
    """Record LLM request, token and estimated cost metrics."""

    LLM_REQUESTS_TOTAL.labels(
        provider=provider,
        model=model,
        status=status,
    ).inc()

    if prompt_tokens > 0:
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            token_type="prompt",
        ).inc(prompt_tokens)

    if completion_tokens > 0:
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            token_type="completion",
        ).inc(completion_tokens)

    if estimated_cost_usd > 0:
        LLM_ESTIMATED_COST_USD.labels(
            provider=provider,
            model=model,
        ).inc(estimated_cost_usd)


# --------------------------------------------------
# Multiprocess metrics exporter
# --------------------------------------------------

def get_metrics() -> tuple[bytes, str]:
    """Aggregate metrics from all application processes."""

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)

    return generate_latest(registry), CONTENT_TYPE_LATEST
