from game.run_state import RunState
from rendering.shop_layout import ShopLayout


def handle_shop_click(run: RunState, pos: tuple[int, int], layout: ShopLayout) -> str | None:
    if layout.continue_button.collidepoint(pos):
        pending = run.shop.unclaimed_collection()
        if pending is not None:
            run.shop.collection_open = pending
            run.notice = "Choose a reward"
            return None
        return "leave"
    if layout.reroll.collidepoint(pos):
        run.reroll_shop()
        return None
    return None
