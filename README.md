# Crownless

A 6×6 chess roguelike. A run is a short campaign: preview the enemy army, deploy your pieces, fight, then spend gold in the shop before the next level.

## Run

From the project folder:

```powershell
.\.venv\Scripts\python.exe main.py
```

The window opens at 1440×900 and can be resized. 1280×720 is supported. Art is loaded from paths next to `main.py`, so the working directory does not matter.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Flow

1. A new run starts with one pawn, knight, bishop, rook, queen, and king, plus 5 gold.
2. Level preview shows the enemy formation.
3. Deploy fills ranks 1 and 2 from the army. The king is always included and does not use an army slot. Other pieces fill the army capacity, which starts at 5. Survivors keep the squares you chose last battle. The battle screen is three columns: battle status on the left, the board in the center, and your army on the right. You can swap pieces, replace one from the reserve, or press Reset Formation before Start Battle.
4. Battle is fought by hand for both sides. Clear every enemy piece to win. If your king is captured, the run ends.
5. A win awards 3 gold and keeps the board up. A level-complete banner shows the reward, then Continue slides the board off to the left while the shop slides in from the right.
6. The shop Continue button slides the shop away and brings in the next level, with that enemy army already on the board.
7. Starting the battle keeps the board where it is and shows a short Battle Start banner.
8. After level 5, Continue fades to the run-complete screen instead of another shop. Losing the king shows Game Over.

## Scene changes

Scene changes are animated in the normal frame loop. Nothing waits on a timer. `game/scene_manager.py` asks `game/transitions/transition_manager.py` to slide or fade the outgoing scene and the incoming scene together. The dark brown background stays still. The board, pieces, relic row, and the left and right panels move as one group. The shop slides in as that group slides away. Shop cards follow the shop, with a short stagger. Clicks are ignored until the new scene has settled, then the shop cards use their normal hit boxes.

The timings live in `config/settings.py`:

- `VICTORY_BANNER_TIME` and `VICTORY_REWARD_TIME` — the level-complete banner
- `SCENE_SLIDE_TIME` — battle into the shop
- `SHOP_CARD_STAGGER` — delay between shop cards
- `LEVEL_PREVIEW_TIME` — shop into the next level
- `BATTLE_START_TIME` — the battle-start banner

## Shop

The shop offers three cards:

- A random piece for 5 gold. It joins your reserve and can be deployed next battle.
- A relic for 7 gold. It is chosen from the relics you do not already own.
- +1 army size for 12 gold. This raises how many non-king pieces you may deploy.

The reroll board costs 2 gold. It draws a new piece, a new relic, and restocks the piece and army-size cards. Gold you already spent stays spent. Continue leaves the shop without buying.

## Relics

Relics are permanent for the run. Each one is a data record plus an effect class. The battle loop does not special-case relic names. It publishes events, and the relics you own react to them.

Open the collection with the Relics button. Blood Contract can be activated on the level preview or the deployment screen. Capture relics such as Recruitment and Conversion run during the battle.

Special Piece traits live on the piece, not on the relic. The rules are in the trait modules described under Special pieces. Blood Contract assigns one at random through the trait manager. Recruitment starts a normal piece. Conversion's ghost is spawned afterward, on an empty square next to the bishop.

Recruitment, when you own it, adds the captured enemy to your side on the square your piece just left. A recruited piece can stay in your army after the battle even if you are over the deployment limit. The next deployment still uses that limit. Ghosts do not stay.

### Where the pieces live

- `game/relics/relic_data.py` holds names, flavor, descriptions, triggers, and shop availability.
- `game/relics/effects/` holds one effect class per relic.
- `game/relics/events.py` is the synchronous dispatcher.
- `rendering/relic_card.py` draws every card from the same layout.
- Artwork is optional. Put a shared frame at `assets/relics/card_background.png` and a picture at `assets/relics/art/<relic_id>.png`. Missing files use a parchment placeholder.

### Events

Effects subscribe with a priority. Lower priorities run first. Recruitment is 10 and Conversion is 20, so a capture fills the original square before a ghost looks for a neighbor. Chained publishes stop after 8 nested events. Spawning a piece does not count as another capture.

Hooks in use:

- `battle_start`
- `before_capture`
- `capture_resolved`
- `piece_moved`
- `piece_spawned`
- `piece_removed`
- `battle_end`
- `shop_enter`
- `relic_acquired`
- `relic_activated`
- `relic_visual_trigger`

### Relic row

Owned relics sit in a row above the chessboard during deployment and battle, in the order they were acquired. The row uses the same parchment cards and artwork as the collection. An empty row says "No Relics".

Up to five cards are visible. Further relics stay owned and keep working; the mouse wheel over the row, or the arrows at the ends, scrolls them into view.

Hovering a card lifts it and shows its name, saying, and effect. Left-click opens a larger card. Right-click, or Close, dismisses it. Blood Contract shows an Activate button there when it can still be used, and the click is passed to the relic manager. Passive relics have no Activate button.

A relic that can be activated and is not currently allowed is desaturated. A spent Blood Contract, or a Conversion that has already triggered this battle, is darkened and marked with a check. When a relic actually triggers, it publishes `relic_visual_trigger` and its card flashes gold. That flash is only visual. The effect has already resolved.

```python
from game.relics.events import visual_trigger

visual_trigger(dispatcher, owned.instance_id)
```

### Adding a relic

`GoldCharmEffect` in `game/relics/effects/gold_charm.py` is a complete extra relic. It is registered and defined, and `in_shop` is false, so the shop does not sell it. To sell a new relic, add a `RelicDef` with `in_shop=True` and an effect class:

```python
from game.relics.events import BATTLE_END, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("gold_charm")
class GoldCharmEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_END, self._on_battle_end, priority=40)

    def _on_battle_end(self, event) -> None:
        if event.payload.get("outcome") != "victory" or self.context is None:
            return
        self.context.run.gold += int(self.definition.parameters.get("gold", 1))
        visual_trigger(self.context.dispatcher, self.owned.instance_id)
```

Import the module from `game/relics/effects/__init__.py` so the decorator runs. Give the relic a stable id. Gameplay code should use that id, not the display name. Do not use `eval` or `exec`.

```python
RelicDef(
    id="gold_charm",
    name="Gold Charm",
    art="gold_charm.png",
    flavor_text="Victory leaves a coin in the cup.",
    description="After a victory, gain 1 gold.",
    effect_id="gold_charm",
    trigger="on_battle_end",
    parameters={"gold": 1},
    rarity="common",
    in_shop=True,
)
```

## Special pieces

A special piece is a normal chess piece with one extra trait. The trait is stored on `piece.trait` and stays with that piece id through movement, captures, deployment, the shop, and the army. Normal chess movement is unchanged unless the trait says otherwise. Each piece has at most one trait.

- Golden — Earn +2 Gold if this piece survives the battle. The bonus is added once, with the normal victory gold, and the result screen shows both amounts. A captured or removed Golden piece pays nothing. Opening the result screen again does not pay again.
- Ghost — Temporary piece. Disappears after battle. It can move and capture, then it is taken off the board after the other end-of-battle rewards, and it does not return to the army.
- Wooden — A piece that captures this cannot move for 2 turns. The capture turn does not count, and the other side's turns do not count. The locked piece cannot be selected. It can still be captured. A small lock is drawn on it. The lock is a status, separate from the Wooden trait, and it is dropped if that piece leaves the board.
- Wanted — Effect coming soon. A bright red crosshair is drawn behind the piece.
- Explosive — Effect coming soon. The piece is tinted and marked. It does not explode.

### Architecture

- `game/traits/trait_registry.py` holds the names and descriptions.
- `game/traits/trait_manager.py` assigns, clears, and reads a trait.
- `game/traits/effects/` holds one module per trait. Each module subscribes to the relic event dispatcher. There is no second event bus.
- `rendering/special_piece_renderer.py` tints a copy of the normal piece and caches that copy.
- `rendering/overlay_renderer.py` draws the crosshair, the explosive marks, the lock, and the hover tooltip.

Golden listens for the end of a victorious battle. Ghost removes its pieces on that same event, after Golden has been counted. Wooden listens for a resolved capture. Wanted and Explosive register a placeholder and do not change the rules.

### Assigning a trait

```python
run.traits.assign_trait(piece_id, "golden")
run.traits.get_trait(piece_id)
run.traits.remove_trait(piece_id)
```

Unknown trait ids are rejected. A piece that already has a trait is left alone unless you pass `overwrite=True`. The call updates the army piece and the battle copy when both exist, so the picture and the saved army stay in step. Blood Contract uses the overwrite. Recruitment does not pass a trait. Conversion asks for the ghost trait, and the manager assigns it.

### Adding a trait

Add a `TraitDef` in `game/traits/trait_registry.py`. Add `game/traits/effects/<id>.py` with a `register(dispatcher, context)` function that subscribes to an existing event. Call that function from `register_trait_handlers` in `game/traits/__init__.py`. Draw the extra look from `special_piece_renderer.py` or `overlay_renderer.py`. Leave the move generator alone unless the trait changes how the piece moves.

### Overlays

The files in `assets/pieces/normal/` stay as they are. Each special piece is the normal picture plus three readable layers: a tint or texture on the piece, a colored ring on the square, and a small badge in the top-right corner. Golden is a strong gold tint with a gold outline, a gold ring, and a star. Wanted keeps the original colors, with a thick red crosshair, a crimson ring, and a target badge. Explosive is an orange-red tint with crack lines, an orange ring, and a bomb badge. Ghost is a pale cyan piece at about 78% opacity, with a cyan outline, a blue ring, and a small orb. Wooden is a darker brown tint with grain lines, a brown ring, and a small log mark. There is no crown, cloak, smoke, chain, or explosion aura.

Tinted copies are cached by color, piece type, trait, size, and whether high readability is on. Resizing the window clears that cache. The ring stays on the square with the shadow. The tint, crosshair, cracks, and badge rise with the piece. Hovering a special piece shows its name in the trait color and its effect beside the square. `TRAIT_HIGH_READABILITY` in `config/settings.py` starts in the stronger look. Press F6 to switch to the quieter look and back.

## Board depth

The board stays on the same squares the mouse already uses. Depth is drawn around that grid. A soft shadow sits down and to the right of the frame. A dark lip along the lower edge gives the frame thickness. Each square keeps its existing art and gets a light top-left edge, a dark bottom-right edge, and a faint sheen. The opening inside the frame is shaded so the tiles look set into the wood. The original frame picture is not changed.

A selected square is an inset gold ring with a slow glow, not a flat box. Empty-move dots sit on the tile with a small contact shadow. Capture marks are inset on the square. Piece shadows and trait rings are drawn after those marks, and the lifted piece is drawn last.

Tune the depth in `config/settings.py`:

- `BOARD_SHADOW_OFFSET_X`, `BOARD_SHADOW_OFFSET_Y`, `BOARD_SHADOW_ALPHA` — the shadow under the board
- `BOARD_THICKNESS` — the dark lip on the lower frame
- `BOARD_RECESS` — how deep the tile opening looks
- `BOARD_BEVEL` — the inner tile edge
- `BOARD_HIGHLIGHT`, `BOARD_SHADE` — upper-left light and lower-right shade
- `BOARD_SELECT_GLOW` — the selected-square ring

The board is drawn as the shadow, the lower lip, the tiles, the frame, the recess, then the move marks, then piece shadows and rings, then the pieces. The selected piece is drawn last. Locks are drawn after that. Hovering a special piece shows its name and effect beside the square. Square positions are unchanged, so clicks still land on the same tiles. Cached edges are cleared when the window is resized.

## Piece miniatures

Board pieces are drawn as small tabletop figures on top of the existing artwork. The files in `assets/pieces/normal/` are not modified. Each piece gets a soft shadow on its square, a little shading along the base, and a faint highlight. Idle pieces stay on the board. `PIECE_IDLE_BOB` is 0, so they do not bob unless you raise it.

Selecting a piece lifts it, grows it slightly, and tilts it a few degrees. The shadow stays on the square, and it gets wider and softer while the piece is up. The piece bobs a little until you let go. Clicking it again, or clicking off it, eases it back down. A move carries it from that raised spot onto the destination square, then it settles. The motion is timed from the clock, so it stays smooth when the frame rate changes. It does not delay the move, and it does not change what is legal.

The same lift is used for normal pieces and for Golden, Wanted, Explosive, Ghost, and Wooden pieces. Ghost pieces stay pale. Dragging a piece off the army tray holds that figure above the cursor. Press F5 to draw each shadow outline and the square anchor while tuning.

The feel is configured in `config/settings.py`:

- `PIECE_LIFT_RATIO`, `PIECE_LIFT_MIN`, `PIECE_LIFT_MAX` — how high a selected piece rises
- `PIECE_SELECT_SCALE` — how much it grows while held
- `PIECE_TILT` — the lean, in degrees
- `PIECE_BOB_AMPLITUDE`, `PIECE_BOB_SPEED` — the float while it is held
- `PIECE_EASE_RATE` — how quickly it rises and settles
- `PIECE_SHADOW_ALPHA`, `PIECE_SHADOW_WIDTH`, `PIECE_SHADOW_HEIGHT`, `PIECE_SHADOW_LIFT_SPREAD`, `PIECE_SHADOW_OFFSET` — the contact shadow
- `PIECE_TRAVEL_TIME` — how long a move takes to reach the destination square
- `PIECE_IDLE_BOB` — resting motion, left at 0

### Trying traits

Press F4. The trait menu stays closed during a normal game. While it is open, click a piece on the board or in the army tray, then click a trait, or None to clear it. The overlay updates immediately. Those clicks assign traits instead of moving or deploying until you press F4 again.

### Trait visual test

`SPECIAL_PIECE_VISUAL_TEST` in `config/settings.py` is off, so a new launch starts the campaign. Press F7 to open a temporary board. The white pieces are a Golden pawn, a Wanted knight, an Explosive bishop, a Ghost rook, a Wooden queen, and a normal king. Every black piece stays normal. Rank 1 already alternates light and dark squares, and the pieces can move onto either color.

The board is a copy. Traits are assigned with `TraitManager` onto those copies. The army, gold, relics, and saved run are left alone. Leaving the test returns to the normal run. Press F7 to turn the test off, or to turn it back on with a fresh formation. F4 still edits traits on the pieces you are looking at. Hover a piece to read its name and effect. F6 compares the strong and quiet overlay styles.

## Controls

- Shop: click Buy on a card, click the reroll board, or click Continue.
- Deployment: click a piece in the army, then click a highlighted square. Click a deployed piece again to take it back. You can also drag a piece onto a square. Start Battle begins the fight once the king is deployed.
- Battle: click a piece of the side to move, then a highlighted square. Green dots are empty squares. Red outlines are captures. Both sides use the mouse.
- Relics opens the collection. The owned relics also sit above the board. Hover a card for its text, left-click it for a closer look, and right-click to close that view. Activate Blood Contract from that card, or from the collection, before the battle.
- The mouse wheel over the relic row scrolls when more than five relics are owned.
- F3 toggles the battle debug overlay.
- F4 opens the trait menu. Click a piece, then a trait. None clears it. Press F4 again to close the menu and return to normal play.
- F5 draws piece shadow bounds and anchors. Press it again to hide them.
- F6 switches special-piece overlays between the strong readable look and the quieter look.
- F7 turns the special-piece visual test on or off. Turning it on builds a fresh temporary board and does not change the army.
- Debug Win and Debug Loss end the current fight so the reward and run-over screens can be tried early.

## Rules

Pieces use their normal chess moves on a 6×6 board. Pawns promote to queens. Knights may jump. In a Crownless battle, kings can be captured, and check does not end the fight. The battle ends when every enemy piece is gone, or when your king is captured. Surviving pieces return to your army. Captured pieces are gone for the rest of the run, unless Recruitment or Conversion brings a copy onto your side.

Files are A–F. Rank 6 is the top of the board and rank 1 is the bottom.
