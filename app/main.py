"""Reference-data API with temporary shared bearer-token authentication."""
import json
import logging
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, make_asgi_app

logger = logging.getLogger("reference-api")
logging.basicConfig(level=logging.INFO, format="%(message)s")
REQUESTS = Counter("reference_api_requests_total", "Completed requests", ["route", "method", "status"])
LATENCY = Histogram("reference_api_duration_seconds", "Request latency", ["route", "method"])
bearer = HTTPBearer(auto_error=False)
REFERENCE = {"SGD": {"code": "SGD", "name": "Singapore Dollar"},
             "USD": {"code": "USD", "name": "US Dollar"}}


@asynccontextmanager
async def lifespan(app):
    token = os.getenv("API_TOKEN", "")
    if not token or any(character.isspace() for character in token):
        raise RuntimeError("Set API_TOKEN to a nonempty token without whitespace")
    app.state.api_token = token.encode("utf-8")
    try:
        yield
    finally:
        app.state.api_token = b""


app = FastAPI(title="Hybrid Reference API", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


async def require_api_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(credentials.credentials.encode("utf-8"), app.state.api_token):
        raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})


@app.middleware("http")
async def telemetry(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else uuid.uuid4().hex
    start = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        if request.url.path not in ("/livez", "/readyz", "/metrics", "/metrics/"):
            elapsed = time.monotonic() - start
            method = request.method if request.method in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"} else "OTHER"
            REQUESTS.labels(route, method, str(status)).inc()
            LATENCY.labels(route, method).observe(elapsed)
            context = trace.get_current_span().get_span_context()
            logger.info(json.dumps({"service": "reference-api", "request_id": request_id,
                                    "trace_id": format(context.trace_id, "032x"),
                                    "route": route, "method": method, "status": status,
                                    "duration_ms": round(elapsed * 1000, 2)}))


@app.get("/livez")
async def live():
    return {"status": "ok"}


@app.get("/readyz")
async def ready():
    # Startup validates the configured token; readiness represents this process.
    return {"status": "ready"}


@app.get("/v1/reference/{code}")
async def reference(code: str, authenticated: None = Depends(require_api_token)):
    item = REFERENCE.get(code.upper())
    if item is None:
        raise HTTPException(404, "Reference code not found")
    return item


app.mount("/metrics", make_asgi_app())
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    provider = TracerProvider(resource=Resource.create({"service.name": "reference-api"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app, excluded_urls="livez,readyz,metrics")
