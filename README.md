<div align="center">

# Knight's Quest: The Stolen Crown

**The goblins took the Golden Crown. One knight is going to take it back.**

A retro 2D action-platformer in Python. Two levels. One boss. No installer, no launcher, no excuses.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![pygame-ce](https://img.shields.io/badge/engine-pygame--ce-2E7D32)
![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-555)
![Input](https://img.shields.io/badge/input-keyboard%20%7C%20mouse%20%7C%20gamepad-C9A227)

<img src="docs/images/gameplay.gif" alt="Aldric fighting through the Dark Forest" width="720">

</div>

---

## The Story

The kingdom's Golden Crown has been stolen in the night. You are **Aldric**, a young knight with a sword, a shield and a promise. Cross the **Emerald Grasslands**, find the Gold Key, and descend into the **Goblin Stronghold**, where archers hold the walls and a Goblin Brute guards the key to the crown.

Five minutes of play. Real stakes: three lives, three hearts each, and a leaderboard that remembers.

## Why You'll Keep Playing

- **Combat with a pulse.** A three-hit sword combo, air slashes, and enemies that telegraph their swings. Watch the wind-up, dodge, then strike.
- **Five enemy types, five behaviours.** Slimes that chase, bats that swoop, warriors that wind up, archers that shoot, and a Goblin Brute whose swing cannot be interrupted.
- **Platforming that forgives you.** Coyote time and jump buffering mean the game honours the jump you meant to make. Tap to hop, hold to soar.
- **Secrets worth smashing.** Break crates, open chests, pull levers to reveal bonus gems.
- **Play your way.** Keyboard, mouse or any gamepad. Plug a controller in mid-level and it just works.
- **A story, told properly.** Animated pixel-art cutscenes open the quest, introduce the Stronghold, and close the ending.
- **A score to beat.** Your top five runs are saved locally, with the level and the date.

## See It

<table>
  <tr>
    <td><img src="docs/images/main-menu.png" alt="Main menu" width="100%"><br><sub><b>Main menu.</b> Mouse, keyboard or controller.</sub></td>
    <td><img src="docs/images/level1-start.png" alt="Level 1: Emerald Grasslands" width="100%"><br><sub><b>Level 1.</b> Emerald Grasslands: ladders, bridges, spikes.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/images/level1-door.png" alt="Key collected, locked door and cave exit" width="100%"><br><sub><b>The key.</b> Collect it, unlock the gate, reach the exit.</sub></td>
    <td><img src="docs/images/level2-combat.png" alt="Level 2: Dark Forest" width="100%"><br><sub><b>Level 2.</b> The Dark Forest: archers, levers, the Brute.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/images/pause-menu.png" alt="Pause menu" width="100%"><br><sub><b>Pause menu.</b> Resume, restart, controls, quit.</sub></td>
    <td><img src="docs/images/victory.png" alt="Victory screen with top 5 highscores" width="100%"><br><sub><b>Victory.</b> Quest complete, and your top five, saved.</sub></td>
  </tr>
</table>

---

## Quick Start

You need **Python 3.10 or newer** ([python.org/downloads](https://www.python.org/downloads/)). On Windows, tick **"Add python.exe to PATH"** in the installer.

**Windows (PowerShell or Command Prompt)**

```powershell
git clone https://github.com/akhil-kk15/PythonSideScroller_game.git
cd PythonSideScroller_game
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

**macOS and Linux**

```bash
git clone https://github.com/akhil-kk15/PythonSideScroller_game.git
cd PythonSideScroller_game
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

No Git? Click **Code → Download ZIP** on GitHub, unzip, open a terminal inside the folder that contains `main.py`, and run the last three lines above.

**Next time**, setup is already done. Run only `.venv\Scripts\python main.py` (Windows) or `.venv/bin/python main.py` (macOS/Linux).

> All sprites ship with the repository and are prepared automatically on first launch.

---

## Controls

| Action | Keyboard and mouse | Gamepad |
| :--- | :--- | :--- |
| Move | `A` `D` or `←` `→` | Left stick or D-pad |
| Jump (tap = hop, hold = high) | `Space`, `W` or `↑` | `A` or `LB` |
| Drop through a wooden bridge | Hold `S`/`↓`, press `Space` | Hold Down, press `A` |
| Climb ladders | `W` `S` or `↑` `↓` | Left stick or D-pad |
| Sword attack / air slash | `J` `Z` `X` `F` `K` or left click | `X` `B` `Y` `RB` or `RT` |
| Pause / resume | `Esc` or `P` | `Start` |
| Restart level | `R` or `Enter` | `Back` / `Select` |
| Menus | Mouse, or `W`/`S` + `Enter` | Stick or D-pad + `A` (`B` = back) |
| Cutscenes | `Enter` / `Space` / click = next, `Esc` = skip | `A` = next, `B` or `Start` = skip |

<details>
<summary><b>The in-game Controls screen</b></summary>
<br>
<img src="docs/images/controls.png" alt="In-game controls screen" width="640">
</details>

---

## How to Win

**Goal.** Take the Gold Key, unlock the gate, reach the cave exit. Do it twice. The second time, a Goblin Brute stands in your way.

**Survival.** You have **3 lives**, each with **3 hearts**. Lose all hearts and the level restarts. Lose all lives and the run ends. Potions restore a heart.

### Enemies

| Enemy | Health | Damage | Behaviour | Points |
| :--- | :---: | :---: | :--- | ---: |
| Slime | 1 | 1 | Patrols, then chases when you come close | 150 |
| Bat | 1 | 1 | Flies, then swoops | 200 |
| Goblin Warrior | 2 | 2 | Chases, raises its weapon, strikes. Dodge the wind-up | 300 |
| Goblin Archer | 2 | 1 | Holds position and fires arrows | 350 |
| Goblin Brute | 4 | 3 | Slow, heavy, and cannot be interrupted mid-swing | 800 |

### Scoring

| Pickup or action | Points |
| :--- | ---: |
| Coin | 100 |
| Blue gem | 250 |
| Health potion | 150 (plus one heart) |
| Gold key | 500 |
| Smash a crate or barrel | 50 |
| Open a chest | 300 (plus 3 coins, 1 gem) |
| Reach a level exit | 1,000 |

Pull a lever and three bonus gems appear nearby.

---

## Requirements Specification

A short, honest account of what this project does and what it expects from your machine.

### Functional requirements

| ID | Requirement |
| :--- | :--- |
| FR-1 | The player can move, jump (variable height), climb ladders, drop through bridges and attack with a three-hit combo. |
| FR-2 | Two playable levels with distinct layouts, parallax backgrounds, hazards (spikes) and interactive props (crates, chests, levers, locked gate). |
| FR-3 | Five enemy types with distinct AI: patrol and chase, swoop, telegraphed melee, ranged attack, and an uninterruptible boss swing. |
| FR-4 | Progression gated by a key and a locked gate in each level. |
| FR-5 | Health, lives, coins, gems and score shown in an always-on HUD. |
| FR-6 | Main, pause, controls, game-over and victory menus, operable by mouse, keyboard and gamepad. |
| FR-7 | Animated story cutscenes before Level 1, before Level 2 and at the ending. |
| FR-8 | A persistent top-five leaderboard stored in `highscores.txt`. |
| FR-9 | Gamepad support with hot-plugging, in Auto, XInput or DirectInput mode. |

### Non-functional requirements

| ID | Requirement |
| :--- | :--- |
| NFR-1 | Runs at a fixed **60 FPS** in a **1280 × 720** window. |
| NFR-2 | **Python 3.10+** and a single dependency: `pygame-ce`. |
| NFR-3 | Cross-platform: Windows, macOS and Linux. |
| NFR-4 | Zero setup beyond `pip install`. Sprites are sliced from the bundled sheets automatically on first launch. |
| NFR-5 | Input is forgiving by design: jump buffering and coyote time. |

### Out of scope

Online multiplayer, save slots beyond the leaderboard, and level editing.

---

## Architecture

```
main.py         Game loop, HUD, state machine, level interactions
player.py       Knight physics, ladders, jump buffering, combo attacks
level.py        Level 1 and 2 layouts, enemy AI, collectibles, projectiles
story.py        Animated pixel-art cutscenes
ui.py           Mouse, keyboard and gamepad menus
joystick.py     XInput and DirectInput controller support with hot-plug
highscores.py   Persistent top-five leaderboard
background.py   Parallax scrolling backgrounds
animation.py    Sprite animation system
slice_assets.py Cuts the master sprite sheets into individual PNGs
assets/         Sprite sheets, sliced sprites and backgrounds
```

### For developers

```bash
python main.py --controller-mode auto          # or: xinput, directinput
python -m compileall -q *.py                   # syntax check
python slice_assets.py                         # re-slice assets/base.jpg, knight.jpg, goblin.jpg
```

Press `1` or `2` in-game to jump straight to a level. Scores from a skipped run are not saved. Delete `highscores.txt` at any time to reset the leaderboard.

---

## Troubleshooting

<details>
<summary><b>"python", "py" or "python3" is not recognized</b></summary>

Python is missing or not on your `PATH`. Install Python 3.10+, and on Windows re-run the installer, choose **Modify**, and enable **Add python.exe to PATH**. Reopen your terminal.
</details>

<details>
<summary><b>"No such file or directory: requirements.txt" or "main.py"</b></summary>

Your terminal is not inside the game folder. `cd PythonSideScroller_game` (or `PythonSideScroller_game-main` for the ZIP) and try again.
</details>

<details>
<summary><b>"No module named pygame"</b></summary>

Start the game with the virtual environment's Python: `.venv\Scripts\python main.py` (Windows) or `.venv/bin/python main.py` (macOS/Linux).
</details>

<details>
<summary><b>PowerShell: "running scripts is disabled on this system"</b></summary>

You do not need to activate the environment. Call `.venv\Scripts\python` directly, as shown above.
</details>

<details>
<summary><b>Linux: "ensurepip is not available"</b></summary>

```bash
sudo apt update && sudo apt install -y python3-venv
```
</details>

<details>
<summary><b>My controller is not responding, or buttons feel swapped</b></summary>

Open **Controls** from the main or pause menu, check the Gamepad status line, and click **Mode** to switch between Auto, XInput (Xbox-style) and DirectInput (classic USB/Bluetooth). Or launch with `--controller-mode xinput` / `directinput`.
</details>

---

<div align="center">

**Ready, Aldric? The crown will not rescue itself.**

</div>
