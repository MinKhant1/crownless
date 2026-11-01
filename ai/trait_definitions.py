AGGRESSIVE = "aggressive"
GUARDIAN = "guardian"
HUNTER = "hunter"
VENGEFUL = "vengeful"
BERSERKER = "berserker"

AI_TRAITS = (AGGRESSIVE, GUARDIAN, HUNTER, VENGEFUL, BERSERKER)

HUNT_VALUES = {
    "pawn": 1,
    "knight": 3,
    "bishop": 3,
    "rook": 5,
    "queen": 9,
    "king": 12,
}

WIN_CAPTURE = 250

TRAIT_COPY = {
    AGGRESSIVE: ("AGGRESSIVE", "Prioritizes attacks and captures."),
    GUARDIAN: ("GUARDIAN", "Protects valuable allied pieces."),
    HUNTER: ("HUNTER", "Targets your most valuable piece."),
    VENGEFUL: ("VENGEFUL", "Seeks revenge against pieces that capture enemy allies."),
    BERSERKER: ("BERSERKER", "Attacks recklessly, accepting dangerous trades."),
}

TAG_FILES = {
    AGGRESSIVE: ("aggressive.png",),
    GUARDIAN: ("guardian.png",),
    HUNTER: ("hunter.png",),
    VENGEFUL: ("vengeful.png",),
    BERSERKER: ("berserker.png", "bersker.png"),
}


class TraitWeights:
    def __init__(self, capture: float, threat: float, defense: float, target: float, risk: float, position: float = 2.0) -> None:
        self.capture = capture
        self.threat = threat
        self.defense = defense
        self.target = target
        self.risk = risk
        self.position = position

    def scale(self) -> float:
        return max(1.0, self.capture + self.threat + self.defense + self.target + self.position)


TRAIT_WEIGHTS = {
    AGGRESSIVE: TraitWeights(9, 8, 2, 5, 4),
    GUARDIAN: TraitWeights(4, 3, 10, 3, 8),
    HUNTER: TraitWeights(6, 7, 2, 10, 5),
    VENGEFUL: TraitWeights(7, 7, 2, 10, 5),
    BERSERKER: TraitWeights(10, 10, 0, 4, 1),
}


def weights_for(trait: str | None, revenge: bool) -> TraitWeights:
    if trait == VENGEFUL and not revenge:
        return TRAIT_WEIGHTS[AGGRESSIVE]
    return TRAIT_WEIGHTS.get(trait or HUNTER, TRAIT_WEIGHTS[HUNTER])


def trait_title(trait: str) -> str:
    return TRAIT_COPY.get(trait, (trait.upper(), ""))[0]


def trait_description(trait: str) -> str:
    return TRAIT_COPY.get(trait, ("", ""))[1]
