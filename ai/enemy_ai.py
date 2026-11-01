import random
from dataclasses import dataclass

from config.settings import square_name
from game.board import Board
from game.move import Move
from ai.ai_config import AI_DIFFICULTY, DIFFICULTY, HIGHLIGHT_SECONDS, TRAVEL_SECONDS
from ai.move_evaluator import allowed_moves, score_move
from ai.trait_definitions import HUNT_VALUES, trait_title


@dataclass
class ScoredMove:
    move: Move
    score: int
    capture_value: int
    target_pressure: int
    positional_bonus: int
    danger_penalty: int
    captured_kind: str | None
    threat_name: str | None
    threat_value: int
    exposed: bool
    target: str | None
    mover_kind: str
    personality: str

    @property
    def reason(self) -> str:
        if self.captured_kind == "king":
            return "Captures the King"
        if self.capture_value > 0 and self.capture_value >= self.danger_penalty:
            name = "Piece" if self.captured_kind is None else self.captured_kind.capitalize()
            return f"Captures Player {name}"
        if self.threat_value > 0 and self.threat_name is not None:
            return f"Creates pressure on Player {self.threat_name.capitalize()}"
        if self.target is not None:
            return f"Moves toward Player {self.target.capitalize()}"
        return "Repositions"


@dataclass
class Decision:
    move: Move | None
    scored: list[ScoredMove]
    target: str | None
    report: str


class EnemyAI:
    def __init__(self) -> None:
        self.previous: Move | None = None
        self.last_decision: Decision | None = None

    def choose(self, board: Board, rules=None, rng: random.Random | None = None, difficulty: str | None = None, turn: int | None = None, trait: str | None = None) -> Decision:
        source = rng if rng is not None else random.Random(0)
        name = difficulty or DIFFICULTY
        moves = allowed_moves(board, rules, "black")
        scored = [_scored(board, rules, move, self.previous, trait) for move in moves]
        scored.sort(key=lambda item: (-item.score, item.move.from_col, item.move.from_row, item.move.to_col, item.move.to_row))
        picked = _pick(scored, source, name)
        if picked is not None:
            self.previous = picked.move
        focus = None if picked is None else picked.target
        decision = Decision(None if picked is None else picked.move, scored, focus, _report(focus, scored, picked, turn))
        self.last_decision = decision
        return decision


class EnemyTurn:
    def __init__(self) -> None:
        self.ai = EnemyAI()
        self.phase = "idle"
        self.move: Move | None = None
        self.timer = 0.0
        self.session = None

    def busy(self) -> bool:
        return self.phase != "idle"

    def reset(self) -> None:
        self.phase = "idle"
        self.move = None
        self.timer = 0.0

    def update(self, session, dt: float, rng: random.Random) -> str | None:
        if session is not self.session:
            self.reset()
            self.ai.previous = None
            self.session = session
        if session.outcome is not None:
            self.reset()
            return None
        game = session.game
        if self.phase == "travel":
            self.timer += dt
            if self.timer >= TRAVEL_SECONDS:
                self.reset()
            return None
        if self.phase == "highlight":
            self.timer += dt
            if self.timer < HIGHLIGHT_SECONDS or self.move is None:
                return None
            return self._commit(session)
        if game.turns.finished or game.turns.current != "black" or game.pending_turn:
            return None
        trait = getattr(session, "enemy_trait", None)
        turn_number = game.turns.move_count // 2 + 1
        decision = self.ai.choose(game.board, session.rules, rng, turn=turn_number, trait=trait)
        if decision.move is None:
            return None
        if trait:
            print(f"[Turn {turn_number}] Enemy AI: {trait.upper()}")
        if game.debug:
            print(decision.report)
        self.move = decision.move
        self.phase = "highlight"
        self.timer = 0.0
        game.on_board_click(decision.move.from_col, decision.move.from_row)
        return None

    def _commit(self, session) -> str | None:
        move = self.move
        game = session.game
        mover = None if move is None else game.board.piece_at(move.from_col, move.from_row)
        if move is None or mover is None or game.selected_id != mover.id:
            game.clear_selection()
            self.reset()
            return None
        session.click(move.to_col, move.to_row)
        outcome = session.outcome
        if outcome is not None or game.turns.current != "black":
            self.phase = "travel"
            self.timer = 0.0
            self.move = None
            return outcome
        game.clear_selection()
        self.reset()
        return None


def _scored(board: Board, rules, move: Move, previous: Move | None, trait: str | None = None) -> ScoredMove:
    detail = score_move(board, rules, move, previous, trait)
    mover = board.piece_at(move.from_col, move.from_row)
    return ScoredMove(
        move,
        detail["score"],
        detail["capture_value"],
        detail["target_pressure"],
        detail["positional_bonus"],
        detail["danger_penalty"],
        detail["captured_kind"],
        detail["threat_name"],
        detail["threat_value"],
        detail["exposed"],
        detail["target"],
        "piece" if mover is None else mover.kind,
        detail["personality"],
    )


def _pick(scored: list[ScoredMove], rng: random.Random, difficulty: str) -> ScoredMove | None:
    if not scored:
        return None
    best = max(item.score for item in scored)
    top = [item for item in scored if item.score == best]
    others = [item for item in scored if item.score != best]
    chance = AI_DIFFICULTY[difficulty]["optimal_move_chance"]
    if not others or rng.random() < chance:
        return rng.choice(top)
    return rng.choice(others)


def _report(target: str | None, scored: list[ScoredMove], picked: ScoredMove | None, turn: int | None) -> str:
    heading = "[Enemy AI]" if turn is None else f"[Enemy AI] Turn {turn}"
    if target is None:
        headline = "Priority Target: none"
    else:
        headline = f"Priority Target: Player {target.capitalize()} (Value {HUNT_VALUES.get(target, 0)})"
    lines = [heading, headline, "", "Candidate Moves:"]
    if not scored:
        lines.append("none")
    for item in scored:
        lines.append(
            f"{item.mover_kind.capitalize()} {square_name(item.move.from_col, item.move.from_row)} -> {square_name(item.move.to_col, item.move.to_row)} | {trait_title(item.personality).title()} | Score: {item.score}"
        )
    lines.append("")
    if picked is None:
        lines.append("Selected: none")
        lines.append("Reason: No legal move")
        return "\n".join(lines)
    lines.append(f"Selected: {picked.mover_kind.capitalize()} {square_name(picked.move.from_col, picked.move.from_row)} -> {square_name(picked.move.to_col, picked.move.to_row)}")
    lines.append(f"Reason: {picked.reason}")
    lines.append(f"Exposed: {'yes' if picked.exposed else 'no'}")
    return "\n".join(lines)
