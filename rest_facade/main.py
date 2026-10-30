import logging
import os
import time
import uuid

import grpc
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from rest_facade.grpc_client import change_state, get_entity


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("rest-facade")

app = FastAPI(title="Lab 5 REST facade", version="1.0.0")

STATUS_TO_HTTP = {
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.FAILED_PRECONDITION: 409,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.UNAVAILABLE: 503,
}


class StateCommand(BaseModel):
    command: str = Field(min_length=1, max_length=64)


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _as_dict(reply) -> dict[str, str]:
    return {
        "id": reply.id,
        "name": reply.name,
        "status": reply.status,
        "instance": reply.instance,
    }


def _raise_http(exc: grpc.RpcError, request_id: str) -> None:
    raise HTTPException(
        status_code=STATUS_TO_HTTP.get(exc.code(), 502),
        detail={
            "grpc_code": exc.code().name,
            "message": exc.details(),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    ) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/entities/{entity_id}")
def read_entity(entity_id: str, request: Request, response: Response):
    request_id = _request_id(request)
    started = time.perf_counter()
    try:
        reply = get_entity(entity_id, request_id)
        response.headers["X-Request-ID"] = request_id
        return _as_dict(reply)
    except grpc.RpcError as exc:
        _raise_http(exc, request_id)
    finally:
        LOGGER.info(
            "request_id=%s route=read_entity elapsed_ms=%.1f",
            request_id,
            (time.perf_counter() - started) * 1000,
        )


@app.post("/api/v1/entities/{entity_id}/state")
def update_entity_state(
    entity_id: str, body: StateCommand, request: Request, response: Response
):
    request_id = _request_id(request)
    started = time.perf_counter()
    try:
        reply = change_state(entity_id, body.command, request_id)
        response.headers["X-Request-ID"] = request_id
        return _as_dict(reply)
    except grpc.RpcError as exc:
        _raise_http(exc, request_id)
    finally:
        LOGGER.info(
            "request_id=%s route=update_entity_state elapsed_ms=%.1f",
            request_id,
            (time.perf_counter() - started) * 1000,
        )

