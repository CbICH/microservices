import sys
from pathlib import Path


GENERATED = Path(__file__).parents[1] / "grpc_service" / "generated"
sys.path.insert(0, str(GENERATED))

import domain_pb2  # noqa: E402 — путь к сгенерированному модулю добавлен выше


def test_contract_contains_read_and_command_rpc():
    service = domain_pb2.DESCRIPTOR.services_by_name["DomainService"]

    assert set(service.methods_by_name) == {"GetEntity", "ChangeState"}


def test_entity_field_numbers_are_stable():
    fields = domain_pb2.EntityReply.DESCRIPTOR.fields_by_name

    assert fields["id"].number == 1
    assert fields["name"].number == 2
    assert fields["status"].number == 3
    assert fields["instance"].number == 4

