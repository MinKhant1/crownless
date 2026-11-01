from dataclasses import dataclass

from config.settings import VICTORY_GOLD
from game.relics.relic_data import relic_by_id


@dataclass(frozen=True)
class RewardRow:
    label: str
    amount: int
    style: str = "normal"
    source: str = ""
    counts_toward_gold: bool = True


@dataclass(frozen=True)
class FallenGroup:
    kind: str
    count: int
    trait: str | None = None
    category: str = "permanent"

    @property
    def name(self) -> str:
        kind = self.kind.replace("_", " ").title()
        if self.trait == "ghost":
            return f"Ghost {kind}"
        if self.trait:
            return f"{self.trait.replace('_', ' ').title()} {kind}"
        return kind


@dataclass(frozen=True)
class BattleSummary:
    battle_number: int
    gold_before: int
    gold_after: int
    army_count: int
    army_capacity: int
    surviving: int
    rows: tuple[RewardRow, ...] = ()
    fallen: tuple[FallenGroup, ...] = ()
    interest: int = 0

    @property
    def total_gold(self) -> int:
        return sum(row.amount for row in self.rows if row.counts_toward_gold)

    @property
    def fallen_count(self) -> int:
        return sum(group.count for group in self.fallen)

    @property
    def permanent_losses(self) -> int:
        return sum(group.count for group in self.fallen if group.category == "permanent")

    @property
    def temporary_losses(self) -> int:
        return sum(group.count for group in self.fallen if group.category == "temporary")

    @property
    def flawless(self) -> bool:
        return self.fallen_count == 0


def interest_amount(_run) -> int:
    """Return interest gold. finish_victory adds this on top of the battle reward."""
    return 0


def extra_reward_rows(_run) -> list[RewardRow]:
    """Rows for gold already paid during battle end and not covered by the built-in relic rows."""
    return []


def white_board_pieces(run) -> list[tuple[int, str, str | None]]:
    battle = run.battle
    if battle is None:
        return []
    return [
        (piece.id, piece.kind, piece.trait)
        for piece in battle.game.board.pieces
        if piece.color == "white"
    ]


def build_battle_summary(run, gold_before: int, relic_gold: int, reroll_gain: int, present: list[tuple[int, str, str | None]]) -> BattleSummary:
    kept = {piece.id for piece in run.army.pieces}
    deployed = set(run.deployment.placed)
    fallen = _fallen(run.battle_roster, deployed, kept, present)
    surviving = _surviving(run.battle_roster, deployed, kept, present)
    rows = _rows(run, relic_gold, reroll_gain)
    return BattleSummary(
        battle_number=run.level,
        gold_before=gold_before,
        gold_after=run.gold,
        army_count=sum(1 for piece in run.army.pieces if piece.kind != "king"),
        army_capacity=run.army.capacity,
        surviving=surviving,
        rows=tuple(rows),
        fallen=tuple(fallen),
        interest=interest_amount(run),
    )


def _rows(run, relic_gold: int, reroll_gain: int) -> list[RewardRow]:
    rows = [RewardRow("Battle Win", VICTORY_GOLD, "normal")]
    interest = interest_amount(run)
    remaining = relic_gold
    if interest > 0:
        rows.append(RewardRow("Interest", interest, "bonus"))
    remaining = _claim(rows, remaining, _golden_row(run))
    remaining = _claim(rows, remaining, _relic_gold_row(run, "flawless_victory"))
    remaining = _claim(rows, remaining, _relic_gold_row(run, "gold_charm"))
    for extra in extra_reward_rows(run):
        remaining = _claim(rows, remaining, extra)
    if remaining:
        rows.append(RewardRow("Other", remaining, "bonus"))
    crown = _relic_row(run, "collectors_crown", reroll_gain, "Shop Rerolls", counts_toward_gold=False)
    if crown is not None:
        rows.append(crown)
    return rows


def _claim(rows: list[RewardRow], remaining: int, row: RewardRow | None) -> int:
    if row is None or row.amount <= 0:
        return remaining
    if row.counts_toward_gold and row.amount > remaining:
        return remaining
    rows.append(row)
    if row.counts_toward_gold:
        return remaining - row.amount
    return remaining


def _golden_row(run) -> RewardRow | None:
    if run.golden_reward <= 0:
        return None
    return RewardRow("Golden Piece", run.golden_reward, "bonus", source="Trait")


def _relic_gold_row(run, relic_id: str) -> RewardRow | None:
    if relic_id == "flawless_victory":
        owned = run.relics.find(relic_id)
        if owned is None or owned.state.get("lost_piece"):
            return None
    amount = _relic_parameter(run, relic_id, "gold")
    return _relic_row(run, relic_id, amount, "")


def _relic_row(run, relic_id: str, amount: int, source: str, counts_toward_gold: bool = True) -> RewardRow | None:
    if amount <= 0 or not run.relics.owns(relic_id):
        return None
    definition = relic_by_id(relic_id)
    name = relic_id.replace("_", " ").title() if definition is None else definition.name
    return RewardRow(f"Relic: {name}", amount, "relic", source=source, counts_toward_gold=counts_toward_gold)


def _relic_parameter(run, relic_id: str, key: str) -> int:
    if not run.relics.owns(relic_id):
        return 0
    definition = relic_by_id(relic_id)
    if definition is None:
        return 0
    return int(definition.parameters.get(key, 0))


def _fallen(roster, deployed: set[int], kept: set[int], present: list[tuple[int, str, str | None]]) -> list[FallenGroup]:
    counts: dict[tuple[str, str | None, str], int] = {}
    roster_ids = set()
    for piece_id, kind, trait in roster:
        roster_ids.add(piece_id)
        if piece_id not in deployed or piece_id in kept:
            continue
        _count(counts, kind, trait, "temporary" if trait == "ghost" else "permanent")
    for piece_id, kind, trait in present:
        if piece_id in roster_ids or piece_id in kept:
            continue
        _count(counts, kind, trait, "temporary" if trait == "ghost" else "permanent")
    groups = [
        FallenGroup(kind, count, trait, category)
        for (kind, trait, category), count in counts.items()
    ]
    groups.sort(key=lambda group: (0 if group.category == "permanent" else 1, group.kind, group.trait or ""))
    return groups


def _count(counts: dict[tuple[str, str | None, str], int], kind: str, trait: str | None, category: str) -> None:
    key = (kind, trait, category)
    counts[key] = counts.get(key, 0) + 1


def _surviving(roster, deployed: set[int], kept: set[int], present: list[tuple[int, str, str | None]]) -> int:
    roster_ids = {piece_id for piece_id, _kind, _trait in roster}
    total = sum(1 for piece_id, _kind, _trait in roster if piece_id in deployed and piece_id in kept)
    total += sum(1 for piece_id, _kind, _trait in present if piece_id not in roster_ids and piece_id in kept)
    return total
