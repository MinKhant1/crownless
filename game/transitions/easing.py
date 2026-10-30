def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def ease_out_cubic(value: float) -> float:
    t = clamp01(value)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(value: float) -> float:
    t = clamp01(value)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease(name: str, value: float) -> float:
    if name == "out_cubic":
        return ease_out_cubic(value)
    return ease_in_out_cubic(value)
