from collections.abc import Callable
from dataclasses import dataclass


BATTLE_START = "battle_start"
PIECE_MOVED = "piece_moved"
BEFORE_CAPTURE = "before_capture"
CAPTURE_RESOLVED = "capture_resolved"
PIECE_SPAWNED = "piece_spawned"
PIECE_REMOVED = "piece_removed"
BATTLE_END = "battle_end"
SHOP_ENTER = "shop_enter"
RELIC_ACQUIRED = "relic_acquired"
RELIC_ACTIVATED = "relic_activated"
RELIC_VISUAL_TRIGGER = "relic_visual_trigger"


def visual_trigger(dispatcher, instance_id: str, message: str = "") -> None:
    dispatcher.publish(
        GameEvent(
            RELIC_VISUAL_TRIGGER,
            {"type": "RELIC_VISUAL_TRIGGER", "relic_instance_id": instance_id, "message": message},
        )
    )


@dataclass(frozen=True)
class GameEvent:
    kind: str
    payload: dict


class Dispatcher:
    def __init__(self) -> None:
        self._handlers: list[tuple[int, int, str, Callable]] = []
        self._next = 0
        self._depth = 0
        self.limit = 8

    def subscribe(self, kind: str, callback: Callable, priority: int = 100) -> None:
        self._next += 1
        self._handlers.append((priority, self._next, kind, callback))

    def publish(self, event: GameEvent) -> None:
        if self._depth >= self.limit:
            return
        self._depth += 1
        try:
            matched = [item for item in self._handlers if item[2] == event.kind]
            matched.sort(key=lambda item: (item[0], item[1]))
            for _priority, _order, _kind, callback in matched:
                callback(event)
        finally:
            self._depth -= 1

    def count(self, kind: str) -> int:
        return sum(1 for item in self._handlers if item[2] == kind)
