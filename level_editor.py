"""Interactive drag-and-drop Level Editor and Sprite Sheet Slicer for Knight's Quest."""

import copy
import json
import math
import os
import shutil
import subprocess
import sys
import pygame

import sounds
from slice_assets import (
    BASE_SPRITES,
    GOBLIN_SPRITES,
    KNIGHT_SPRITES,
    extract_sprite,
    slice_all_assets,
)
from level import (
    TILE_SIZE,
    AssetLibrary,
    Level,
    VFXParticle,
    default_level_json_path,
    get_available_levels,
    get_levels_dir,
)
from player import Player, load_player_sprites
from titlebar import BAR_HEIGHT, TitleBar, create_opaque_surface, create_window, shift_mouse_event, toggle_fullscreen
from ui import draw_squircle

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
EDITOR_TITLE = "Knight's Quest - Level Editor & Texture Slicer"

# Layout constants (within 1280x720 screen area).
TOPBAR_H = 44
STATUSBAR_H = 26
LEFT_PANEL_W = 244
RIGHT_PANEL_W = 252
CANVAS_X = LEFT_PANEL_W
CANVAS_Y = TOPBAR_H
CANVAS_W = SCREEN_WIDTH - LEFT_PANEL_W - RIGHT_PANEL_W  # 784
CANVAS_H = SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H - 28  # 622
MINIMAP_Y = CANVAS_Y + CANVAS_H
MINIMAP_H = 28

# Slicer layout constants.
SLICER_VIEW_W = 860
SLICER_PANEL_X = SLICER_VIEW_W
SLICER_PANEL_W = SCREEN_WIDTH - SLICER_VIEW_W


def sync_editor_layout(vw: int, vh: int) -> None:
    """Update layout dimensions to match the native viewport size."""
    global SCREEN_WIDTH, SCREEN_HEIGHT, CANVAS_W, CANVAS_H, MINIMAP_Y
    global SLICER_VIEW_W, SLICER_PANEL_X, SLICER_PANEL_W
    SCREEN_WIDTH = max(1280, vw)
    SCREEN_HEIGHT = max(720, vh)
    CANVAS_W = SCREEN_WIDTH - LEFT_PANEL_W - RIGHT_PANEL_W
    CANVAS_H = SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H - MINIMAP_H
    MINIMAP_Y = CANVAS_Y + CANVAS_H
    SLICER_PANEL_W = 420
    SLICER_VIEW_W = SCREEN_WIDTH - SLICER_PANEL_W
    SLICER_PANEL_X = SLICER_VIEW_W

# Colors matching the game's dark medieval HUD palette.
BG_DARK = (18, 22, 32)
PANEL_BG = (26, 31, 46)
PANEL_HEADER = (34, 41, 60)
CARD_BG = (36, 43, 64)
CARD_HOVER = (50, 60, 88)
CARD_SELECTED = (62, 76, 112)
BORDER_COL = (78, 90, 120)
HIGHLIGHT_COL = (255, 215, 75)
ACCENT_BLUE = (95, 175, 255)
ACCENT_GREEN = (85, 215, 125)
ACCENT_RED = (235, 75, 80)
TEXT_MAIN = (235, 242, 255)
TEXT_DIM = (165, 178, 205)

# Color-coded collision / object type badges.
TYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "solid": (75, 215, 110),
    "one_way": (80, 200, 255),
    "ladder": (245, 170, 65),
    "spike": (245, 75, 75),
    "slope_down_right": (235, 215, 75),
    "slope_up_right": (235, 215, 75),
    "decoration": (160, 170, 195),
    "destructible": (215, 145, 85),
    "chest": (255, 215, 70),
    "lever": (190, 140, 255),
    "locked_door": (255, 130, 70),
    "collectible": (105, 225, 255),
    "enemy": (245, 90, 165),
    "spawn": (90, 255, 160),
    "exit": (255, 225, 95),
}

TYPE_LABELS: dict[str, str] = {
    "solid": "Solid Tile",
    "one_way": "One-Way Plat",
    "ladder": "Ladder",
    "spike": "Spike Hazard",
    "slope_down_right": "Slope Down \\",
    "slope_up_right": "Slope Up /",
    "decoration": "Decoration",
    "destructible": "Destructible",
    "chest": "Treasure Chest",
    "lever": "Lever Switch",
    "locked_door": "Locked Door",
    "collectible": "Collectible",
    "enemy": "Enemy AI",
    "spawn": "Player Spawn",
    "exit": "Cave Exit",
}

ALL_OBJECT_TYPES = list(TYPE_LABELS.keys())


class PaletteItem:
    """Represents a draggable texture/object template in the editor palette."""

    def __init__(
        self,
        category: str,
        name: str,
        ref: str,
        obj_type: str,
        default_w: int,
        default_h: int,
        layer: int = 1,
        props: dict | None = None,
    ):
        self.category = category  # "Tiles", "Props", "Items", "Enemies", "Custom", "Special"
        self.name = name
        self.ref = ref
        self.obj_type = obj_type
        self.default_w = default_w
        self.default_h = default_h
        self.layer = layer
        self.props = props or {}


def load_custom_manifest(sliced_dir: str) -> dict[str, dict]:
    """Load saved metadata for custom-sliced textures."""
    manifest_path = os.path.join(sliced_dir, "custom", "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_custom_manifest(sliced_dir: str, manifest: dict[str, dict]) -> None:
    """Save metadata for custom-sliced textures."""
    custom_dir = os.path.join(sliced_dir, "custom")
    os.makedirs(custom_dir, exist_ok=True)
    manifest_path = os.path.join(custom_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def build_palette(assets: AssetLibrary) -> list[PaletteItem]:
    """Construct the palette of all pre-sliced and custom-sliced textures."""
    items: list[PaletteItem] = []

    # 1. Tiles.
    tile_defs = [
        ("Grass Block 1", "tiles:grass_1", "solid", 64, 64),
        ("Grass Block 2", "tiles:grass_2", "solid", 64, 64),
        ("Grass Vines 1", "tiles:grass_vines_1", "solid", 64, 64),
        ("Grass Vines 2", "tiles:grass_vines_2", "solid", 64, 64),
        ("Grass Vines 3", "tiles:grass_vines_3", "solid", 64, 64),
        ("Grass Wide", "tiles:grass_vines_wide", "solid", 128, 64),
        ("Deep Dirt", "tiles:dirt_single", "solid", 64, 64),
        ("Dirt Tall", "tiles:dirt_narrow", "solid", 64, 128),
        ("Moss Pillar", "tiles:moss_pillar", "solid", 64, 128),
        ("Moss L-Block", "tiles:moss_l", "solid", 128, 128),
        ("Hill Slope \\", "tiles:hill_slope", "slope_down_right", 128, 64),
        ("Bridge Full", "tiles:bridge_full", "one_way", 128, 64),
        ("Bridge Plank", "tiles:bridge_plank", "one_way", 128, 32),
        ("Ladder Seg", "tiles:ladder_seg", "ladder", 48, 64),
        ("Ladder Tall", "tiles:ladder_tall", "ladder", 48, 192),
        ("Spike Block 1", "tiles:spike_1", "spike", 64, 80),
        ("Spike Block 2", "tiles:spike_2", "spike", 64, 80),
        ("Cave Exit", "tiles:cave_exit", "exit", 128, 128),
    ]
    for label, ref, otype, w, h in tile_defs:
        layer = 0 if otype == "exit" else 1
        items.append(PaletteItem("Tiles", label, ref, otype, w, h, layer=layer))

    # 2. Props & Interactables.
    prop_defs = [
        ("Crate (Coin)", "props:crate", "destructible", 54, 54, 2, {"kind": "crate", "drop": "coin"}),
        ("Barrel (Potion)", "props:barrel", "destructible", 48, 56, 2, {"kind": "barrel", "drop": "potion"}),
        ("Treasure Chest", "props:chest_closed", "chest", 60, 54, 2, {}),
        ("Lever Switch", "props:lever_off", "lever", 36, 56, 2, {}),
        ("Locked Door", "props:door_locked", "locked_door", 60, 128, 2, {}),
        ("Campfire", "props:campfire", "decoration", 84, 58, 0, {}),
        ("Banner", "props:banner", "decoration", 52, 108, 0, {}),
        ("Barricade", "props:barricade", "solid", 96, 58, 1, {}),
        ("Bones", "props:bones", "decoration", 64, 40, 0, {}),
        ("Loot Bag", "props:loot_bag", "decoration", 40, 48, 0, {}),
    ]
    for label, ref, otype, w, h, layer, props in prop_defs:
        items.append(PaletteItem("Props", label, ref, otype, w, h, layer=layer, props=props))

    # 3. Collectibles.
    for kind, label in (("coin", "Gold Coin"), ("gem", "Blue Gem"), ("key", "Gold Key"), ("potion", "Health Potion")):
        surf = assets.get_base_surface(f"items:{kind}")
        w, h = surf.get_size() if surf else (36, 36)
        items.append(
            PaletteItem("Items", label, f"items:{kind}", "collectible", w, h, layer=2, props={"kind": kind})
        )

    # 4. Enemies.
    enemy_defs = [
        ("Slime", "slime", 48, 42),
        ("Bat", "bat", 62, 40),
        ("Goblin Warrior", "goblin_warrior", 44, 60),
        ("Goblin Archer", "goblin_archer", 44, 60),
        ("Goblin Brute", "goblin_brute", 68, 82),
        ("Goblin Scout", "goblin_scout", 42, 54),
    ]
    for label, kind, w, h in enemy_defs:
        items.append(
            PaletteItem(
                "Enemies",
                label,
                f"enemies:{kind}",
                "enemy",
                w,
                h,
                layer=2,
                props={"kind": kind},
            )
        )

    # 5. Custom sliced textures from `assets/sliced/custom/`.
    assets.reload_custom()
    manifest = load_custom_manifest(assets.sliced_dir)
    for key, surf in sorted(assets.custom.items()):
        meta = manifest.get(key, {})
        otype = meta.get("obj_type", "solid")
        sw, sh = surf.get_size()
        w = int(meta.get("w", sw))
        h = int(meta.get("h", sh))
        layer = int(meta.get("layer", 0 if otype == "decoration" else 1))
        items.append(
            PaletteItem("Custom", key, f"custom:{key}", otype, w, h, layer=layer, props=meta.get("props", {}))
        )

    # 6. Special markers.
    items.append(PaletteItem("Special", "Player Spawn", "special:spawn", "spawn", 38, 62, layer=2))
    items.append(PaletteItem("Special", "Cave Exit", "tiles:cave_exit", "exit", 128, 128, layer=0))

    return items


def draw_checkerboard(surface: pygame.Surface, rect: pygame.Rect, cell: int = 8) -> None:
    """Draw a dark transparency checkerboard inside `rect`."""
    c1 = (32, 36, 48)
    c2 = (46, 52, 68)
    prev_clip = surface.get_clip()
    surface.set_clip(rect)
    surface.fill(c1, rect)
    for y in range(rect.top, rect.bottom, cell):
        row_idx = (y - rect.top) // cell
        for x in range(rect.left, rect.right, cell):
            col_idx = (x - rect.left) // cell
            if (row_idx + col_idx) % 2 == 1:
                surface.fill(c2, (x, y, cell, cell))
    surface.set_clip(prev_clip)


class LevelEditorApp:
    """Main application class for the Level Editor, Sprite Sheet Slicer, and Playtester."""

    def __init__(self, assets_dir: str = "assets", initial_level: int = 1):
        self.assets_dir = assets_dir
        self.sliced_dir = slice_all_assets(assets_dir, force=False)
        self.assets = AssetLibrary(self.sliced_dir)
        self.player_sprites = load_player_sprites(self.sliced_dir)
        self.palette: list[PaletteItem] = build_palette(self.assets)

        # Fonts.
        self.font_xs = pygame.font.SysFont("dejavusans,arial,sans-serif", 12, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans,arial,sans-serif", 14, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans,arial,sans-serif", 18, bold=True)
        self.font_lg = pygame.font.SysFont("dejavusans,arial,sans-serif", 32, bold=True)

        # Editor modes: "editor", "slicer", "playtest".
        self.mode = "editor"

        # Palette filter & scroll.
        self.categories = ["All", "Tiles", "Props", "Items", "Enemies", "Custom", "Special"]
        self.active_category = "All"
        self.palette_scroll = 0
        self.selected_palette_item: PaletteItem | None = self.palette[0] if self.palette else None

        # Active level state.
        self.current_level_num = initial_level
        self.level_name = "Level 1: Emerald Grasslands"
        self.background_id = 1
        self.level_width = 56 * TILE_SIZE
        self.level_height = 720
        self.ground_y = 10 * TILE_SIZE
        self.banner_message = ""
        self.objects: list[dict] = []
        self.next_obj_id = 1

        # Undo / Redo stacks (snapshots of `self.objects`).
        self.undo_stack: list[list[dict]] = []
        self.redo_stack: list[list[dict]] = []

        # Camera & canvas settings.
        self.cam_x = 0.0
        self.cam_y = 64.0  # Default vertical scroll so rows 1..11 (including ground row 10) are centered
        self.grid_snap = True
        self.grid_size = TILE_SIZE  # 64, 32, or 16
        self.show_hitboxes = True

        # Selection & drag state on the level canvas.
        self.selected_obj_id: int | None = None
        self.dragging_from_palette: PaletteItem | None = None
        self.dragging_canvas_obj: bool = False
        self.drag_offset = (0, 0)
        self.drag_start_snapshot: list[dict] | None = None
        self.resizing_handle: str | None = None  # "nw", "n", "ne", "e", "se", "s", "sw", "w"
        self.resize_initial_rect: tuple[int, int, int, int] = (0, 0, 64, 64)
        self.resize_mouse_start: tuple[int, int] = (0, 0)
        self.dragging_patrol_handle: str | None = None  # "min" or "max"
        self.painting_brush: bool = False
        self.painted_cells: set[tuple[int, int]] = set()
        self.panning_canvas: bool = False
        self.pan_start_mouse: tuple[int, int] = (0, 0)
        self.pan_start_cam: tuple[float, float] = (0.0, 0.0)
        self.dragging_minimap: bool = False

        # Status notification toast.
        self.status_text = "Tip: Drag any texture from the left palette onto the level canvas!"
        self.status_timer = 300

        # Sprite Sheet Slicer state.
        self.sheet_files = self._discover_sheets()
        self.active_sheet_idx = 0
        self.sheet_surfaces: dict[str, pygame.Surface] = {}
        self.slicer_zoom = 0.5
        self.slicer_pan_x = 20.0
        self.slicer_pan_y = 20.0
        self.slicer_panning = False
        self.slicer_pan_start = (0, 0)
        self.slicer_crop_rect: pygame.Rect = pygame.Rect(94, 85, 177, 183)  # Default: grass_block_1
        self.slicer_selecting = False
        self.slicer_select_start = (0, 0)
        self.slicer_Moving_crop = False
        self.slicer_move_offset = (0, 0)
        self.slicer_resizing_handle: str | None = None
        self.slicer_resize_start_rect = pygame.Rect(0, 0, 10, 10)
        self.slicer_resize_start_pt = (0, 0)
        self.slicer_remove_bg = True
        self.slicer_remove_interior = False
        self.slicer_auto_trim = True
        self.slicer_strict_bg = False
        self.slicer_show_predefined = True
        self.slicer_target_cat = "Custom"
        self.slicer_default_type = "solid"
        self.slicer_scale_mode = "tile_64"  # "tile_64", "height_64", "original", "wide_128", "tall_128"
        self.slicer_name_text = self._next_custom_slice_name()
        self.slicer_editing_name = False
        self.slicer_preview_surf: pygame.Surface | None = None
        self.slicer_preview_dirty = True
        self.slicer_preview_card_rect = pygame.Rect(0, 0, 1, 1)

        # Playtest state.
        self.playtest_level: Level | None = None
        self.playtest_player: Player | None = None
        self.playtest_cam_x = 0.0
        self.playtest_step_timer = 0

        # Level name editing & Image Importer Modal state.
        self.editing_level_name = False
        self.image_modal_open = False
        self.modal_dir = os.path.abspath(self.assets_dir)
        self.modal_entries: list[tuple[str, bool]] = []  # (name, is_dir)
        self.modal_scroll = 0
        self.modal_selected_path: str | None = None
        self.modal_preview_surf: pygame.Surface | None = None
        self.modal_remove_bg = False

        # Load initial level.
        self.load_level_slot(initial_level)
        self._update_slicer_preview()

    # ------------------------------------------------------------------
    # Level loading, saving, and undo/redo management
    # ------------------------------------------------------------------
    def _set_status(self, message: str, duration: int = 240) -> None:
        self.status_text = message
        self.status_timer = duration

    def _push_undo(self, snapshot: list[dict] | None = None) -> None:
        snap = copy.deepcopy(snapshot if snapshot is not None else self.objects)
        self.undo_stack.append(snap)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> None:
        if not self.undo_stack:
            self._set_status("Nothing to undo.")
            return
        self.redo_stack.append(copy.deepcopy(self.objects))
        self.objects = self.undo_stack.pop()
        self._ensure_valid_selection()
        self._set_status("Undo applied.")

    def redo(self) -> None:
        if not self.redo_stack:
            self._set_status("Nothing to redo.")
            return
        self.undo_stack.append(copy.deepcopy(self.objects))
        self.objects = self.redo_stack.pop()
        self._ensure_valid_selection()
        self._set_status("Redo applied.")

    def _ensure_valid_selection(self) -> None:
        if self.selected_obj_id is not None and self.get_selected_obj() is None:
            self.selected_obj_id = None

    def get_selected_obj(self) -> dict | None:
        if self.selected_obj_id is None:
            return None
        for obj in self.objects:
            if obj["id"] == self.selected_obj_id:
                return obj
        return None

    def get_levels_list(self) -> list[int]:
        """Return all available level numbers (including the currently edited level)."""
        return sorted(set(get_available_levels()) | {self.current_level_num})

    def create_new_level(self) -> int:
        """Create and save a brand-new level (Level N+1) and switch to it."""
        new_num = max(self.get_levels_list()) + 1
        self.load_level_slot(new_num, force_default=True)
        self.save_current_level()
        self._set_status(f"Created Level {new_num}! Drag textures onto the canvas to build it.")
        return new_num

    def cycle_level(self, delta: int) -> None:
        """Switch to the previous or next available level."""
        lvls = self.get_levels_list()
        if not lvls:
            return
        idx = lvls.index(self.current_level_num) if self.current_level_num in lvls else 0
        next_lvl = lvls[(idx + delta) % len(lvls)]
        self.load_level_slot(next_lvl)

    def delete_current_level(self) -> None:
        """Delete a custom level (Level 3+) or reset Level 1/2 to built-in default."""
        path = default_level_json_path(self.current_level_num)
        if self.current_level_num <= 2:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self.load_level_slot(self.current_level_num, force_default=True)
            self._set_status(f"Reset Level {self.current_level_num} to built-in default.")
            return

        removed_num = self.current_level_num
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        remaining = get_available_levels()
        target = max((n for n in remaining if n < removed_num), default=remaining[-1])
        self.load_level_slot(target)
        sounds.play("hit")
        self._set_status(f"Deleted Level {removed_num}; switched to Level {target}.")

    def open_image_modal(self, start_dir: str | None = None) -> None:
        """Open the in-editor Visual Image Importer modal."""
        self.image_modal_open = True
        if start_dir and os.path.isdir(start_dir):
            self.modal_dir = os.path.abspath(start_dir)
        elif not os.path.isdir(self.modal_dir):
            self.modal_dir = os.path.expanduser("~")
        self._refresh_modal_entries()

    def _refresh_modal_entries(self) -> None:
        self.modal_entries.clear()
        self.modal_scroll = 0
        try:
            names = sorted(os.listdir(self.modal_dir), key=lambda s: s.lower())
        except OSError:
            names = []
        dirs = []
        files = []
        valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
        for n in names:
            if n.startswith("."):
                continue
            full = os.path.join(self.modal_dir, n)
            if os.path.isdir(full):
                dirs.append((n, True))
            elif n.lower().endswith(valid_exts):
                files.append((n, False))
        self.modal_entries = dirs + files

    def _select_modal_file(self, path: str) -> None:
        self.modal_selected_path = path
        try:
            self.modal_preview_surf = pygame.image.load(path).convert_alpha()
        except pygame.error:
            self.modal_preview_surf = None

    def _open_native_file_dialog(self) -> str | None:
        """Try opening a native OS file dialog via zenity, kdialog, or tkinter."""
        for cmd in (
            ["zenity", "--file-selection", "--title=Select Image File", "--file-filter=Images | *.png *.jpg *.jpeg *.bmp *.webp"],
            ["kdialog", "--getopenfilename", self.modal_dir, "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)"],
        ):
            if shutil.which(cmd[0]):
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
                    chosen = res.stdout.strip()
                    if res.returncode == 0 and chosen and os.path.isfile(chosen):
                        return chosen
                    return None
                except (OSError, subprocess.SubprocessError):
                    pass
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            chosen = filedialog.askopenfilename(
                initialdir=self.modal_dir,
                title="Select Image File",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All Files", "*.*")],
            )
            root.destroy()
            if chosen and os.path.isfile(chosen):
                return chosen
        except Exception:
            pass
        return None

    def import_image_file(self, path: str, as_sheet: bool = False, remove_bg: bool = False) -> PaletteItem | None:
        """Import an external image file either into the Custom Palette or into `assets/` as a Slicer sheet."""
        if not path or not os.path.isfile(path):
            self._set_status("Select a valid image file first!")
            return None

        base_name = os.path.splitext(os.path.basename(path))[0]
        clean_name = "".join(c if (c.isalnum() or c in "_-") else "_" for c in base_name).strip("_") or "imported_img"

        if as_sheet:
            ext = os.path.splitext(path)[1].lower() or ".png"
            dest_fname = f"{clean_name}{ext}"
            dest_path = os.path.join(self.assets_dir, dest_fname)
            if os.path.abspath(path) != os.path.abspath(dest_path):
                shutil.copy2(path, dest_path)
            self.sheet_files = self._discover_sheets()
            if dest_fname in self.sheet_files:
                self.active_sheet_idx = self.sheet_files.index(dest_fname)
                self.sheet_surfaces.pop(dest_fname, None)
            sheet = self._get_active_sheet_surface()
            if sheet is not None:
                sw, sh = sheet.get_size()
                self.slicer_crop_rect = pygame.Rect(0, 0, min(256, sw), min(256, sh))
                self.slicer_preview_dirty = True
                self._update_slicer_preview()
            self.image_modal_open = False
            self.mode = "slicer"
            sounds.play("coin")
            self._set_status(f"Imported '{dest_fname}' into Sprite Sheet Slicer!")
            return None

        # Import directly as a usable texture in `assets/sliced/custom/`.
        try:
            loaded = pygame.image.load(path).convert_alpha()
        except pygame.error as exc:
            self._set_status(f"Failed to load image: {exc}")
            return None

        if remove_bg:
            sw, sh = loaded.get_size()
            loaded = extract_sprite(loaded, (0, 0, sw, sh), remove_interior_bg=False, auto_trim=True)

        custom_dir = os.path.join(self.sliced_dir, "custom")
        os.makedirs(custom_dir, exist_ok=True)
        unique_name = clean_name
        idx = 1
        while os.path.exists(os.path.join(custom_dir, f"{unique_name}.png")):
            unique_name = f"{clean_name}_{idx:02d}"
            idx += 1

        out_path = os.path.join(custom_dir, f"{unique_name}.png")
        pygame.image.save(loaded, out_path)

        iw, ih = loaded.get_size()
        if iw <= 160 and ih <= 160:
            tw, th = max(16, iw), max(16, ih)
        else:
            scale = TILE_SIZE / max(1, ih)
            tw, th = max(16, min(256, int(round(iw * scale)))), TILE_SIZE

        manifest = load_custom_manifest(self.sliced_dir)
        manifest[unique_name] = {
            "obj_type": "solid",
            "w": tw,
            "h": th,
            "layer": 1,
        }
        save_custom_manifest(self.sliced_dir, manifest)

        self.assets.reload_custom()
        self.palette = build_palette(self.assets)
        created_item = None
        for item in self.palette:
            if item.ref == f"custom:{unique_name}":
                created_item = item
                break
        if created_item is not None:
            self.selected_palette_item = created_item
            self.active_category = "Custom"
        self.image_modal_open = False
        self.mode = "editor"
        sounds.play("coin")
        self._set_status(f"Imported '{unique_name}.png' ({tw}x{th}) to Custom palette!")
        return created_item

    def load_level_slot(self, level_num: int, force_default: bool = False) -> None:
        """Load any level slot (Level 1, 2, 3, ...) into the editor."""
        self.current_level_num = level_num
        json_path = default_level_json_path(level_num)
        if not force_default and os.path.exists(json_path):
            lvl = Level(level_num, self.assets, json_path=json_path)
            source_label = os.path.basename(json_path)
        else:
            lvl = Level(level_num, self.assets, use_default=True)
            source_label = f"Built-in Level {level_num}" if level_num in (1, 2) else f"Level {level_num} Starter Template"

        d = lvl.to_dict()
        self.level_name = d["level_name"]
        self.background_id = d.get("background_id", 1 if level_num != 2 else 2)
        self.level_width = d["width"]
        self.level_height = d["height"]
        self.ground_y = d["ground_y"]
        self.banner_message = d.get("banner_message", "")
        self.objects = d["editor_objects"]
        self.next_obj_id = max((o["id"] for o in self.objects), default=0) + 1
        self.selected_obj_id = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cam_x = 0.0
        self.cam_y = 64.0
        self._set_status(f"Loaded {source_label} ({len(self.objects)} objects).")

    def clear_level(self) -> None:
        """Clear all objects except Player Spawn and Cave Exit."""
        self._push_undo()
        kept = [o for o in self.objects if o["obj_type"] in ("spawn", "exit")]
        if not any(o["obj_type"] == "spawn" for o in kept):
            kept.append(
                {
                    "id": self.next_obj_id,
                    "obj_type": "spawn",
                    "ref": "special:spawn",
                    "x": 96,
                    "y": 9 * TILE_SIZE - 10,
                    "w": 38,
                    "h": 62,
                    "flip_x": False,
                    "flip_y": False,
                    "layer": 2,
                    "props": {},
                }
            )
            self.next_obj_id += 1
        if not any(o["obj_type"] == "exit" for o in kept):
            kept.append(
                {
                    "id": self.next_obj_id,
                    "obj_type": "exit",
                    "ref": "tiles:cave_exit",
                    "x": self.level_width - 4 * TILE_SIZE,
                    "y": 8 * TILE_SIZE,
                    "w": 128,
                    "h": 128,
                    "flip_x": False,
                    "flip_y": False,
                    "layer": 0,
                    "props": {},
                }
            )
            self.next_obj_id += 1
        self.objects = kept
        self.selected_obj_id = None
        self._set_status("Cleared level canvas (kept Spawn and Cave Exit).")

    def build_level_dict(self) -> dict:
        """Return the current level state as a serializable dictionary."""
        spawn_pos = [96, 9 * TILE_SIZE - 10]
        for o in self.objects:
            if o["obj_type"] == "spawn":
                spawn_pos = [int(o["x"]), int(o["y"])]
                break
        return {
            "version": 1,
            "level_number": self.current_level_num,
            "background_id": self.background_id,
            "level_name": self.level_name,
            "width": self.level_width,
            "height": self.level_height,
            "ground_y": self.ground_y,
            "spawn_pos": spawn_pos,
            "banner_message": self.banner_message,
            "editor_objects": copy.deepcopy(self.objects),
        }

    def save_current_level(self) -> str:
        """Save the current level to `levels/level_<N>.json`."""
        data = self.build_level_dict()
        path = default_level_json_path(self.current_level_num)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        sounds.play("pickup")
        self._set_status(f"Saved level to {os.path.relpath(path)}! Ready to play in game.")
        return path

    # ------------------------------------------------------------------
    # Playtest Mode
    # ------------------------------------------------------------------
    def start_playtest(self, spawn_at_camera: bool = False) -> None:
        """Compile the edited level and start interactive playtest mode."""
        data = self.build_level_dict()
        self.playtest_level = Level(self.current_level_num, self.assets, data=data)
        sx, sy = self.playtest_level.spawn_pos
        if spawn_at_camera:
            sx = int(self.cam_x + CANVAS_W // 2)
            sy = 200
        self.playtest_player = Player(sx, sy, self.player_sprites)
        self.playtest_cam_x = max(0.0, min(float(self.playtest_level.width - 1280), sx - 1280 * 0.38))
        self.playtest_step_timer = 0
        self.mode = "playtest"
        self._set_status("Playtest started! Press Esc or F5 to return to the Level Editor.")

    def stop_playtest(self) -> None:
        """Return from playtest mode to the Level Editor."""
        self.mode = "editor"
        self.playtest_level = None
        self.playtest_player = None
        self._set_status("Returned to Level Editor.")

    # ------------------------------------------------------------------
    # Sprite Sheet Slicer helpers
    # ------------------------------------------------------------------
    def _discover_sheets(self) -> list[str]:
        sheets = []
        for preferred in ("base.jpg", "knight.jpg", "goblin.jpg"):
            p = os.path.join(self.assets_dir, preferred)
            if os.path.exists(p):
                sheets.append(preferred)
        if os.path.isdir(self.assets_dir):
            for fname in sorted(os.listdir(self.assets_dir)):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")) and fname not in sheets:
                    sheets.append(fname)
        return sheets

    def _get_active_sheet_surface(self) -> pygame.Surface | None:
        if not self.sheet_files:
            return None
        fname = self.sheet_files[self.active_sheet_idx % len(self.sheet_files)]
        if fname not in self.sheet_surfaces:
            path = os.path.join(self.assets_dir, fname)
            self.sheet_surfaces[fname] = pygame.image.load(path).convert()
        return self.sheet_surfaces[fname]

    def _get_predefined_sprites_for_active_sheet(self) -> list[tuple[str, str, tuple[int, int, int, int], bool, bool]]:
        if not self.sheet_files:
            return []
        fname = self.sheet_files[self.active_sheet_idx % len(self.sheet_files)]
        if fname == "base.jpg":
            return BASE_SPRITES
        if fname == "knight.jpg":
            return KNIGHT_SPRITES
        if fname == "goblin.jpg":
            return GOBLIN_SPRITES
        return []

    def _next_custom_slice_name(self) -> str:
        custom_dir = os.path.join(self.sliced_dir, "custom")
        idx = 1
        while True:
            candidate = f"slice_{idx:02d}"
            if not os.path.exists(os.path.join(custom_dir, f"{candidate}.png")):
                return candidate
            idx += 1

    def _update_slicer_preview(self) -> None:
        sheet = self._get_active_sheet_surface()
        if sheet is None:
            self.slicer_preview_surf = None
            return
        sw, sh = sheet.get_size()
        r = self.slicer_crop_rect.clip(pygame.Rect(0, 0, sw, sh))
        if r.width < 2 or r.height < 2:
            self.slicer_preview_surf = None
            return
        if self.slicer_remove_bg:
            self.slicer_preview_surf = extract_sprite(
                sheet,
                (r.x, r.y, r.width, r.height),
                remove_interior_bg=self.slicer_remove_interior,
                auto_trim=self.slicer_auto_trim,
                strict_bg_only=self.slicer_strict_bg,
            )
        else:
            sub = sheet.subsurface(r).copy().convert_alpha()
            if self.slicer_auto_trim:
                bbox = sub.get_bounding_rect(min_alpha=10)
                if bbox.width > 0 and bbox.height > 0:
                    sub = sub.subsurface(bbox).copy()
            self.slicer_preview_surf = sub
        self.slicer_preview_dirty = False

    def _compute_slice_target_size(self, surf: pygame.Surface) -> tuple[int, int]:
        iw, ih = surf.get_size()
        if self.slicer_scale_mode == "tile_64":
            return (TILE_SIZE, TILE_SIZE)
        if self.slicer_scale_mode == "height_64":
            scale = TILE_SIZE / max(1, ih)
            return (max(8, int(round(iw * scale))), TILE_SIZE)
        if self.slicer_scale_mode == "wide_128":
            return (TILE_SIZE * 2, TILE_SIZE)
        if self.slicer_scale_mode == "tall_128":
            return (TILE_SIZE, TILE_SIZE * 2)
        # "original" (clamped to reasonable level size)
        return (max(8, min(512, iw)), max(8, min(512, ih)))

    def save_current_slice_to_palette(self) -> PaletteItem | None:
        """Save the currently previewed sprite slice to `assets/sliced/custom/` and register it in the palette."""
        if self.slicer_preview_dirty:
            self._update_slicer_preview()
        if self.slicer_preview_surf is None:
            self._set_status("Select a valid region on the sprite sheet first!")
            return None

        clean_name = "".join(c if (c.isalnum() or c in "_-") else "_" for c in self.slicer_name_text.strip())
        if not clean_name:
            clean_name = self._next_custom_slice_name()

        custom_dir = os.path.join(self.sliced_dir, "custom")
        os.makedirs(custom_dir, exist_ok=True)
        out_path = os.path.join(custom_dir, f"{clean_name}.png")
        pygame.image.save(self.slicer_preview_surf, out_path)

        tw, th = self._compute_slice_target_size(self.slicer_preview_surf)
        manifest = load_custom_manifest(self.sliced_dir)
        manifest[clean_name] = {
            "obj_type": self.slicer_default_type,
            "w": tw,
            "h": th,
            "layer": 0 if self.slicer_default_type == "decoration" else 1,
        }
        save_custom_manifest(self.sliced_dir, manifest)

        # Reload custom assets and rebuild palette.
        self.assets.reload_custom()
        self.palette = build_palette(self.assets)
        created_item = None
        for item in self.palette:
            if item.ref == f"custom:{clean_name}":
                created_item = item
                break
        if created_item:
            self.selected_palette_item = created_item
        self.slicer_name_text = self._next_custom_slice_name()
        sounds.play("coin")
        self._set_status(f"Sliced & saved '{clean_name}.png' ({tw}x{th}) to Custom palette!")
        return created_item

    # ------------------------------------------------------------------
    # Coordinate & Snapping Helpers
    # ------------------------------------------------------------------
    def screen_to_world(self, sx: int, sy: int) -> tuple[int, int]:
        wx = int(round(sx - CANVAS_X + self.cam_x))
        wy = int(round(sy - CANVAS_Y + self.cam_y))
        return wx, wy

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = int(round(wx - self.cam_x + CANVAS_X))
        sy = int(round(wy - self.cam_y + CANVAS_Y))
        return sx, sy

    def snap_value(self, val: int, bypass_snap: bool = False) -> int:
        if not self.grid_snap or bypass_snap:
            return val
        g = self.grid_size
        return (val // g) * g

    def place_palette_item(self, item: PaletteItem, wx: int, wy: int, bypass_snap: bool = False, record_undo: bool = True) -> dict:
        """Instantiate an editor object from `item` at world position `(wx, wy)`."""
        if record_undo:
            self._push_undo()

        if self.grid_snap and not bypass_snap:
            gx = (wx // self.grid_size) * self.grid_size
            gy = (wy // self.grid_size) * self.grid_size
            # Align props/enemies/items neatly onto the bottom of the grid cell if smaller than a tile.
            if item.obj_type in ("destructible", "chest", "lever", "locked_door", "enemy"):
                x = gx + max(0, (TILE_SIZE - item.default_w) // 2)
                y = gy + TILE_SIZE - item.default_h
            elif item.obj_type == "ladder":
                x = gx + (TILE_SIZE - item.default_w) // 2
                y = gy
            elif item.obj_type == "spike":
                x = gx
                y = gy - 16
            elif item.obj_type == "collectible":
                x = gx + (TILE_SIZE - item.default_w) // 2
                y = gy + (TILE_SIZE - item.default_h) // 2
            else:
                x, y = gx, gy
        else:
            x = wx - item.default_w // 2
            y = wy - item.default_h // 2

        x = max(0, min(self.level_width - item.default_w, x))
        y = max(-128, min(self.level_height + 64, y))

        # Only one spawn and one exit per level: move existing if placing another.
        if item.obj_type in ("spawn", "exit"):
            for existing in self.objects:
                if existing["obj_type"] == item.obj_type:
                    existing["x"] = int(x)
                    existing["y"] = int(y)
                    self.selected_obj_id = existing["id"]
                    self._set_status(f"Moved {TYPE_LABELS[item.obj_type]} to ({x}, {y}).")
                    return existing

        props = copy.deepcopy(item.props)
        if item.obj_type == "enemy":
            props.setdefault("patrol_min_x", max(0, x - 2 * TILE_SIZE))
            props.setdefault("patrol_max_x", min(self.level_width, x + item.default_w + 2 * TILE_SIZE))

        new_obj = {
            "id": self.next_obj_id,
            "obj_type": item.obj_type,
            "ref": item.ref,
            "x": int(x),
            "y": int(y),
            "w": int(item.default_w),
            "h": int(item.default_h),
            "flip_x": False,
            "flip_y": False,
            "layer": int(item.layer),
            "props": props,
        }
        self.next_obj_id += 1
        self.objects.append(new_obj)
        self.selected_obj_id = new_obj["id"]
        sounds.play("click")
        return new_obj

    def _get_resize_handles(self, obj: dict) -> dict[str, pygame.Rect]:
        """Return 8 screen-space handle rects around `obj` for interactive resizing."""
        sx, sy = self.world_to_screen(obj["x"], obj["y"])
        w, h = obj["w"], obj["h"]
        hs = 8
        half = hs // 2
        return {
            "nw": pygame.Rect(sx - half, sy - half, hs, hs),
            "n": pygame.Rect(sx + w // 2 - half, sy - half, hs, hs),
            "ne": pygame.Rect(sx + w - half, sy - half, hs, hs),
            "e": pygame.Rect(sx + w - half, sy + h // 2 - half, hs, hs),
            "se": pygame.Rect(sx + w - half, sy + h - half, hs, hs),
            "s": pygame.Rect(sx + w // 2 - half, sy + h - half, hs, hs),
            "sw": pygame.Rect(sx - half, sy + h - half, hs, hs),
            "w": pygame.Rect(sx - half, sy + h // 2 - half, hs, hs),
        }

    def _get_patrol_handles(self, obj: dict) -> tuple[pygame.Rect, pygame.Rect] | None:
        if obj.get("obj_type") != "enemy":
            return None
        props = obj.get("props") or {}
        p_min = int(props.get("patrol_min_x", obj["x"] - 128))
        p_max = int(props.get("patrol_max_x", obj["x"] + obj["w"] + 128))
        y_mid = obj["y"] + obj["h"] // 2
        s_min_x, s_mid_y = self.world_to_screen(p_min, y_mid)
        s_max_x, _ = self.world_to_screen(p_max, y_mid)
        return (
            pygame.Rect(s_min_x - 7, s_mid_y - 9, 14, 18),
            pygame.Rect(s_max_x - 7, s_mid_y - 9, 14, 18),
        )

    def _find_topmost_object_at(self, wx: int, wy: int) -> dict | None:
        """Find the topmost object on the level canvas containing world point `(wx, wy)`."""
        sorted_objs = sorted(enumerate(self.objects), key=lambda p: (p[1].get("layer", 1), p[0]), reverse=True)
        for _, obj in sorted_objs:
            r = pygame.Rect(obj["x"], obj["y"], obj["w"], obj["h"])
            if r.collidepoint(wx, wy):
                return obj
        return None

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Process a single Pygame event. Returns 'quit' or 'main_menu' if requested."""
        if event.type == pygame.DROPFILE:
            dropped_path = getattr(event, "file", "")
            if dropped_path and os.path.isfile(dropped_path):
                self.import_image_file(dropped_path, as_sheet=(self.mode == "slicer"))
            return None

        if self.image_modal_open:
            self._handle_image_modal_event(event)
            return None

        if self.mode == "playtest":
            return self._handle_playtest_event(event)

        # Global keyboard shortcuts.
        if event.type == pygame.KEYDOWN:
            if self.mode == "editor" and self.editing_level_name:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.editing_level_name = False
                elif event.key == pygame.K_BACKSPACE:
                    self.level_name = self.level_name[:-1]
                elif event.unicode and event.unicode.isprintable():
                    if len(self.level_name) < 36:
                        self.level_name += event.unicode
                return None

            if self.mode == "slicer" and self.slicer_editing_name:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.slicer_editing_name = False
                elif event.key == pygame.K_BACKSPACE:
                    self.slicer_name_text = self.slicer_name_text[:-1]
                elif event.unicode and (event.unicode.isalnum() or event.unicode in "_-"):
                    if len(self.slicer_name_text) < 24:
                        self.slicer_name_text += event.unicode
                return None

            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)
            shift = bool(mods & pygame.KMOD_SHIFT)

            if ctrl and event.key == pygame.K_s:
                self.save_current_level()
                return None
            if ctrl and event.key == pygame.K_z:
                self.undo()
                return None
            if ctrl and event.key == pygame.K_y:
                self.redo()
                return None
            if ctrl and event.key == pygame.K_d:
                self._duplicate_selected()
                return None
            if event.key == pygame.K_TAB:
                self.mode = "slicer" if self.mode == "editor" else "editor"
                return None
            if event.key in (pygame.K_F5, pygame.K_p):
                self.start_playtest(spawn_at_camera=shift)
                return None
            if event.key == pygame.K_g and self.mode == "editor":
                self.grid_snap = not self.grid_snap
                self._set_status(f"Grid Snap: {'ON' if self.grid_snap else 'OFF (Free Pixel)'}")
                return None
            if event.key == pygame.K_h and self.mode == "editor":
                self.show_hitboxes = not self.show_hitboxes
                self._set_status(f"Collision Hitboxes: {'ON' if self.show_hitboxes else 'OFF'}")
                return None
            if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self.mode == "editor":
                self._delete_selected()
                return None
            if event.key == pygame.K_f and self.mode == "editor":
                self._flip_selected(horizontal=True)
                return None
            if event.key == pygame.K_v and self.mode == "editor":
                self._flip_selected(horizontal=False)
                return None
            if event.key == pygame.K_LEFTBRACKET and self.mode == "editor":
                self._change_selected_layer(-1)
                return None
            if event.key == pygame.K_RIGHTBRACKET and self.mode == "editor":
                self._change_selected_layer(1)
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.mode == "slicer":
                self.save_current_slice_to_palette()
                return None

            # Slicer 1px crop box nudging with arrow keys.
            if self.mode == "slicer" and event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                dx = (-1 if event.key == pygame.K_LEFT else (1 if event.key == pygame.K_RIGHT else 0))
                dy = (-1 if event.key == pygame.K_UP else (1 if event.key == pygame.K_DOWN else 0))
                if shift:
                    self.slicer_crop_rect.width = max(4, self.slicer_crop_rect.width + dx)
                    self.slicer_crop_rect.height = max(4, self.slicer_crop_rect.height + dy)
                else:
                    self.slicer_crop_rect.x = max(0, self.slicer_crop_rect.x + dx)
                    self.slicer_crop_rect.y = max(0, self.slicer_crop_rect.y + dy)
                self.slicer_preview_dirty = True
                return None

        # Top bar click handling (shared between Editor and Slicer modes).
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[1] < TOPBAR_H:
            return self._handle_topbar_click(event.pos)

        if self.mode == "slicer":
            self._handle_slicer_event(event)
        else:
            self._handle_editor_event(event)
        return None

    def _handle_topbar_click(self, pos: tuple[int, int]) -> str | None:
        for rect, action in self._get_topbar_buttons():
            if rect.collidepoint(pos):
                sounds.play("click")
                if action == "mode_editor":
                    self.mode = "editor"
                elif action == "mode_slicer":
                    self.mode = "slicer"
                elif action == "playtest":
                    self.start_playtest(spawn_at_camera=bool(pygame.key.get_mods() & pygame.KMOD_SHIFT))
                elif action == "prev_lvl":
                    self.cycle_level(-1)
                elif action in ("next_lvl", "cycle_lvl"):
                    self.cycle_level(1)
                elif action == "add_lvl":
                    self.create_new_level()
                elif action == "add_image":
                    self.open_image_modal()
                elif action == "save":
                    self.save_current_level()
                elif action == "reset_default":
                    self.load_level_slot(self.current_level_num, force_default=True)
                elif action == "clear":
                    self.clear_level()
                elif action == "toggle_snap":
                    self.grid_snap = not self.grid_snap
                elif action == "toggle_hitboxes":
                    self.show_hitboxes = not self.show_hitboxes
                elif action == "undo":
                    self.undo()
                elif action == "redo":
                    self.redo()
                elif action == "main_menu":
                    return "main_menu"
                return None
        return None

    def _get_topbar_buttons(self) -> list[tuple[pygame.Rect, str]]:
        btns = [
            (pygame.Rect(8, 6, 112, 32), "mode_editor"),
            (pygame.Rect(124, 6, 118, 32), "mode_slicer"),
            (pygame.Rect(246, 6, 102, 32), "playtest"),
            (pygame.Rect(356, 6, 28, 32), "prev_lvl"),
            (pygame.Rect(386, 6, 76, 32), "cycle_lvl"),
            (pygame.Rect(464, 6, 28, 32), "next_lvl"),
            (pygame.Rect(496, 6, 68, 32), "add_lvl"),
            (pygame.Rect(568, 6, 74, 32), "add_image"),
            (pygame.Rect(648, 6, 76, 32), "save"),
            (pygame.Rect(728, 6, 68, 32), "reset_default"),
            (pygame.Rect(800, 6, 56, 32), "clear"),
            (pygame.Rect(862, 6, 88, 32), "toggle_snap"),
            (pygame.Rect(954, 6, 84, 32), "toggle_hitboxes"),
            (pygame.Rect(1044, 6, 52, 32), "undo"),
            (pygame.Rect(1100, 6, 52, 32), "redo"),
            (pygame.Rect(1160, 6, 112, 32), "main_menu"),
        ]
        return btns

    # ------------------------------------------------------------------
    # Editor Mode Events (Palette drag-and-drop, Canvas manipulation, Inspector)
    # ------------------------------------------------------------------
    def _filtered_palette(self) -> list[PaletteItem]:
        if self.active_category == "All":
            return self.palette
        return [p for p in self.palette if p.category == self.active_category]

    def _get_palette_card_rects(self) -> list[tuple[pygame.Rect, PaletteItem]]:
        items = self._filtered_palette()
        cards: list[tuple[pygame.Rect, PaletteItem]] = []
        start_y = TOPBAR_H + 68 - self.palette_scroll
        col_w = 108
        card_h = 84
        for idx, item in enumerate(items):
            col = idx % 2
            row = idx // 2
            x = 10 + col * (col_w + 8)
            y = start_y + row * (card_h + 8)
            cards.append((pygame.Rect(x, y, col_w, card_h), item))
        return cards

    def _handle_editor_event(self, event: pygame.event.Event) -> None:
        canvas_rect = pygame.Rect(CANVAS_X, CANVAS_Y, CANVAS_W, CANVAS_H)
        minimap_rect = pygame.Rect(CANVAS_X, MINIMAP_Y, CANVAS_W, MINIMAP_H)
        left_rect = pygame.Rect(0, TOPBAR_H, LEFT_PANEL_W, SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H)
        right_rect = pygame.Rect(
            SCREEN_WIDTH - RIGHT_PANEL_W, TOPBAR_H, RIGHT_PANEL_W, SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H
        )

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            my -= BAR_HEIGHT
            if left_rect.collidepoint(mx, my):
                max_scroll = max(0, ((len(self._filtered_palette()) + 1) // 2) * 92 - (left_rect.height - 80))
                self.palette_scroll = max(0, min(max_scroll, self.palette_scroll - event.y * 36))
            elif canvas_rect.collidepoint(mx, my):
                self.cam_x = max(0.0, min(float(self.level_width - CANVAS_W), self.cam_x - event.y * 96))
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            mods = pygame.key.get_mods()
            bypass_snap = bool(mods & pygame.KMOD_ALT)
            shift = bool(mods & pygame.KMOD_SHIFT)
            ctrl = bool(mods & pygame.KMOD_CTRL)

            # 1. Left Sidebar (Palette).
            if event.button == 1 and left_rect.collidepoint(mx, my):
                # Category buttons.
                for cat_rect, cat_name in self._get_category_buttons():
                    if cat_rect.collidepoint(mx, my):
                        self.active_category = cat_name
                        self.palette_scroll = 0
                        sounds.play("click")
                        return
                # Slice new sprite & Add image buttons at top of palette.
                half_w = (LEFT_PANEL_W - 20) // 2
                slice_btn = pygame.Rect(8, TOPBAR_H + 36, half_w, 26)
                add_img_btn = pygame.Rect(12 + half_w, TOPBAR_H + 36, half_w, 26)
                if slice_btn.collidepoint(mx, my):
                    self.mode = "slicer"
                    sounds.play("click")
                    return
                if add_img_btn.collidepoint(mx, my):
                    self.open_image_modal()
                    sounds.play("click")
                    return
                # Palette cards -> start drag-and-drop!
                for card_rect, item in self._get_palette_card_rects():
                    if card_rect.top >= TOPBAR_H + 64 and card_rect.collidepoint(mx, my):
                        self.selected_palette_item = item
                        self.dragging_from_palette = item
                        sounds.play("click")
                        self._set_status(f"Dragging '{item.name}' — release on the level canvas to place!")
                        return
                return

            # 2. Right Sidebar (Inspector).
            if event.button == 1 and right_rect.collidepoint(mx, my):
                self._handle_inspector_click((mx, my))
                return

            # 3. Minimap scrollbar.
            if event.button == 1 and minimap_rect.collidepoint(mx, my):
                self.dragging_minimap = True
                self._update_minimap_drag(mx)
                return

            # 4. Level Canvas.
            if canvas_rect.collidepoint(mx, my):
                wx, wy = self.screen_to_world(mx, my)

                # Middle mouse or Right-drag on empty space pans canvas; Right-click on object deletes it.
                if event.button == 2:
                    self.panning_canvas = True
                    self.pan_start_mouse = (mx, my)
                    self.pan_start_cam = (self.cam_x, self.cam_y)
                    return

                if event.button == 3:
                    hit = self._find_topmost_object_at(wx, wy)
                    if hit is not None and hit["obj_type"] not in ("spawn", "exit"):
                        self._push_undo()
                        self.objects = [o for o in self.objects if o["id"] != hit["id"]]
                        if self.selected_obj_id == hit["id"]:
                            self.selected_obj_id = None
                        sounds.play("hit")
                        self._set_status(f"Deleted {hit['ref']}.")
                    else:
                        self.panning_canvas = True
                        self.pan_start_mouse = (mx, my)
                        self.pan_start_cam = (self.cam_x, self.cam_y)
                    return

                if event.button == 1:
                    # Shift + Left Click/Drag paints with the selected palette brush!
                    if shift and self.selected_palette_item is not None:
                        self._push_undo()
                        self.painting_brush = True
                        self.painted_cells.clear()
                        cell = (wx // self.grid_size, wy // self.grid_size)
                        self.painted_cells.add(cell)
                        self.place_palette_item(
                            self.selected_palette_item, wx, wy, bypass_snap=bypass_snap, record_undo=False
                        )
                        return

                    # Check patrol handles or resize handles on currently selected object first.
                    sel = self.get_selected_obj()
                    if sel is not None:
                        p_handles = self._get_patrol_handles(sel)
                        if p_handles is not None:
                            min_rect, max_rect = p_handles
                            if min_rect.collidepoint(mx, my):
                                self.drag_start_snapshot = copy.deepcopy(self.objects)
                                self.dragging_patrol_handle = "min"
                                return
                            if max_rect.collidepoint(mx, my):
                                self.drag_start_snapshot = copy.deepcopy(self.objects)
                                self.dragging_patrol_handle = "max"
                                return

                        if sel["obj_type"] not in ("spawn",):
                            for h_name, h_rect in self._get_resize_handles(sel).items():
                                if h_rect.collidepoint(mx, my):
                                    self.drag_start_snapshot = copy.deepcopy(self.objects)
                                    self.resizing_handle = h_name
                                    self.resize_initial_rect = (sel["x"], sel["y"], sel["w"], sel["h"])
                                    self.resize_mouse_start = (wx, wy)
                                    return

                    # Check if clicking an object on the canvas to select and drag-move it.
                    hit = self._find_topmost_object_at(wx, wy)
                    if hit is not None:
                        self.drag_start_snapshot = copy.deepcopy(self.objects)
                        if ctrl and hit["obj_type"] not in ("spawn", "exit"):
                            # Ctrl+Drag duplicates the clicked object and drags the duplicate.
                            dup = copy.deepcopy(hit)
                            dup["id"] = self.next_obj_id
                            self.next_obj_id += 1
                            self.objects.append(dup)
                            hit = dup
                        self.selected_obj_id = hit["id"]
                        self.dragging_canvas_obj = True
                        self.drag_offset = (wx - hit["x"], wy - hit["y"])
                        return
                    else:
                        self.selected_obj_id = None

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            mods = pygame.key.get_mods()
            bypass_snap = bool(mods & pygame.KMOD_ALT)
            wx, wy = self.screen_to_world(mx, my)

            if self.dragging_minimap:
                self._update_minimap_drag(mx)
                return

            if self.panning_canvas:
                dx = mx - self.pan_start_mouse[0]
                dy = my - self.pan_start_mouse[1]
                self.cam_x = max(0.0, min(float(self.level_width - CANVAS_W), self.pan_start_cam[0] - dx))
                self.cam_y = max(-64.0, min(160.0, self.pan_start_cam[1] - dy))
                return

            if self.painting_brush and self.selected_palette_item is not None and canvas_rect.collidepoint(mx, my):
                cell = (wx // self.grid_size, wy // self.grid_size)
                if cell not in self.painted_cells:
                    self.painted_cells.add(cell)
                    self.place_palette_item(
                        self.selected_palette_item, wx, wy, bypass_snap=bypass_snap, record_undo=False
                    )
                return

            sel = self.get_selected_obj()
            if self.dragging_patrol_handle and sel is not None:
                props = sel.setdefault("props", {})
                snapped_x = self.snap_value(wx, bypass_snap=bypass_snap)
                if self.dragging_patrol_handle == "min":
                    props["patrol_min_x"] = max(0, min(sel["x"], snapped_x))
                else:
                    props["patrol_max_x"] = max(sel["x"] + sel["w"], min(self.level_width, snapped_x))
                return

            if self.resizing_handle and sel is not None:
                ix, iy, iw, ih = self.resize_initial_rect
                dx = wx - self.resize_mouse_start[0]
                dy = wy - self.resize_mouse_start[1]
                step = 1 if (not self.grid_snap or bypass_snap) else max(16, self.grid_size // 2)
                dx = int(round(dx / step)) * step
                dy = int(round(dy / step)) * step

                nx, ny, nw, nh = ix, iy, iw, ih
                hname = self.resizing_handle
                if "e" in hname:
                    nw = max(16, iw + dx)
                if "s" in hname:
                    nh = max(16, ih + dy)
                if "w" in hname:
                    new_left = min(ix + iw - 16, ix + dx)
                    nw = (ix + iw) - new_left
                    nx = new_left
                if "n" in hname:
                    new_top = min(iy + ih - 16, iy + dy)
                    nh = (iy + ih) - new_top
                    ny = new_top
                sel["x"], sel["y"], sel["w"], sel["h"] = int(nx), int(ny), int(nw), int(nh)
                return

            if self.dragging_canvas_obj and sel is not None:
                raw_x = wx - self.drag_offset[0]
                raw_y = wy - self.drag_offset[1]
                if self.grid_snap and not bypass_snap:
                    nx = int(round(raw_x / self.grid_size)) * self.grid_size
                    ny = int(round(raw_y / self.grid_size)) * self.grid_size
                    if sel["obj_type"] == "ladder":
                        nx += (TILE_SIZE - sel["w"]) // 2
                    elif sel["obj_type"] == "spike":
                        ny -= 16
                    elif sel["obj_type"] in ("destructible", "chest", "lever", "locked_door", "enemy"):
                        ny += TILE_SIZE - sel["h"]
                else:
                    nx, ny = raw_x, raw_y
                dx_move = int(nx) - sel["x"]
                sel["x"] = max(0, min(self.level_width - sel["w"], int(nx)))
                sel["y"] = max(-128, min(self.level_height + 64, int(ny)))
                if sel["obj_type"] == "enemy" and dx_move != 0:
                    props = sel.setdefault("props", {})
                    props["patrol_min_x"] = max(0, int(props.get("patrol_min_x", sel["x"] - 128)) + dx_move)
                    props["patrol_max_x"] = min(
                        self.level_width, int(props.get("patrol_max_x", sel["x"] + sel["w"] + 128)) + dx_move
                    )
                return

        elif event.type == pygame.MOUSEBUTTONUP:
            mx, my = event.pos
            mods = pygame.key.get_mods()
            bypass_snap = bool(mods & pygame.KMOD_ALT)

            if event.button == 1:
                if self.dragging_from_palette is not None:
                    item = self.dragging_from_palette
                    self.dragging_from_palette = None
                    if canvas_rect.collidepoint(mx, my):
                        wx, wy = self.screen_to_world(mx, my)
                        placed = self.place_palette_item(item, wx, wy, bypass_snap=bypass_snap, record_undo=True)
                        self._set_status(
                            f"Placed '{item.name}' at ({placed['x']}, {placed['y']}) [{TYPE_LABELS[placed['obj_type']]}]."
                        )
                    return

                if self.dragging_canvas_obj or self.resizing_handle or self.dragging_patrol_handle:
                    if self.drag_start_snapshot is not None and self.drag_start_snapshot != self.objects:
                        self._push_undo(self.drag_start_snapshot)
                    self.drag_start_snapshot = None
                    self.dragging_canvas_obj = False
                    self.resizing_handle = None
                    self.dragging_patrol_handle = None

                self.painting_brush = False
                self.painted_cells.clear()
                self.dragging_minimap = False

            if event.button in (2, 3):
                self.panning_canvas = False

    def _update_minimap_drag(self, mx: int) -> None:
        rel = max(0.0, min(1.0, (mx - CANVAS_X) / max(1, CANVAS_W)))
        self.cam_x = max(0.0, min(float(self.level_width - CANVAS_W), rel * self.level_width - CANVAS_W * 0.5))

    def _get_category_buttons(self) -> list[tuple[pygame.Rect, str]]:
        btns: list[tuple[pygame.Rect, str]] = []
        x = 6
        y = TOPBAR_H + 6
        for cat in self.categories:
            w = max(30, self.font_xs.size(cat)[0] + 10)
            btns.append((pygame.Rect(x, y, w, 24), cat))
            x += w + 3
        return btns

    # ------------------------------------------------------------------
    # Selected Object Actions & Inspector Clicks
    # ------------------------------------------------------------------
    def _delete_selected(self) -> None:
        sel = self.get_selected_obj()
        if sel is None:
            return
        if sel["obj_type"] in ("spawn", "exit"):
            self._set_status("Spawn and Cave Exit cannot be deleted — drag them to reposition!")
            return
        self._push_undo()
        self.objects = [o for o in self.objects if o["id"] != sel["id"]]
        self.selected_obj_id = None
        sounds.play("hit")
        self._set_status("Deleted selected object.")

    def _duplicate_selected(self) -> None:
        sel = self.get_selected_obj()
        if sel is None or sel["obj_type"] in ("spawn", "exit"):
            return
        self._push_undo()
        dup = copy.deepcopy(sel)
        dup["id"] = self.next_obj_id
        self.next_obj_id += 1
        dup["x"] = min(self.level_width - dup["w"], dup["x"] + self.grid_size)
        self.objects.append(dup)
        self.selected_obj_id = dup["id"]
        sounds.play("click")
        self._set_status("Duplicated selected object.")

    def _flip_selected(self, horizontal: bool = True) -> None:
        sel = self.get_selected_obj()
        if sel is None:
            return
        self._push_undo()
        key = "flip_x" if horizontal else "flip_y"
        sel[key] = not sel.get(key, False)

    def _change_selected_layer(self, delta: int) -> None:
        sel = self.get_selected_obj()
        if sel is None:
            return
        self._push_undo()
        sel["layer"] = max(0, min(2, int(sel.get("layer", 1)) + delta))
        self._set_status(f"Set object layer to {sel['layer']} (0=Back, 1=Terrain, 2=Front).")

    def _get_inspector_buttons(self) -> list[tuple[pygame.Rect, str]]:
        rx = SCREEN_WIDTH - RIGHT_PANEL_W + 10
        w = RIGHT_PANEL_W - 20
        btns: list[tuple[pygame.Rect, str]] = []
        sel = self.get_selected_obj()
        if sel is None:
            # Level settings buttons when nothing is selected.
            btns.append((pygame.Rect(rx, TOPBAR_H + 34, w, 26), "edit_level_name"))
            y = TOPBAR_H + 84
            btns.append((pygame.Rect(rx, y, w // 2 - 4, 26), "bg_1"))
            btns.append((pygame.Rect(rx + w // 2 + 4, y, w // 2 - 4, 26), "bg_2"))
            y += 52
            btns.append((pygame.Rect(rx, y, w // 2 - 4, 26), "width_minus"))
            btns.append((pygame.Rect(rx + w // 2 + 4, y, w // 2 - 4, 26), "width_plus"))

            # Dynamic Level Slots grid + Add/Delete Level.
            y += 52
            lvls = self.get_levels_list()
            cell_w = (w - 12) // 3
            for i, lnum in enumerate(lvls[:12]):
                col = i % 3
                row = i // 3
                btns.append((pygame.Rect(rx + col * (cell_w + 6), y + row * 28, cell_w, 24), f"select_lvl:{lnum}"))
            rows_used = (min(12, len(lvls)) + 2) // 3
            y_act = y + rows_used * 28 + 6
            btns.append((pygame.Rect(rx, y_act, w // 2 - 4, 26), "add_lvl"))
            btns.append((pygame.Rect(rx + w // 2 + 4, y_act, w // 2 - 4, 26), "delete_lvl"))
            return btns

        # Action row buttons.
        y = TOPBAR_H + 148
        bw = (w - 6) // 2
        btns.append((pygame.Rect(rx, y, bw, 24), "flip_h"))
        btns.append((pygame.Rect(rx + bw + 6, y, bw, 24), "flip_v"))
        y += 28
        btns.append((pygame.Rect(rx, y, bw, 24), "layer_down"))
        btns.append((pygame.Rect(rx + bw + 6, y, bw, 24), "layer_up"))
        y += 28
        btns.append((pygame.Rect(rx, y, bw, 24), "reset_size"))
        btns.append((pygame.Rect(rx + bw + 6, y, bw, 24), "duplicate"))
        y += 28
        btns.append((pygame.Rect(rx, y, w, 24), "delete"))

        # Object / Collision Type pills (2 columns).
        y += 46
        for idx, otype in enumerate(ALL_OBJECT_TYPES):
            col = idx % 2
            row = idx // 2
            px = rx + col * (bw + 6)
            py = y + row * 24
            btns.append((pygame.Rect(px, py, bw, 21), f"type:{otype}"))

        # Sub-property buttons at bottom of inspector.
        y_sub = y + ((len(ALL_OBJECT_TYPES) + 1) // 2) * 24 + 22
        if sel["obj_type"] == "destructible":
            for i, drop in enumerate(("coin", "potion", "gem")):
                dw = (w - 8) // 3
                btns.append((pygame.Rect(rx + i * (dw + 4), y_sub, dw, 22), f"drop:{drop}"))
        elif sel["obj_type"] == "collectible":
            for i, kind in enumerate(("coin", "gem", "key", "potion")):
                kw = (w - 12) // 4
                btns.append((pygame.Rect(rx + i * (kw + 4), y_sub, kw, 22), f"item_kind:{kind}"))
        elif sel["obj_type"] == "enemy":
            kinds = ("slime", "bat", "goblin_warrior", "goblin_archer", "goblin_brute", "goblin_scout")
            for i, kind in enumerate(kinds):
                col = i % 2
                row = i // 2
                btns.append((pygame.Rect(rx + col * (bw + 6), y_sub + row * 22, bw, 20), f"enemy_kind:{kind}"))

        return btns

    def _handle_inspector_click(self, pos: tuple[int, int]) -> None:
        sel = self.get_selected_obj()
        self.editing_level_name = False
        for rect, action in self._get_inspector_buttons():
            if not rect.collidepoint(pos):
                continue
            sounds.play("click")
            if action == "edit_level_name":
                self.editing_level_name = True
            elif action == "bg_1":
                self.background_id = 1
                self._set_status("Background set to 1: Emerald Grasslands.")
            elif action == "bg_2":
                self.background_id = 2
                self._set_status("Background set to 2: Dark Forest.")
            elif action == "width_minus":
                self.level_width = max(24 * TILE_SIZE, self.level_width - 4 * TILE_SIZE)
                self._set_status(f"Level width: {self.level_width // TILE_SIZE} tiles ({self.level_width}px).")
            elif action == "width_plus":
                self.level_width = min(120 * TILE_SIZE, self.level_width + 4 * TILE_SIZE)
                self._set_status(f"Level width: {self.level_width // TILE_SIZE} tiles ({self.level_width}px).")
            elif action.startswith("select_lvl:"):
                self.load_level_slot(int(action.split(":", 1)[1]))
            elif action == "add_lvl":
                self.create_new_level()
            elif action == "delete_lvl":
                self.delete_current_level()
            elif sel is not None:
                if action == "flip_h":
                    self._flip_selected(True)
                elif action == "flip_v":
                    self._flip_selected(False)
                elif action == "layer_down":
                    self._change_selected_layer(-1)
                elif action == "layer_up":
                    self._change_selected_layer(1)
                elif action == "reset_size":
                    base = self.assets.get_base_surface(sel["ref"])
                    if base is not None:
                        self._push_undo()
                        sel["w"], sel["h"] = base.get_size()
                elif action == "duplicate":
                    self._duplicate_selected()
                elif action == "delete":
                    self._delete_selected()
                elif action.startswith("type:"):
                    new_type = action.split(":", 1)[1]
                    self._push_undo()
                    sel["obj_type"] = new_type
                    if new_type == "enemy":
                        sel.setdefault("props", {}).setdefault("kind", "slime")
                        sel["props"].setdefault("patrol_min_x", max(0, sel["x"] - 128))
                        sel["props"].setdefault("patrol_max_x", min(self.level_width, sel["x"] + sel["w"] + 128))
                    elif new_type == "collectible":
                        sel.setdefault("props", {}).setdefault("kind", "coin")
                    elif new_type == "destructible":
                        sel.setdefault("props", {}).setdefault("kind", "crate")
                        sel["props"].setdefault("drop", "coin")
                    self._set_status(f"Changed object type to {TYPE_LABELS[new_type]}.")
                elif action.startswith("drop:"):
                    self._push_undo()
                    sel.setdefault("props", {})["drop"] = action.split(":", 1)[1]
                elif action.startswith("item_kind:"):
                    kind = action.split(":", 1)[1]
                    self._push_undo()
                    sel.setdefault("props", {})["kind"] = kind
                    sel["ref"] = f"items:{kind}"
                elif action.startswith("enemy_kind:"):
                    kind = action.split(":", 1)[1]
                    self._push_undo()
                    sel.setdefault("props", {})["kind"] = kind
                    sel["ref"] = f"enemies:{kind}"
                    base = self.assets.get_base_surface(sel["ref"])
                    if base is not None:
                        sel["w"], sel["h"] = base.get_size()
            return

    # ------------------------------------------------------------------
    # Slicer Mode Events
    # ------------------------------------------------------------------
    def _sheet_to_screen(self, sx: float, sy: float) -> tuple[int, int]:
        px = int(round(self.slicer_pan_x + sx * self.slicer_zoom))
        py = int(round(TOPBAR_H + 38 + self.slicer_pan_y + sy * self.slicer_zoom))
        return px, py

    def _screen_to_sheet(self, px: int, py: int) -> tuple[int, int]:
        sx = int(round((px - self.slicer_pan_x) / self.slicer_zoom))
        sy = int(round((py - (TOPBAR_H + 38) - self.slicer_pan_y) / self.slicer_zoom))
        return sx, sy

    def _get_slicer_crop_handles(self) -> dict[str, pygame.Rect]:
        r = self.slicer_crop_rect
        x0, y0 = self._sheet_to_screen(r.left, r.top)
        x1, y1 = self._sheet_to_screen(r.right, r.bottom)
        xm, ym = (x0 + x1) // 2, (y0 + y1) // 2
        hs = 8
        h = hs // 2
        return {
            "nw": pygame.Rect(x0 - h, y0 - h, hs, hs),
            "n": pygame.Rect(xm - h, y0 - h, hs, hs),
            "ne": pygame.Rect(x1 - h, y0 - h, hs, hs),
            "e": pygame.Rect(x1 - h, ym - h, hs, hs),
            "se": pygame.Rect(x1 - h, y1 - h, hs, hs),
            "s": pygame.Rect(xm - h, y1 - h, hs, hs),
            "sw": pygame.Rect(x0 - h, y1 - h, hs, hs),
            "w": pygame.Rect(x0 - h, ym - h, hs, hs),
        }

    def _get_slicer_buttons(self) -> list[tuple[pygame.Rect, str]]:
        btns: list[tuple[pygame.Rect, str]] = []
        # Sheet selector tabs at top of slicer view.
        x = 10
        y = TOPBAR_H + 6
        for idx, sname in enumerate(self.sheet_files):
            w = max(72, self.font_xs.size(sname[:16])[0] + 18)
            if x + w > SLICER_VIEW_W - 350:
                break
            btns.append((pygame.Rect(x, y, w, 26), f"sheet:{idx}"))
            x += w + 6
        btns.append((pygame.Rect(x, y, 86, 26), "add_sheet"))

        btns.append((pygame.Rect(SLICER_VIEW_W - 250, y, 52, 26), "zoom_out"))
        btns.append((pygame.Rect(SLICER_VIEW_W - 194, y, 52, 26), "zoom_in"))
        btns.append((pygame.Rect(SLICER_VIEW_W - 138, y, 128, 26), "toggle_predefined"))

        # Right panel controls.
        rx = SLICER_PANEL_X + 16
        rw = SLICER_PANEL_W - 32
        bw = (rw - 8) // 2

        cy = TOPBAR_H + 258
        btns.append((pygame.Rect(rx, cy, bw, 26), "toggle_rem_bg"))
        btns.append((pygame.Rect(rx + bw + 8, cy, bw, 26), "toggle_rem_interior"))
        cy += 32
        btns.append((pygame.Rect(rx, cy, bw, 26), "toggle_trim"))
        btns.append((pygame.Rect(rx + bw + 8, cy, bw, 26), "toggle_strict_bg"))

        # Name text box.
        cy += 50
        btns.append((pygame.Rect(rx, cy, rw - 78, 28), "focus_name"))
        btns.append((pygame.Rect(rx + rw - 72, cy, 72, 28), "auto_name"))

        # Default collision type pills.
        cy += 50
        slicer_types = ("solid", "one_way", "decoration", "ladder", "spike", "slope_down_right")
        for i, otype in enumerate(slicer_types):
            col = i % 2
            row = i // 2
            btns.append((pygame.Rect(rx + col * (bw + 8), cy + row * 26, bw, 23), f"slicer_type:{otype}"))

        # Scale mode pills.
        cy += 98
        scales = [
            ("tile_64", "64x64 Tile"),
            ("height_64", "Height 64px"),
            ("original", "Original px"),
            ("wide_128", "128x64 Wide"),
        ]
        for i, (skey, _) in enumerate(scales):
            col = i % 2
            row = i // 2
            btns.append((pygame.Rect(rx + col * (bw + 8), cy + row * 26, bw, 23), f"scale:{skey}"))

        # Main action buttons.
        cy += 62
        btns.append((pygame.Rect(rx, cy, rw, 34), "save_slice"))
        cy += 40
        btns.append((pygame.Rect(rx, cy, rw, 32), "save_and_place"))

        return btns

    def _handle_slicer_event(self, event: pygame.event.Event) -> None:
        view_rect = pygame.Rect(0, TOPBAR_H + 38, SLICER_VIEW_W, SCREEN_HEIGHT - TOPBAR_H - 38 - STATUSBAR_H)
        sheet = self._get_active_sheet_surface()

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            my -= BAR_HEIGHT
            if view_rect.collidepoint(mx, my):
                before_sx, before_sy = self._screen_to_sheet(mx, my)
                factor = 1.15 if event.y > 0 else (1.0 / 1.15)
                self.slicer_zoom = max(0.2, min(4.0, self.slicer_zoom * factor))
                after_px, after_py = self._sheet_to_screen(before_sx, before_sy)
                self.slicer_pan_x += mx - after_px
                self.slicer_pan_y += my - after_py
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            self.slicer_editing_name = False

            # Check dragging directly from the Live Preview Card to the Level Canvas!
            if event.button == 1 and self.slicer_preview_card_rect.collidepoint(mx, my):
                created = self.save_current_slice_to_palette()
                if created is not None:
                    self.dragging_from_palette = created
                    self.mode = "editor"
                    self._set_status(
                        f"Dragging newly sliced '{created.name}' — release on the Level Canvas to drop it!"
                    )
                return

            # Check Slicer UI buttons.
            if event.button == 1:
                for rect, action in self._get_slicer_buttons():
                    if rect.collidepoint(mx, my):
                        sounds.play("click")
                        if action.startswith("sheet:"):
                            self.active_sheet_idx = int(action.split(":")[1])
                            self.slicer_preview_dirty = True
                        elif action == "add_sheet":
                            self.open_image_modal()
                        elif action == "zoom_out":
                            self.slicer_zoom = max(0.2, self.slicer_zoom / 1.25)
                        elif action == "zoom_in":
                            self.slicer_zoom = min(4.0, self.slicer_zoom * 1.25)
                        elif action == "toggle_predefined":
                            self.slicer_show_predefined = not self.slicer_show_predefined
                        elif action == "toggle_rem_bg":
                            self.slicer_remove_bg = not self.slicer_remove_bg
                            self.slicer_preview_dirty = True
                        elif action == "toggle_rem_interior":
                            self.slicer_remove_interior = not self.slicer_remove_interior
                            self.slicer_preview_dirty = True
                        elif action == "toggle_trim":
                            self.slicer_auto_trim = not self.slicer_auto_trim
                            self.slicer_preview_dirty = True
                        elif action == "toggle_strict_bg":
                            self.slicer_strict_bg = not self.slicer_strict_bg
                            self.slicer_preview_dirty = True
                        elif action == "focus_name":
                            self.slicer_editing_name = True
                        elif action == "auto_name":
                            self.slicer_name_text = self._next_custom_slice_name()
                        elif action.startswith("slicer_type:"):
                            self.slicer_default_type = action.split(":", 1)[1]
                        elif action.startswith("scale:"):
                            self.slicer_scale_mode = action.split(":", 1)[1]
                        elif action == "save_slice":
                            self.save_current_slice_to_palette()
                        elif action == "save_and_place":
                            created = self.save_current_slice_to_palette()
                            if created is not None:
                                self.mode = "editor"
                        return

            # Sheet viewport interactions.
            if view_rect.collidepoint(mx, my) and sheet is not None:
                if event.button in (2, 3):
                    self.slicer_panning = True
                    self.slicer_pan_start = (mx - self.slicer_pan_x, my - self.slicer_pan_y)
                    return

                if event.button == 1:
                    sx, sy = self._screen_to_sheet(mx, my)
                    # 1. Check crop resize handles.
                    for hname, hrect in self._get_slicer_crop_handles().items():
                        if hrect.collidepoint(mx, my):
                            self.slicer_resizing_handle = hname
                            self.slicer_resize_start_rect = self.slicer_crop_rect.copy()
                            self.slicer_resize_start_pt = (sx, sy)
                            return

                    # 2. If clicking inside current crop rect, drag-move the crop rect.
                    if self.slicer_crop_rect.collidepoint(sx, sy):
                        self.slicer_Moving_crop = True
                        self.slicer_move_offset = (sx - self.slicer_crop_rect.x, sy - self.slicer_crop_rect.y)
                        return

                    # 3. If predefined boxes are visible and user Shift-clicks a predefined box, snap to it.
                    if self.slicer_show_predefined and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                        for cat, name, rect_tup, rem_int, trim in self._get_predefined_sprites_for_active_sheet():
                            pr = pygame.Rect(*rect_tup)
                            if pr.collidepoint(sx, sy):
                                self.slicer_crop_rect = pr.copy()
                                self.slicer_remove_interior = rem_int
                                self.slicer_auto_trim = trim
                                self.slicer_name_text = f"{name}_custom"
                                self.slicer_preview_dirty = True
                                return

                    # 4. Otherwise start drawing a brand-new selection rectangle!
                    sw, sh = sheet.get_size()
                    clamped_x = max(0, min(sw - 1, sx))
                    clamped_y = max(0, min(sh - 1, sy))
                    self.slicer_selecting = True
                    self.slicer_select_start = (clamped_x, clamped_y)
                    self.slicer_crop_rect = pygame.Rect(clamped_x, clamped_y, 1, 1)
                    self.slicer_preview_dirty = True

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.slicer_panning:
                self.slicer_pan_x = mx - self.slicer_pan_start[0]
                self.slicer_pan_y = my - self.slicer_pan_start[1]
                return

            if sheet is None:
                return
            sw, sh = sheet.get_size()
            sx, sy = self._screen_to_sheet(mx, my)
            sx = max(0, min(sw, sx))
            sy = max(0, min(sh, sy))

            if self.slicer_resizing_handle:
                r0 = self.slicer_resize_start_rect
                dx = sx - self.slicer_resize_start_pt[0]
                dy = sy - self.slicer_resize_start_pt[1]
                nx, ny, nw, nh = r0.x, r0.y, r0.width, r0.height
                hname = self.slicer_resizing_handle
                if "e" in hname:
                    nw = max(4, r0.width + dx)
                if "s" in hname:
                    nh = max(4, r0.height + dy)
                if "w" in hname:
                    new_l = max(0, min(r0.right - 4, r0.left + dx))
                    nw = r0.right - new_l
                    nx = new_l
                if "n" in hname:
                    new_t = max(0, min(r0.bottom - 4, r0.top + dy))
                    nh = r0.bottom - new_t
                    ny = new_t
                self.slicer_crop_rect = pygame.Rect(nx, ny, nw, nh)
                self.slicer_preview_dirty = True
            elif self.slicer_Moving_crop:
                nx = max(0, min(sw - self.slicer_crop_rect.width, sx - self.slicer_move_offset[0]))
                ny = max(0, min(sh - self.slicer_crop_rect.height, sy - self.slicer_move_offset[1]))
                self.slicer_crop_rect.topleft = (nx, ny)
                self.slicer_preview_dirty = True
            elif self.slicer_selecting:
                x0, y0 = self.slicer_select_start
                left = min(x0, sx)
                top = min(y0, sy)
                width = max(4, abs(sx - x0))
                height = max(4, abs(sy - y0))
                self.slicer_crop_rect = pygame.Rect(left, top, width, height)
                self.slicer_preview_dirty = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.slicer_selecting and self.slicer_crop_rect.width < 8 and self.slicer_crop_rect.height < 8:
                    # Single click on a predefined box selects it for convenience!
                    mx, my = event.pos
                    sx, sy = self._screen_to_sheet(mx, my)
                    for cat, name, rect_tup, rem_int, trim in self._get_predefined_sprites_for_active_sheet():
                        pr = pygame.Rect(*rect_tup)
                        if pr.collidepoint(sx, sy):
                            self.slicer_crop_rect = pr.copy()
                            self.slicer_remove_interior = rem_int
                            self.slicer_auto_trim = trim
                            self.slicer_preview_dirty = True
                            break
                self.slicer_selecting = False
                self.slicer_Moving_crop = False
                self.slicer_resizing_handle = None
                if self.slicer_preview_dirty:
                    self._update_slicer_preview()
            elif event.button in (2, 3):
                self.slicer_panning = False

    # ------------------------------------------------------------------
    # Playtest Mode Events & Update
    # ------------------------------------------------------------------
    def _handle_playtest_event(self, event: pygame.event.Event) -> str | None:
        if self.playtest_player is None or self.playtest_level is None:
            self.stop_playtest()
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_F5):
                self.stop_playtest()
                return None
            if event.key == pygame.K_SPACE:
                self.playtest_player.trigger_jump()
            elif event.key in (pygame.K_w, pygame.K_UP):
                if (
                    not self.playtest_player.on_ladder
                    and self.playtest_player.find_climbable_ladder_up(self.playtest_level.ladder_rects) is None
                ):
                    self.playtest_player.trigger_jump()
            elif event.key in (pygame.K_j, pygame.K_z, pygame.K_x, pygame.K_f, pygame.K_k):
                self.playtest_player.trigger_attack()
            elif event.key == pygame.K_r:
                self.start_playtest()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            stop_btn = pygame.Rect(SCREEN_WIDTH // 2 - 110, 10, 220, 34)
            if stop_btn.collidepoint(event.pos):
                self.stop_playtest()
                return None
            self.playtest_player.trigger_attack()
        return None

    def update(self) -> None:
        """Per-frame update for camera keyboard panning, slicer preview, and playtest physics."""
        if self.status_timer > 0:
            self.status_timer -= 1

        if self.mode == "playtest":
            self._update_playtest()
            return

        keys = pygame.key.get_pressed()
        if self.mode == "editor":
            pan_speed = 14.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.cam_x = max(0.0, self.cam_x - pan_speed)
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.cam_x = min(float(max(0, self.level_width - CANVAS_W)), self.cam_x + pan_speed)
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.cam_y = max(-64.0, self.cam_y - pan_speed * 0.6)
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.cam_y = min(160.0, self.cam_y + pan_speed * 0.6)
        elif self.mode == "slicer" and not self.slicer_editing_name:
            if self.slicer_preview_dirty and not self.slicer_selecting:
                self._update_slicer_preview()

    def _update_playtest(self) -> None:
        from main import handle_level_interactions

        player = self.playtest_player
        level = self.playtest_level
        if player is None or level is None:
            return

        keys = pygame.key.get_pressed()
        move_events = player.update(
            keys,
            level.get_active_solid_rects(),
            level.one_way_rects,
            level.ladder_rects,
            level.slope_tiles,
            level.width,
        )
        walking = player.on_ground and not player.on_ladder and abs(player.vel_x) > 1.5
        self.playtest_step_timer = self.playtest_step_timer - 1 if walking else 0
        if walking and self.playtest_step_timer <= 0:
            sounds.play("step")
            self.playtest_step_timer = 16

        if move_events["jumped"]:
            sounds.play("jump")
            level.particles.append(
                VFXParticle(player.rect.centerx, player.rect.bottom - 6, image=self.assets.vfx["dust_1"], duration=14)
            )
        elif move_events["landed"]:
            level.particles.append(
                VFXParticle(player.rect.centerx, player.rect.bottom - 6, image=self.assets.vfx["dust_2"], duration=14)
            )

        status = handle_level_interactions(player, level, self.assets)
        if status == "next_level":
            sounds.play("victory")
            level.banner_message = "EXIT REACHED! Press R to replay or Esc to return to Editor!"
            level.banner_timer = 180
            player.respawn(*level.spawn_pos)

        if player.dead:
            player.respawn(*level.spawn_pos)
            level.banner_message = "RESPAWNED AT SPAWN POINT (Press Esc to return to Editor)"
            level.banner_timer = 120

        target_cam_x = player.rect.centerx - 1280 * 0.38
        target_cam_x = max(0.0, min(float(level.width - 1280), target_cam_x))
        self.playtest_cam_x += (target_cam_x - self.playtest_cam_x) * 0.14

    # ------------------------------------------------------------------
    # Image Importer Modal Events & Layout
    # ------------------------------------------------------------------
    def _get_image_modal_rects(self) -> tuple[pygame.Rect, pygame.Rect, list[tuple[pygame.Rect, str]]]:
        mw, mh = min(860, SCREEN_WIDTH - 64), min(580, SCREEN_HEIGHT - 80)
        mx = (SCREEN_WIDTH - mw) // 2
        my = (SCREEN_HEIGHT - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)
        list_rect = pygame.Rect(mx + 18, my + 86, int(mw * 0.54), mh - 104)

        btns: list[tuple[pygame.Rect, str]] = []
        # Close button
        btns.append((pygame.Rect(mx + mw - 42, my + 10, 32, 28), "close"))

        # Quick folder jump bar
        qx = mx + 18
        qy = my + 48
        home = os.path.expanduser("~")
        proj_dir = os.path.dirname(self.assets_dir)
        quick_folders = [
            ("Project", proj_dir),
            ("Assets", self.assets_dir),
            ("Home", home),
            ("Pictures", os.path.join(home, "Pictures")),
            ("Downloads", os.path.join(home, "Downloads")),
            ("Desktop", os.path.join(home, "Desktop")),
        ]
        for label, fpath in quick_folders:
            if os.path.isdir(fpath):
                bw = self.font_xs.size(label)[0] + 16
                btns.append((pygame.Rect(qx, qy, bw, 26), f"dir:{fpath}"))
                qx += bw + 6

        parent_dir = os.path.dirname(self.modal_dir.rstrip(os.sep)) or os.sep
        btns.append((pygame.Rect(qx, qy, 52, 26), f"dir:{parent_dir}"))
        qx += 58
        btns.append((pygame.Rect(qx, qy, 128, 26), "os_dialog"))

        # Right side preview & import controls
        rx = list_rect.right + 18
        rw = mx + mw - 18 - rx
        btns.append((pygame.Rect(rx, my + mh - 122, rw, 28), "toggle_rem_bg"))
        btns.append((pygame.Rect(rx, my + mh - 86, rw, 34), "import_sprite"))
        btns.append((pygame.Rect(rx, my + mh - 46, rw, 34), "import_sheet"))

        return modal_rect, list_rect, btns

    def _handle_image_modal_event(self, event: pygame.event.Event) -> None:
        modal_rect, list_rect, btns = self._get_image_modal_rects()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.image_modal_open = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.modal_selected_path:
                self.import_image_file(self.modal_selected_path, as_sheet=False, remove_bg=self.modal_remove_bg)
            return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            my -= BAR_HEIGHT
            if list_rect.collidepoint(mx, my):
                max_scroll = max(0, len(self.modal_entries) * 28 - (list_rect.height - 12))
                self.modal_scroll = max(0, min(max_scroll, self.modal_scroll - event.y * 28))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not modal_rect.collidepoint(mx, my):
                self.image_modal_open = False
                return

            for rect, action in btns:
                if rect.collidepoint(mx, my):
                    sounds.play("click")
                    if action == "close":
                        self.image_modal_open = False
                    elif action.startswith("dir:"):
                        target_dir = action.split(":", 1)[1]
                        if os.path.isdir(target_dir):
                            self.modal_dir = os.path.abspath(target_dir)
                            self._refresh_modal_entries()
                    elif action == "os_dialog":
                        chosen = self._open_native_file_dialog()
                        if chosen:
                            self.modal_dir = os.path.dirname(os.path.abspath(chosen))
                            self._refresh_modal_entries()
                            self._select_modal_file(chosen)
                    elif action == "toggle_rem_bg":
                        self.modal_remove_bg = not self.modal_remove_bg
                    elif action == "import_sprite":
                        if self.modal_selected_path:
                            self.import_image_file(
                                self.modal_selected_path, as_sheet=False, remove_bg=self.modal_remove_bg
                            )
                        else:
                            self._set_status("Click an image file in the list first!")
                    elif action == "import_sheet":
                        if self.modal_selected_path:
                            self.import_image_file(self.modal_selected_path, as_sheet=True)
                        else:
                            self._set_status("Click an image file in the list first!")
                    return

            if list_rect.collidepoint(mx, my):
                rel_y = my - (list_rect.y + 6) + self.modal_scroll
                idx = rel_y // 28
                if 0 <= idx < len(self.modal_entries):
                    name, is_dir = self.modal_entries[idx]
                    full_path = os.path.join(self.modal_dir, name)
                    sounds.play("click")
                    if is_dir:
                        self.modal_dir = os.path.abspath(full_path)
                        self._refresh_modal_entries()
                    else:
                        self._select_modal_file(full_path)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        """Render the active mode to `surface`."""
        if self.mode == "playtest":
            self._draw_playtest(surface)
            return

        surface.fill(BG_DARK)
        if self.mode == "slicer":
            self._draw_slicer_mode(surface)
        else:
            self._draw_editor_mode(surface)

        self._draw_topbar(surface)
        self._draw_statusbar(surface)

        # Floating drag preview when dragging an item from the Palette (or Slicer).
        if self.dragging_from_palette is not None:
            self._draw_floating_drag_preview(surface)

        if self.image_modal_open:
            self._draw_image_modal(surface)

    def _draw_topbar(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, PANEL_HEADER, (0, 0, SCREEN_WIDTH, TOPBAR_H))
        pygame.draw.line(surface, BORDER_COL, (0, TOPBAR_H - 1), (SCREEN_WIDTH, TOPBAR_H - 1), 2)

        lvls = self.get_levels_list()
        labels = {
            "mode_editor": ("1. Level Editor", self.mode == "editor", ACCENT_BLUE),
            "mode_slicer": ("2. Sheet Slicer", self.mode == "slicer", ACCENT_BLUE),
            "playtest": ("▶ Playtest (F5)", False, ACCENT_GREEN),
            "prev_lvl": ("<", False, HIGHLIGHT_COL),
            "cycle_lvl": (f"Lvl {self.current_level_num}/{len(lvls)}", True, HIGHLIGHT_COL),
            "next_lvl": (">", False, HIGHLIGHT_COL),
            "add_lvl": ("+ Level", False, ACCENT_GREEN),
            "add_image": ("+ Image", False, ACCENT_BLUE),
            "save": ("Save JSON", False, ACCENT_GREEN),
            "reset_default": ("Reset", False, TEXT_MAIN),
            "clear": ("Clear", False, ACCENT_RED),
            "toggle_snap": (f"Snap: {'64px' if self.grid_snap else 'Free'}", self.grid_snap, HIGHLIGHT_COL),
            "toggle_hitboxes": (f"Boxes: {'ON' if self.show_hitboxes else 'OFF'}", self.show_hitboxes, HIGHLIGHT_COL),
            "undo": ("Undo", False, TEXT_MAIN),
            "redo": ("Redo", False, TEXT_MAIN),
            "main_menu": ("Game Menu", False, TEXT_MAIN),
        }

        mx, my = pygame.mouse.get_pos()
        my -= BAR_HEIGHT

        for rect, action in self._get_topbar_buttons():
            text, active, col = labels[action]
            hovered = rect.collidepoint(mx, my)
            bg = CARD_SELECTED if active else (CARD_HOVER if hovered else CARD_BG)
            border_c = col if (active or hovered) else BORDER_COL
            draw_squircle(surface, bg, rect, border_c, 2 if active else 1)
            lbl = self.font_xs.render(text, True, col if active else TEXT_MAIN)
            surface.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_statusbar(self, surface: pygame.Surface) -> None:
        y = SCREEN_HEIGHT - STATUSBAR_H
        pygame.draw.rect(surface, PANEL_HEADER, (0, y, SCREEN_WIDTH, STATUSBAR_H))
        pygame.draw.line(surface, BORDER_COL, (0, y), (SCREEN_WIDTH, y), 1)

        mx, my = pygame.mouse.get_pos()
        my -= BAR_HEIGHT
        wx, wy = self.screen_to_world(mx, my)
        col, row = wx // TILE_SIZE, wy // TILE_SIZE

        msg_col = HIGHLIGHT_COL if self.status_timer > 0 else TEXT_DIM
        msg_surf = self.font_xs.render(self.status_text, True, msg_col)
        surface.blit(msg_surf, (10, y + 6))

        coord_str = f"World: ({wx}, {wy})  |  Grid: Col {col}, Row {row}  |  Objects: {len(self.objects)}"
        coord_surf = self.font_xs.render(coord_str, True, TEXT_MAIN)
        surface.blit(coord_surf, (SCREEN_WIDTH - coord_surf.get_width() - 12, y + 6))

    # ------------------------------------------------------------------
    # Draw Editor Mode (Palette + Level Canvas + Minimap + Inspector)
    # ------------------------------------------------------------------
    def _draw_editor_mode(self, surface: pygame.Surface) -> None:
        self._draw_level_canvas(surface)
        self._draw_minimap(surface)
        self._draw_left_palette(surface)
        self._draw_right_inspector(surface)

    def _draw_level_canvas(self, surface: pygame.Surface) -> None:
        canvas_rect = pygame.Rect(CANVAS_X, CANVAS_Y, CANVAS_W, CANVAS_H)
        prev_clip = surface.get_clip()
        surface.set_clip(canvas_rect)

        # 1. Background parallax preview.
        bg = self.assets.backgrounds.get(self.background_id) or self.assets.backgrounds.get(1)
        if bg is not None:
            temp_bg = create_opaque_surface((CANVAS_W, self.level_height))
            bg.draw(temp_bg, int(self.cam_x))
            surface.blit(temp_bg, (CANVAS_X, int(CANVAS_Y - self.cam_y)))
        else:
            surface.fill((24, 28, 38), canvas_rect)

        # 2. Tile Grid lines (64x64).
        start_col = max(0, int(self.cam_x // TILE_SIZE))
        end_col = min(self.level_width // TILE_SIZE, int((self.cam_x + CANVAS_W) // TILE_SIZE) + 2)
        for c in range(start_col, end_col + 1):
            sx, _ = self.world_to_screen(c * TILE_SIZE, 0)
            line_col = (70, 82, 110) if c % 5 == 0 else (42, 50, 68)
            pygame.draw.line(surface, line_col, (sx, CANVAS_Y), (sx, CANVAS_Y + CANVAS_H), 1)
            if c % 2 == 0 and c < self.level_width // TILE_SIZE:
                clbl = self.font_xs.render(str(c), True, (130, 145, 175))
                surface.blit(clbl, (sx + 3, CANVAS_Y + 2))

        for r in range(-2, 14):
            _, sy = self.world_to_screen(0, r * TILE_SIZE)
            if CANVAS_Y <= sy <= CANVAS_Y + CANVAS_H:
                is_ground = r == 10
                line_col = (110, 185, 110) if is_ground else (42, 50, 68)
                pygame.draw.line(surface, line_col, (CANVAS_X, sy), (CANVAS_X + CANVAS_W, sy), 2 if is_ground else 1)
                rlbl = self.font_xs.render(f"R{r}" + (" (GND)" if is_ground else ""), True, line_col)
                surface.blit(rlbl, (CANVAS_X + 4, sy + 2))

        # 3. Placed Objects sorted by layer.
        sorted_objs = sorted(enumerate(self.objects), key=lambda p: (p[1].get("layer", 1), p[0]))
        for _, obj in sorted_objs:
            self._draw_canvas_object(surface, obj)

        # 4. Selection handles & patrol bars on top.
        sel = self.get_selected_obj()
        if sel is not None:
            sx, sy = self.world_to_screen(sel["x"], sel["y"])
            sel_rect = pygame.Rect(sx, sy, sel["w"], sel["h"])
            pygame.draw.rect(surface, HIGHLIGHT_COL, sel_rect, 2)

            if sel["obj_type"] != "spawn":
                for h_rect in self._get_resize_handles(sel).values():
                    pygame.draw.rect(surface, HIGHLIGHT_COL, h_rect)
                    pygame.draw.rect(surface, BG_DARK, h_rect, 1)

            p_handles = self._get_patrol_handles(sel)
            if p_handles is not None:
                min_r, max_r = p_handles
                pygame.draw.line(
                    surface, (255, 145, 65), (min_r.centerx, min_r.centery), (max_r.centerx, max_r.centery), 3
                )
                for hr, tag in ((min_r, "MIN"), (max_r, "MAX")):
                    pygame.draw.rect(surface, (255, 145, 65), hr, border_radius=3)
                    pygame.draw.rect(surface, BG_DARK, hr, 1, border_radius=3)
                    tlbl = self.font_xs.render(tag, True, (255, 220, 160))
                    surface.blit(tlbl, (hr.centerx - tlbl.get_width() // 2, hr.top - 14))

        surface.set_clip(prev_clip)
        pygame.draw.rect(surface, BORDER_COL, canvas_rect, 1)

    def _draw_canvas_object(self, surface: pygame.Surface, obj: dict) -> None:
        sx, sy = self.world_to_screen(obj["x"], obj["y"])
        w, h = obj["w"], obj["h"]
        if sx + w < CANVAS_X - 64 or sx > CANVAS_X + CANVAS_W + 64:
            return

        otype = obj.get("obj_type", "solid")
        ref = obj.get("ref", "")
        flip_x = bool(obj.get("flip_x", False))
        flip_y = bool(obj.get("flip_y", False))

        if otype == "spawn":
            idle_frame = self.player_sprites["idle"][0]
            surface.blit(
                idle_frame,
                (sx + w // 2 - idle_frame.get_width() // 2, sy + h + 20 - idle_frame.get_height()),
            )
            tag = self.font_xs.render("SPAWN", True, ACCENT_GREEN)
            surface.blit(tag, (sx - 4, sy - 16))
        else:
            surf = self.assets.get_surface(ref, w, h, flip_x=flip_x, flip_y=flip_y)
            if surf is not None:
                surface.blit(surf, (sx, sy))
            else:
                pygame.draw.rect(surface, TYPE_COLORS.get(otype, (150, 150, 150)), (sx, sy, w, h), border_radius=4)

            if otype == "exit":
                tag = self.font_xs.render("EXIT", True, HIGHLIGHT_COL)
                surface.blit(tag, (sx + w // 2 - tag.get_width() // 2, sy - 16))

        # Draw collision/role overlay if `show_hitboxes` is enabled.
        if self.show_hitboxes:
            col = TYPE_COLORS.get(otype, (180, 180, 180))
            if otype == "one_way":
                pygame.draw.rect(surface, col, (sx, sy, w, min(18, h)), 2)
            elif otype == "spike":
                pygame.draw.rect(surface, ACCENT_RED, (sx + 6, sy + 6, max(8, w - 12), 22), 2)
                pygame.draw.rect(surface, ACCENT_GREEN, (sx, sy + 28, w, max(16, h - 16)), 1)
            elif otype == "slope_down_right":
                pygame.draw.line(surface, col, (sx, sy), (sx + w, sy + h), 3)
                pygame.draw.rect(surface, col, (sx, sy, w, h), 1)
            elif otype == "slope_up_right":
                pygame.draw.line(surface, col, (sx, sy + h), (sx + w, sy), 3)
                pygame.draw.rect(surface, col, (sx, sy, w, h), 1)
            elif otype == "enemy":
                pygame.draw.rect(surface, col, (sx, sy, w, h), 1)
                props = obj.get("props") or {}
                p_min = int(props.get("patrol_min_x", obj["x"] - 128))
                p_max = int(props.get("patrol_max_x", obj["x"] + w + 128))
                p0, _ = self.world_to_screen(p_min, obj["y"])
                p1, _ = self.world_to_screen(p_max, obj["y"])
                pygame.draw.line(surface, (220, 110, 165), (p0, sy + h - 4), (p1, sy + h - 4), 2)
            elif otype != "decoration":
                pygame.draw.rect(surface, col, (sx, sy, w, h), 1)

    def _draw_minimap(self, surface: pygame.Surface) -> None:
        mm_rect = pygame.Rect(CANVAS_X, MINIMAP_Y, CANVAS_W, MINIMAP_H)
        pygame.draw.rect(surface, (20, 24, 36), mm_rect)
        pygame.draw.rect(surface, BORDER_COL, mm_rect, 1)

        scale_x = CANVAS_W / max(1, self.level_width)
        scale_y = MINIMAP_H / max(1, self.level_height)

        for obj in self.objects:
            mx = int(CANVAS_X + obj["x"] * scale_x)
            my = int(MINIMAP_Y + max(0, min(self.level_height - 4, obj["y"])) * scale_y)
            mw = max(2, int(obj["w"] * scale_x))
            mh = max(2, int(obj["h"] * scale_y))
            col = TYPE_COLORS.get(obj["obj_type"], (120, 130, 150))
            surface.fill(col, (mx, my, mw, mh))

        # Viewport thumb.
        vx = int(CANVAS_X + self.cam_x * scale_x)
        vw = max(16, int(CANVAS_W * scale_x))
        pygame.draw.rect(surface, HIGHLIGHT_COL, (vx, MINIMAP_Y + 1, vw, MINIMAP_H - 2), 2, border_radius=3)

    def _draw_left_palette(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(0, TOPBAR_H, LEFT_PANEL_W, SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H)
        pygame.draw.rect(surface, PANEL_BG, panel_rect)
        pygame.draw.line(surface, BORDER_COL, (LEFT_PANEL_W - 1, TOPBAR_H), (LEFT_PANEL_W - 1, panel_rect.bottom), 2)

        # Category filter tabs.
        for cat_rect, cat_name in self._get_category_buttons():
            active = self.active_category == cat_name
            pygame.draw.rect(surface, CARD_SELECTED if active else CARD_BG, cat_rect, border_radius=4)
            pygame.draw.rect(surface, HIGHLIGHT_COL if active else BORDER_COL, cat_rect, 1, border_radius=4)
            lbl = self.font_xs.render(cat_name, True, HIGHLIGHT_COL if active else TEXT_DIM)
            surface.blit(lbl, lbl.get_rect(center=cat_rect.center))

        # "+ Slice Sheet" and "+ Add Image" shortcut buttons.
        half_w = (LEFT_PANEL_W - 20) // 2
        slice_btn = pygame.Rect(8, TOPBAR_H + 36, half_w, 26)
        add_img_btn = pygame.Rect(12 + half_w, TOPBAR_H + 36, half_w, 26)
        draw_squircle(surface, (42, 68, 98), slice_btn, ACCENT_BLUE, 1)
        slbl = self.font_xs.render("+ Slice Sheet", True, TEXT_MAIN)
        surface.blit(slbl, slbl.get_rect(center=slice_btn.center))

        draw_squircle(surface, (42, 86, 62), add_img_btn, ACCENT_GREEN, 1)
        albl = self.font_xs.render("+ Add Image", True, TEXT_MAIN)
        surface.blit(albl, albl.get_rect(center=add_img_btn.center))

        # Palette cards list (keep square/rectangular cards for sliced image selection).
        list_clip = pygame.Rect(0, TOPBAR_H + 66, LEFT_PANEL_W - 2, panel_rect.height - 66)
        prev_clip = surface.get_clip()
        surface.set_clip(list_clip)

        mx, my = pygame.mouse.get_pos()
        my -= BAR_HEIGHT

        for card_rect, item in self._get_palette_card_rects():
            if card_rect.bottom < list_clip.top or card_rect.top > list_clip.bottom:
                continue
            selected = self.selected_palette_item is item
            hovered = card_rect.collidepoint(mx, my)
            bg = CARD_SELECTED if selected else (CARD_HOVER if hovered else CARD_BG)
            tcol = TYPE_COLORS.get(item.obj_type, BORDER_COL)
            pygame.draw.rect(surface, bg, card_rect, border_radius=4)
            pygame.draw.rect(
                surface, HIGHLIGHT_COL if selected else tcol, card_rect, 2 if selected else 1, border_radius=4
            )

            # Thumbnail preview.
            thumb_box = pygame.Rect(card_rect.x + 6, card_rect.y + 6, card_rect.width - 12, 46)
            draw_checkerboard(surface, thumb_box, cell=6)
            if item.obj_type == "spawn":
                surf = self.player_sprites["idle"][0]
            else:
                surf = self.assets.get_base_surface(item.ref)
            if surf is not None:
                iw, ih = surf.get_size()
                scale = min((thumb_box.width - 4) / max(1, iw), (thumb_box.height - 4) / max(1, ih), 1.5)
                tw = max(4, int(round(iw * scale)))
                th = max(4, int(round(ih * scale)))
                scaled = pygame.transform.smoothscale(surf, (tw, th))
                surface.blit(scaled, scaled.get_rect(center=thumb_box.center))

            # Item name & size badge.
            name_str = item.name[:14]
            nlbl = self.font_xs.render(name_str, True, TEXT_MAIN)
            surface.blit(nlbl, (card_rect.x + 6, card_rect.bottom - 28))

            type_str = f"{item.default_w}x{item.default_h} {item.obj_type[:7]}"
            tlbl = self.font_xs.render(type_str, True, tcol)
            surface.blit(tlbl, (card_rect.x + 6, card_rect.bottom - 14))

        surface.set_clip(prev_clip)

    def _draw_right_inspector(self, surface: pygame.Surface) -> None:
        rx = SCREEN_WIDTH - RIGHT_PANEL_W
        panel_rect = pygame.Rect(rx, TOPBAR_H, RIGHT_PANEL_W, SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H)
        pygame.draw.rect(surface, PANEL_BG, panel_rect)
        pygame.draw.line(surface, BORDER_COL, (rx, TOPBAR_H), (rx, panel_rect.bottom), 2)

        pad_x = rx + 10
        y = TOPBAR_H + 10
        sel = self.get_selected_obj()

        if sel is None:
            hdr = self.font_sm.render("LEVEL SETTINGS", True, HIGHLIGHT_COL)
            surface.blit(hdr, (pad_x, y))
            surface.blit(self.font_xs.render("Parallax Background Theme:", True, TEXT_DIM), (pad_x, TOPBAR_H + 66))
            surface.blit(
                self.font_xs.render(
                    f"Level Width: {self.level_width // TILE_SIZE} cols ({self.level_width}px)", True, TEXT_DIM
                ),
                (pad_x, TOPBAR_H + 118),
            )
            surface.blit(self.font_xs.render("LEVEL SLOTS (CLICK TO SWITCH):", True, HIGHLIGHT_COL), (pad_x, TOPBAR_H + 170))

            max_btn_bottom = TOPBAR_H + 220
            for rect, action in self._get_inspector_buttons():
                max_btn_bottom = max(max_btn_bottom, rect.bottom)
                if action == "edit_level_name":
                    draw_squircle(
                        surface,
                        (16, 20, 30),
                        rect,
                        HIGHLIGHT_COL if self.editing_level_name else BORDER_COL,
                        2 if self.editing_level_name else 1,
                    )
                    cursor = "_" if self.editing_level_name and (pygame.time.get_ticks() // 400) % 2 == 0 else ""
                    lbl = self.font_xs.render((self.level_name + cursor)[:30], True, TEXT_MAIN)
                    surface.blit(lbl, (rect.x + 8, rect.y + 6))
                elif action in ("bg_1", "bg_2"):
                    active = (action == "bg_1" and self.background_id == 1) or (action == "bg_2" and self.background_id == 2)
                    draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, HIGHLIGHT_COL if active else BORDER_COL, 1)
                    txt = "1: Grasslands" if action == "bg_1" else "2: Stronghold"
                    lbl = self.font_xs.render(txt, True, HIGHLIGHT_COL if active else TEXT_MAIN)
                    surface.blit(lbl, lbl.get_rect(center=rect.center))
                elif action in ("width_minus", "width_plus"):
                    draw_squircle(surface, CARD_BG, rect, BORDER_COL, 1)
                    txt = "- 4 Tiles" if action == "width_minus" else "+ 4 Tiles"
                    lbl = self.font_xs.render(txt, True, TEXT_MAIN)
                    surface.blit(lbl, lbl.get_rect(center=rect.center))
                elif action.startswith("select_lvl:"):
                    lnum = int(action.split(":", 1)[1])
                    active = lnum == self.current_level_num
                    draw_squircle(
                        surface,
                        CARD_SELECTED if active else CARD_BG,
                        rect,
                        HIGHLIGHT_COL if active else BORDER_COL,
                        2 if active else 1,
                    )
                    lbl = self.font_xs.render(f"Level {lnum}", True, HIGHLIGHT_COL if active else TEXT_MAIN)
                    surface.blit(lbl, lbl.get_rect(center=rect.center))
                elif action == "add_lvl":
                    draw_squircle(surface, (42, 86, 62), rect, ACCENT_GREEN, 1)
                    lbl = self.font_xs.render("+ New Level", True, TEXT_MAIN)
                    surface.blit(lbl, lbl.get_rect(center=rect.center))
                elif action == "delete_lvl":
                    draw_squircle(surface, (86, 40, 46), rect, ACCENT_RED, 1)
                    txt = "Reset Lvl" if self.current_level_num <= 2 else f"Delete Lvl {self.current_level_num}"
                    lbl = self.font_xs.render(txt, True, TEXT_MAIN)
                    surface.blit(lbl, lbl.get_rect(center=rect.center))

            # Quick Editor Guide.
            y = max_btn_bottom + 18
            surface.blit(self.font_sm.render("QUICK CONTROLS", True, HIGHLIGHT_COL), (pad_x, y))
            y += 22
            tips = [
                "• Drag from Left Palette -> Canvas",
                "• Click + Drag object to move",
                "• Drag 8 corner handles to resize",
                "• Ctrl + Drag object to duplicate",
                "• Shift + Drag canvas to paint row",
                "• Hold Alt to bypass 64px snap",
                "• Right-Click object to delete",
                "• Middle/Right Drag canvas to pan",
                "• + Image: Import external PNG/JPG",
                "• + Level: Add Level 3, 4, 5...",
                "• F5 / P: Playtest with Knight!",
            ]
            for tip in tips:
                if y + 16 > panel_rect.bottom - 4:
                    break
                surface.blit(self.font_xs.render(tip, True, TEXT_DIM), (pad_x, y))
                y += 19
            return

        # Selected Object Inspector.
        hdr = self.font_sm.render(f"OBJECT #{sel['id']}", True, HIGHLIGHT_COL)
        surface.blit(hdr, (pad_x, y))
        y += 24

        # Thumbnail + Coordinates.
        thumb_rect = pygame.Rect(pad_x, y, 56, 56)
        draw_checkerboard(surface, thumb_rect, cell=6)
        pygame.draw.rect(surface, BORDER_COL, thumb_rect, 1)
        surf = (
            self.player_sprites["idle"][0]
            if sel["obj_type"] == "spawn"
            else self.assets.get_surface(sel["ref"], flip_x=sel.get("flip_x", False), flip_y=sel.get("flip_y", False))
        )
        if surf is not None:
            iw, ih = surf.get_size()
            sc = min(50 / max(1, iw), 50 / max(1, ih), 1.5)
            scaled = pygame.transform.smoothscale(surf, (max(4, int(iw * sc)), max(4, int(ih * sc))))
            surface.blit(scaled, scaled.get_rect(center=thumb_rect.center))

        info_x = pad_x + 64
        surface.blit(self.font_xs.render(f"Ref: {sel['ref'][:20]}", True, TEXT_MAIN), (info_x, y + 2))
        surface.blit(
            self.font_xs.render(f"Pos: ({sel['x']}, {sel['y']})", True, TEXT_DIM),
            (info_x, y + 20),
        )
        surface.blit(
            self.font_xs.render(f"Size: {sel['w']}x{sel['h']}  |  Layer: {sel.get('layer', 1)}", True, TEXT_DIM),
            (info_x, y + 38),
        )

        # Action & Type buttons.
        btn_labels = {
            "flip_h": f"Flip H (F): {'ON' if sel.get('flip_x') else 'OFF'}",
            "flip_v": f"Flip V (V): {'ON' if sel.get('flip_y') else 'OFF'}",
            "layer_down": "Layer - ([)",
            "layer_up": "Layer + (])",
            "reset_size": "Native Size",
            "duplicate": "Duplicate",
            "delete": "Delete Object (Del)",
        }

        surface.blit(self.font_xs.render("COLLISION / OBJECT ROLE:", True, HIGHLIGHT_COL), (pad_x, TOPBAR_H + 266))

        for rect, action in self._get_inspector_buttons():
            if action in btn_labels:
                col = ACCENT_RED if action == "delete" else BORDER_COL
                draw_squircle(surface, CARD_BG, rect, col, 1)
                lbl = self.font_xs.render(btn_labels[action], True, ACCENT_RED if action == "delete" else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("type:"):
                otype = action.split(":", 1)[1]
                active = sel["obj_type"] == otype
                tcol = TYPE_COLORS.get(otype, BORDER_COL)
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, tcol if active else BORDER_COL, 2 if active else 1)
                lbl = self.font_xs.render(TYPE_LABELS[otype][:14], True, tcol if active else TEXT_DIM)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("drop:"):
                drop = action.split(":", 1)[1]
                active = (sel.get("props") or {}).get("drop", "coin") == drop
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, HIGHLIGHT_COL if active else BORDER_COL, 1)
                lbl = self.font_xs.render(drop.capitalize(), True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("item_kind:"):
                kind = action.split(":", 1)[1]
                active = (sel.get("props") or {}).get("kind", "coin") == kind
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, HIGHLIGHT_COL if active else BORDER_COL, 1)
                lbl = self.font_xs.render(kind.capitalize(), True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("enemy_kind:"):
                kind = action.split(":", 1)[1]
                active = (sel.get("props") or {}).get("kind", "slime") == kind
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, HIGHLIGHT_COL if active else BORDER_COL, 1)
                lbl = self.font_xs.render(kind.replace("goblin_", "g_"), True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_floating_drag_preview(self, surface: pygame.Surface) -> None:
        item = self.dragging_from_palette
        if item is None:
            return
        mx, my = pygame.mouse.get_pos()
        my -= BAR_HEIGHT
        mods = pygame.key.get_mods()
        bypass_snap = bool(mods & pygame.KMOD_ALT)

        canvas_rect = pygame.Rect(CANVAS_X, CANVAS_Y, CANVAS_W, CANVAS_H)
        if canvas_rect.collidepoint(mx, my):
            wx, wy = self.screen_to_world(mx, my)
            if self.grid_snap and not bypass_snap:
                gx = (wx // self.grid_size) * self.grid_size
                gy = (wy // self.grid_size) * self.grid_size
                if item.obj_type in ("destructible", "chest", "lever", "locked_door", "enemy"):
                    px = gx + max(0, (TILE_SIZE - item.default_w) // 2)
                    py = gy + TILE_SIZE - item.default_h
                elif item.obj_type == "ladder":
                    px = gx + (TILE_SIZE - item.default_w) // 2
                    py = gy
                elif item.obj_type == "spike":
                    px = gx
                    py = gy - 16
                elif item.obj_type == "collectible":
                    px = gx + (TILE_SIZE - item.default_w) // 2
                    py = gy + (TILE_SIZE - item.default_h) // 2
                else:
                    px, py = gx, gy
            else:
                px = wx - item.default_w // 2
                py = wy - item.default_h // 2
            sx, sy = self.world_to_screen(px, py)
        else:
            sx = mx - item.default_w // 2
            sy = my - item.default_h // 2

        surf = (
            self.player_sprites["idle"][0]
            if item.obj_type == "spawn"
            else self.assets.get_surface(item.ref, item.default_w, item.default_h)
        )
        if surf is not None:
            ghost = surf.copy()
            ghost.fill((255, 255, 255, 190), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(ghost, (sx, sy))
        tcol = TYPE_COLORS.get(item.obj_type, HIGHLIGHT_COL)
        pygame.draw.rect(surface, tcol, (sx, sy, item.default_w, item.default_h), 2)

    # ------------------------------------------------------------------
    # Draw Sprite Sheet Slicer Mode
    # ------------------------------------------------------------------
    def _draw_slicer_mode(self, surface: pygame.Surface) -> None:
        # 1. Sheet selector header bar.
        pygame.draw.rect(surface, PANEL_BG, (0, TOPBAR_H, SLICER_VIEW_W, 38))
        pygame.draw.line(surface, BORDER_COL, (0, TOPBAR_H + 37), (SLICER_VIEW_W, TOPBAR_H + 37), 1)

        # 2. Interactive sheet viewport.
        view_rect = pygame.Rect(0, TOPBAR_H + 38, SLICER_VIEW_W, SCREEN_HEIGHT - TOPBAR_H - 38 - STATUSBAR_H)
        draw_checkerboard(surface, view_rect, cell=16)

        prev_clip = surface.get_clip()
        surface.set_clip(view_rect)

        sheet = self._get_active_sheet_surface()
        if sheet is not None:
            sw, sh = sheet.get_size()
            zw = max(1, int(round(sw * self.slicer_zoom)))
            zh = max(1, int(round(sh * self.slicer_zoom)))
            scaled_sheet = pygame.transform.smoothscale(sheet, (zw, zh))
            px, py = self._sheet_to_screen(0, 0)
            surface.blit(scaled_sheet, (px, py))
            pygame.draw.rect(surface, BORDER_COL, (px, py, zw, zh), 1)

            # Optional predefined slice overlays.
            if self.slicer_show_predefined:
                for cat, name, rect_tup, _, _ in self._get_predefined_sprites_for_active_sheet():
                    rx, ry, rw, rh = rect_tup
                    x0, y0 = self._sheet_to_screen(rx, ry)
                    x1, y1 = self._sheet_to_screen(rx + rw, ry + rh)
                    pygame.draw.rect(surface, (80, 175, 255), (x0, y0, x1 - x0, y1 - y0), 1)

            # Active user selection crop rectangle.
            cr = self.slicer_crop_rect
            cx0, cy0 = self._sheet_to_screen(cr.left, cr.top)
            cx1, cy1 = self._sheet_to_screen(cr.right, cr.bottom)
            crop_screen_rect = pygame.Rect(cx0, cy0, max(2, cx1 - cx0), max(2, cy1 - cy0))
            pygame.draw.rect(surface, HIGHLIGHT_COL, crop_screen_rect, 2)

            for hrect in self._get_slicer_crop_handles().values():
                pygame.draw.rect(surface, HIGHLIGHT_COL, hrect)
                pygame.draw.rect(surface, BG_DARK, hrect, 1)

            dim_tag = self.font_xs.render(f"Crop: ({cr.x}, {cr.y}, {cr.width}x{cr.height})", True, HIGHLIGHT_COL)
            tag_bg = pygame.Rect(cx0, max(view_rect.top + 2, cy0 - 20), dim_tag.get_width() + 8, 18)
            pygame.draw.rect(surface, BG_DARK, tag_bg, border_radius=3)
            surface.blit(dim_tag, (tag_bg.x + 4, tag_bg.y + 2))

        surface.set_clip(prev_clip)

        # 3. Right Slicer Panel (Live Extracted Preview + Drag-to-Canvas Card + Controls).
        panel_rect = pygame.Rect(SLICER_PANEL_X, TOPBAR_H, SLICER_PANEL_W, SCREEN_HEIGHT - TOPBAR_H - STATUSBAR_H)
        pygame.draw.rect(surface, PANEL_BG, panel_rect)
        pygame.draw.line(surface, BORDER_COL, (SLICER_PANEL_X, TOPBAR_H), (SLICER_PANEL_X, panel_rect.bottom), 2)

        rx = SLICER_PANEL_X + 16
        rw = SLICER_PANEL_W - 32
        surface.blit(
            self.font_sm.render("LIVE SLICE PREVIEW (DRAG TO LEVEL!)", True, HIGHLIGHT_COL),
            (rx, TOPBAR_H + 10),
        )

        # Draggable Preview Card.
        preview_box = pygame.Rect(rx, TOPBAR_H + 34, rw, 196)
        self.slicer_preview_card_rect = preview_box
        draw_checkerboard(surface, preview_box, cell=10)
        pygame.draw.rect(surface, ACCENT_BLUE, preview_box, 2, border_radius=6)

        if self.slicer_preview_surf is not None:
            pw, ph = self.slicer_preview_surf.get_size()
            scale = min((preview_box.width - 24) / max(1, pw), (preview_box.height - 40) / max(1, ph), 2.5)
            dw = max(4, int(round(pw * scale)))
            dh = max(4, int(round(ph * scale)))
            scaled_p = pygame.transform.smoothscale(self.slicer_preview_surf, (dw, dh))
            surface.blit(scaled_p, scaled_p.get_rect(center=(preview_box.centerx, preview_box.centery - 10)))

            tw, th = self._compute_slice_target_size(self.slicer_preview_surf)
            info_txt = f"Trimmed: {pw}x{ph}px  ->  Level Size: {tw}x{th}px  |  Drag this box to drop into Level!"
            ilbl = self.font_xs.render(info_txt, True, HIGHLIGHT_COL)
            surface.blit(ilbl, ilbl.get_rect(midbottom=(preview_box.centerx, preview_box.bottom - 6)))

        surface.blit(self.font_xs.render("BACKGROUND REMOVAL & TRIMMING:", True, TEXT_DIM), (rx, TOPBAR_H + 238))
        surface.blit(self.font_xs.render("SPRITE NAME (IN CUSTOM PALETTE):", True, TEXT_DIM), (rx, TOPBAR_H + 320))
        surface.blit(self.font_xs.render("DEFAULT COLLISION ROLE:", True, TEXT_DIM), (rx, TOPBAR_H + 372))
        surface.blit(self.font_xs.render("PLACEMENT SCALE:", True, TEXT_DIM), (rx, TOPBAR_H + 468))

        # Draw all Slicer buttons as squircles.
        for rect, action in self._get_slicer_buttons():
            if action.startswith("sheet:"):
                idx = int(action.split(":")[1])
                active = (self.active_sheet_idx % max(1, len(self.sheet_files))) == idx
                draw_squircle(
                    surface,
                    CARD_SELECTED if active else CARD_BG,
                    rect,
                    HIGHLIGHT_COL if active else BORDER_COL,
                    2 if active else 1,
                )
                lbl = self.font_xs.render(self.sheet_files[idx][:16], True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "add_sheet":
                draw_squircle(surface, (42, 68, 108), rect, ACCENT_BLUE, 1)
                lbl = self.font_xs.render("+ Add Sheet", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action in ("zoom_out", "zoom_in", "toggle_predefined"):
                active = action == "toggle_predefined" and self.slicer_show_predefined
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, HIGHLIGHT_COL if active else BORDER_COL, 1)
                txt = (
                    "- Zoom"
                    if action == "zoom_out"
                    else ("+ Zoom" if action == "zoom_in" else f"Guides: {'ON' if self.slicer_show_predefined else 'OFF'}")
                )
                lbl = self.font_xs.render(txt, True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action in ("toggle_rem_bg", "toggle_rem_interior", "toggle_trim", "toggle_strict_bg"):
                state_map = {
                    "toggle_rem_bg": ("Remove Sheet BG", self.slicer_remove_bg),
                    "toggle_rem_interior": ("Hollow Interior BG", self.slicer_remove_interior),
                    "toggle_trim": ("Auto-Trim Alpha", self.slicer_auto_trim),
                    "toggle_strict_bg": ("Strict BG Match", self.slicer_strict_bg),
                }
                label, on = state_map[action]
                draw_squircle(surface, CARD_SELECTED if on else CARD_BG, rect, ACCENT_GREEN if on else BORDER_COL, 1)
                lbl = self.font_xs.render(f"[{'x' if on else ' '}] {label}", True, ACCENT_GREEN if on else TEXT_DIM)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "focus_name":
                draw_squircle(
                    surface,
                    (16, 20, 30),
                    rect,
                    HIGHLIGHT_COL if self.slicer_editing_name else BORDER_COL,
                    2 if self.slicer_editing_name else 1,
                )
                cursor = "_" if self.slicer_editing_name and (pygame.time.get_ticks() // 400) % 2 == 0 else ""
                lbl = self.font_sm.render(self.slicer_name_text + cursor, True, TEXT_MAIN)
                surface.blit(lbl, (rect.x + 8, rect.y + 5))
            elif action == "auto_name":
                draw_squircle(surface, CARD_BG, rect, BORDER_COL, 1)
                lbl = self.font_xs.render("Next #", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("slicer_type:"):
                otype = action.split(":", 1)[1]
                active = self.slicer_default_type == otype
                tcol = TYPE_COLORS.get(otype, BORDER_COL)
                draw_squircle(surface, CARD_SELECTED if active else CARD_BG, rect, tcol if active else BORDER_COL, 2 if active else 1)
                lbl = self.font_xs.render(TYPE_LABELS[otype], True, tcol if active else TEXT_DIM)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("scale:"):
                skey = action.split(":", 1)[1]
                active = self.slicer_scale_mode == skey
                slabels = {
                    "tile_64": "Fit 64x64 Tile",
                    "height_64": "Height 64px",
                    "original": "Original Size",
                    "wide_128": "Wide 128x64",
                }
                draw_squircle(
                    surface,
                    CARD_SELECTED if active else CARD_BG,
                    rect,
                    HIGHLIGHT_COL if active else BORDER_COL,
                    2 if active else 1,
                )
                lbl = self.font_xs.render(slabels[skey], True, HIGHLIGHT_COL if active else TEXT_DIM)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "save_slice":
                draw_squircle(surface, (42, 92, 58), rect, ACCENT_GREEN, 2)
                lbl = self.font_sm.render("Slice & Save to Custom Palette (Enter)", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "save_and_place":
                draw_squircle(surface, (42, 68, 108), rect, ACCENT_BLUE, 2)
                lbl = self.font_sm.render("Slice & Switch to Level Editor", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))

    # ------------------------------------------------------------------
    # Draw Image Importer Modal
    # ------------------------------------------------------------------
    def _draw_image_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 195))
        surface.blit(overlay, (0, 0))

        modal_rect, list_rect, btns = self._get_image_modal_rects()
        pygame.draw.rect(surface, PANEL_BG, modal_rect, border_radius=8)
        pygame.draw.rect(surface, HIGHLIGHT_COL, modal_rect, 2, border_radius=8)

        title_lbl = self.font_md.render("ADD ADDITIONAL IMAGES & SPRITE SHEETS", True, HIGHLIGHT_COL)
        surface.blit(title_lbl, (modal_rect.x + 18, modal_rect.y + 12))

        sub_lbl = self.font_xs.render(
            f"Folder: {self.modal_dir}   (Tip: You can also drag-and-drop image files onto the window!)",
            True,
            TEXT_DIM,
        )
        surface.blit(sub_lbl, (modal_rect.x + 18, modal_rect.y + 32))

        # File & folder list box
        pygame.draw.rect(surface, (16, 20, 30), list_rect, border_radius=6)
        pygame.draw.rect(surface, BORDER_COL, list_rect, 1, border_radius=6)

        mx, my = pygame.mouse.get_pos()
        my -= BAR_HEIGHT

        prev_clip = surface.get_clip()
        surface.set_clip(list_rect.inflate(-4, -4))
        for idx, (name, is_dir) in enumerate(self.modal_entries):
            row_y = list_rect.y + 6 + idx * 28 - self.modal_scroll
            if row_y + 26 < list_rect.top or row_y > list_rect.bottom:
                continue
            row_rect = pygame.Rect(list_rect.x + 6, row_y, list_rect.width - 12, 25)
            full_p = os.path.join(self.modal_dir, name)
            is_sel = not is_dir and os.path.abspath(full_p) == os.path.abspath(self.modal_selected_path or "")
            is_hov = row_rect.collidepoint(mx, my)
            if is_sel or is_hov:
                pygame.draw.rect(surface, CARD_SELECTED if is_sel else CARD_HOVER, row_rect, border_radius=4)
                pygame.draw.rect(surface, HIGHLIGHT_COL if is_sel else BORDER_COL, row_rect, 1, border_radius=4)
            prefix = "[DIR] " if is_dir else "[IMG] "
            col = HIGHLIGHT_COL if is_dir else (ACCENT_GREEN if is_sel else TEXT_MAIN)
            rlbl = self.font_xs.render(f"{prefix}{name}", True, col)
            surface.blit(rlbl, (row_rect.x + 8, row_rect.y + 5))
        surface.set_clip(prev_clip)

        # Right side image preview box
        rx = list_rect.right + 18
        rw = modal_rect.right - 18 - rx
        preview_rect = pygame.Rect(rx, list_rect.y, rw, list_rect.height - 134)
        draw_checkerboard(surface, preview_rect, cell=10)
        pygame.draw.rect(surface, BORDER_COL, preview_rect, 1, border_radius=6)

        if self.modal_preview_surf is not None:
            iw, ih = self.modal_preview_surf.get_size()
            sc = min((preview_rect.width - 16) / max(1, iw), (preview_rect.height - 32) / max(1, ih), 3.0)
            tw, th = max(4, int(round(iw * sc))), max(4, int(round(ih * sc)))
            scaled = pygame.transform.smoothscale(self.modal_preview_surf, (tw, th))
            surface.blit(scaled, scaled.get_rect(center=(preview_rect.centerx, preview_rect.centery - 8)))
            info_lbl = self.font_xs.render(
                f"{os.path.basename(self.modal_selected_path)} ({iw}x{ih}px)", True, HIGHLIGHT_COL
            )
            surface.blit(info_lbl, info_lbl.get_rect(midbottom=(preview_rect.centerx, preview_rect.bottom - 6)))
        else:
            empty_lbl = self.font_xs.render("Select an image file on the left to preview", True, TEXT_DIM)
            surface.blit(empty_lbl, empty_lbl.get_rect(center=preview_rect.center))

        # Modal buttons (squircles)
        for rect, action in btns:
            hovered = rect.collidepoint(mx, my)
            if action == "close":
                draw_squircle(surface, (110, 36, 44) if hovered else (82, 28, 36), rect, ACCENT_RED, 1)
                lbl = self.font_xs.render("X", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action.startswith("dir:"):
                target = action.split(":", 1)[1]
                parent_dir = os.path.dirname(self.modal_dir.rstrip(os.sep)) or os.sep
                if rect.width == 52 and target == parent_dir:
                    txt = ".. Up"
                else:
                    txt = os.path.basename(target) or "Project"
                    if target == os.path.dirname(self.assets_dir):
                        txt = "Project"
                    elif target == self.assets_dir:
                        txt = "Assets"
                    elif target == os.path.expanduser("~"):
                        txt = "Home"
                active = os.path.abspath(target) == os.path.abspath(self.modal_dir)
                draw_squircle(
                    surface,
                    CARD_SELECTED if active else (CARD_HOVER if hovered else CARD_BG),
                    rect,
                    HIGHLIGHT_COL if active else BORDER_COL,
                    1,
                )
                lbl = self.font_xs.render(txt, True, HIGHLIGHT_COL if active else TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "os_dialog":
                draw_squircle(surface, (42, 68, 108) if not hovered else (55, 86, 132), rect, ACCENT_BLUE, 1)
                lbl = self.font_xs.render("OS File Dialog...", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "toggle_rem_bg":
                on = self.modal_remove_bg
                draw_squircle(surface, CARD_SELECTED if on else CARD_BG, rect, ACCENT_GREEN if on else BORDER_COL, 1)
                lbl = self.font_xs.render(
                    f"[{'x' if on else ' '}] Auto-Remove Solid Background & Trim",
                    True,
                    ACCENT_GREEN if on else TEXT_DIM,
                )
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "import_sprite":
                draw_squircle(surface, (42, 92, 58) if not hovered else (52, 114, 72), rect, ACCENT_GREEN, 2)
                lbl = self.font_sm.render("+ Add to Custom Palette (Sprite)", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))
            elif action == "import_sheet":
                draw_squircle(surface, (42, 68, 108) if not hovered else (55, 86, 132), rect, ACCENT_BLUE, 2)
                lbl = self.font_sm.render("Open as Sprite Sheet in Slicer", True, TEXT_MAIN)
                surface.blit(lbl, lbl.get_rect(center=rect.center))

    # ------------------------------------------------------------------
    # Draw Playtest Mode
    # ------------------------------------------------------------------
    def _draw_playtest(self, surface: pygame.Surface) -> None:
        from main import draw_hud

        if self.playtest_level is None or self.playtest_player is None:
            return
        cam_int = int(round(self.playtest_cam_x))
        world_surf = create_opaque_surface((1280, 720))
        self.playtest_level.draw(world_surf, cam_int, self.font_sm)
        self.playtest_player.draw(world_surf, cam_int)
        for p in self.playtest_level.particles:
            p.draw(world_surf, cam_int, self.font_sm)
        if surface.get_size() == (1280, 720):
            surface.blit(world_surf, (0, 0))
        else:
            pygame.transform.smoothscale(world_surf, surface.get_size(), surface)
        draw_hud(
            surface,
            self.playtest_player,
            self.playtest_level,
            self.assets,
            self.font_sm,
            self.font_md,
            self.font_lg,
        )

        # Floating "Stop Playtest" squircle pill at top center.
        stop_btn = pygame.Rect(SCREEN_WIDTH // 2 - 110, 10, 220, 34)
        draw_squircle(surface, (145, 38, 46), stop_btn, HIGHLIGHT_COL, 2)
        lbl = self.font_sm.render("■ Return to Editor (Esc/F5)", True, TEXT_MAIN)
        surface.blit(lbl, lbl.get_rect(center=stop_btn.center))


def run_editor(
    window: pygame.Surface | None = None,
    screen: pygame.Surface | None = None,
    titlebar: TitleBar | None = None,
    initial_level: int = 1,
    max_frames: int | None = None,
) -> None:
    """Run the interactive Level Editor & Sprite Sheet Slicer loop."""
    standalone = window is None
    if standalone:
        pygame.init()
        window = create_window(1280, 720 + BAR_HEIGHT, fullscreen=True)
        screen = create_opaque_surface((window.get_width(), window.get_height() - BAR_HEIGHT))
        pygame.display.set_caption(EDITOR_TITLE)
        titlebar = TitleBar(window.get_width(), EDITOR_TITLE)
        sounds.init()

    assert window is not None and screen is not None and titlebar is not None
    prev_title = titlebar.title
    titlebar.title = EDITOR_TITLE

    def sync_editor_surface() -> None:
        nonlocal window, screen
        disp = pygame.display.get_surface()
        if disp is not None:
            window = disp
        vw = max(1280, window.get_width())
        vh = max(720, window.get_height() - BAR_HEIGHT)
        sync_editor_layout(vw, vh)
        if screen.get_size() != (vw, vh):
            screen = create_opaque_surface((vw, vh))
        titlebar.set_width(window.get_width())

    sync_editor_surface()
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    app = LevelEditorApp(assets_dir=assets_dir, initial_level=initial_level)
    clock = pygame.time.Clock()
    font_title = pygame.font.SysFont("dejavusans,arial,sans-serif", 15, bold=True)

    frames = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                if not standalone:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                break
            if titlebar.handle_event(event):
                sync_editor_surface()
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                window = toggle_fullscreen()
                sync_editor_surface()
                continue
            shift_mouse_event(event)
            result = app.handle_event(event)
            if result in ("quit", "main_menu"):
                running = False
                break

        sync_editor_surface()
        app.update()
        app.draw(screen)
        window.blit(screen, (0, BAR_HEIGHT))
        titlebar.draw(window, font_title)
        pygame.display.flip()
        clock.tick(FPS)

        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False

    titlebar.title = prev_title
    if standalone:
        pygame.quit()


if __name__ == "__main__":
    run_editor()
