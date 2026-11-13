"""Минимальная инструментация FastAPI для учебной работы.

Перед копированием согласуйте ее с уже существующим middleware и логированием.
Не создавайте два middleware, которые измеряют один и тот же HTTP-запрос.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


REQUESTS = Counter(
    "http_requests_total",
    "Количество завершенных HTTP-запросов",
    ("method", "route", "status"),
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "Длительность HTTP-запроса в секундах",
    ("method", "route"),
    buckets=(0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 2.0, 5.0),
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Количество HTTP-запросов в обработке",
)


def _json_logger() -> logging.Logger:
    logger = logging.getLogger("application.observability")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = _json_logger()


def configure_observability(app: FastAPI, service_name: str) -> None:
    """Добавить к FastAPI метрики, correlation ID и структурированный лог."""

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started = time.perf_counter()
        status_code = 500
        IN_PROGRESS.inc()

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            route_object = request.scope.get("route")
            route = getattr(route_object, "path", "unmatched")

            # Шаблон маршрута имеет ограниченную кардинальность, в отличие от сырого URL.
            REQUESTS.labels(request.method, route, str(status_code)).inc()
            LATENCY.labels(request.method, route).observe(elapsed)
            IN_PROGRESS.dec()

            LOGGER.info(
                json.dumps(
                    {
                        "timestamp": time.time(),
                        "level": "error" if status_code >= 500 else "info",
                        "service": service_name,
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "route": route,
                        "status_code": status_code,
                        "elapsed_ms": round(elapsed * 1000, 2),
                        "pod": os.getenv("HOSTNAME", "local"),
                    },
                    ensure_ascii=False,
                )
            )

