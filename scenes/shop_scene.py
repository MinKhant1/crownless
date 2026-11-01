from game.run_state import RunState
from rendering.shop_layout import ShopLayout


def handle_shop_click(run: RunState, pos: tuple[int, int], layout: ShopLayout) -> str | None:
    if layout.continue_button.collidepoint(pos):
        return "leave"
    if layout.reroll.collidepoint(pos):
        run.reroll_shop()
        return
    if layout.buys[0].collidepoint(pos):
        if run.shop.piece_sold:
            run.buy_piece()
        return
    if layout.buys[2].collidepoint(pos):
        run.buy_army()
