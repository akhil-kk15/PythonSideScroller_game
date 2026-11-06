"""Level, entity, and tilemap management."""

import math
import os
import pygame

TILE_SIZE = 64


def _scale_to_size(img: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(img, (max(1, w), max(1, h)))


def _scale_to_height(img: pygame.Surface, target_h: int) -> pygame.Surface:
    iw, ih = img.get_size()
    scale = target_h / max(1, ih)
    return pygame.transform.smoothscale(img, (max(1, int(round(iw * scale))), target_h))


class AssetLibrary:
    """Loads and caches all sliced sprites for tiles, items, props, enemies, UI, and VFX."""

    def __init__(self, sliced_dir: str = "assets/sliced"):
        self.sliced_dir = sliced_dir
        self.tiles: dict[str, pygame.Surface] = {}
        self.items: dict[str, list[pygame.Surface]] = {}
        self.props: dict[str, pygame.Surface] = {}
        self.enemies: dict[str, list[pygame.Surface]] = {}
        self.ui: dict[str, pygame.Surface] = {}
        self.vfx: dict[str, pygame.Surface] = {}
        self._load_all()

    def _load_raw(self, category: str, name: str) -> pygame.Surface:
        path = os.path.join(self.sliced_dir, category, f"{name}.png")
        return pygame.image.load(path).convert_alpha()

    def _load_all(self) -> None:
        # Tiles.
        self.tiles["grass_1"] = _scale_to_size(self._load_raw("tiles", "grass_block_1"), TILE_SIZE, TILE_SIZE)
        self.tiles["grass_2"] = _scale_to_size(self._load_raw("tiles", "grass_block_2"), TILE_SIZE, TILE_SIZE)
        self.tiles["grass_vines_1"] = _scale_to_size(self._load_raw("tiles", "grass_vines_1"), TILE_SIZE, TILE_SIZE)
        self.tiles["grass_vines_2"] = _scale_to_size(self._load_raw("tiles", "grass_vines_2"), TILE_SIZE, TILE_SIZE)
        self.tiles["grass_vines_3"] = _scale_to_size(self._load_raw("tiles", "grass_vines_3"), TILE_SIZE, TILE_SIZE)
        self.tiles["grass_vines_wide"] = _scale_to_size(
            self._load_raw("tiles", "grass_vines_wide"), TILE_SIZE * 2, TILE_SIZE
        )
        self.tiles["dirt_narrow"] = _scale_to_size(
            self._load_raw("tiles", "deep_dirt_narrow"), TILE_SIZE, TILE_SIZE * 2
        )
        self.tiles["dirt_single"] = _scale_to_size(
            self._load_raw("tiles", "deep_dirt_wide"), TILE_SIZE, TILE_SIZE
        )
        self.tiles["moss_pillar"] = _scale_to_size(
            self._load_raw("tiles", "moss_pillar"), TILE_SIZE, TILE_SIZE * 2
        )
        self.tiles["moss_l"] = _scale_to_size(
            self._load_raw("tiles", "moss_l_block"), TILE_SIZE * 2, TILE_SIZE * 2
        )
        self.tiles["hill_slope"] = _scale_to_size(
            self._load_raw("tiles", "grass_hill_slope"), TILE_SIZE * 2, TILE_SIZE
        )
        self.tiles["ladder_tall"] = _scale_to_size(
            self._load_raw("tiles", "ladder"), 48, TILE_SIZE * 3
        )
        # Crop a single ladder segment.
        ladder_raw = self.tiles["ladder_tall"]
        self.tiles["ladder_seg"] = ladder_raw.subsurface((0, 0, 48, TILE_SIZE)).copy()

        self.tiles["spike_1"] = _scale_to_size(self._load_raw("tiles", "spike_block_1"), TILE_SIZE, TILE_SIZE + 16)
        self.tiles["spike_2"] = _scale_to_size(self._load_raw("tiles", "spike_block_2"), TILE_SIZE, TILE_SIZE + 16)
        self.tiles["bridge_full"] = _scale_to_size(
            self._load_raw("tiles", "bridge_full"), TILE_SIZE * 2, TILE_SIZE
        )
        self.tiles["bridge_plank"] = _scale_to_size(
            self._load_raw("tiles", "bridge_plank"), TILE_SIZE * 2, 32
        )
        self.tiles["cave_exit"] = _scale_to_size(
            self._load_raw("tiles", "cave_exit"), TILE_SIZE * 2, TILE_SIZE * 2
        )

        # Collectibles.
        self.items["coin"] = [
            _scale_to_height(self._load_raw("items", f"coin_{i}"), 34) for i in range(1, 5)
        ]
        self.items["gem"] = [
            _scale_to_height(self._load_raw("items", f"gem_{i}"), 38) for i in range(1, 4)
        ]
        self.items["key"] = [
            _scale_to_height(self._load_raw("items", f"key_{i}"), 42) for i in range(1, 3)
        ]
        self.items["potion"] = [
            _scale_to_height(self._load_raw("items", f"potion_{i}"), 40) for i in range(1, 3)
        ]

        # Props and interactables.
        self.props["crate"] = _scale_to_size(self._load_raw("props", "crate"), 54, 54)
        self.props["barrel"] = _scale_to_size(self._load_raw("props", "barrel"), 48, 56)
        self.props["chest_closed"] = _scale_to_size(self._load_raw("props", "chest_closed"), 60, 54)
        self.props["chest_open"] = _scale_to_size(self._load_raw("props", "chest_open"), 60, 62)
        self.props["door_locked"] = _scale_to_size(self._load_raw("props", "door_locked"), 60, 88)
        self.props["lever_off"] = _scale_to_size(self._load_raw("props", "lever"), 36, 56)
        self.props["lever_on"] = pygame.transform.flip(self.props["lever_off"], True, False)
        self.props["barricade"] = _scale_to_size(self._load_raw("props", "barricade"), 96, 58)
        self.props["banner"] = _scale_to_size(self._load_raw("props", "banner"), 52, 108)
        self.props["campfire"] = _scale_to_size(self._load_raw("props", "campfire"), 84, 58)
        self.props["bones"] = _scale_to_size(self._load_raw("props", "bones"), 64, 40)
        self.props["loot_bag"] = _scale_to_size(self._load_raw("props", "loot_bag"), 40, 48)

        # Enemies.
        self.enemies["slime"] = [
            _scale_to_height(self._load_raw("enemies", "slime_1"), 44),
            _scale_to_height(self._load_raw("enemies", "slime_2"), 46),
        ]
        bat_f1 = _scale_to_height(self._load_raw("enemies", "bat"), 48)
        bat_f2 = pygame.transform.smoothscale(
            bat_f1, (bat_f1.get_width(), max(28, int(bat_f1.get_height() * 0.82)))
        )
        self.enemies["bat"] = [bat_f1, bat_f2]

        self.enemies["goblin_scout"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_1"), 58),
            _scale_to_height(self._load_raw("enemies", "goblin_2"), 58),
        ]
        self.enemies["goblin_warrior_walk"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_idle"), 64),
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_walk_1"), 64),
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_walk_2"), 64),
        ]
        self.enemies["goblin_warrior_attack"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_attack_1"), 72),
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_attack_2"), 66),
        ]
        self.enemies["goblin_warrior_dead"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_warrior_dead"), 42)
        ]
        self.enemies["goblin_archer"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_archer_idle"), 64),
            _scale_to_height(self._load_raw("enemies", "goblin_archer_aim"), 64),
            _scale_to_height(self._load_raw("enemies", "goblin_archer_shoot"), 64),
        ]
        self.enemies["arrow"] = [_scale_to_height(self._load_raw("enemies", "goblin_arrow"), 16)]

        self.enemies["goblin_brute"] = [
            _scale_to_height(self._load_raw("enemies", "goblin_brute_idle"), 86),
            _scale_to_height(self._load_raw("enemies", "goblin_brute_attack"), 102),
            _scale_to_height(self._load_raw("enemies", "goblin_brute_smash"), 86),
        ]

        # UI icons.
        self.ui["heart_full"] = _scale_to_size(self._load_raw("ui", "heart_full"), 32, 30)
        self.ui["heart_half"] = _scale_to_size(self._load_raw("ui", "heart_half"), 32, 30)
        self.ui["heart_empty"] = _scale_to_size(self._load_raw("ui", "heart_empty"), 32, 30)
        self.ui["coin_icon"] = _scale_to_size(self._load_raw("items", "coin_1"), 24, 30)
        self.ui["gem_icon"] = _scale_to_size(self._load_raw("items", "gem_1"), 24, 32)
        self.ui["key_icon"] = _scale_to_size(self._load_raw("items", "key_1"), 32, 32)

        # Visual effects.
        for vname in ("hit_burst", "star_hit", "dust_1", "dust_2", "smoke_puff", "fire_spark"):
            self.vfx[vname] = _scale_to_size(self._load_raw("vfx", vname), 48, 48)


class VFXParticle:
    """Short-lived visual effect."""

    def __init__(
        self,
        x: int,
        y: int,
        image: pygame.Surface | None = None,
        text: str | None = None,
        color: tuple[int, int, int] = (255, 235, 90),
        duration: int = 22,
    ):
        self.x = float(x)
        self.y = float(y)
        self.image = image
        self.text = text
        self.color = color
        self.timer = duration
        self.max_timer = duration

    def update(self) -> bool:
        self.timer -= 1
        self.y -= 1.1 if self.text else 0.4
        return self.timer > 0

    def draw(self, surface: pygame.Surface, camera_x: int, font: pygame.font.Font) -> None:
        sx = int(self.x - camera_x)
        sy = int(self.y)
        if self.text:
            shadow = font.render(self.text, True, (20, 20, 30))
            label = font.render(self.text, True, self.color)
            surface.blit(shadow, (sx + 2, sy + 2))
            surface.blit(label, (sx, sy))
        elif self.image:
            ratio = self.timer / max(1, self.max_timer)
            scale = 0.6 + 0.5 * (1.0 - ratio)
            w = max(4, int(self.image.get_width() * scale))
            h = max(4, int(self.image.get_height() * scale))
            scaled = pygame.transform.smoothscale(self.image, (w, h))
            scaled.set_alpha(int(255 * ratio))
            surface.blit(scaled, (sx - w // 2, sy - h // 2))


class Projectile:
    """Enemy arrow projectile."""

    def __init__(self, x: int, y: int, direction: int, image: pygame.Surface):
        self.direction = direction
        self.speed = 6.5 * direction
        self.image = image if direction > 0 else pygame.transform.flip(image, True, False)
        self.rect = pygame.Rect(x, y, self.image.get_width(), self.image.get_height())
        self.alive = True
        self.timer = 180

    def update(self, solid_rects: list[pygame.Rect]) -> None:
        self.rect.x += int(self.speed)
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False
            return
        for s_rect in solid_rects:
            if self.rect.colliderect(s_rect):
                self.alive = False
                return

    def draw(self, surface: pygame.Surface, camera_x: int) -> None:
        surface.blit(self.image, (self.rect.x - camera_x, self.rect.y))


class Collectible:
    """Animated collectible."""

    def __init__(self, x: int, y: int, kind: str, frames: list[pygame.Surface]):
        self.kind = kind  # coin, gem, key, or potion.
        self.frames = frames
        w, h = frames[0].get_size()
        self.base_y = float(y)
        self.rect = pygame.Rect(x, y, w, h)
        self.anim_timer = float((x + y) % 10) * 0.2
        self.collected = False

    def update(self) -> None:
        self.anim_timer += 0.14
        bob = math.sin(self.anim_timer * 1.6) * 4.0
        self.rect.y = int(self.base_y + bob)

    def draw(self, surface: pygame.Surface, camera_x: int) -> None:
        if self.collected:
            return
        frame = self.frames[int(self.anim_timer) % len(self.frames)]
        surface.blit(frame, (self.rect.x - camera_x, self.rect.y))


class Enemy:
    """Patrolling or ranged enemy (Slime, Bat, Goblin Warrior, Goblin Archer, Goblin Brute)."""

    def __init__(
        self,
        x: int,
        y: int,
        kind: str,
        patrol_min_x: int,
        patrol_max_x: int,
        assets: AssetLibrary,
    ):
        self.kind = kind
        self.patrol_min_x = patrol_min_x
        self.patrol_max_x = patrol_max_x
        self.assets = assets
        self.base_y = float(y)
        self.facing_right = True
        self.anim_timer = 0.0
        self.hurt_timer = 0
        self.dead = False
        self.dead_timer = 90
        self.shoot_cooldown = 90

        if kind == "slime":
            self.rect = pygame.Rect(x, y - 42, 48, 42)
            self.speed = 1.6
            self.hp = 1
            self.max_hp = 1
            self.score_value = 150
            self.sprites_faces_right_natively = False
        elif kind == "bat":
            self.rect = pygame.Rect(x, y - 44, 62, 40)
            self.speed = 2.4
            self.hp = 1
            self.max_hp = 1
            self.score_value = 200
            self.sprites_faces_right_natively = True
        elif kind == "goblin_warrior":
            self.rect = pygame.Rect(x, y - 60, 44, 60)
            self.speed = 2.1
            self.hp = 2
            self.max_hp = 2
            self.score_value = 300
            self.sprites_faces_right_natively = True
        elif kind == "goblin_archer":
            self.rect = pygame.Rect(x, y - 60, 44, 60)
            self.speed = 0.0
            self.hp = 2
            self.max_hp = 2
            self.score_value = 350
            self.sprites_faces_right_natively = True
        elif kind == "goblin_brute":
            self.rect = pygame.Rect(x, y - 82, 68, 82)
            self.speed = 1.5
            self.hp = 4
            self.max_hp = 4
            self.score_value = 800
            self.sprites_faces_right_natively = True
        else:
            self.rect = pygame.Rect(x, y - 54, 42, 54)
            self.speed = 1.8
            self.hp = 1
            self.max_hp = 1
            self.score_value = 200
            self.sprites_faces_right_natively = True

        self.vel_x = self.speed

    def take_hit(self, damage: int = 1) -> bool:
        """Deals damage to this enemy. Returns True if defeated."""
        if self.dead:
            return False
        self.hp -= damage
        self.hurt_timer = 14
        if self.hp <= 0:
            self.dead = True
            self.dead_timer = 75
            return True
        return False

    def update(self, player_rect: pygame.Rect, projectiles: list[Projectile]) -> None:
        if self.dead:
            if self.dead_timer > 0:
                self.dead_timer -= 1
            return

        if self.hurt_timer > 0:
            self.hurt_timer -= 1

        self.anim_timer += 0.12

        if self.kind == "goblin_archer":
            self.facing_right = player_rect.centerx > self.rect.centerx
            dist_x = abs(player_rect.centerx - self.rect.centerx)
            dist_y = abs(player_rect.centery - self.rect.centery)
            if dist_x < 520 and dist_y < 180:
                self.shoot_cooldown -= 1
                if self.shoot_cooldown <= 0:
                    self.shoot_cooldown = 105
                    direction = 1 if self.facing_right else -1
                    arrow_img = self.assets.enemies["arrow"][0]
                    ax = self.rect.right if direction > 0 else self.rect.left - arrow_img.get_width()
                    ay = self.rect.centery - 8
                    projectiles.append(Projectile(ax, ay, direction, arrow_img))
            return

        # Patrol between the horizontal limits.
        self.rect.x += int(round(self.vel_x))
        if self.rect.left <= self.patrol_min_x:
            self.rect.left = self.patrol_min_x
            self.vel_x = abs(self.speed)
            self.facing_right = True
        elif self.rect.right >= self.patrol_max_x:
            self.rect.right = self.patrol_max_x
            self.vel_x = -abs(self.speed)
            self.facing_right = False

        if self.kind == "bat":
            self.rect.y = int(self.base_y - 44 + math.sin(self.anim_timer * 1.8) * 18)

    def draw(self, surface: pygame.Surface, camera_x: int) -> None:
        if self.dead:
            if self.dead_timer <= 0:
                return
            if self.kind in ("goblin_warrior", "goblin_archer", "goblin_brute"):
                corpse = self.assets.enemies["goblin_warrior_dead"][0]
                surface.blit(
                    corpse,
                    (self.rect.centerx - corpse.get_width() // 2 - camera_x, self.rect.bottom - corpse.get_height()),
                )
            return

        if self.hurt_timer > 0 and (self.hurt_timer // 2) % 2 == 1:
            return

        if self.kind == "slime":
            frames = self.assets.enemies["slime"]
            frame = frames[int(self.anim_timer) % len(frames)]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
        elif self.kind == "bat":
            frames = self.assets.enemies["bat"]
            frame = frames[int(self.anim_timer * 1.5) % len(frames)]
        elif self.kind == "goblin_warrior":
            frames = self.assets.enemies["goblin_warrior_walk"]
            frame = frames[int(self.anim_timer) % len(frames)]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
        elif self.kind == "goblin_archer":
            frames = self.assets.enemies["goblin_archer"]
            if self.shoot_cooldown < 25:
                frame = frames[2]
            elif self.shoot_cooldown < 55:
                frame = frames[1]
            else:
                frame = frames[0]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
        elif self.kind == "goblin_brute":
            frames = self.assets.enemies["goblin_brute"]
            frame = frames[int(self.anim_timer * 0.9) % len(frames)]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
        else:
            frames = self.assets.enemies["goblin_scout"]
            frame = frames[int(self.anim_timer) % len(frames)]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)

        draw_x = self.rect.centerx - frame.get_width() // 2 - camera_x
        draw_y = self.rect.bottom - frame.get_height()
        surface.blit(frame, (draw_x, draw_y))

        # Show health for damaged multi-HP enemies.
        if self.max_hp > 1 and (self.hp < self.max_hp or self.kind == "goblin_brute"):
            bw = 46 if self.kind != "goblin_brute" else 68
            bh = 6
            bx = self.rect.centerx - bw // 2 - camera_x
            by = draw_y - 10
            pygame.draw.rect(surface, (30, 20, 25), (bx - 1, by - 1, bw + 2, bh + 2), border_radius=3)
            fill_w = int(bw * (self.hp / self.max_hp))
            pygame.draw.rect(surface, (235, 65, 65), (bx, by, fill_w, bh), border_radius=2)


class Level:
    """
    Represents a side-scrolling level with solid tiles, slopes, bridges, ladders,
    spikes, interactive props (crates, chests, levers, locked door, cave exit),
    collectibles, and enemies.
    """

    def __init__(self, level_number: int, assets: AssetLibrary):
        self.level_number = level_number
        self.assets = assets
        self.level_name = (
            "Level 1: We can name the level something"
            if level_number == 1
            else "Level 2: Goblin Stronghold"
        )
        self.width = 56 * TILE_SIZE  # 3584 px wide
        self.height = 720
        self.ground_y = 10 * TILE_SIZE  # y = 640

        # Collision and tile collections.
        self.visual_tiles: list[tuple[pygame.Surface, int, int]] = []
        self.ladder_tiles: list[tuple[pygame.Surface, int, int]] = []
        self.solid_rects: list[pygame.Rect] = []
        self.one_way_rects: list[pygame.Rect] = []
        self.ladder_rects: list[pygame.Rect] = []
        self.slope_tiles: list[tuple[pygame.Rect, str]] = []
        self.spike_rects: list[pygame.Rect] = []

        # Interactive objects and entities.
        self.collectibles: list[Collectible] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.particles: list[VFXParticle] = []

        # Props and decorations.
        self.destructibles: list[dict] = []
        self.chests: list[dict] = []
        self.levers: list[dict] = []
        self.decorations: list[tuple[pygame.Surface, int, int]] = []
        self.locked_door: dict | None = None
        self.cave_exit_rect: pygame.Rect = pygame.Rect(self.width - 180, self.ground_y - 128, 128, 128)

        self.spawn_pos = (100, self.ground_y - 80)
        self.banner_message = ""
        self.banner_timer = 150

        if level_number == 1:
            self._build_level_1()
        else:
            self._build_level_2()

    # Level-building helpers.
    def _add_ground_segment(self, start_col: int, end_col: int, row: int = 10, deep_rows: int = 2) -> None:
        """Adds a contiguous horizontal run of grass-topped blocks + deep dirt underneath."""
        variants = ["grass_1", "grass_2", "grass_vines_1", "grass_vines_2", "grass_vines_3"]
        for c in range(start_col, end_col):
            x = c * TILE_SIZE
            y = row * TILE_SIZE
            t_name = variants[(c * 3 + row) % len(variants)]
            self.visual_tiles.append((self.assets.tiles[t_name], x, y))
            for d in range(1, deep_rows + 1):
                self.visual_tiles.append((self.assets.tiles["dirt_single"], x, (row + d) * TILE_SIZE))

        seg_rect = pygame.Rect(
            start_col * TILE_SIZE,
            row * TILE_SIZE,
            (end_col - start_col) * TILE_SIZE,
            (deep_rows + 1) * TILE_SIZE,
        )
        self.solid_rects.append(seg_rect)

    def _add_platform(self, start_col: int, width_cols: int, row: int, vine_style: bool = True) -> None:
        """Adds an elevated solid grass/vine platform."""
        for i in range(width_cols):
            c = start_col + i
            x = c * TILE_SIZE
            y = row * TILE_SIZE
            t_name = "grass_vines_1" if (vine_style and i % 2 == 0) else "grass_1"
            self.visual_tiles.append((self.assets.tiles[t_name], x, y))
        self.solid_rects.append(
            pygame.Rect(start_col * TILE_SIZE, row * TILE_SIZE, width_cols * TILE_SIZE, TILE_SIZE)
        )

    def _add_bridge(self, start_col: int, width_blocks: int, row: int, full_supports: bool = True) -> None:
        """Adds a wooden bridge (one-way platform) spanning `width_blocks * 2` tiles."""
        tile_key = "bridge_full" if full_supports else "bridge_plank"
        for i in range(width_blocks):
            x = (start_col + i * 2) * TILE_SIZE
            y = row * TILE_SIZE
            self.visual_tiles.append((self.assets.tiles[tile_key], x, y))
            self.one_way_rects.append(pygame.Rect(x, y, TILE_SIZE * 2, 18))

    def _add_ladder(self, col: int, top_row: int, height_rows: int) -> None:
        """Adds a climbable wooden ladder spanning `height_rows` tiles vertically."""
        x = col * TILE_SIZE + 8
        for r in range(top_row, top_row + height_rows):
            y = r * TILE_SIZE
            self.ladder_tiles.append((self.assets.tiles["ladder_seg"], x, y))
        ladder_rect = pygame.Rect(x + 4, top_row * TILE_SIZE - 8, 40, height_rows * TILE_SIZE + 8)
        self.ladder_rects.append(ladder_rect)
        # The ladder top is one-way.
        self.one_way_rects.append(pygame.Rect(x, top_row * TILE_SIZE, 48, 12))

    def _add_spikes(self, start_col: int, count: int, row: int = 10) -> None:
        """Adds spike-topped blocks along a pit floor."""
        for i in range(count):
            c = start_col + i
            x = c * TILE_SIZE
            y = row * TILE_SIZE - 16
            t_key = "spike_1" if i % 2 == 0 else "spike_2"
            self.visual_tiles.append((self.assets.tiles[t_key], x, y))
            # The block is solid and the spikes are hazardous.
            self.solid_rects.append(pygame.Rect(x, row * TILE_SIZE + 12, TILE_SIZE, TILE_SIZE))
            self.spike_rects.append(pygame.Rect(x + 6, y + 6, TILE_SIZE - 12, 22))

    def _add_slope_down_right(self, start_col: int, row: int) -> None:
        """Adds a 2-tile-wide grassy hill slope descending from row to row+1."""
        x = start_col * TILE_SIZE
        y = row * TILE_SIZE
        self.visual_tiles.append((self.assets.tiles["hill_slope"], x, y))
        self.visual_tiles.append((self.assets.tiles["dirt_single"], x, (row + 1) * TILE_SIZE))
        self.visual_tiles.append((self.assets.tiles["dirt_single"], x + TILE_SIZE, (row + 1) * TILE_SIZE))
        self.slope_tiles.append((pygame.Rect(x, y, TILE_SIZE * 2, TILE_SIZE), "down_right"))

    def _add_coin_row(self, start_col: int, count: int, y_px: int, spacing: int = 48) -> None:
        sx = start_col * TILE_SIZE + 14
        for i in range(count):
            self.collectibles.append(Collectible(sx + i * spacing, y_px, "coin", self.assets.items["coin"]))

    def _build_level_1(self) -> None:
        """
        Level 1: Emerald Grasslands & Outpost (Mario + Dangerous Dave style)
        - Introduces running, jumping, smashing crates, opening chests, climbing ladders,
          crossing spike bridges, collecting the Gold Key, unlocking the door, and
          entering the Stone Cave Archway!
        """
        self.spawn_pos = (96, 9 * TILE_SIZE - 10)
        self.banner_message = "LEVEL 1: Find the GOLD KEY and reach the Cave Exit!"

        # Ground sections and pits.
        self._add_ground_segment(0, 14, row=10)
        # Spike pit with a bridge.
        self._add_spikes(14, 4, row=10)
        self._add_bridge(14, 2, row=9, full_supports=True)

        # Elevated hill.
        self._add_ground_segment(18, 26, row=9, deep_rows=3)
        self._add_slope_down_right(26, row=9)
        self._add_ground_segment(28, 38, row=10)

        # Second chasm with high and low paths.
        self._add_spikes(38, 4, row=10)
        self._add_bridge(38, 2, row=8, full_supports=False)

        # Fortress courtyard and cave exit.
        self._add_ground_segment(42, 56, row=10)

        # Upper platforms and ladders.
        self._add_platform(5, 4, row=7)
        self._add_ladder(5, top_row=7, height_rows=3)

        self._add_platform(11, 3, row=5)
        self._add_ladder(19, top_row=6, height_rows=3)
        self._add_platform(19, 5, row=6)

        # High treasure tower.
        self._add_ladder(30, top_row=6, height_rows=4)
        self._add_platform(29, 6, row=6)
        self._add_ladder(34, top_row=3, height_rows=3)
        self._add_platform(31, 5, row=3)

        # Watchtower before the exit.
        self._add_platform(43, 4, row=7)
        self._add_ladder(43, top_row=7, height_rows=3)

        # Mossy wall above the locked door.
        door_col = 49
        self.visual_tiles.append((self.assets.tiles["moss_pillar"], door_col * TILE_SIZE, 6 * TILE_SIZE))
        self.visual_tiles.append((self.assets.tiles["moss_pillar"], door_col * TILE_SIZE, 4 * TILE_SIZE))
        self.solid_rects.append(pygame.Rect(door_col * TILE_SIZE, 4 * TILE_SIZE, TILE_SIZE, 4 * TILE_SIZE))

        door_rect = pygame.Rect(door_col * TILE_SIZE + 2, 10 * TILE_SIZE - 128, 60, 128)
        self.locked_door = {"rect": door_rect, "open": False}

        # Cave exit.
        exit_x = 52 * TILE_SIZE
        exit_y = 8 * TILE_SIZE
        self.cave_exit_rect = pygame.Rect(exit_x + 24, exit_y + 24, TILE_SIZE * 2 - 48, TILE_SIZE * 2 - 24)

        # Props and decorations.
        self.destructibles.append(
            {"kind": "crate", "rect": pygame.Rect(4 * TILE_SIZE, 10 * TILE_SIZE - 54, 54, 54), "drop": "coin"}
        )
        self.destructibles.append(
            {"kind": "barrel", "rect": pygame.Rect(10 * TILE_SIZE, 10 * TILE_SIZE - 56, 48, 56), "drop": "potion"}
        )
        self.destructibles.append(
            {"kind": "crate", "rect": pygame.Rect(24 * TILE_SIZE, 9 * TILE_SIZE - 54, 54, 54), "drop": "coin"}
        )
        self.destructibles.append(
            {"kind": "barrel", "rect": pygame.Rect(45 * TILE_SIZE, 7 * TILE_SIZE - 56, 48, 56), "drop": "potion"}
        )

        # Chests.
        self.chests.append(
            {"rect": pygame.Rect(12 * TILE_SIZE, 5 * TILE_SIZE - 54, 60, 54), "open": False}
        )
        self.chests.append(
            {"rect": pygame.Rect(22 * TILE_SIZE, 6 * TILE_SIZE - 54, 60, 54), "open": False}
        )

        # Lever that spawns bonus bridge and gems.
        self.levers.append(
            {"rect": pygame.Rect(20 * TILE_SIZE + 14, 6 * TILE_SIZE - 56, 36, 56), "active": False}
        )

        # Decorations.
        self.decorations.append((self.assets.props["campfire"], 2 * TILE_SIZE, 10 * TILE_SIZE - 56))
        self.decorations.append((self.assets.props["banner"], 48 * TILE_SIZE, 10 * TILE_SIZE - 108))
        self.decorations.append((self.assets.props["loot_bag"], 51 * TILE_SIZE, 10 * TILE_SIZE - 48))

        # Collectibles.
        self._add_coin_row(6, 3, 7 * TILE_SIZE - 44)
        self._add_coin_row(14, 4, 9 * TILE_SIZE - 48)
        self._add_coin_row(20, 4, 9 * TILE_SIZE - 44)
        self._add_coin_row(30, 4, 6 * TILE_SIZE - 44)
        self._add_coin_row(38, 4, 8 * TILE_SIZE - 48)
        self._add_coin_row(44, 3, 7 * TILE_SIZE - 44)

        # Gems on high platforms.
        self.collectibles.append(Collectible(13 * TILE_SIZE, 5 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(23 * TILE_SIZE, 6 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(35 * TILE_SIZE, 10 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(46 * TILE_SIZE, 7 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))

        # Mid-level health potion.
        self.collectibles.append(
            Collectible(28 * TILE_SIZE + 12, 10 * TILE_SIZE - 46, "potion", self.assets.items["potion"])
        )

        # Gold key on the high tower.
        self.collectibles.append(
            Collectible(32 * TILE_SIZE + 10, 3 * TILE_SIZE - 52, "key", self.assets.items["key"])
        )

        # Enemies.
        self.enemies.append(
            Enemy(8 * TILE_SIZE, 10 * TILE_SIZE, "slime", 6 * TILE_SIZE, 13 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(7 * TILE_SIZE, 7 * TILE_SIZE, "slime", 5 * TILE_SIZE, 9 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(15 * TILE_SIZE, 7 * TILE_SIZE, "bat", 13 * TILE_SIZE, 19 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(21 * TILE_SIZE, 9 * TILE_SIZE, "goblin_warrior", 18 * TILE_SIZE, 25 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(31 * TILE_SIZE, 6 * TILE_SIZE, "goblin_warrior", 29 * TILE_SIZE, 35 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(32 * TILE_SIZE, 10 * TILE_SIZE, "slime", 29 * TILE_SIZE, 37 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(39 * TILE_SIZE, 6 * TILE_SIZE, "bat", 37 * TILE_SIZE, 43 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(45 * TILE_SIZE, 10 * TILE_SIZE, "goblin_warrior", 42 * TILE_SIZE, 48 * TILE_SIZE, self.assets)
        )

    def _build_level_2(self) -> None:
        """
        Level 2: Goblin Stronghold & Cave Depths
        - Features Goblin Archers firing arrows, multi-tier bridges over spike canyons,
          climbable siege ladders, and the Goblin Brute boss guarding the Gold Key!
        """
        self.spawn_pos = (96, 10 * TILE_SIZE - 70)
        self.banner_message = "LEVEL 2: Defeat the Goblin Stronghold & claim the Key!"

        # Ground and spike canyons.
        self._add_ground_segment(0, 10, row=10)
        self._add_spikes(10, 5, row=10)
        self._add_bridge(10, 2, row=8, full_supports=False)

        self._add_ground_segment(15, 25, row=10)
        self._add_spikes(25, 6, row=10)
        self._add_bridge(25, 3, row=9, full_supports=True)

        # Elevated fortress keep.
        self._add_ground_segment(31, 41, row=9, deep_rows=3)
        self._add_slope_down_right(41, row=9)
        self._add_ground_segment(43, 56, row=10)

        # Platforms and ladders.
        self._add_platform(4, 4, row=7)
        self._add_ladder(4, top_row=7, height_rows=3)

        self._add_platform(16, 4, row=7)
        self._add_ladder(16, top_row=7, height_rows=3)
        self._add_platform(21, 4, row=5)
        self._add_ladder(20, top_row=5, height_rows=2)

        # Fortress battlements.
        self._add_ladder(32, top_row=5, height_rows=4)
        self._add_platform(32, 8, row=5)
        self._add_ladder(39, top_row=5, height_rows=4)

        # Locked gate before the cave exit.
        door_col = 49
        self.visual_tiles.append((self.assets.tiles["moss_pillar"], door_col * TILE_SIZE, 6 * TILE_SIZE))
        self.visual_tiles.append((self.assets.tiles["moss_pillar"], door_col * TILE_SIZE, 4 * TILE_SIZE))
        self.solid_rects.append(pygame.Rect(door_col * TILE_SIZE, 4 * TILE_SIZE, TILE_SIZE, 4 * TILE_SIZE))

        door_rect = pygame.Rect(door_col * TILE_SIZE + 2, 10 * TILE_SIZE - 128, 60, 128)
        self.locked_door = {"rect": door_rect, "open": False}

        exit_x = 52 * TILE_SIZE
        exit_y = 8 * TILE_SIZE
        self.cave_exit_rect = pygame.Rect(exit_x + 24, exit_y + 24, TILE_SIZE * 2 - 48, TILE_SIZE * 2 - 24)

        # Props and decorations.
        self.decorations.append((self.assets.props["banner"], 3 * TILE_SIZE, 10 * TILE_SIZE - 108))
        self.decorations.append((self.assets.props["bones"], 15 * TILE_SIZE, 10 * TILE_SIZE - 40))
        self.decorations.append((self.assets.props["campfire"], 18 * TILE_SIZE, 10 * TILE_SIZE - 56))
        self.decorations.append((self.assets.props["banner"], 33 * TILE_SIZE, 9 * TILE_SIZE - 108))
        self.decorations.append((self.assets.props["banner"], 38 * TILE_SIZE, 9 * TILE_SIZE - 108))
        self.decorations.append((self.assets.props["campfire"], 45 * TILE_SIZE, 10 * TILE_SIZE - 56))
        self.decorations.append((self.assets.props["loot_bag"], 51 * TILE_SIZE, 10 * TILE_SIZE - 48))

        self.destructibles.append(
            {"kind": "barrel", "rect": pygame.Rect(6 * TILE_SIZE, 7 * TILE_SIZE - 56, 48, 56), "drop": "potion"}
        )
        self.destructibles.append(
            {"kind": "crate", "rect": pygame.Rect(17 * TILE_SIZE, 10 * TILE_SIZE - 54, 54, 54), "drop": "coin"}
        )
        self.destructibles.append(
            {"kind": "barrel", "rect": pygame.Rect(31 * TILE_SIZE, 9 * TILE_SIZE - 56, 48, 56), "drop": "potion"}
        )
        self.destructibles.append(
            {"kind": "crate", "rect": pygame.Rect(44 * TILE_SIZE, 10 * TILE_SIZE - 54, 54, 54), "drop": "potion"}
        )

        self.chests.append(
            {"rect": pygame.Rect(23 * TILE_SIZE, 5 * TILE_SIZE - 54, 60, 54), "open": False}
        )
        self.chests.append(
            {"rect": pygame.Rect(35 * TILE_SIZE, 5 * TILE_SIZE - 54, 60, 54), "open": False}
        )
        self.levers.append(
            {"rect": pygame.Rect(18 * TILE_SIZE, 7 * TILE_SIZE - 56, 36, 56), "active": False}
        )

        # Collectibles.
        self._add_coin_row(5, 3, 7 * TILE_SIZE - 44)
        self._add_coin_row(10, 4, 8 * TILE_SIZE - 48)
        self._add_coin_row(25, 6, 9 * TILE_SIZE - 48)
        self._add_coin_row(33, 2, 5 * TILE_SIZE - 44)
        self._add_coin_row(45, 2, 10 * TILE_SIZE - 44)

        self.collectibles.append(Collectible(8 * TILE_SIZE, 7 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(22 * TILE_SIZE, 5 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(38 * TILE_SIZE, 5 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))
        self.collectibles.append(Collectible(47 * TILE_SIZE, 10 * TILE_SIZE - 48, "gem", self.assets.items["gem"]))

        # Gold key on the battlements.
        self.collectibles.append(
            Collectible(36 * TILE_SIZE + 12, 5 * TILE_SIZE - 52, "key", self.assets.items["key"])
        )

        # Enemies, including archers and the brute.
        self.enemies.append(
            Enemy(7 * TILE_SIZE, 10 * TILE_SIZE, "goblin_warrior", 4 * TILE_SIZE, 9 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(12 * TILE_SIZE, 6 * TILE_SIZE, "bat", 10 * TILE_SIZE, 15 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(19 * TILE_SIZE, 7 * TILE_SIZE, "goblin_archer", 16 * TILE_SIZE, 20 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(21 * TILE_SIZE, 10 * TILE_SIZE, "slime", 16 * TILE_SIZE, 24 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(27 * TILE_SIZE, 7 * TILE_SIZE, "bat", 25 * TILE_SIZE, 31 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(35 * TILE_SIZE, 9 * TILE_SIZE, "goblin_brute", 32 * TILE_SIZE, 40 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(37 * TILE_SIZE, 5 * TILE_SIZE, "goblin_archer", 33 * TILE_SIZE, 39 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(46 * TILE_SIZE, 10 * TILE_SIZE, "goblin_warrior", 43 * TILE_SIZE, 48 * TILE_SIZE, self.assets)
        )

    def get_active_solid_rects(self) -> list[pygame.Rect]:
        """Returns all solid rects including the locked door if it is still closed."""
        if self.locked_door and not self.locked_door["open"]:
            return self.solid_rects + [self.locked_door["rect"]]
        return self.solid_rects

    def draw_background(self, surface: pygame.Surface, camera_x: int) -> None:
        """Clear the screen until the final background art is added."""
        surface.fill((24, 28, 38))

    def draw(self, surface: pygame.Surface, camera_x: int, font: pygame.font.Font) -> None:
        """Draw the level and its entities."""
        sw = surface.get_width()
        self.draw_background(surface, camera_x)

        # Cave exit archway.
        exit_draw_x = self.cave_exit_rect.x - 24 - camera_x
        exit_draw_y = self.cave_exit_rect.y - 24
        surface.blit(self.assets.tiles["cave_exit"], (exit_draw_x, exit_draw_y))
        exit_tag = font.render("EXIT", True, (255, 230, 110))
        surface.blit(exit_tag, (exit_draw_x + 44, exit_draw_y - 22))

        # Decorations.
        for img, dx, dy in self.decorations:
            if -160 <= dx - camera_x <= sw + 160:
                surface.blit(img, (dx - camera_x, dy))

        # Terrain and ladders.
        for img, tx, ty in self.visual_tiles:
            if -160 <= tx - camera_x <= sw + 160:
                surface.blit(img, (tx - camera_x, ty))

        for img, lx, ly in self.ladder_tiles:
            if -160 <= lx - camera_x <= sw + 160:
                surface.blit(img, (lx - camera_x, ly))

        # Levers.
        for lv in self.levers:
            lrect = lv["rect"]
            img = self.assets.props["lever_on"] if lv["active"] else self.assets.props["lever_off"]
            surface.blit(img, (lrect.x - camera_x, lrect.y))

        # Chests.
        for ch in self.chests:
            crect = ch["rect"]
            if ch["open"]:
                surface.blit(self.assets.props["chest_open"], (crect.x - camera_x, crect.y - 8))
            else:
                surface.blit(self.assets.props["chest_closed"], (crect.x - camera_x, crect.y))

        # Destructibles.
        for d in self.destructibles:
            drect = d["rect"]
            surface.blit(self.assets.props[d["kind"]], (drect.x - camera_x, drect.y))

        # Locked door.
        if self.locked_door and not self.locked_door["open"]:
            drect = self.locked_door["rect"]
            door_img = _scale_to_size(self.assets.props["door_locked"], drect.width, drect.height)
            surface.blit(door_img, (drect.x - camera_x, drect.y))

        # Collectibles.
        for item in self.collectibles:
            if not item.collected and -80 <= item.rect.x - camera_x <= sw + 80:
                item.draw(surface, camera_x)

        # Enemies and projectiles.
        for enemy in self.enemies:
            if -160 <= enemy.rect.x - camera_x <= sw + 160:
                enemy.draw(surface, camera_x)

        for proj in self.projectiles:
            proj.draw(surface, camera_x)
