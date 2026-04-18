"""Observability bootstrap — Sentry + OpenTelemetry for all Axis services.

Call ``init_observability(app, settings)`` once from each service's
``main.py``, after ``configure_logging()``. It's safe to call when the
DSN / OTLP endpoint are empty — everything degrades to no-ops.

Sentry captures unhandled exceptions and performance transactions.
OpenTelemetry instruments FastAPI with `X-Request-ID` propagation into
the trace context so distributed traces in Jaeger/Tempo carry the same
ID the user sees in the response header.
"""
from __future__ import annotations

import os
from typing import Any

from axis_common.logging import get_logger

logger = get_logger(__name__)


def init_observability(
    app: Any,
    *,
    service_name: str,
    sentry_dsn: str = "",
    environment: str = "dev",
    sentry_traces_sample_rate: float = 0.2,
    otel_endpoint: str = "",
) -> None:
    """Wire Sentry + OpenTelemetry into a FastAPI app.

    - ``sentry_dsn``: if empty, Sentry is skipped.
    - ``otel_endpoint``: OTLP gRPC endpoint (e.g. ``http://localhost:4317``).
      If empty, OTel is configured with a no-op exporter so spans still
      appear in structlog but don't ship anywhere.
    """
    _init_sentry(
        dsn=sentry_dsn,
        service_name=service_name,
        environment=environment,
        traces_sample_rate=sentry_traces_sample_rate,
    )
    _init_otel(
        app=app,
        service_name=service_name,
        endpoint=otel_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
    )


def _init_sentry(
    *,
    dsn: str,
    service_name: str,
    environment: str,
    traces_sample_rate: float,
) -> None:
    if not dsn:
        logger.info("sentry_skipped_no_dsn")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            release=f"{service_name}@0.1.0",
        )
        logger.info("sentry_initialized", dsn=dsn[:20] + "…")
    except Exception as e:  # noqa: BLE001
        logger.warning("sentry_init_failed", error=str(e))


def _init_otel(*, app: Any, service_name: str, endpoint: str) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("otel_otlp_exporter_configured", endpoint=endpoint)
            except ImportError:
                logger.warning("otel_otlp_exporter_not_available_using_console")
                provider.add_span_processor(
                    BatchSpanProcessor(ConsoleSpanExporter())
                )
        else:
            logger.info("otel_no_endpoint_console_only")

        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel_initialized", service=service_name)
    except Exception as e:  # noqa: BLE001
        logger.warning("otel_init_failed", error=str(e))
