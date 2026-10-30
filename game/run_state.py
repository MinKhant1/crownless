import random

from config.settings import MAX_LEVEL, STARTING_GOLD, VICTORY_GOLD
from game.army_manager import ArmyManager
from game.battle_rules import BattleRules
from game.battle_session import BattleSession
from game.deployment_manager import DeploymentManager
from game.level_manager import spawn_enemies
from game.piece import Piece
from game.relics.events import BATTLE_END, BATTLE_START, SHOP_ENTER, GameEvent
from game.relics.relic_data import shop_relic_ids
from game.relics.relic_manager import RelicManager
from game.shop_manager import ShopManager
from game.traits import TraitManager


class RunState:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.gold = STARTING_GOLD
        self.level = 1
        self.army = ArmyManager()
        self.army.add_starters()
        self.traits = TraitManager(self)
        self.relics = RelicManager(self)
        self.golden_reward = 0
        self.shop = ShopManager(self.rng, shop_relic_ids())
        self.deployment = DeploymentManager()
        self.enemies: list[Piece] = []
        self.battle: BattleSession | None = None
        self.phase = "preview"
        self.notice = ""
        self.selected_piece_id: int | None = None
        self.prepare_level()

    @classmethod
    def new(cls, seed: int | None = None) -> "RunState":
        if seed is None:
            seed = random.SystemRandom().randrange(1, 1_000_000_000)
        return cls(seed)

    def prepare_level(self) -> None:
        self.enemies = spawn_enemies(self.level)
        self.deployment = DeploymentManager()
        self.battle = None
        self.selected_piece_id = None
        self.notice = ""
        self.phase = "preview"

    def blocked_squares(self) -> set[tuple[int, int]]:
        squares: set[tuple[int, int]] = set()
        for piece in self.enemies:
            if piece.col is not None and piece.row is not None:
                squares.add((piece.col, piece.row))
        return squares

    def begin_deployment(self) -> None:
        self.phase = "deployment"
        self.selected_piece_id = None
        self.notice = ""

    def start_battle(self) -> bool:
        if not self.deployment.ready(self.army):
            self.notice = "Deploy the King"
            return False
        rules = BattleRules()
        self.battle = BattleSession(
            self.army,
            self.deployment,
            self.enemies,
            dispatcher=self.relics.dispatcher,
            rules=rules,
        )
        rules.bind(lambda: self.battle.game.board if self.battle is not None else None)
        self.relics.context.rules = rules
        self.relics.dispatcher.publish(GameEvent(BATTLE_START, {"level": self.level}))
        self.phase = "battle"
        self.notice = ""
        self.selected_piece_id = None
        return True

    def _keep_survivors(self) -> None:
        if self.battle is None:
            return
        living = {
            piece.id: piece
            for piece in self.battle.game.board.pieces
            if piece.color == "white" and piece.trait != "ghost"
        }
        known = {piece.id for piece in self.army.pieces}
        kept: list[Piece] = []
        for piece in self.army.pieces:
            if piece.id not in self.deployment.placed:
                kept.append(piece)
                continue
            survivor = living.get(piece.id)
            if survivor is None:
                continue
            piece.kind = survivor.kind
            piece.trait = survivor.trait
            piece.col = None
            piece.row = None
            piece.has_moved = False
            kept.append(piece)
        for piece in self.battle.game.board.pieces:
            if piece.color != "white" or piece.id in known or piece.trait == "ghost":
                continue
            recruit = piece.copy()
            recruit.col = None
            recruit.row = None
            recruit.has_moved = False
            kept.append(recruit)
        self.army.pieces = kept

    def finish_victory(self) -> None:
        if self.phase == "victory":
            return
        self.golden_reward = 0
        self.relics.dispatcher.publish(GameEvent(BATTLE_END, {"outcome": "victory"}))
        self._keep_survivors()
        self.gold += VICTORY_GOLD
        self.phase = "victory"
        self.notice = ""

    def finish_defeat(self) -> None:
        if self.phase == "defeat":
            return
        self.relics.dispatcher.publish(GameEvent(BATTLE_END, {"outcome": "defeat"}))
        self.phase = "defeat"
        self.notice = ""

    def continue_from_victory(self) -> None:
        if self.level >= MAX_LEVEL:
            self.phase = "complete"
            return
        self.shop.begin_visit(self.relics.owned_ids())
        self.notice = ""
        self.phase = "shop"
        self.relics.dispatcher.publish(GameEvent(SHOP_ENTER, {"level": self.level}))

    def leave_shop(self) -> None:
        self.level += 1
        self.prepare_level()

    def restart(self) -> "RunState":
        return RunState.new()

    def buy_piece(self) -> str | None:
        gold, notice = self.shop.buy_piece(self.gold, self.army)
        self.gold = gold
        self.notice = notice or ""
        return notice

    def buy_relic(self) -> str | None:
        relic_id = self.shop.relic_id
        if self.shop.relic_sold or relic_id is None:
            gold, notice = self.shop.buy_relic(self.gold)
            self.gold = gold
            self.notice = notice or ""
            return notice
        if self.relics.owns(relic_id):
            self.notice = "Already owned"
            return self.notice
        gold, notice = self.shop.buy_relic(self.gold)
        self.gold = gold
        if notice is None and relic_id:
            self.relics.acquire(relic_id)
        self.notice = notice or ""
        return notice

    def buy_army(self) -> str | None:
        gold, notice = self.shop.buy_army(self.gold, self.army)
        self.gold = gold
        self.notice = notice or ""
        return notice

    def reroll_shop(self) -> str | None:
        gold, notice = self.shop.reroll(self.gold, self.relics.owned_ids())
        self.gold = gold
        self.notice = notice or ""
        return notice
