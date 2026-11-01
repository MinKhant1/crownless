import random

from ai.trait_definitions import AI_TRAITS


def battle_personality(seed: int, level: int) -> str:
    return random.Random(f"{seed}:{level}:battle-personality").choice(AI_TRAITS)


def coming_battle(run) -> tuple[str, list] | None:
    from config.settings import ENEMY_FORMATIONS, MAX_LEVEL
    from game.level_manager import spawn_enemies

    level = getattr(run, "level", 0) + 1
    if level > MAX_LEVEL or level not in ENEMY_FORMATIONS:
        return None
    trait = battle_personality(run.seed, level)
    enemies = spawn_enemies(level)
    _stamp(enemies, trait)
    return trait, enemies


def current_enemy_trait(run) -> str | None:
    if getattr(run, "phase", "") == "shop":
        preview = coming_battle(run)
        if preview is not None:
            return preview[0]
    battle = getattr(run, "battle", None)
    trait = getattr(battle, "enemy_trait", None) if battle is not None else None
    if trait in AI_TRAITS:
        return trait
    trait = getattr(run, "enemy_trait", None)
    return trait if trait in AI_TRAITS else None


def assign_battle_personality(run, fresh: bool = False) -> str:
    current = getattr(run, "enemy_trait", None)
    if not fresh and current in AI_TRAITS:
        _stamp(getattr(run, "enemies", ()), current)
        return current
    trait = battle_personality(run.seed, run.level)
    run.enemy_trait = trait
    _stamp(getattr(run, "enemies", ()), trait)
    print(f"[Battle {run.level}] Enemy AI assigned: {trait.upper()}")
    return trait


def assign_personalities(pieces, seed: int, level: int) -> None:
    pending = [piece for piece in pieces if piece.color == "black" and not piece.ai_trait]
    if not pending:
        return
    trait = battle_personality(seed, level)
    for piece in pending:
        piece.ai_trait = trait


def _stamp(pieces, trait: str) -> None:
    for piece in pieces:
        if getattr(piece, "color", None) == "black":
            piece.ai_trait = trait


def assign_spawned(piece, seed: int, level: int) -> str | None:
    if piece.color != "black" or piece.ai_trait:
        return piece.ai_trait
    piece.ai_trait = battle_personality(seed, level)
    return piece.ai_trait


def living_enemies(run) -> list:
    battle = run.battle
    if battle is not None:
        return [
            piece
            for piece in battle.game.board.pieces
            if piece.color == "black" and piece.col is not None and piece.ai_trait
        ]
    return [piece for piece in run.enemies if piece.color == "black" and piece.ai_trait and piece.col is not None]


def living_trait_counts(run) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for piece in living_enemies(run):
        counts[piece.ai_trait] = counts.get(piece.ai_trait, 0) + 1
    return [(trait, counts[trait]) for trait in AI_TRAITS if counts.get(trait, 0) > 0]
