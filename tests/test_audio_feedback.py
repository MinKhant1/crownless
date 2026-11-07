import tempfile
import unittest
from pathlib import Path

import pygame

from config.settings import PIECE_TRAVEL_TIME
from game.relics.events import CAPTURE_RESOLVED, PIECE_MOVED, RELIC_FLASH, GameEvent
from game.run_state import RunState
from rendering import audio as audio_module
from rendering.audio import Audio, track_for
from rendering.battle_feedback import BattleFeedback
from rendering.effects import board_effects
from rendering.layout import build_layout
from scenes.screen_menu import ScreenMenu, _geometry

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (1440, 900)


class RecordingAudio(Audio):
    """Records play() calls instead of making noise."""

    def __init__(self) -> None:
        super().__init__(ROOT / "assets" / "audio", None)
        self.played: list[tuple[str, float]] = []

    def play(self, name: str, volume: float = 1.0, delay: float = 0.0) -> None:
        self.played.append((name, delay))


class AudioSettingsTests(unittest.TestCase):
    def test_volumes_step_clamp_and_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            first = Audio(ROOT / "assets" / "audio", path)
            for _ in range(20):
                first.change_music(0.1)
            self.assertEqual(first.music_volume, 1.0)
            for _ in range(3):
                first.change_sound(-0.1)
            self.assertAlmostEqual(first.sound_volume, 0.5)
            second = Audio(ROOT / "assets" / "audio", path)
            self.assertEqual(second.music_volume, 1.0)
            self.assertAlmostEqual(second.sound_volume, 0.5)

    def test_without_a_mixer_every_call_is_silent(self):
        sound = Audio(ROOT / "assets" / "audio", None)
        sound.play("move")
        sound.music("battle")
        sound.update(0.1)
        self.assertFalse(sound.enabled)

    def test_every_sound_file_is_shipped(self):
        for name in audio_module.SOUND_FILES:
            self.assertTrue((ROOT / "assets" / "audio" / f"{name}.wav").exists(), name)
        for track in audio_module.TRACKS.values():
            self.assertTrue((ROOT / "assets" / "audio" / track).exists(), track)

    def test_board_screens_get_the_battle_theme(self):
        self.assertEqual(track_for("menu", "battle"), "menu")
        self.assertEqual(track_for("play", "battle"), "battle")
        self.assertEqual(track_for("play", "deployment"), "battle")
        self.assertEqual(track_for("play", "shop"), "menu")


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.sound = RecordingAudio()
        audio_module.install(self.sound)
        board_effects.clear()
        self.run = RunState(42)
        self.run.begin_deployment()
        self.run.start_battle()
        self.feedback = BattleFeedback()
        self.feedback.bind(self.run, build_layout(*WINDOW))

    def tearDown(self):
        audio_module.install(audio_module._Silent())
        board_effects.clear()

    def test_a_move_lands_with_a_wooden_knock_after_the_travel_animation(self):
        piece = next(p for p in self.run.battle.game.board.pieces if p.color == "white" and p.kind == "pawn")
        self.run.relics.dispatcher.publish(GameEvent(PIECE_MOVED, {"piece_id": piece.id, "origin_square": (0, 2), "destination_square": (0, 3)}))
        self.assertEqual(self.sound.played, [("move", PIECE_TRAVEL_TIME)])
        self.assertTrue(board_effects.pending)
        board_effects.update(PIECE_TRAVEL_TIME + 0.01)
        self.assertTrue(board_effects.particles or board_effects.rings)

    def test_a_capture_plays_once_not_as_a_move_too(self):
        payload = {"capturing_piece_id": 1, "capturing_kind": "knight", "capturing_color": "white", "captured_piece_id": 9,
                   "captured_piece_type": "pawn", "captured_piece_color": "black", "captured_trait": None,
                   "origin_square": (1, 1), "destination_square": (2, 3)}
        dispatcher = self.run.relics.dispatcher
        dispatcher.publish(GameEvent(CAPTURE_RESOLVED, payload))
        dispatcher.publish(GameEvent(PIECE_MOVED, {"piece_id": 1, "origin_square": (1, 1), "destination_square": (2, 3)}))
        self.assertEqual([name for name, _delay in self.sound.played], ["capture"])

    def test_the_enemy_taking_your_piece_sounds_darker(self):
        payload = {"capturing_piece_id": 10001, "capturing_kind": "knight", "capturing_color": "black", "captured_piece_id": 3,
                   "captured_piece_type": "pawn", "captured_piece_color": "white", "captured_trait": None,
                   "origin_square": (3, 6), "destination_square": (4, 4)}
        self.run.relics.dispatcher.publish(GameEvent(CAPTURE_RESOLVED, payload))
        self.assertEqual([name for name, _delay in self.sound.played], ["capture_enemy"])

    def test_an_explosive_capture_explodes(self):
        payload = {"capturing_piece_id": 10001, "capturing_kind": "knight", "capturing_color": "black", "captured_piece_id": 3,
                   "captured_piece_type": "pawn", "captured_piece_color": "white", "captured_trait": "explosive",
                   "origin_square": (3, 6), "destination_square": (4, 4)}
        self.run.relics.dispatcher.publish(GameEvent(CAPTURE_RESOLVED, payload))
        names = [name for name, _delay in self.sound.played]
        self.assertIn("explosion", names)
        self.assertNotIn("relic", names)
        board_effects.update(PIECE_TRAVEL_TIME + 0.01)
        self.assertGreater(len(board_effects.particles), 40)

    def test_relic_flashes_ring_once_per_burst(self):
        dispatcher = self.run.relics.dispatcher
        dispatcher.publish(GameEvent(RELIC_FLASH, {"square": (2, 2), "color": (230, 190, 70)}))
        dispatcher.publish(GameEvent(RELIC_FLASH, {"square": (3, 2), "color": (230, 190, 70)}))
        self.assertEqual([name for name, _delay in self.sound.played], ["relic"])

    def test_winning_and_losing_play_their_stingers(self):
        self.feedback.watch(self.run)
        self.run.finish_victory()
        self.feedback.watch(self.run)
        self.assertIn("victory", [name for name, _delay in self.sound.played])


class UISoundTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        self.screen = pygame.display.set_mode((640, 480), pygame.HIDDEN)
        self.sound = RecordingAudio()
        audio_module.install(self.sound)
        from rendering.ui_sounds import UISounds

        self.ui = UISounds()
        self.button = pygame.Rect(100, 100, 200, 40)

    def tearDown(self):
        audio_module.install(audio_module._Silent())

    def _frame(self, pointer, hand=False, register=True):
        if register:
            self.ui.register(self.screen, self.button, "Start")
        self.ui.end_frame(pointer, hand, 0.1)

    def test_entering_a_button_ticks_once_and_pressing_it_clicks(self):
        self._frame((10, 10))
        self._frame(self.button.center)
        self._frame((self.button.centerx + 30, self.button.centery))
        self.assertEqual([name for name, _ in self.sound.played], ["hover"])
        self.ui.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.button.center))
        self.ui.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5)))
        self.assertEqual([name for name, _ in self.sound.played], ["hover", "click"])

    def test_cards_that_show_the_hand_cursor_count_as_clickable(self):
        self._frame((10, 10), hand=False, register=False)
        self._frame((400, 300), hand=True, register=False)
        self.ui.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)))
        self.assertEqual([name for name, _ in self.sound.played], ["hover", "click"])

    def test_buttons_under_a_modal_panel_stay_quiet(self):
        self.ui.register(self.screen, self.button, "Start")
        self.ui.modal()
        self.ui.end_frame(self.button.center, False, 0.1)
        self.assertEqual(self.sound.played, [])

    def test_off_screen_layers_do_not_register(self):
        layer = pygame.Surface((640, 480))
        self.ui.register(layer, self.button, "Start")
        self.ui.end_frame(self.button.center, False, 0.1)
        self.assertEqual(self.sound.played, [])


class OptionsMenuTests(unittest.TestCase):
    def setUp(self):
        self.sound = Audio(ROOT / "assets" / "audio", None)
        audio_module.install(self.sound)

    def tearDown(self):
        audio_module.install(audio_module._Silent())

    def test_options_buttons_change_music_and_sound(self):
        menu = ScreenMenu()
        menu.mode = "options"
        _panel, buttons = _geometry(WINDOW, "options")
        rects = dict(buttons)
        music = self.sound.music_volume
        self.assertEqual(menu.on_release(rects["music+"].center, WINDOW, None), "audio")
        self.assertAlmostEqual(self.sound.music_volume, round(music + 0.1, 2))
        sound = self.sound.sound_volume
        self.assertEqual(menu.on_release(rects["sound-"].center, WINDOW, None), "audio")
        self.assertAlmostEqual(self.sound.sound_volume, round(sound - 0.1, 2))
        self.assertEqual(menu.mode, "options")
        self.assertEqual(menu.on_release(rects["close"].center, WINDOW, None), "close")
        self.assertEqual(menu.mode, "")

    def test_the_in_game_menu_can_leave_for_the_main_menu(self):
        menu = ScreenMenu()
        menu.mode = "menu"
        rects = dict(_geometry(WINDOW, "menu")[1])
        self.assertEqual(set(rects), {"main_menu", "restart", "cancel"})
        self.assertEqual(menu.on_release(rects["main_menu"].center, WINDOW, None), "main_menu")
        self.assertEqual(menu.mode, "")

    def test_options_buttons_do_not_overlap(self):
        for mode in ("options", "menu"):
            panel, buttons = _geometry(WINDOW, mode)
            rects = [rect for _name, rect in buttons]
            inner = panel.inflate(-2 * 18, -2 * 18)  # clear of the 12px parchment frame, with room to spare
            for i, first in enumerate(rects):
                self.assertTrue(inner.contains(first), (mode, first, inner))
                for second in rects[i + 1:]:
                    self.assertFalse(first.colliderect(second))


if __name__ == "__main__":
    pygame.init()
    unittest.main()
