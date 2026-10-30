import pygame

from config.settings import BATTLE_START_TIME, LEVEL_PREVIEW_TIME, SCENE_SLIDE_TIME, VICTORY_BANNER_TIME, VICTORY_REWARD_TIME
from game.run_state import RunState
from game.transitions.transition_manager import TransitionManager


class SceneManager:
    def __init__(self) -> None:
        self.motion = TransitionManager()
        self.outgoing: str | None = None
        self.incoming: str | None = None
        self.banner_name = ""
        self.banner_elapsed = 0.0
        self._layers: dict[str, pygame.Surface] = {}

    def transition_to(
        self,
        next_scene: str,
        transition: str = "slide_left",
        duration: float = SCENE_SLIDE_TIME,
        source: str | None = None,
    ) -> bool:
        if self.motion.active:
            return False
        self.outgoing = source
        self.incoming = next_scene
        self.banner_name = ""
        self.banner_elapsed = 0.0
        return self.motion.start(transition, duration)

    def begin(self, run: RunState, mutate, transition: str, duration: float) -> bool:
        if self.motion.active:
            return False
        source = run.phase
        mutate()
        return self.transition_to(run.phase, transition=transition, duration=duration, source=source)

    def begin_banner(self, name: str) -> None:
        self.banner_name = name
        self.banner_elapsed = 0.0

    def reset(self) -> None:
        self.motion = TransitionManager()
        self.outgoing = None
        self.incoming = None
        self.banner_name = ""
        self.banner_elapsed = 0.0

    def update(self, dt: float) -> None:
        step = max(0.0, dt)
        if self.banner_name:
            self.banner_elapsed += step
        was_running = self.motion.active
        self.motion.update(step)
        if was_running and not self.motion.active:
            self.outgoing = None
            self.incoming = None

    def blocks_pointer(self) -> bool:
        if self.motion.active:
            return True
        if self.banner_name == "battle_start" and self.banner_elapsed < BATTLE_START_TIME:
            return True
        return False

    def result_ready(self) -> bool:
        if self.motion.active or self.banner_name not in ("level_complete", "game_over"):
            return False
        return self.banner_elapsed >= VICTORY_BANNER_TIME + VICTORY_REWARD_TIME

    def shop_interactive(self, run: RunState) -> bool:
        return run.phase == "shop" and not self.blocks_pointer()

    def layer(self, key: str, size: tuple[int, int]) -> pygame.Surface:
        surface = self._layers.get(key)
        if surface is None or surface.get_size() != size:
            surface = pygame.Surface(size, pygame.SRCALPHA)
            self._layers[key] = surface
        surface.fill((0, 0, 0, 0))
        return surface


def slide_duration(source: str, destination: str) -> tuple[str, float]:
    if destination == "complete":
        return "fade", 0.7
    if source == "shop":
        return "slide_left", LEVEL_PREVIEW_TIME
    return "slide_left", SCENE_SLIDE_TIME
