"""Sound effects and background music.

Everything is optional: with no audio device (tests, a headless machine) the mixer never starts and every call
is a quiet no-op. Volumes are saved to ~/.crownless/settings.json so they survive restarts and new builds.
"""

import json
import os
from pathlib import Path

import pygame

SOUND_FILES = (
    "move", "move_enemy", "capture", "capture_enemy", "explosion", "relic", "spawn", "coin", "click", "hover",
    "battle_start", "victory", "defeat",
)
TRACKS = {"battle": "theme_battle.ogg", "menu": "theme_menu.ogg"}
DEFAULT_MUSIC = 0.6
DEFAULT_SOUND = 0.8
STEP = 0.1


def settings_path() -> Path:
    override = os.environ.get("CROWNLESS_SETTINGS")
    if override:
        return Path(override)
    return Path.home() / ".crownless" / "settings.json"


class Audio:
    def __init__(self, folder: Path, settings: Path | None = None) -> None:
        self.folder = Path(folder)
        self.settings = settings
        self.enabled = False
        self.music_volume = DEFAULT_MUSIC
        self.sound_volume = DEFAULT_SOUND
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.track: str | None = None
        self._wanted: str | None = None
        self._delayed: list[list] = []
        self._load_settings()

    # ------------------------------------------------------------------ setup
    def start(self) -> bool:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            self.enabled = False
            return False
        self.enabled = True
        for name in SOUND_FILES:
            path = self.folder / f"{name}.wav"
            if path.exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    pass
        return True

    # ------------------------------------------------------------------ effects
    def play(self, name: str, volume: float = 1.0, delay: float = 0.0) -> None:
        if not self.enabled or self.sound_volume <= 0:
            return
        if delay > 0:
            self._delayed.append([delay, name, volume])
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        channel = sound.play()
        if channel is not None:
            channel.set_volume(max(0.0, min(1.0, volume * self.sound_volume)))

    # ------------------------------------------------------------------ music
    def music(self, name: str | None) -> None:
        """Ask for a track ('battle', 'menu' or None); update() crossfades to it."""
        self._wanted = name

    def update(self, dt: float) -> None:
        if self._delayed:
            due = []
            for item in self._delayed:
                item[0] -= dt
                if item[0] <= 0:
                    due.append(item)
            for item in due:
                self._delayed.remove(item)
                self.play(item[1], item[2])
        if not self.enabled:
            return
        if self._wanted == self.track:
            return
        mixer_music = pygame.mixer.music
        if self.track is not None and mixer_music.get_busy():
            mixer_music.fadeout(450)
            self.track = None
            return
        if mixer_music.get_busy():
            return
        self.track = self._wanted
        if self.track is None:
            return
        path = self.folder / TRACKS[self.track]
        try:
            mixer_music.load(str(path))
            mixer_music.set_volume(self.music_volume)
            mixer_music.play(loops=-1, fade_ms=900)
        except pygame.error:
            self.track = None
            self._wanted = None

    # ------------------------------------------------------------------ volume
    def change_music(self, delta: float) -> float:
        self.music_volume = _step(self.music_volume, delta)
        if self.enabled:
            pygame.mixer.music.set_volume(self.music_volume)
        self._save_settings()
        return self.music_volume

    def change_sound(self, delta: float) -> float:
        self.sound_volume = _step(self.sound_volume, delta)
        self._save_settings()
        self.play("hover", 1.0)  # a quiet preview at the new level (the press itself already clicked)
        return self.sound_volume

    def _load_settings(self) -> None:
        if self.settings is None or not self.settings.exists():
            return
        try:
            data = json.loads(self.settings.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self.music_volume = _clamp(data.get("music_volume", self.music_volume))
        self.sound_volume = _clamp(data.get("sound_volume", self.sound_volume))

    def _save_settings(self) -> None:
        if self.settings is None:
            return
        data = {}
        try:
            if self.settings.exists():
                data = json.loads(self.settings.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data["music_volume"] = round(self.music_volume, 2)
        data["sound_volume"] = round(self.sound_volume, 2)
        try:
            self.settings.parent.mkdir(parents=True, exist_ok=True)
            self.settings.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass


def _clamp(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _step(value: float, delta: float) -> float:
    return round(_clamp(round((value + delta) / STEP) * STEP), 2)


def track_for(mode: str, phase: str) -> str:
    """Front screens, the shop and the win screen get the calm theme; anything on the board gets the battle theme."""
    if mode != "play":
        return "menu"
    if phase in ("preview", "deployment", "battle", "victory", "defeat"):
        return "battle"
    return "menu"


# A silent stand-in so scenes and tests can call audio without a mixer.
class _Silent(Audio):
    def __init__(self) -> None:
        super().__init__(Path("."), None)


audio = _Silent()


def install(instance: Audio) -> None:
    global audio
    audio = instance
