import re
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

_UUID_PATTERN = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)
_INTEGER_PATTERN = re.compile(r"/\d+(?=/|$)")
_HEX_ID_PATTERN = re.compile(r"/[0-9a-fA-F]{24,64}(?=/|$)")


def normalize_path(path: str) -> str:
    """Normalize dynamic path values to avoid metric cardinality growth."""

    normalized_path = str(path or "/").split("?", 1)[0]
    normalized_path = _UUID_PATTERN.sub("/{uuid}", normalized_path)
    normalized_path = _HEX_ID_PATTERN.sub("/{id}", normalized_path)
    normalized_path = _INTEGER_PATTERN.sub("/{id}", normalized_path)
    return normalized_path or "/"


def get_metric_endpoint(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return str(route_path)
    return normalize_path(request.url.path)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            endpoint = get_metric_endpoint(request)
            method = request.method
            duration = time.perf_counter() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)


def setup_metrics(app: FastAPI) -> None:
    """Install Prometheus middleware and expose the /metrics endpoint."""

    app.add_middleware(PrometheusMiddleware)

    existing_paths = {
        getattr(route, "path", None)
        for route in app.routes
    }
    if "/metrics" in existing_paths:
        return

    @app.get(
        "/metrics",
        include_in_schema=False,
    )
    async def metrics_endpoint() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
