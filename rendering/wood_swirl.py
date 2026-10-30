import array
import math
from pathlib import Path

import pygame


FALLBACK = (36, 22, 16)
_SHADER_DIR = Path(__file__).resolve().parent / "shaders"
_CONTEXT = None
_CONTEXT_ERROR = ""

_STEPS = {
    "flow_speed": (0.02, 0.0, 1.0),
    "distortion_strength": (0.01, 0.0, 0.15),
    "swirl_strength": (0.01, 0.0, 0.15),
    "noise_scale": (0.5, 0.5, 8.0),
}


def _shared_context():
    global _CONTEXT, _CONTEXT_ERROR
    if _CONTEXT is False:
        return None
    if _CONTEXT is not None:
        return _CONTEXT
    try:
        import moderngl

        _CONTEXT = moderngl.create_context(standalone=True)
    except Exception as error:
        _CONTEXT = False
        _CONTEXT_ERROR = str(error)
        return None
    return _CONTEXT


class WoodSwirlBackground:
    def __init__(
        self,
        texture_path: str | Path = "assets/backgrounds/wood_swirl.png",
        enabled: bool = True,
        flow_speed: float = 0.12,
        distortion_strength: float = 0.035,
        noise_scale: float = 2.5,
        swirl_strength: float = 0.025,
        swirl_scale: float = 3.0,
        vignette_strength: float = 0.25,
    ) -> None:
        self.texture_path = Path(texture_path)
        self.enabled = enabled
        self.flow_speed = flow_speed
        self.distortion_strength = distortion_strength
        self.noise_scale = noise_scale
        self.swirl_strength = swirl_strength
        self.swirl_scale = swirl_scale
        self.vignette_strength = vignette_strength
        self.paused = False
        self.elapsed = 0.0
        self.debug_open = False
        self.uses_shader = False
        self.shader_error = ""
        self._path: Path | None = None
        self._texture: pygame.Surface | None = None
        self._missing = False
        self._shader_failed = False
        self._ready = False
        self._ctx = None
        self._program = None
        self._vao = None
        self._wood = None
        self._fbo = None
        self._target = None
        self._target_size: tuple[int, int] | None = None
        self._pixels: bytearray | None = None
        self._static: pygame.Surface | None = None
        self._static_size: tuple[int, int] | None = None
        self._vignette: pygame.Surface | None = None
        self._vignette_key: tuple[int, int, int] | None = None
        self._font: pygame.font.Font | None = None

    def update(self, dt: float) -> None:
        if not self.enabled or self.paused:
            return
        self.elapsed += max(0.0, dt)

    def resize(self) -> None:
        self._static = None
        self._static_size = None
        self._vignette = None
        self._vignette_key = None
        self._release_target()

    def toggle_debug(self) -> None:
        self.debug_open = not self.debug_open

    def ensure(self, path: str | Path | None = None) -> None:
        chosen = self._resolve(path)
        if self._path == chosen and (self._texture is not None or self._missing):
            return
        self._path = chosen
        self._texture = None
        self._missing = False
        self._static = None
        self._static_size = None
        if self._wood is not None:
            self._wood.release()
            self._wood = None
        if not chosen.exists():
            self._missing = True
            return
        try:
            self._texture = pygame.image.load(chosen).convert()
        except pygame.error:
            self._missing = True

    def draw(self, screen: pygame.Surface) -> None:
        if self._texture is None and not self._missing:
            self.ensure(None)
        if self._texture is None or not self.enabled:
            self._draw_static(screen)
            return
        try:
            if self._draw_shader(screen):
                self.uses_shader = True
                return
        except Exception as error:
            self._shader_failed = True
            self.shader_error = str(error)
        self.uses_shader = False
        self._draw_static(screen)

    def debug_hit(self, pos: tuple[int, int]) -> bool:
        if not self.debug_open:
            return False
        panel, _rows, _pause = _debug_layout()
        return panel.collidepoint(pos)

    def debug_click(self, pos: tuple[int, int]) -> bool:
        if not self.debug_hit(pos):
            return False
        _panel, rows, pause = _debug_layout()
        if pause.collidepoint(pos):
            self.paused = not self.paused
            return True
        for name, minus, plus in rows:
            if minus.collidepoint(pos):
                self._nudge(name, -1)
                return True
            if plus.collidepoint(pos):
                self._nudge(name, 1)
                return True
        return True

    def draw_debug(self, screen: pygame.Surface) -> None:
        if not self.debug_open:
            return
        panel, rows, pause = _debug_layout()
        pygame.draw.rect(screen, (42, 26, 16), panel, border_radius=12)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=12)
        font = self._ui_font()
        title = "Wood flow" if self.uses_shader else "Wood flow  static"
        _label(screen, font, title, (236, 220, 196), (panel.x + 14, panel.y + 12))
        names = {
            "flow_speed": "Flow",
            "distortion_strength": "Distort",
            "swirl_strength": "Swirl",
            "noise_scale": "Noise",
        }
        for name, minus, plus in rows:
            _label(screen, font, names[name], (236, 220, 196), (panel.x + 14, minus.y + 4))
            _label(screen, font, f"{getattr(self, name):.3f}", (232, 214, 184), (panel.x + 96, minus.y + 4))
            _button(screen, font, minus, "-")
            _button(screen, font, plus, "+")
        _button(screen, font, pause, "Paused" if self.paused else "Pause")
        if self.shader_error and not self.uses_shader:
            _label(screen, font, self.shader_error[:42], (196, 92, 72), (panel.x + 14, panel.bottom - 22))

    def _resolve(self, path: str | Path | None) -> Path:
        if path is None:
            chosen = self.texture_path
            if not chosen.is_absolute():
                chosen = Path(__file__).resolve().parents[1] / chosen
            return chosen
        return Path(path)

    def _nudge(self, name: str, direction: int) -> None:
        step, low, high = _STEPS[name]
        value = getattr(self, name) + step * direction
        setattr(self, name, min(high, max(low, round(value, 4))))

    def _draw_static(self, screen: pygame.Surface) -> None:
        self.uses_shader = False
        if self._texture is None:
            screen.fill(FALLBACK)
        else:
            size = screen.get_size()
            if self._static is None or self._static_size != size:
                self._static = _cover_surface(self._texture, size)
                self._static_size = size
            screen.blit(self._static, (0, 0))
        self._blit_vignette(screen)

    def _draw_shader(self, screen: pygame.Surface) -> bool:
        if self._shader_failed or not self._prepare_shader():
            return False
        width, height = screen.get_size()
        if width < 2 or height < 2:
            return False
        self._upload_wood()
        self._ensure_target(width, height)
        program = self._program
        texture_size = self._texture.get_size()
        program["u_time"].value = float(self.elapsed)
        program["u_speed"].value = float(self.flow_speed)
        program["u_distortion"].value = float(self.distortion_strength)
        program["u_noise_scale"].value = float(self.noise_scale)
        program["u_swirl"].value = float(self.swirl_strength)
        program["u_swirl_scale"].value = float(self.swirl_scale)
        program["u_vignette"].value = float(self.vignette_strength)
        program["u_resolution"].value = (float(width), float(height))
        program["u_tex_size"].value = (float(texture_size[0]), float(texture_size[1]))
        self._fbo.use()
        self._ctx.viewport = (0, 0, width, height)
        self._wood.use(location=0)
        self._vao.render()
        count = width * height * 3
        if self._pixels is None or len(self._pixels) != count:
            self._pixels = bytearray(count)
        self._fbo.read_into(self._pixels, components=3, alignment=1)
        frame = pygame.image.frombuffer(self._pixels, (width, height), "RGB")
        screen.blit(frame, (0, 0))
        return True

    def _prepare_shader(self) -> bool:
        if self._ready:
            return True
        ctx = _shared_context()
        if ctx is None:
            self._shader_failed = True
            self.shader_error = _CONTEXT_ERROR or "ModernGL is unavailable"
            return False
        import moderngl

        vertex = (_SHADER_DIR / "wood_swirl.vert").read_text(encoding="utf-8")
        fragment = (_SHADER_DIR / "wood_swirl.frag").read_text(encoding="utf-8")
        self._ctx = ctx
        self._program = ctx.program(vertex_shader=vertex, fragment_shader=fragment)
        self._program["u_texture"].value = 0
        vertices = array.array(
            "f",
            [
                -1.0, -1.0, 0.0, 0.0,
                1.0, -1.0, 1.0, 0.0,
                1.0, 1.0, 1.0, 1.0,
                -1.0, -1.0, 0.0, 0.0,
                1.0, 1.0, 1.0, 1.0,
                -1.0, 1.0, 0.0, 1.0,
            ],
        )
        buffer = ctx.buffer(vertices)
        self._vao = ctx.vertex_array(self._program, [(buffer, "2f 2f", "a_pos", "a_uv")])
        self._moderngl = moderngl
        self._ready = True
        return True

    def _upload_wood(self) -> None:
        if self._wood is not None or self._texture is None:
            return
        width, height = self._texture.get_size()
        data = pygame.image.tobytes(self._texture, "RGB", True)
        self._wood = self._ctx.texture((width, height), 3, data, alignment=1)
        self._wood.filter = (self._moderngl.LINEAR, self._moderngl.LINEAR)
        self._wood.repeat_x = False
        self._wood.repeat_y = False

    def _ensure_target(self, width: int, height: int) -> None:
        if self._target_size == (width, height) and self._fbo is not None:
            return
        self._release_target()
        self._target = self._ctx.texture((width, height), 3)
        self._fbo = self._ctx.framebuffer(color_attachments=[self._target])
        self._target_size = (width, height)
        self._pixels = None

    def _release_target(self) -> None:
        if self._fbo is not None:
            self._fbo.release()
            self._fbo = None
        if self._target is not None:
            self._target.release()
            self._target = None
        self._target_size = None
        self._pixels = None

    def _blit_vignette(self, screen: pygame.Surface) -> None:
        if self.vignette_strength <= 0:
            return
        width, height = screen.get_size()
        key = (width, height, round(self.vignette_strength * 1000))
        if self._vignette is None or self._vignette_key != key:
            self._vignette = _vignette_surface(width, height, self.vignette_strength)
            self._vignette_key = key
        screen.blit(self._vignette, (0, 0))

    def _ui_font(self) -> pygame.font.Font:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("georgia", 16)
        return self._font


def _cover_surface(texture: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    width, height = size
    source_w, source_h = texture.get_size()
    scale = max(width / source_w, height / source_h)
    fitted = pygame.transform.smoothscale(
        texture,
        (max(1, int(round(source_w * scale))), max(1, int(round(source_h * scale)))),
    )
    frame = pygame.Surface((width, height))
    frame.fill(FALLBACK)
    frame.blit(fitted, fitted.get_rect(center=(width // 2, height // 2)))
    return frame.convert()


def _vignette_surface(width: int, height: int, strength: float) -> pygame.Surface:
    sample_w = 160
    sample_h = max(90, int(round(sample_w * height / max(1, width))))
    small = pygame.Surface((sample_w, sample_h), pygame.SRCALPHA)
    center_x = (sample_w - 1) * 0.5
    center_y = (sample_h - 1) * 0.5
    reach = math.hypot(center_x, center_y)
    for y in range(sample_h):
        for x in range(sample_w):
            distance = math.hypot(x - center_x, y - center_y) / reach
            shade = max(0.0, (distance - 0.45) / 0.55)
            alpha = int(255 * strength * shade * shade)
            if alpha:
                small.set_at((x, y), (16, 9, 6, alpha))
    return pygame.transform.smoothscale(small, (width, height))


def _debug_layout() -> tuple[pygame.Rect, list[tuple[str, pygame.Rect, pygame.Rect]], pygame.Rect]:
    panel = pygame.Rect(16, 16, 292, 236)
    rows = []
    top = panel.y + 40
    for index, name in enumerate(_STEPS):
        y = top + index * 36
        rows.append((name, pygame.Rect(panel.right - 84, y, 32, 28), pygame.Rect(panel.right - 46, y, 32, 28)))
    pause = pygame.Rect(panel.x + 14, top + len(_STEPS) * 36, panel.w - 28, 30)
    return panel, rows, pause


def _label(screen: pygame.Surface, font: pygame.font.Font, text: str, color: tuple[int, int, int], pos: tuple[int, int]) -> None:
    screen.blit(font.render(text, True, color), pos)


def _button(screen: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect, text: str) -> None:
    pygame.draw.rect(screen, (92, 64, 42), rect, border_radius=6)
    pygame.draw.rect(screen, (214, 170, 90), rect, width=1, border_radius=6)
    image = font.render(text, True, (245, 232, 210))
    screen.blit(image, image.get_rect(center=rect.center))


wood_swirl = WoodSwirlBackground(
    texture_path="assets/backgrounds/wood_swirl.png",
    enabled=True,
    flow_speed=0.12,
    distortion_strength=0.035,
    noise_scale=2.5,
    swirl_strength=0.025,
    swirl_scale=3.0,
    vignette_strength=0.25,
)
