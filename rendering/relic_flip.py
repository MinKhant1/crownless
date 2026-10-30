import math


class ShopReveal:
    def __init__(self) -> None:
        self.progress = 1.0
        self.key = None

    def update(self, dt: float, key) -> None:
        if key != self.key:
            self.key = key
            self.progress = 0.0
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + max(0.0, dt) / 0.55)

    @property
    def face_up(self) -> bool:
        return self.progress >= 0.5

    @property
    def scale_x(self) -> float:
        width = abs(math.cos(self.progress * math.pi))
        if self.progress > 0.85:
            width *= 1.0 + 0.05 * math.sin((self.progress - 0.85) / 0.15 * math.pi)
        return max(0.04, width)


shop_reveal = ShopReveal()
