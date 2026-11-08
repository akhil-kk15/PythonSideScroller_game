# Knight's Quest: The Stolen Crown

A retro 2D action-platformer built with Python and Pygame. Play as **Aldric**, battle through the **Emerald Grasslands** and the **Goblin Stronghold**, dodge traps, smash crates, defeat the Goblin Brute, and bring back the kingdom's stolen Golden Crown!

---

## Play in 60 Seconds (Zero-Effort Setup)

### Before You Start: Install Python (If You Don't Have It)
You only need **Python 3.10 or newer**:
- Download it from **[python.org/downloads](https://www.python.org/downloads/)**.
- **Windows users:** On the very first installer screen, check the box that says **"Add python.exe to PATH"** before clicking *Install Now*.

---

### Option 1: Copy & Paste (If You Have Git)

Open your terminal (**PowerShell** or **Command Prompt** on Windows, **Terminal** on macOS/Linux), copy the block for your system, paste it in, and press **Enter** — the game will install and launch automatically!

#### Windows (PowerShell or Command Prompt)
```powershell
git clone https://github.com/akhil-kk15/PythonSideScroller_game.git
cd PythonSideScroller_game
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```
> *Tip: If `py` isn't recognized on your Windows PC, replace `py` with `python` on line 3.*

#### macOS & Linux
```bash
git clone https://github.com/akhil-kk15/PythonSideScroller_game.git
cd PythonSideScroller_game
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

---

### Option 2: No Git? Download the ZIP Instead!

1. At the top of the GitHub page, click the green **`<> Code`** button and click **`Download ZIP`**.
2. **Unzip / Extract** the downloaded file anywhere you like (for example, your `Desktop` or `Downloads` folder).
3. Open the extracted folder **until you see `main.py` inside it**, then open a terminal right there:
   - **Windows:** Right-click an empty spot inside that folder and click **"Open in Terminal"** (or click the folder's address bar at the top, type `cmd`, and press **Enter**).
   - **macOS:** Go one level up in Finder, right-click (or two-finger click) the game folder, and choose **"New Terminal at Folder"**.
   - **Linux:** Right-click an empty spot inside that folder and choose **"Open in Terminal"**.
4. Copy and paste the command block below and press **Enter**:

**Windows:**
```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

**macOS & Linux:**
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

*(All game sprites are already included and automatically prepared on first launch — no extra setup steps needed!)*

---

### Playing Again Next Time

Once you've done the setup above once, you **never** need to install anything again. Next time you want to play, open a terminal in the game folder and run just this one line:

- **Windows:**
  ```powershell
  .venv\Scripts\python main.py
  ```
- **macOS & Linux:**
  ```bash
  .venv/bin/python main.py
  ```

---

## Controls

Play with **Keyboard & Mouse** or **any Gamepad / Controller** (Xbox, PlayStation, 8BitDo, Logitech, or generic USB/Bluetooth). You can plug in a controller at any time — even in the middle of a level!

| Action | Keyboard & Mouse | Controller (Gamepad) |
| :--- | :--- | :--- |
| **Move Left / Right** | `A` / `D` or `Left` / `Right` Arrows | Left Stick or D-Pad |
| **Jump** *(tap = hop, hold = high jump)* | `Space`, `W`, or `Up` Arrow | `A` (bottom button) or `LB` |
| **Drop Down Through Wooden Bridges** | Hold `S` (or `Down`) + press `Space` | Hold `Down` + press `A` |
| **Climb Ladders** | `W` / `S` or `Up` / `Down` Arrows | Left Stick or D-Pad `Up` / `Down` |
| **Sword Attack / Air Slash** | `J`, `Z`, `X`, `F`, `K`, or `Left Click` | `X`, `B`, `Y`, `RB`, or `RT` |
| **Pause / Resume** | `Esc` or `P` | `Start` / `Menu` |
| **Restart Current Level** | `R` or `Enter` | `Back` / `Select` / `View` |
| **Navigate Menus** | Mouse, or `W`/`S` / Arrows + `Enter` | Left Stick / D-Pad + `A` (`B` = Back) |
| **Story Cutscenes** | `Enter` / `Space` / Click = Next, `Esc` = Skip | `A` = Next, `B` or `Start` = Skip |

---

## Troubleshooting (Quick Fixes)

<details>
<summary><b>"python / py / python3 is not recognized"</b></summary>

Python isn't installed or wasn't added to your `PATH`.
- Install Python 3.10+ from **[python.org/downloads](https://www.python.org/downloads/)**.
- On Windows, re-run the Python installer, click **Modify**, and make sure **"Add Python to environment variables" / "Add python.exe to PATH"** is checked. Close and reopen your terminal afterward.
</details>

<details>
<summary><b>"No such file or directory: 'requirements.txt'" or "'main.py'"</b></summary>

Your terminal isn't inside the game's folder yet. Use `cd` to enter the folder first (for example `cd PythonSideScroller_game` or `cd PythonSideScroller_game-main` if you downloaded the ZIP), then run the commands again.
</details>

<details>
<summary><b>"No module named 'pygame'" when starting the game</b></summary>

Make sure you start the game using the virtual environment's Python rather than system Python:
- **Windows:** `.venv\Scripts\python main.py`
- **macOS / Linux:** `.venv/bin/python main.py`
</details>

<details>
<summary><b>Windows PowerShell says "running scripts is disabled on this system"</b></summary>

You don't need `.venv\Scripts\Activate.ps1`! Just run `.venv\Scripts\python main.py` directly as shown in this guide — it works in PowerShell with zero security settings changes.
</details>

<details>
<summary><b>Linux (Ubuntu / Mint / Debian) says "ensurepip is not available" or "python3-venv"</b></summary>

Install the standard Python virtual environment package once, then re-run the setup block:
```bash
sudo apt update && sudo apt install -y python3-venv
```
</details>

<details>
<summary><b>My controller isn't working or the buttons feel swapped</b></summary>

1. Open **Controls** from the Main Menu or Pause Menu.
2. Check the live **Gamepad** status line at the bottom of the panel.
3. Click the **`Mode: Auto (Both)`** button to switch between **Auto**, **XInput** (Xbox-style), and **DirectInput** (classic USB/Bluetooth pads).
4. You can also choose a mode at launch:
   ```bash
   python main.py --controller-mode auto          # default
   python main.py --controller-mode xinput
   python main.py --controller-mode directinput
   ```
</details>

---

## For Developers & Modders

- **Testing level-jump keys:** Press `1` or `2` during gameplay to jump directly to Level 1 or Level 2 (highscores are not saved for that run; delete `highscores.txt` anytime to reset saved scores).
- **Re-slice sprite sheets:** If you edit the master sprite sheets in `assets/` (`base.jpg`, `knight.jpg`, `goblin.jpg`), regenerate all PNGs in `assets/sliced/` with:
  ```bash
  .venv/bin/python slice_assets.py        # macOS / Linux
  .venv\Scripts\python slice_assets.py    # Windows
  ```
- **Syntax / compile check:**
  ```bash
  .venv/bin/python -m compileall -q *.py
  ```
- **Code structure:**
  - `main.py` — game loop, HUD, interactions, state management
  - `player.py` — knight physics, ladders, jump buffering/coyote time, 3-hit sword combo
  - `level.py` — Level 1 & Level 2 layouts, tile/ladder carving, enemy AI, collectibles
  - `story.py` — animated pixel-art story cutscenes
  - `ui.py` — mouse/keyboard/controller menus
  - `joystick.py` — cross-platform XInput & DirectInput hot-plug controller support
  - `highscores.py` — persistent top-5 leaderboard (`highscores.txt`)
  - `background.py` & `animation.py` — parallax backgrounds and sprite animation system
