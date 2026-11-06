# PythonSideScroller_game

This is a group project where we are making a Python side-scroller game.

## Running the Game

Activate the virtual environment and run `main.py` (or `player.py`):

```bash
.venv/bin/python main.py
```

To re-slice the combined sprite sheets (`assets/base.jpg`, `assets/knight.jpg`, `assets/goblin.jpg`) into individual transparent PNGs under `assets/sliced/`:

```bash
.venv/bin/python slice_assets.py
```

## Controls

- **Move Left / Right**: `A` / `D` or `Left` / `Right` Arrow keys
- **Jump**: `Space`, `W`, or `Up` Arrow (hold for higher jump; `S` + `Space` drops through wooden bridges)
- **Climb Ladders**: `W` / `S` or `Up` / `Down` Arrow when touching a ladder
- **Sword Attack**: `J`, `Z`, `X`, `F`, `K`, or `Left Mouse Click` (can also stomp enemies from above!)
- **Switch Levels**: `1` (Level 1: Emerald Grasslands) or `2` (Level 2: Goblin Stronghold)
- **Restart**: `R` or `Enter`
- **Quit**: `Esc`

