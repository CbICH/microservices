import json
import os

import grpc

import domain_pb2 as pb2
import domain_pb2_grpc as pb2_grpc


TARGET = os.getenv("GRPC_TARGET", "127.0.0.1:50051")
DEADLINE_SECONDS = float(os.getenv("GRPC_DEADLINE_SECONDS", "0.35"))

# Повтор намеренно разрешен только для метода чтения без побочных эффектов.
GRPC_SERVICE_CONFIG = {
    "methodConfig": [
        {
            "name": [
                {"service": "domain.v1.DomainService", "method": "GetEntity"}
            ],
            "retryPolicy": {
                "maxAttempts": 3,
                "initialBackoff": "0.1s",
                "maxBackoff": "0.4s",
                "backoffMultiplier": 2,
                "retryableStatusCodes": ["UNAVAILABLE"],
            },
        }
    ]
}

channel = grpc.insecure_channel(
    TARGET,
    options=(
        ("grpc.enable_retries", 1),
        ("grpc.service_config", json.dumps(GRPC_SERVICE_CONFIG)),
    ),
)
stub = pb2_grpc.DomainServiceStub(channel)


def get_entity(entity_id: str, request_id: str) -> pb2.EntityReply:
    return stub.GetEntity(
        pb2.GetEntityRequest(id=entity_id),
        timeout=DEADLINE_SECONDS,
        metadata=(("x-request-id", request_id),),
    )


def change_state(entity_id: str, command: str, request_id: str) -> pb2.EntityReply:
    # Не добавляйте автоматический повтор для RPC, изменяющего состояние.
    return stub.ChangeState(
        pb2.ChangeStateRequest(id=entity_id, command=command),
        timeout=DEADLINE_SECONDS,
        metadata=(("x-request-id", request_id),),
    )

