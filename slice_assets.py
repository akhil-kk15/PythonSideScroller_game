"""Slice combined sprite sheets into transparent PNG sprites."""

import os
from collections import deque
import pygame


def is_bg_or_grid(r: int, g: int, b: int) -> bool:
    """Return whether a color matches the sheet background or grid."""
    return (
        12 <= r <= 82
        and 16 <= g <= 90
        and 24 <= b <= 102
        and (g >= r - 3)
        and (b >= g + 2)
        and (5 <= (b - r) <= 32)
    )


def extract_sprite(
    sheet: pygame.Surface,
    rect: tuple[int, int, int, int],
    remove_interior_bg: bool = False,
    auto_trim: bool = True,
    pad: int = 3,
    exclude_rects: list[tuple[int, int, int, int]] | None = None,
    strict_bg_only: bool = False,
) -> pygame.Surface:
    """Crop a sprite, remove its background, and optionally trim it."""
    sw, sh = sheet.get_size()
    rx, ry, rw, rh = rect

    # Add a border for flood-fill.
    x0 = max(0, rx - pad)
    y0 = max(0, ry - pad)
    x1 = min(sw, rx + rw + pad)
    y1 = min(sh, ry + rh + pad)
    w = x1 - x0
    h = y1 - y0

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))

    bg_mask = [[False] * h for _ in range(w)]
    for x in range(w):
        for y in range(h):
            sx, sy = x0 + x, y0 + y
            r, g, b, _ = sheet.get_at((sx, sy))
            in_pad = (
                (sx < rx)
                or (sx >= rx + rw)
                or (sy < ry)
                or (sy >= ry + rh)
            )
            in_excl = False
            if exclude_rects:
                for ex, ey, ew, eh in exclude_rects:
                    if ex <= sx < ex + ew and ey <= sy < ey + eh:
                        in_excl = True
                        break
            if strict_bg_only:
                is_bg = 52 <= r <= 78 and 60 <= g <= 86 and 70 <= b <= 98 and (b > g >= r)
            else:
                is_bg = is_bg_or_grid(r, g, b)

            if in_pad or in_excl or is_bg:
                bg_mask[x][y] = True
            if in_excl:
                out.set_at((x, y), (0, 0, 0, 0))
            else:
                out.set_at((x, y), (r, g, b, 255))

    if remove_interior_bg:
        for x in range(w):
            for y in range(h):
                if bg_mask[x][y]:
                    out.set_at((x, y), (0, 0, 0, 0))
    else:
        # Remove background connected to the border.
        vis = [[False] * h for _ in range(w)]
        q = deque()
        for x in range(w):
            for y in (0, h - 1):
                if bg_mask[x][y] and not vis[x][y]:
                    vis[x][y] = True
                    q.append((x, y))
        for y in range(h):
            for x in (0, w - 1):
                if bg_mask[x][y] and not vis[x][y]:
                    vis[x][y] = True
                    q.append((x, y))

        while q:
            cx, cy = q.popleft()
            out.set_at((cx, cy), (0, 0, 0, 0))
            for nx, ny in (
                (cx + 1, cy),
                (cx - 1, cy),
                (cx, cy + 1),
                (cx, cy - 1),
                (cx + 1, cy + 1),
                (cx - 1, cy - 1),
                (cx + 1, cy - 1),
                (cx - 1, cy + 1),
            ):
                if 0 <= nx < w and 0 <= ny < h and not vis[nx][ny] and bg_mask[nx][ny]:
                    vis[nx][ny] = True
                    q.append((nx, ny))

    # Restore the requested crop before trimming.
    inner = out.subsurface((rx - x0, ry - y0, rw, rh)).copy()

    if auto_trim:
        bbox = inner.get_bounding_rect(min_alpha=10)
        if bbox.width > 0 and bbox.height > 0:
            return inner.subsurface(bbox).copy()
    return inner


# Sprite definitions: category, name, crop, remove_interior_bg, auto_trim.
BASE_SPRITES = [
    # Terrain and tiles.
    ("tiles", "grass_block_1", (94, 85, 177, 183), False, True),
    ("tiles", "grass_block_2", (277, 85, 134, 183), False, True),
    ("tiles", "grass_vines_wide", (416, 85, 270, 183), False, True),
    ("tiles", "grass_vines_1", (692, 85, 134, 183), False, True),
    ("tiles", "grass_slope_block", (869, 85, 227, 183), False, True),
    ("tiles", "grass_vines_2", (1103, 85, 135, 183), False, True),
    ("tiles", "grass_vines_3", (1240, 85, 136, 183), False, True),
    ("tiles", "ladder", (1391, 70, 113, 520), True, True),
    ("tiles", "moss_l_block", (92, 314, 320, 276), False, True),
    ("tiles", "deep_dirt_wide", (415, 271, 271, 318), False, True),
    ("tiles", "deep_dirt_narrow", (692, 271, 134, 318), False, True),
    ("tiles", "grass_hill_slope", (872, 272, 504, 321), False, True),
    ("tiles", "spike_block_1", (1513, 355, 138, 235), False, True),
    ("tiles", "spike_block_2", (1652, 355, 136, 235), False, True),
    ("tiles", "spike_block_3", (1788, 355, 138, 235), False, True),
    ("tiles", "bridge_full", (1928, 365, 314, 225), True, True),
    ("tiles", "bridge_plank", (1928, 365, 314, 115), True, True),
    ("tiles", "moss_pillar", (2244, 267, 139, 323), False, True),
    ("tiles", "cave_exit", (2385, 267, 276, 323), False, True),

    # Knight.
    ("knight", "idle_1", (86, 712, 160, 238), False, True),
    ("knight", "idle_2", (294, 712, 152, 238), False, True),
    ("knight", "run_1", (499, 712, 165, 238), False, True),
    ("knight", "run_2", (712, 694, 177, 256), False, True),
    ("knight", "jump_attack", (940, 595, 263, 282), False, True),
    ("knight", "slash", (1193, 712, 281, 239), False, True),

    # Enemies.
    ("enemies", "slime_1", (1588, 825, 172, 126), False, True),
    ("enemies", "slime_2", (1806, 820, 155, 131), False, True),
    ("enemies", "bat", (2001, 774, 309, 144), False, True),
    ("enemies", "goblin_1", (2368, 780, 131, 171), False, True),
    ("enemies", "goblin_2", (2546, 780, 131, 171), False, True),

    # Props and interactables.
    ("props", "crate", (69, 1095, 184, 189), False, True),
    ("props", "barrel", (310, 1095, 153, 189), False, True),
    ("props", "chest_closed", (539, 1107, 190, 177), False, True),
    ("props", "chest_open", (797, 1082, 189, 202), False, True),
    ("props", "door_locked", (1054, 1071, 155, 214), False, True),
    ("props", "lever", (1273, 1101, 90, 182), False, True),

    # Collectibles and UI.
    ("items", "coin_1", (92, 1365, 87, 119), True, True),
    ("items", "coin_2", (251, 1356, 93, 128), True, True),
    ("items", "coin_3", (418, 1364, 92, 120), True, True),
    ("items", "coin_4", (569, 1357, 97, 127), True, True),
    ("ui", "heart_full", (705, 1371, 107, 102), False, True),
    ("ui", "heart_half", (1391, 1371, 109, 102), False, True),
    ("ui", "heart_empty", (1528, 1371, 110, 102), False, True),
    ("items", "gem_1", (1674, 1359, 92, 130), False, True),
    ("items", "gem_2", (1812, 1359, 91, 130), False, True),
    ("items", "gem_3", (1950, 1358, 92, 132), False, True),
    ("items", "key_1", (2087, 1359, 119, 126), True, True),
    ("items", "key_2", (2243, 1358, 119, 127), True, True),
    ("items", "potion_1", (2416, 1358, 101, 133), False, True),
    ("items", "potion_2", (2580, 1358, 97, 133), False, True),
]

KNIGHT_SPRITES = [
    # Slash combo.
    ("knight", "combo_1", (305, 82, 292, 224), False, True),
    ("knight", "combo_2", (642, 82, 229, 224), False, True),
    ("knight", "combo_3", (918, 82, 232, 224), False, True),
    # Lunge and jump attacks.
    ("knight", "lunge", (408, 725, 353, 231), False, True),
    ("knight", "jump_start", (1827, 680, 143, 260), False, True),
    ("knight", "jump_peak", (2029, 657, 165, 250), False, True),
    ("knight", "jump_slash", (2241, 680, 190, 260), False, True),
    # Spin attack.
    ("knight", "spin_1", (375, 1060, 346, 222), False, True),
    ("knight", "spin_2", (756, 1060, 332, 222), False, True),
    # Combat effects.
    ("vfx", "slash_arc_1", (424, 1360, 110, 126), True, True),
    ("vfx", "slash_arc_2", (556, 1360, 120, 126), True, True),
    ("vfx", "fire_spark", (978, 1360, 107, 126), True, True),
    ("vfx", "hit_burst", (1111, 1360, 111, 126), True, True),
    ("vfx", "dust_1", (1397, 1360, 98, 126), True, True),
    ("vfx", "dust_2", (1523, 1360, 117, 126), True, True),
    ("vfx", "star_hit", (1803, 1360, 113, 126), True, True),
    ("vfx", "smoke_puff", (1939, 1360, 114, 126), True, True),
]

GOBLIN_SPRITES = [
    # Goblin warrior.
    ("enemies", "goblin_warrior_idle", (105, 55, 215, 217), False, True),
    ("enemies", "goblin_warrior_walk_1", (391, 55, 157, 217), False, True),
    ("enemies", "goblin_warrior_walk_2", (636, 55, 189, 217), False, True),
    ("enemies", "goblin_warrior_attack_1", (895, 16, 198, 256), False, True),
    ("enemies", "goblin_warrior_attack_2", (1194, 50, 214, 222), False, True),
    ("enemies", "goblin_warrior_hurt", (1755, 45, 203, 227), False, True),
    ("enemies", "goblin_warrior_dead", (2369, 120, 280, 152), False, True),
    # Goblin archer.
    ("enemies", "goblin_archer_idle", (86, 374, 198, 232), False, True),
    ("enemies", "goblin_archer_aim", (630, 374, 253, 232), False, True),
    ("enemies", "goblin_archer_shoot", (930, 374, 259, 232), False, True),
    ("enemies", "goblin_arrow", (1659, 465, 174, 50), True, True),
    # Goblin mage.
    ("enemies", "goblin_mage_idle", (86, 685, 227, 265), False, True),
    ("enemies", "goblin_mage_cast", (1067, 685, 238, 265), False, True),
    ("enemies", "goblin_fireball", (1448, 750, 347, 160), True, True),
    # Goblin brute.
    ("enemies", "goblin_brute_idle", (75, 1020, 382, 265), False, True),
    ("enemies", "goblin_brute_attack", (500, 960, 415, 325), False, True),
    ("enemies", "goblin_brute_smash", (1279, 1020, 374, 265), False, True),
    # Goblin props.
    ("props", "barricade", (82, 1310, 302, 182), False, True),
    ("props", "banner", (946, 1185, 142, 308), False, True),
    ("props", "campfire", (1393, 1320, 261, 172), True, True),
    ("props", "bones", (1691, 1365, 200, 126), False, True),
    ("props", "loot_bag", (2414, 1365, 101, 126), False, True),
]


def slice_all_assets(assets_dir: str = "assets", force: bool = False) -> str:
    """
    Slices all sprite sheets into `assets/sliced/<category>/<name>.png`.
    Returns the path to the `sliced` directory.
    """
    sliced_dir = os.path.join(assets_dir, "sliced")
    marker_file = os.path.join(sliced_dir, ".sliced_v1")
    if os.path.exists(marker_file) and not force:
        return sliced_dir

    if not pygame.get_init():
        pygame.init()

    sheets = {
        "base.jpg": BASE_SPRITES,
        "knight.jpg": KNIGHT_SPRITES,
        "goblin.jpg": GOBLIN_SPRITES,
    }

    total_saved = 0
    for sheet_filename, sprite_defs in sheets.items():
        sheet_path = os.path.join(assets_dir, sheet_filename)
        if not os.path.exists(sheet_path):
            continue
        sheet = pygame.image.load(sheet_path)
        for category, name, rect, rem_interior, trim in sprite_defs:
            cat_dir = os.path.join(sliced_dir, category)
            os.makedirs(cat_dir, exist_ok=True)
            out_path = os.path.join(cat_dir, f"{name}.png")
            excl = None
            strict = False
            if name == "jump_attack":
                excl = [(1190, 815, 30, 80)]
            elif name == "slash":
                excl = [(1190, 710, 18, 50)]
            elif name == "heart_empty":
                strict = True

            sprite_surf = extract_sprite(
                sheet,
                rect,
                remove_interior_bg=rem_interior,
                auto_trim=trim,
                exclude_rects=excl,
                strict_bg_only=strict,
            )
            pygame.image.save(sprite_surf, out_path)
            total_saved += 1

    os.makedirs(sliced_dir, exist_ok=True)
    with open(marker_file, "w", encoding="utf-8") as f:
        f.write(f"Sliced {total_saved} sprites\n")

    return sliced_dir


if __name__ == "__main__":
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    out_dir = slice_all_assets("assets", force=True)
    print(f"Successfully sliced assets into: {out_dir}")
