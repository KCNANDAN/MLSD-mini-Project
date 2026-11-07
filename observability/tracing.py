
import functools
import time

from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config.settings import get_settings
from config.logging_config import get_logger
from observability.metrics import record_agent_execution


settings = get_settings()
logger = get_logger(__name__)

_tracing_configured = False
_tracer_provider: TracerProvider | None = None


def configure_tracing() -> None:
    """
    Configure OpenTelemetry with an OTLP exporter.

    Initializes the SDK provider only once and avoids replacing
    a provider configured elsewhere in the application.
    """

    global _tracing_configured
    global _tracer_provider

    if _tracing_configured:
        return

    current_provider = trace.get_tracer_provider()

    # Do not replace an already configured provider.
    if current_provider.__class__.__name__ != "ProxyTracerProvider":
        logger.info("tracing_provider_already_configured")
        _tracing_configured = True
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )

        provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )

        trace.set_tracer_provider(provider)

        _tracer_provider = provider
        _tracing_configured = True

        logger.info(
            "tracing_configured",
            service_name=settings.otel_service_name,
            endpoint=settings.otel_exporter_otlp_endpoint,
        )

    except Exception:
        provider.shutdown()
        logger.exception("tracing_configuration_failed")
        raise


def get_tracer(name: str = "academic-petition-triage"):
    """Return a named OpenTelemetry tracer."""

    return trace.get_tracer(name)


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """
    Create an OpenTelemetry span.

    Records attributes and automatically records exceptions
    and marks the span as failed when an exception occurs.
    """

    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:

        if attributes:
            for key, value in attributes.items():

                if value is None:
                    continue

                if isinstance(value, (str, bool, int, float)):
                    span.set_attribute(key, value)

                else:
                    span.set_attribute(key, str(value))

        try:
            yield span

        except Exception as exc:
            span.record_exception(exc)

            span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    str(exc),
                )
            )

            raise


def shutdown_tracing() -> None:
    """
    Flush and shut down the provider created by this module.

    Does not shut down providers owned by other application components.
    """

    global _tracer_provider

    if _tracer_provider is None:
        return

    try:
        _tracer_provider.force_flush()
        _tracer_provider.shutdown()

        logger.info("tracing_shutdown")

    except Exception:
        logger.exception("tracing_shutdown_failed")

    finally:
        _tracer_provider = None


def observe_agent(agent_name: str):
    """
    Decorator for recording async agent execution metrics and traces.

    Records:
    - Execution status
    - Execution duration
    - Agent steps
    - Tool calls
    """

    def decorator(function):

        @functools.wraps(function)
        async def wrapper(*args, **kwargs):

            start_time = time.perf_counter()
            status = "success"

            with trace_span(
                f"agent.{agent_name}",
                {
                    "agent.name": agent_name,
                },
            ) as span:

                try:
                    result = await function(*args, **kwargs)

                    if isinstance(result, dict):

                        agent_steps = result.get("agent_steps", 0)
                        tool_calls = result.get("tool_calls", 0)

                        if isinstance(agent_steps, (int, float)):
                            span.set_attribute(
                                "agent.agent_steps",
                                agent_steps,
                            )

                        if isinstance(tool_calls, (int, float)):
                            span.set_attribute(
                                "agent.tool_calls",
                                tool_calls,
                            )

                    return result

                except Exception:
                    status = "failed"
                    raise

                finally:
                    duration = time.perf_counter() - start_time

                    record_agent_execution(
                        agent_name=agent_name,
                        status=status,
                        duration=duration,
                    )

                    span.set_attribute(
                        "agent.duration_seconds",
                        duration,
                    )

        return wrapper

    return decorator
