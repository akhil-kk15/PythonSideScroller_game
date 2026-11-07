# PythonSideScroller_game

A Python/Pygame side-scroller game with two levels, platforming, combat,
collectibles, ladders, and enemies.

## Requirements

- Python 3.10 or newer
- A desktop environment that can open a Pygame window
- `pip`

## Clone and install

Clone the repository and enter its folder:

```bash
git clone https://github.com/akhil-kk15/PythonSideScroller_game.git
cd PythonSideScroller_game
```

Create and activate a virtual environment.

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Prepare the game assets

The combined sprite sheets are included in `assets/`. Generate the individual
sprites used by the game with:

```bash
python slice_assets.py
```

This creates the `assets/sliced/` directory. Run the command again whenever
the source sprite sheets change.

## Play the game

Start the game with:

```bash
python main.py
```

If the virtual environment is not activated, use `.venv/bin/python main.py` on
Linux/macOS or `.venv\Scripts\python.exe main.py` on Windows.

## Menus

The game starts in the main menu (Start Game, Controls, Quit). All menus work
with the mouse or with `W` / `S` (or the arrow keys) and `Enter`.

- **Pause menu:** `Esc` or `P` during the game. It offers Resume, Restart
  Level, Controls, Main Menu, and Quit Game. `Esc` closes it again. The game
  also pauses automatically when the window loses focus.
- **Game over / victory:** shows the final score with Play Again, Main Menu,
  and Quit.

## Controls

- **Move left/right:** `A` / `D` or the left/right arrow keys
- **Jump:** `Space`, `W`, or the up arrow
- **Drop through bridges:** hold `S` or down and press `Space`
- **Climb ladders:** `W` / `S` or the up/down arrow keys while touching a ladder
- **Attack:** `J`, `Z`, `X`, `F`, `K`, or left mouse click
- **Switch levels:** `1` for Emerald Grasslands, `2` for Goblin Stronghold
- **Restart level:** `R` or `Enter`
- **Pause:** `Esc` or `P`

## Test the project

There is no automated test suite yet. You can still check that all Python
files compile successfully:

```bash
python -m compileall -q *.py
```

Then launch the game and verify movement, jumping, combat, collectibles,
level switching, restarting, and quitting.
