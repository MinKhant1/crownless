from dataclasses import dataclass, field

from game.relics.events import RELIC_ACQUIRED, GameEvent, Dispatcher
from game.relics.relic_context import RelicContext
from game.relics.relic_data import relic_by_id
from game.relics.relic_registry import build_effect
from game.traits import register_trait_handlers

import game.relics.effects as relic_effects

_ = relic_effects


@dataclass
class OwnedRelic:
    relic_id: str
    instance_id: str
    acquisition_order: int
    state: dict = field(default_factory=dict)


class RelicManager:
    def __init__(self, run) -> None:
        self.run = run
        self.owned: list[OwnedRelic] = []
        self.dispatcher = Dispatcher()
        self.context = RelicContext(run)
        self._effects: dict[str, object] = {}
        self._next_instance = 1
        self._order = 1
        register_trait_handlers(self.dispatcher, self.context)

    def owned_ids(self) -> set[str]:
        return {item.relic_id for item in self.owned}

    def owns(self, relic_id: str) -> bool:
        return relic_id in self.owned_ids()

    def find(self, relic_id: str) -> OwnedRelic | None:
        for item in self.owned:
            if item.relic_id == relic_id:
                return item
        return None

    def effect_for(self, relic_id: str):
        owned = self.find(relic_id)
        if owned is None:
            return None
        return self._effects.get(owned.instance_id)

    def acquire(self, relic_id: str) -> OwnedRelic | None:
        if self.owns(relic_id):
            return None
        definition = relic_by_id(relic_id)
        if definition is None:
            return None
        owned = OwnedRelic(
            relic_id=relic_id,
            instance_id=f"relic_{self._next_instance:03d}",
            acquisition_order=self._order,
        )
        effect = build_effect(definition, owned)
        if effect is None:
            return None
        self._next_instance += 1
        self._order += 1
        self.owned.append(owned)
        self._effects[owned.instance_id] = effect
        effect.on_acquired(self.context)
        effect.register(self.dispatcher, self.context)
        self.dispatcher.publish(GameEvent(RELIC_ACQUIRED, {"relic_id": relic_id, "instance_id": owned.instance_id}))
        return owned
