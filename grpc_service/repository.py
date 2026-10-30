"""Минимальный интерфейс репозитория для учебного проекта.

Реализация в памяти нужна только для первого запуска. Замените ее адаптером
к схеме PostgreSQL, созданной в лабораторных работах № 3–4. Границы транзакции
должны оставаться в методе команды. Не создавайте отдельную базу данных только ради gRPC.
"""

from dataclasses import dataclass, replace
from threading import Lock


@dataclass(frozen=True, slots=True)
class Entity:
    id: str
    name: str
    status: str


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items = {
            "demo-1": Entity(id="demo-1", name="Demo entity", status="draft")
        }

    def get(self, entity_id: str) -> Entity | None:
        return self._items.get(entity_id)

    def change_state(self, entity_id: str, command: str) -> Entity | None:
        """Атомарно выполнить одну команду, изменяющую состояние.

        TODO: проверьте допустимость перехода для своего варианта
        и реализуйте операцию в виде одной транзакции PostgreSQL.
        """
        with self._lock:
            current = self._items.get(entity_id)
            if current is None:
                return None
            updated = replace(current, status=command.strip().lower())
            self._items[entity_id] = updated
            return updated


repository = InMemoryRepository()

