from game.relics.effects.base_effect import RelicEffect
from game.relics.events import BATTLE_END, BATTLE_START, CAPTURE_RESOLVED, PIECE_REMOVED, visual_trigger
from game.relics.relic_registry import register_effect


class GoldRewardEffect(RelicEffect):
    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=12)
        dispatcher.subscribe(BATTLE_END, self._end, priority=30)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._capture, priority=10)

    def _reset(self, _event) -> None:
        self.owned.state["battle_gold"] = 0

    def _capture(self, _event) -> None:
        pass

    def _end(self, _event) -> None:
        pass

    def _pay(self, amount: int, immediate: bool = True) -> None:
        if amount <= 0:
            return
        self.context.run.gold += amount
        self.owned.state["battle_gold"] = self.owned.state.get("battle_gold", 0) + amount
        if immediate:
            self.context.run.gold_earned += amount
        visual_trigger(self.context.dispatcher, self.owned.instance_id, f"{self.definition.name} +{amount} Gold")


@register_effect("war_tax")
class WarTaxEffect(GoldRewardEffect):
    def _end(self, event) -> None:
        board = self.context.board
        if board is not None:
            self._pay(sum(p.color == "white" for p in board.pieces) // 2, immediate=event.payload.get("outcome") != "victory")


@register_effect("spoils_of_war")
class SpoilsOfWarEffect(GoldRewardEffect):
    def _capture(self, event) -> None:
        p = event.payload
        if (p.get("capturing_color") == "white" and p.get("captured_piece_color") == "black"
                and p.get("captured_piece_type") in ("rook", "queen")):
            self._pay(2)


@register_effect("golden_vengeance")
class GoldenVengeanceEffect(GoldRewardEffect):
    def _reset(self, event) -> None:
        super()._reset(event)
        self.owned.state["marked"] = set()
        if self.context.board is not None:
            self.context.board.vengeance_marks.clear()

    def _capture(self, event) -> None:
        p = event.payload
        marked = self.owned.state.setdefault("marked", set())
        board = self.context.board
        if (p.get("captured_piece_color") == "white" and p.get("captured_trait") == "golden"
                and p.get("capturing_color") == "black"):
            killer = p["capturing_piece_id"]
            marked.add(killer)
            if board is not None:
                board.vengeance_marks.add(killer)
            visual_trigger(self.context.dispatcher, self.owned.instance_id, "Golden Vengeance: enemy marked")
        if (p.get("capturing_color") == "white" and p.get("captured_piece_color") == "black"
                and p.get("captured_piece_id") in marked):
            marked.remove(p["captured_piece_id"])
            if board is not None:
                board.vengeance_marks.discard(p["captured_piece_id"])
            self._pay(3)

    def _end(self, _event) -> None:
        self.owned.state["marked"] = set()
        if self.context.board is not None:
            self.context.board.vengeance_marks.clear()


@register_effect("veterans_banner")
class VeteransBannerEffect(RelicEffect):
    def on_acquired(self, context) -> None:
        self.owned.state.update(progress=0, completed=False, lost_piece=False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=12)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._capture, priority=50)
        dispatcher.subscribe(PIECE_REMOVED, self._removed, priority=50)
        dispatcher.subscribe(BATTLE_END, self._end, priority=30)

    def _reset(self, _event) -> None:
        self.owned.state["lost_piece"] = False
        board = self.context.board
        self._allies = {p.id for p in board.pieces if p.color == "white"} if board else set()

    def _capture(self, event) -> None:
        if event.payload.get("captured_piece_color") == "white":
            self.owned.state["lost_piece"] = True
        if event.payload.get("capturing_color") == "white" and event.payload.get("captured_trait") == "explosive":
            self.owned.state["lost_piece"] = True
        board = self.context.board
        if board is not None and not getattr(self, "_allies", set()).issubset({p.id for p in board.pieces if p.color == "white"}):
            self.owned.state["lost_piece"] = True

    def _removed(self, event) -> None:
        if event.payload.get("color") == "white":
            self.owned.state["lost_piece"] = True

    def _end(self, event) -> None:
        self._capture(event)
        state = self.owned.state
        if state["completed"] or state["lost_piece"] or event.payload.get("outcome") != "victory":
            return
        state["progress"] += 1
        if state["progress"] >= 5:
            state["completed"] = True
            self.context.run.army.increase_capacity()
        visual_trigger(self.context.dispatcher, self.owned.instance_id, f"Veteran's Banner {state['progress']}/5")
