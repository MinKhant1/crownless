from game.army_manager import ArmyManager
from game.board import Board
from game.deployment_manager import DeploymentManager
from game.game import Game
from game.piece import Piece


def build_battle_board(army: ArmyManager, deployment: DeploymentManager, enemies: list[Piece]) -> Board:
    pieces: list[Piece] = []
    for piece in army.pieces:
        position = deployment.placed.get(piece.id)
        if position is None:
            continue
        clone = piece.copy()
        clone.col, clone.row = position
        clone.has_moved = False
        pieces.append(clone)
    for enemy in enemies:
        pieces.append(enemy.copy())
    return Board(pieces, capture_kings=True, enforce_check=False)


class BattleSession:
    def __init__(self, army: ArmyManager, deployment: DeploymentManager, enemies: list[Piece], dispatcher=None, rules=None, enemy_trait: str | None = None) -> None:
        self.rules = rules
        self.enemy_trait = enemy_trait
        move_filter = None if rules is None else rules.filter_moves
        on_turn_end = None if rules is None else rules.spend
        self.game = Game(
            build_battle_board(army, deployment, enemies),
            mode="crownless",
            dispatcher=dispatcher,
            move_filter=move_filter,
            on_turn_end=on_turn_end,
        )
        if enemy_trait:
            for piece in self.game.board.pieces:
                if piece.color == "black":
                    piece.ai_trait = enemy_trait
        self.outcome: str | None = None

    def click(self, col: int, row: int) -> None:
        if self.outcome is not None:
            return
        self.game.on_board_click(col, row)
        self.evaluate()
        if self.outcome is None and self.game.pending_turn:
            if self.game.hold_turn:
                self.game.hold_turn = False
                self.game.pending_turn = False
            else:
                self.game.bonus_piece_id = None
                self.game.turns.complete_move(self.game.board)
                self.game.pending_turn = False
                self.game.relic_flashes.clear()

    def evaluate(self) -> None:
        if self.outcome is not None:
            return
        if self.game.board.king("white") is None:
            self.outcome = "defeat"
            self.game.turns.finished = True
            return
        if not any(piece.color == "black" for piece in self.game.board.pieces):
            self.outcome = "victory"
            self.game.turns.finished = True

    def force(self, outcome: str) -> None:
        self.outcome = outcome
        self.game.turns.finished = True
