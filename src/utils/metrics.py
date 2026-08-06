from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import re


# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "endpoint"]
)


def normalize_path(path: str) -> str:
    """
    Normalize dynamic path values to avoid high-cardinality metrics.
    """

    # Replace UUIDs with {id}
    path = re.sub(
        r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "/{id}",
        path
    )

    # Replace numeric IDs with {id}
    path = re.sub(r"/\d+", "/{id}", path)

    return path


class PrometheusMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        method = request.method
        endpoint = normalize_path(request.url.path)

        try:
            response = await call_next(request)
            status_code = str(response.status_code)

        except Exception:
            duration = time.time() - start_time

            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status="500"
            ).inc()

            raise

        duration = time.time() - start_time

        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()

        return response


def setup_metrics(app: FastAPI):
    """
    Setup Prometheus metrics middleware and endpoint.
    """

    app.add_middleware(PrometheusMiddleware)

    @app.get("/TrhBVe_m5gg2002_E5VVqS", include_in_schema=False)
    def metrics():
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )