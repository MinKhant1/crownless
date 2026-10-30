import random

from config.settings import BOARD_SIZE, DEPLOY_ROWS, MAX_LEVEL, STARTING_GOLD, VICTORY_GOLD
from game.army_manager import ArmyManager
from game.battle_rules import BattleRules
from game.battle_session import BattleSession
from game.deployment_manager import KIND_HOMES, DeploymentManager
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
        self.visual_pieces: list[Piece] | None = None
        self.preferred_ids: list[int] = []
        self.preferred_positions: dict[int, tuple[int, int]] = {}
        self.formation_snapshot: dict[int, tuple[int, int]] = {}
        self.battle_roster: tuple[tuple[int, str, str | None], ...] = ()
        self.shop_rerolls = 0
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
        self.battle_roster = ()
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
        self.auto_deploy_army()

    def auto_deploy_army(self) -> None:
        self.deployment.clear()
        king = self.army.king()
        non_kings = [piece for piece in self.army.pieces if piece.kind != "king"]
        preferred_set = set(self.preferred_ids)
        preferred = [piece for piece in non_kings if piece.id in preferred_set]
        preferred.sort(key=lambda piece: self.preferred_ids.index(piece.id))
        rest = [piece for piece in non_kings if piece.id not in preferred_set]
        chosen = preferred[: self.army.capacity]
        if len(chosen) < self.army.capacity:
            chosen.extend(rest[: self.army.capacity - len(chosen)])
        if king is not None:
            self._seat(king)
        for piece in chosen:
            self._seat(piece)
        self.formation_snapshot = dict(self.deployment.placed)
        self.selected_piece_id = None

    def _open_squares(self) -> list[tuple[int, int]]:
        blocked = self.blocked_squares()
        squares: list[tuple[int, int]] = []
        for row in DEPLOY_ROWS:
            for col in range(BOARD_SIZE):
                if self.deployment.piece_id_at(col, row) is None and (col, row) not in blocked:
                    squares.append((col, row))
        return squares

    def _seat(self, piece: Piece) -> bool:
        open_squares = self._open_squares()
        preferred = self.preferred_positions.get(piece.id)
        if preferred in open_squares:
            self.deployment.placed[piece.id] = preferred
            return True
        for square in KIND_HOMES.get(piece.kind, ()):
            if square in open_squares:
                self.deployment.placed[piece.id] = square
                return True
        if not open_squares:
            return False
        rng = random.Random((self.seed, self.level, piece.id))
        self.deployment.placed[piece.id] = rng.choice(open_squares)
        return True

    def reposition_piece(self, piece_id: int, destination: tuple[int, int]) -> bool:
        piece = self.army.piece_by_id(piece_id)
        if piece is None or piece_id not in self.deployment.placed:
            return False
        col, row = destination
        if self.deployment.placed[piece_id] == (col, row):
            return True
        occupant = self.deployment.piece_id_at(col, row)
        if occupant is not None:
            return self.swap_deployed_pieces(piece_id, occupant)
        if not self.deployment.can_place(piece, col, row, self.blocked_squares(), self.army.capacity, self.army):
            self.notice = "Square unavailable"
            return False
        self.deployment.placed[piece.id] = (col, row)
        self.notice = ""
        return True

    def swap_deployed_pieces(self, piece_a_id: int, piece_b_id: int) -> bool:
        if self.army.piece_by_id(piece_a_id) is None or self.army.piece_by_id(piece_b_id) is None:
            return False
        first = self.deployment.placed.get(piece_a_id)
        second = self.deployment.placed.get(piece_b_id)
        if first is None or second is None or first[1] not in DEPLOY_ROWS or second[1] not in DEPLOY_ROWS:
            return False
        self.deployment.swap(piece_a_id, piece_b_id)
        self.notice = ""
        return True

    def replace_with_reserve(self, reserve_id: int, deployed_id: int) -> bool:
        reserve = self.army.piece_by_id(reserve_id)
        deployed = self.army.piece_by_id(deployed_id)
        if reserve is None or deployed is None:
            return False
        if reserve_id in self.deployment.placed or deployed_id not in self.deployment.placed:
            return False
        if deployed.kind == "king":
            self.notice = "King stays"
            return False
        square = self.deployment.placed.pop(deployed_id)
        self.deployment.placed[reserve_id] = square
        self.notice = ""
        return True

    def reset_formation(self) -> None:
        self.deployment.placed = dict(self.formation_snapshot)
        self.selected_piece_id = None
        self.notice = ""

    def validate_deployment(self) -> bool:
        king = self.army.king()
        if king is None or king.id not in self.deployment.placed:
            return False
        seen: set[tuple[int, int]] = set()
        blocked = self.blocked_squares()
        non_king = 0
        for piece_id, (col, row) in self.deployment.placed.items():
            piece = self.army.piece_by_id(piece_id)
            if piece is None:
                return False
            if col < 0 or col >= BOARD_SIZE or row not in DEPLOY_ROWS:
                return False
            if (col, row) in seen or (col, row) in blocked:
                return False
            seen.add((col, row))
            if piece.kind != "king":
                non_king += 1
        return non_king <= self.army.capacity

    def _remember_formation(self) -> None:
        self.preferred_positions = dict(self.deployment.placed)
        ordered: list[tuple[int, int, int]] = []
        for piece_id, (col, row) in self.deployment.placed.items():
            piece = self.army.piece_by_id(piece_id)
            if piece is not None and piece.kind != "king":
                ordered.append((row, col, piece_id))
        ordered.sort()
        self.preferred_ids = [piece_id for _row, _col, piece_id in ordered]

    def start_battle(self) -> bool:
        if not self.validate_deployment():
            king = self.army.king()
            self.notice = "Deploy the King" if king is None or king.id not in self.deployment.placed else "Formation invalid"
            return False
        self._remember_formation()
        self.battle_roster = tuple((piece.id, piece.kind, piece.trait) for piece in self.army.pieces)
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
        if self.phase != "victory":
            return
        if self.level >= MAX_LEVEL:
            self.phase = "complete"
            return
        self.shop.begin_visit(self.relics.owned_ids())
        self.notice = ""
        self.phase = "shop"
        self.relics.dispatcher.publish(GameEvent(SHOP_ENTER, {"level": self.level}))

    def leave_shop(self) -> None:
        if self.phase != "shop":
            return
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
        if self.shop_rerolls > 0:
            self.shop.roll(self.relics.owned_ids())
            self.shop_rerolls -= 1
            self.notice = ""
            return None
        gold, notice = self.shop.reroll(self.gold, self.relics.owned_ids())
        self.gold = gold
        self.notice = notice or ""
        return notice
