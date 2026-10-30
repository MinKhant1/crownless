from config.settings import INITIAL_SETUP, VISUAL_TEST_ID_START, VISUAL_TEST_TRAITS, parse_square
from game.board import Board
from game.game import Game
from game.piece import Piece
from game.run_state import RunState
from rendering.piece_animation_controller import piece_motion


class VisualTest:
    def __init__(self) -> None:
        self.active = False
        self.game: Game | None = None

    def toggle(self, run: RunState) -> None:
        if self.active:
            self.close(run)
            return
        self.open(run)

    def open(self, run: RunState) -> None:
        self.close(run)
        pieces: list[Piece] = []
        for offset, (kind, color, square) in enumerate(INITIAL_SETUP):
            col, row = parse_square(square)
            pieces.append(Piece(VISUAL_TEST_ID_START + offset, kind, color, col, row))
        board = Board(pieces)
        run.visual_pieces = pieces
        for piece in pieces:
            if piece.color != "white":
                continue
            trait = VISUAL_TEST_TRAITS.get(piece.kind)
            if trait is None:
                continue
            run.traits.assign_trait(piece.id, trait, overwrite=True)
        self.game = Game(board)
        self.active = True
        piece_motion.clear()

    def close(self, run: RunState) -> None:
        self.active = False
        self.game = None
        run.visual_pieces = None
        piece_motion.clear()
