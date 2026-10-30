from grpc_service.repository import InMemoryRepository


def test_read_existing_entity():
    repository = InMemoryRepository()

    item = repository.get("demo-1")

    assert item is not None
    assert item.status == "draft"


def test_change_state_updates_existing_entity():
    repository = InMemoryRepository()

    updated = repository.change_state("demo-1", "published")

    assert updated is not None
    assert updated.status == "published"
    assert repository.get("demo-1") == updated


def test_change_state_does_not_create_missing_entity():
    repository = InMemoryRepository()

    assert repository.change_state("missing", "published") is None

