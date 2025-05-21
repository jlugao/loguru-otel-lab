import logging
from loguru import logger
import sys

from opentelemetry.trace import (
    INVALID_SPAN,
    INVALID_SPAN_CONTEXT,
    get_current_span,
    get_tracer_provider,
)


def instrument_loguru():
    provider = get_tracer_provider()
    service_name = None

    def add_trace_context(record):
        record["extra"]["otelSpanID"] = "0"
        record["extra"]["otelTraceID"] = "0"
        record["extra"]["otelTraceSampled"] = False

        nonlocal service_name
        if service_name is None:
            resource = getattr(provider, "resource", None)
            if resource:
                service_name = resource.attributes.get("service.name") or ""
            else:
                service_name = ""

        record["extra"]["otelServiceName"] = service_name

        span = get_current_span()
        if span != INVALID_SPAN:
            ctx = span.get_span_context()
            if ctx != INVALID_SPAN_CONTEXT:
                record["extra"]["otelSpanID"] = format(ctx.span_id, "016x")
                record["extra"]["otelTraceID"] = format(ctx.trace_id, "032x")
                record["extra"]["otelTraceSampled"] = ctx.trace_flags.sampled

    logger.configure(patcher=add_trace_context)

def setup_logging():
    """
    setup json logging to stdout
    """
    instrument_loguru()
    logger.remove()
    logger.add(
        sink="/dev/stdout",
        level="INFO",
        format="{message}",
        serialize=True,
    )

def config_loguru_for_uvicorn():
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller to get correct stack depth
            frame, depth = logging.currentframe(), 2
            while frame.f_back and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            message = record.getMessage()
            if "favicon.ico" in message:
                return
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, message
            )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
    loggers = (
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "fastapi",
    "asyncio",
    "starlette",
    )

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True