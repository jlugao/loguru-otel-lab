from fastapi import FastAPI, status
from log_helpers import config_loguru_for_uvicorn, setup_logging
from loguru import logger


# --- OpenTelemetry ---
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

import httpx

app = FastAPI(title="Loguru OTEL Lab API")

trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: 'loguru-otel-lab-app-1'}))
)
otlp_exporter = OTLPSpanExporter(endpoint='http://grafana:4318/v1/traces')
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))  # type: ignore


HTTPXClientInstrumentor().instrument()


@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup"""
    logger.info("Initializing application")


@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Log from main")
    return {"message": "Hello World"}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health():
    """Health check endpoint that verifies database connection"""
    
    return {"health": "ok"}

@app.get("/proxy", status_code=status.HTTP_200_OK)
async def proxy():
    response = httpx.get("https://api.chucknorris.io/jokes/random")
    return response.json()

setup_logging()

FastAPIInstrumentor().instrument_app(app, excluded_urls="health,metrics,favicon.ico")

def start():
    """Start the application"""
    import uvicorn
    config_loguru_for_uvicorn()
    uvicorn.run(app, host="0.0.0.0", port=8000,log_config=None, log_level=None)


if __name__ == "__main__":
    start()