import logging
import os
import time
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

import domain_pb2 as pb2
import domain_pb2_grpc as pb2_grpc

from grpc_service.repository import Entity, repository


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("domain-grpc")


def _metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return dict(context.invocation_metadata())


def _delay_for_training() -> None:
    delay_ms = int(os.getenv("TEST_DELAY_MS", "0"))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)


def _reply(entity: Entity) -> pb2.EntityReply:
    return pb2.EntityReply(
        id=entity.id,
        name=entity.name,
        status=entity.status,
        instance=os.getenv("HOSTNAME", "local"),
    )


class DomainService(pb2_grpc.DomainServiceServicer):
    def GetEntity(self, request, context):  # noqa: N802 — имя метода задано protobuf API
        started = time.perf_counter()
        metadata = _metadata(context)
        request_id = metadata.get("x-request-id", "missing")
        attempt = int(metadata.get("grpc-previous-rpc-attempts", "0")) + 1
        code = grpc.StatusCode.OK
        try:
            _delay_for_training()
            item = repository.get(request.id)
            if item is None:
                code = grpc.StatusCode.NOT_FOUND
                context.abort(code, "entity not found")
            return _reply(item)
        finally:
            LOGGER.info(
                "request_id=%s rpc_method=GetEntity attempt=%s grpc_code=%s elapsed_ms=%.1f pod=%s",
                request_id,
                attempt,
                code.name,
                (time.perf_counter() - started) * 1000,
                os.getenv("HOSTNAME", "local"),
            )

    def ChangeState(self, request, context):  # noqa: N802 — имя метода задано protobuf API
        started = time.perf_counter()
        metadata = _metadata(context)
        request_id = metadata.get("x-request-id", "missing")
        code = grpc.StatusCode.OK
        try:
            if not request.command.strip():
                code = grpc.StatusCode.INVALID_ARGUMENT
                context.abort(code, "command is required")
            item = repository.change_state(request.id, request.command)
            if item is None:
                code = grpc.StatusCode.NOT_FOUND
                context.abort(code, "entity not found")
            return _reply(item)
        finally:
            LOGGER.info(
                "request_id=%s rpc_method=ChangeState attempt=1 grpc_code=%s elapsed_ms=%.1f pod=%s",
                request_id,
                code.name,
                (time.perf_counter() - started) * 1000,
                os.getenv("HOSTNAME", "local"),
            )


def create_server() -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_DomainServiceServicer_to_server(DomainService(), server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    service_name = pb2.DESCRIPTOR.services_by_name["DomainService"].full_name
    health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    reflection.enable_server_reflection(
        (service_name, health.SERVICE_NAME, reflection.SERVICE_NAME), server
    )
    port = os.getenv("GRPC_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    return server


def main() -> None:
    server = create_server()
    server.start()
    LOGGER.info("gRPC server started port=%s", os.getenv("GRPC_PORT", "50051"))
    server.wait_for_termination()


if __name__ == "__main__":
    main()

