"""Level, entity, and tilemap management."""

import json
import math
import os
import sys
import pygame

import sounds
from background import load_background

TILE_SIZE = 64


def get_levels_dir() -> str:
    """Return the directory where custom/edited level JSON files are saved."""
    base_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    if not os.access(base_dir, os.W_OK):
        base_dir = os.path.expanduser("~")
    return os.path.join(base_dir, "levels")


def default_level_json_path(level_number: int) -> str:
    """Return the default JSON file path for a given level number."""
    return os.path.join(get_levels_dir(), f"level_{level_number}.json")


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
        self.custom: dict[str, pygame.Surface] = {}
        self._surface_to_ref: dict[int, str] = {}
        self._transform_cache: dict[tuple, pygame.Surface] = {}
        self._load_all()
        self.reload_custom()
        self._rebuild_ref_index()

        # Parallax backgrounds, one per level (see background.py).
        backgrounds_dir = os.path.join(os.path.dirname(sliced_dir), "backgrounds")
        self.backgrounds = {}
        for level_number in (1, 2):
            self.backgrounds[level_number] = load_background(backgrounds_dir, level_number)

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

    def reload_custom(self) -> None:
        """Load any custom-sliced PNG sprites from `assets/sliced/custom/`."""
        custom_dir = os.path.join(self.sliced_dir, "custom")
        if os.path.isdir(custom_dir):
            for fname in sorted(os.listdir(custom_dir)):
                if fname.lower().endswith(".png"):
                    key = os.path.splitext(fname)[0]
                    path = os.path.join(custom_dir, fname)
                    try:
                        surf = pygame.image.load(path).convert_alpha()
                        self.custom[key] = surf
                    except pygame.error:
                        pass
        self._rebuild_ref_index()

    def _rebuild_ref_index(self) -> None:
        """Map surface object IDs back to string references for level serialization."""
        self._surface_to_ref.clear()
        for k, s in self.tiles.items():
            self._surface_to_ref[id(s)] = f"tiles:{k}"
        for k, s in self.props.items():
            self._surface_to_ref[id(s)] = f"props:{k}"
        for k, s in self.custom.items():
            self._surface_to_ref[id(s)] = f"custom:{k}"
        for k, frames in self.items.items():
            for s in frames:
                self._surface_to_ref[id(s)] = f"items:{k}"

    def identify_surface(self, surf: pygame.Surface) -> str:
        """Return the reference key (e.g. 'tiles:grass_1') for a given Surface."""
        return self._surface_to_ref.get(id(surf), "tiles:grass_1")

    def get_base_surface(self, ref: str) -> pygame.Surface | None:
        """Resolve a string reference (e.g. 'tiles:grass_1', 'props:crate', 'custom:slice_1') to a Surface."""
        if not ref or ref.startswith("special:"):
            return None
        if ":" in ref:
            cat, key = ref.split(":", 1)
        else:
            cat, key = "tiles", ref

        if cat == "tiles":
            if key in self.tiles:
                return self.tiles[key]
            raw_path = os.path.join(self.sliced_dir, "tiles", f"{key}.png")
            if os.path.exists(raw_path):
                s = pygame.image.load(raw_path).convert_alpha()
                self.tiles[key] = s
                self._surface_to_ref[id(s)] = f"tiles:{key}"
                return s
        elif cat == "props":
            if key in self.props:
                return self.props[key]
            raw_path = os.path.join(self.sliced_dir, "props", f"{key}.png")
            if os.path.exists(raw_path):
                s = pygame.image.load(raw_path).convert_alpha()
                self.props[key] = s
                self._surface_to_ref[id(s)] = f"props:{key}"
                return s
        elif cat == "custom":
            if key in self.custom:
                return self.custom[key]
            raw_path = os.path.join(self.sliced_dir, "custom", f"{key}.png")
            if os.path.exists(raw_path):
                s = pygame.image.load(raw_path).convert_alpha()
                self.custom[key] = s
                self._surface_to_ref[id(s)] = f"custom:{key}"
                return s
        elif cat == "items":
            if key in self.items and self.items[key]:
                return self.items[key][0]
            raw_path = os.path.join(self.sliced_dir, "items", f"{key}.png")
            if os.path.exists(raw_path):
                return pygame.image.load(raw_path).convert_alpha()
        elif cat == "enemies":
            enemy_map = {
                "goblin_warrior": "goblin_warrior_walk",
                "slime": "slime",
                "bat": "bat",
                "goblin_archer": "goblin_archer",
                "goblin_brute": "goblin_brute",
                "goblin_scout": "goblin_scout",
            }
            ekey = enemy_map.get(key, key)
            if ekey in self.enemies and self.enemies[ekey]:
                return self.enemies[ekey][0]
            raw_path = os.path.join(self.sliced_dir, "enemies", f"{key}.png")
            if os.path.exists(raw_path):
                return pygame.image.load(raw_path).convert_alpha()
        elif cat == "ui" and key in self.ui:
            return self.ui[key]
        elif cat == "vfx" and key in self.vfx:
            return self.vfx[key]
        elif cat == "file":
            raw_path = os.path.join(self.sliced_dir, key)
            if os.path.exists(raw_path):
                return pygame.image.load(raw_path).convert_alpha()
        return None

    def get_surface(
        self,
        ref: str,
        w: int | None = None,
        h: int | None = None,
        flip_x: bool = False,
        flip_y: bool = False,
    ) -> pygame.Surface | None:
        """Return a (possibly scaled and flipped) Surface for the given reference."""
        base = self.get_base_surface(ref)
        if base is None:
            return None
        bw, bh = base.get_size()
        tw = w if (w is not None and w > 0) else bw
        th = h if (h is not None and h > 0) else bh
        if tw == bw and th == bh and not flip_x and not flip_y:
            return base
        cache_key = (ref, tw, th, bool(flip_x), bool(flip_y))
        if cache_key in self._transform_cache:
            return self._transform_cache[cache_key]
        out = base
        if tw != bw or th != bh:
            out = _scale_to_size(out, tw, th)
        if flip_x or flip_y:
            out = pygame.transform.flip(out, bool(flip_x), bool(flip_y))
        self._transform_cache[cache_key] = out
        self._surface_to_ref[id(out)] = ref
        return out


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

        # AI state. Walking enemies go patrol, chase, windup, strike, recover.
        # Bats go patrol, swoop, return.
        self.state = "patrol"
        self.state_timer = 0
        self.attack_cooldown = 0
        self.swoop_target = (x, y)

        # AI settings in pixels and frames (60 frames = 1 second).
        # Enemies that cannot chase or attack keep these defaults.
        self.detect_range = 0  # how far away the enemy notices the player
        self.chase_speed = 0
        self.reach = 0  # how far the weapon reaches in front of the enemy
        self.hit_height = 0  # height of the weapon hitbox, measured up from the feet
        self.windup_frames = 0  # raised weapon, the player can dodge
        self.strike_frames = 0  # the weapon can hurt the player
        self.recover_frames = 0  # the enemy cannot attack after a swing
        self.attack_damage = 1
        self.interruptible = True  # False: hitting the enemy cannot cancel its swing
        self.swoop_speed = 0
        self.swoop_cooldown = 0

        if kind == "slime":
            self.rect = pygame.Rect(x, y - 42, 48, 42)
            self.speed = 1.6
            self.hp = 1
            self.max_hp = 1
            self.score_value = 150
            self.sprites_faces_right_natively = False
            self.detect_range = 220
            self.chase_speed = 4
        elif kind == "bat":
            self.rect = pygame.Rect(x, y - 44, 62, 40)
            self.speed = 2.4
            self.hp = 1
            self.max_hp = 1
            self.score_value = 200
            self.sprites_faces_right_natively = True
            self.detect_range = 320
            self.swoop_speed = 6
            self.swoop_cooldown = 110
        elif kind == "goblin_warrior":
            self.rect = pygame.Rect(x, y - 60, 44, 60)
            self.speed = 2.1
            self.hp = 2
            self.max_hp = 2
            self.score_value = 300
            self.sprites_faces_right_natively = True
            self.detect_range = 300
            self.chase_speed = 4
            self.attack_damage = 2
            self.reach = 56
            self.hit_height = 52
            self.windup_frames = 24
            self.strike_frames = 10
            self.recover_frames = 50
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
            self.detect_range = 340
            self.chase_speed = 3
            self.reach = 84
            self.hit_height = 56
            self.windup_frames = 40
            self.strike_frames = 14
            self.recover_frames = 70
            self.attack_damage = 3
            self.interruptible = False
        else:
            self.rect = pygame.Rect(x, y - 54, 42, 54)
            self.speed = 1.8
            self.hp = 1
            self.max_hp = 1
            self.score_value = 200
            self.sprites_faces_right_natively = True

        self.vel_x = self.speed
        # The enemy starts a swing when the player is closer than this.
        self.attack_range = self.reach - 12

    def take_hit(self, damage: int = 1) -> bool:
        """Deals damage to this enemy. Returns True if defeated."""
        if self.dead:
            return False
        self.hp -= damage
        sounds.play("hit")
        self.hurt_timer = 14
        # A hit cancels a swing, so fighting back works (except against the brute).
        if self.interruptible and self.state in ("windup", "strike"):
            self.state = "recover"
            self.state_timer = 30
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
            in_range = dist_x < 520 and dist_y < 180
            # Always finish a shot once the bow is drawn so the archer never freezes mid-aim.
            if in_range or self.shoot_cooldown < 55:
                self.shoot_cooldown -= 1
                if self.shoot_cooldown <= 0:
                    self.shoot_cooldown = 105
                    direction = 1 if self.facing_right else -1
                    arrow_img = self.assets.enemies["arrow"][0]
                    ax = self.rect.right if direction > 0 else self.rect.left - arrow_img.get_width()
                    ay = self.rect.centery - 8
                    projectiles.append(Projectile(ax, ay, direction, arrow_img))
            return

        if self.kind == "bat":
            self._update_bat(player_rect)
        else:
            self._update_walker(player_rect)

    def get_attack_rect(self) -> pygame.Rect | None:
        """Returns the weapon hitbox while the enemy is swinging, otherwise None."""
        if self.dead or self.state != "strike":
            return None
        top = self.rect.bottom - self.hit_height
        if self.facing_right:
            return pygame.Rect(self.rect.right - 6, top, self.reach, self.hit_height)
        return pygame.Rect(self.rect.left - self.reach + 6, top, self.reach, self.hit_height)

    def _patrol(self) -> None:
        """Walks back and forth between the horizontal limits."""
        self.rect.x += int(round(self.vel_x))
        if self.rect.left <= self.patrol_min_x:
            self.rect.left = self.patrol_min_x
            self.vel_x = abs(self.speed)
            self.facing_right = True
        elif self.rect.right >= self.patrol_max_x:
            self.rect.right = self.patrol_max_x
            self.vel_x = -abs(self.speed)
            self.facing_right = False

    def _resume_patrol(self) -> None:
        """Goes back to patrolling, turning inward if sitting at a patrol limit."""
        self.state = "patrol"
        if self.rect.left <= self.patrol_min_x:
            self.facing_right = True
        elif self.rect.right >= self.patrol_max_x:
            self.facing_right = False
        if self.facing_right:
            self.vel_x = abs(self.speed)
        else:
            self.vel_x = -abs(self.speed)

    def _on_same_floor(self, player_rect: pygame.Rect) -> bool:
        """Returns True when the player stands on the same floor (including short jumps)."""
        dy = self.rect.bottom - player_rect.bottom
        return -24 <= dy <= 80

    def _gap_to(self, player_rect: pygame.Rect) -> int:
        """Returns the sideways distance between the edges of the enemy and the player."""
        if player_rect.centerx >= self.rect.centerx:
            return player_rect.left - self.rect.right
        return self.rect.left - player_rect.right

    def _can_reach(self, player_rect: pygame.Rect) -> bool:
        """Returns True when the player is reachable from within this enemy's patrol limits."""
        if self.windup_frames > 0:
            return (
                player_rect.right >= self.patrol_min_x - self.attack_range
                and player_rect.left <= self.patrol_max_x + self.attack_range
            )
        return player_rect.right > self.patrol_min_x and player_rect.left < self.patrol_max_x

    def _update_walker(self, player_rect: pygame.Rect) -> None:
        """Updates slimes, goblin warriors and goblin brutes."""
        if self.state == "patrol":
            noticed = (
                self._on_same_floor(player_rect)
                and self._can_reach(player_rect)
                and self._gap_to(player_rect) <= self.detect_range
            )
            if self.detect_range > 0 and noticed:
                self.state = "chase"
            else:
                self._patrol()
                return

        if self.state == "chase":
            # Once the enemy has noticed the player it keeps chasing a bit longer,
            # unless the player moves onto another floor or beyond its patrol reach.
            lost = (
                not self._on_same_floor(player_rect)
                or not self._can_reach(player_rect)
                or self._gap_to(player_rect) > self.detect_range * 1.3
            )
            if lost:
                self._resume_patrol()
                self._patrol()
                return
            dx = player_rect.centerx - self.rect.centerx
            gap = self._gap_to(player_rect)
            if self.windup_frames > 0:
                if dx != 0:
                    self.facing_right = dx > 0
                if gap <= self.attack_range:
                    self.state = "windup"
                    self.state_timer = self.windup_frames
                    return
            else:
                # Contact chasers (slimes) charge through the player before turning around.
                if abs(dx) > 12:
                    self.facing_right = dx > 0

            if self.facing_right:
                self.rect.x += self.chase_speed
            else:
                self.rect.x -= self.chase_speed
            # Stay inside the patrol area so enemies never walk off a ledge.
            if self.rect.left < self.patrol_min_x:
                self.rect.left = self.patrol_min_x
                if self.windup_frames == 0:
                    self.facing_right = True
            elif self.rect.right > self.patrol_max_x:
                self.rect.right = self.patrol_max_x
                if self.windup_frames == 0:
                    self.facing_right = False
            return

        # windup -> strike -> recover -> chase
        self.state_timer -= 1
        if self.state_timer > 0:
            return
        if self.state == "windup":
            self.state = "strike"
            self.state_timer = self.strike_frames
        elif self.state == "strike":
            self.state = "recover"
            self.state_timer = self.recover_frames
        else:
            self.state = "chase"

    def _hover_y(self) -> int:
        """Returns the height of the bat while it floats up and down."""
        return int(self.base_y - 44 + math.sin(self.anim_timer * 1.8) * 18)

    def _update_bat(self, player_rect: pygame.Rect) -> None:
        """Updates bats: they float around, dive at the player, then fly back up."""
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.state == "patrol":
            self._patrol()
            self.rect.y = self._hover_y()
            dx = abs(player_rect.centerx - self.rect.centerx)
            dy = player_rect.centery - self.rect.centery
            in_patrol_reach = (
                player_rect.right >= self.patrol_min_x
                and player_rect.left <= self.patrol_max_x
            )
            if (
                self.attack_cooldown == 0
                and in_patrol_reach
                and dx <= self.detect_range
                and -60 <= dy <= 230
            ):
                # Clamp dive target inside the patrol limits so the bat never stalls on the edge.
                half_w = self.rect.width // 2
                target_x = max(
                    self.patrol_min_x + half_w,
                    min(self.patrol_max_x - half_w, player_rect.centerx),
                )
                self.swoop_target = (target_x, player_rect.centery)
                self.state = "swoop"
                self.state_timer = 50
            return

        if self.state == "swoop":
            tx, ty = self.swoop_target
            dx = tx - self.rect.centerx
            dy = ty - self.rect.centery
            dist = math.sqrt(dx * dx + dy * dy)
            self.state_timer -= 1
            if dist <= self.swoop_speed or self.state_timer <= 0:
                self.vel_x = abs(self.speed) if self.facing_right else -abs(self.speed)
                self.state = "return"
                return
            if dx != 0:
                self.facing_right = dx > 0
            prev_pos = self.rect.topleft
            self.rect.x += int(round(dx / dist * self.swoop_speed))
            self.rect.y += int(round(dy / dist * self.swoop_speed))
            if self.rect.left < self.patrol_min_x:
                self.rect.left = self.patrol_min_x
            elif self.rect.right > self.patrol_max_x:
                self.rect.right = self.patrol_max_x
            if self.rect.topleft == prev_pos:
                self.vel_x = abs(self.speed) if self.facing_right else -abs(self.speed)
                self.state = "return"
            return

        # return: fly back up to the normal height, then patrol again.
        self._patrol()
        diff = self._hover_y() - self.rect.y
        if abs(diff) <= 5:
            self.rect.y = self._hover_y()
            self.attack_cooldown = self.swoop_cooldown
            self._resume_patrol()
        elif diff > 0:
            self.rect.y += 5
        else:
            self.rect.y -= 5

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
            attack_frames = self.assets.enemies["goblin_warrior_attack"]
            if self.state == "windup":
                frame = attack_frames[0]  # sword raised
            elif self.state == "strike":
                frame = attack_frames[1]  # sword swung
            elif self.state == "recover":
                frame = frames[0]  # standing still
            else:
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
            if self.state == "windup":
                frame = frames[1]  # club raised
            elif self.state == "strike":
                frame = frames[2]  # club smashed down
            else:
                frame = frames[0]
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

        # Red "!" above the head warns the player that a hit is coming.
        if self.state == "windup":
            mark_x = self.rect.centerx - camera_x
            mark_y = draw_y - 32
            pygame.draw.rect(surface, (235, 55, 55), (mark_x - 3, mark_y, 6, 11), border_radius=2)
            pygame.draw.rect(surface, (235, 55, 55), (mark_x - 3, mark_y + 14, 6, 6), border_radius=3)

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

    def __init__(
        self,
        level_number: int,
        assets: AssetLibrary,
        json_path: str | None = None,
        use_default: bool = False,
        data: dict | None = None,
    ):
        self.level_number = level_number
        self.background_id = level_number if level_number in (1, 2) else 1
        self.assets = assets
        self.level_name = (
            "Level 1: Emerald Grasslands"
            if level_number == 1
            else ("Level 2: Dark Forest" if level_number == 2 else f"Level {level_number}: Custom")
        )
        self.width = 56 * TILE_SIZE  # 3584 px wide
        self.height = 720
        self.ground_y = 10 * TILE_SIZE  # y = 640

        # Collision and tile collections.
        self.visual_tiles: list[tuple[pygame.Surface, int, int]] = []
        self.ladder_tiles: list[tuple[pygame.Surface, int, int]] = []
        self.ladder_specs: list[tuple[int, int, int]] = []
        self.solid_rects: list[pygame.Rect] = []
        self._raw_solid_rects: list[pygame.Rect] = []
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
        self.editor_objects: list[dict] = []

        resolved_json = json_path
        if resolved_json is None and not use_default and data is None:
            candidate = default_level_json_path(level_number)
            if os.path.exists(candidate):
                resolved_json = candidate

        if data is not None:
            self.load_from_dict(data)
        elif resolved_json is not None and os.path.exists(resolved_json):
            self.load_json(resolved_json)
        else:
            if level_number == 1:
                self._build_level_1()
            else:
                self._build_level_2()
            self._raw_solid_rects = [r.copy() for r in self.solid_rects]
            self._carve_ladder_openings()

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
        ladder_rect = pygame.Rect(x, top_row * TILE_SIZE, 48, height_rows * TILE_SIZE)
        self.ladder_rects.append(ladder_rect)
        self.ladder_specs.append((col, top_row, height_rows))

    def _carve_ladder_openings(self) -> None:
        """
        Carves pass-through shafts in solid elevated platforms wherever a ladder passes
        through them, replacing the top surface with a one-way platform so the player
        can climb smoothly up and down through platforms without getting blocked or stuck.
        """
        for col, top_row, height_rows in self.ladder_specs:
            shaft = pygame.Rect(
                col * TILE_SIZE,
                top_row * TILE_SIZE,
                TILE_SIZE,
                height_rows * TILE_SIZE,
            )
            new_solids: list[pygame.Rect] = []
            for s in self.solid_rects:
                if not s.colliderect(shaft):
                    new_solids.append(s)
                    continue
                # Split solid rect around the ladder shaft
                if s.left < shaft.left:
                    new_solids.append(pygame.Rect(s.left, s.top, shaft.left - s.left, s.height))
                if s.right > shaft.right:
                    new_solids.append(pygame.Rect(shaft.right, s.top, s.right - shaft.right, s.height))
                inter_left = max(s.left, shaft.left)
                inter_w = min(s.right, shaft.right) - inter_left
                if inter_w > 0:
                    if s.top < shaft.top:
                        new_solids.append(pygame.Rect(inter_left, s.top, inter_w, shaft.top - s.top))
                    if s.bottom > shaft.bottom:
                        new_solids.append(pygame.Rect(inter_left, shaft.bottom, inter_w, s.bottom - shaft.bottom))
            self.solid_rects = new_solids
            # Full tile-width one-way platform across the top of the ladder opening
            self.one_way_rects.append(pygame.Rect(col * TILE_SIZE, top_row * TILE_SIZE, TILE_SIZE, 14))

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
            Enemy(7 * TILE_SIZE, 7 * TILE_SIZE, "slime", 6 * TILE_SIZE, 9 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(15 * TILE_SIZE, 7 * TILE_SIZE, "bat", 13 * TILE_SIZE, 19 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(21 * TILE_SIZE, 9 * TILE_SIZE, "goblin_warrior", 18 * TILE_SIZE, 25 * TILE_SIZE, self.assets)
        )
        self.enemies.append(
            Enemy(32 * TILE_SIZE, 6 * TILE_SIZE, "goblin_warrior", 31 * TILE_SIZE, 34 * TILE_SIZE, self.assets)
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

        self._add_platform(16, 6, row=7)
        self._add_ladder(16, top_row=7, height_rows=3)
        self._add_platform(20, 5, row=5)
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

    @staticmethod
    def _merge_solid_rects(rects: list[pygame.Rect]) -> list[pygame.Rect]:
        """Merge adjacent horizontal and vertical solid rects to avoid internal tile seams."""
        if not rects:
            return []
        # Step 1: merge horizontally contiguous rects with identical top and height.
        by_row = sorted([r.copy() for r in rects], key=lambda r: (r.top, r.height, r.left))
        horiz_merged: list[pygame.Rect] = []
        for r in by_row:
            if (
                horiz_merged
                and horiz_merged[-1].top == r.top
                and horiz_merged[-1].height == r.height
                and horiz_merged[-1].right >= r.left
            ):
                horiz_merged[-1].width = max(horiz_merged[-1].right, r.right) - horiz_merged[-1].left
            else:
                horiz_merged.append(r)

        # Step 2: merge vertically contiguous rects with identical left and width.
        by_col = sorted(horiz_merged, key=lambda r: (r.left, r.width, r.top))
        vert_merged: list[pygame.Rect] = []
        for r in by_col:
            if (
                vert_merged
                and vert_merged[-1].left == r.left
                and vert_merged[-1].width == r.width
                and vert_merged[-1].bottom >= r.top
            ):
                vert_merged[-1].height = max(vert_merged[-1].bottom, r.bottom) - vert_merged[-1].top
            else:
                vert_merged.append(r)
        return vert_merged

    def extract_editor_objects(self) -> list[dict]:
        """Convert this Level's current state into a list of unified editor object dicts."""
        if self.editor_objects:
            return [json.loads(json.dumps(o)) for o in self.editor_objects]

        objs: list[dict] = []
        next_id = 1

        def add_obj(
            obj_type: str,
            ref: str,
            x: int,
            y: int,
            w: int,
            h: int,
            layer: int = 1,
            flip_x: bool = False,
            flip_y: bool = False,
            props: dict | None = None,
        ) -> None:
            nonlocal next_id
            objs.append(
                {
                    "id": next_id,
                    "obj_type": obj_type,
                    "ref": ref,
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h),
                    "flip_x": bool(flip_x),
                    "flip_y": bool(flip_y),
                    "layer": int(layer),
                    "props": props or {},
                }
            )
            next_id += 1

        # 1. Background decorations (layer 0).
        for surf, dx, dy in self.decorations:
            ref = self.assets.identify_surface(surf)
            add_obj("decoration", ref, dx, dy, surf.get_width(), surf.get_height(), layer=0)

        # 2. Visual tiles (solid, one_way, spike, slope, or layer-1 decoration).
        raw_solids = self._raw_solid_rects if self._raw_solid_rects else self.solid_rects
        slope_map = {(sr.x, sr.y): sdir for sr, sdir in self.slope_tiles}
        for surf, tx, ty in self.visual_tiles:
            ref = self.assets.identify_surface(surf)
            w, h = surf.get_size()
            if ref in ("tiles:bridge_full", "tiles:bridge_plank"):
                add_obj("one_way", ref, tx, ty, w, h, layer=1)
            elif ref in ("tiles:spike_1", "tiles:spike_2"):
                add_obj("spike", ref, tx, ty, w, h, layer=1)
            elif (tx, ty) in slope_map or ref == "tiles:hill_slope":
                sdir = slope_map.get((tx, ty), "down_right")
                otype = "slope_down_right" if sdir == "down_right" else "slope_up_right"
                add_obj(otype, ref, tx, ty, w, h, layer=1)
            else:
                cx, cy = tx + w // 2, ty + h // 2
                is_solid = any(sr.collidepoint(cx, cy) for sr in raw_solids)
                add_obj("solid" if is_solid else "decoration", ref, tx, ty, w, h, layer=1)

        # 3. Ladders.
        for surf, lx, ly in self.ladder_tiles:
            ref = self.assets.identify_surface(surf)
            add_obj("ladder", ref, lx, ly, surf.get_width(), surf.get_height(), layer=1)

        # 4. Props: levers, chests, destructibles, locked door.
        for lv in self.levers:
            r = lv["rect"]
            add_obj("lever", "props:lever_off", r.x, r.y, r.width, r.height, layer=2)
        for ch in self.chests:
            r = ch["rect"]
            add_obj("chest", "props:chest_closed", r.x, r.y, r.width, r.height, layer=2)
        for d in self.destructibles:
            r = d["rect"]
            kind = d.get("kind", "crate")
            ref = d.get("ref", f"props:{kind}")
            add_obj(
                "destructible",
                ref,
                r.x,
                r.y,
                r.width,
                r.height,
                layer=2,
                props={"kind": kind, "drop": d.get("drop", "coin")},
            )
        if self.locked_door:
            r = self.locked_door["rect"]
            add_obj("locked_door", "props:door_locked", r.x, r.y, r.width, r.height, layer=2)

        # 5. Collectibles.
        for item in self.collectibles:
            add_obj(
                "collectible",
                f"items:{item.kind}",
                item.rect.x,
                int(item.base_y),
                item.rect.width,
                item.rect.height,
                layer=2,
                props={"kind": item.kind},
            )

        # 6. Enemies.
        for en in self.enemies:
            add_obj(
                "enemy",
                f"enemies:{en.kind}",
                en.rect.x,
                en.rect.y,
                en.rect.width,
                en.rect.height,
                layer=2,
                props={
                    "kind": en.kind,
                    "patrol_min_x": int(en.patrol_min_x),
                    "patrol_max_x": int(en.patrol_max_x),
                },
            )

        # 7. Spawn point & Cave Exit.
        add_obj("spawn", "special:spawn", self.spawn_pos[0], self.spawn_pos[1], 38, 62, layer=2)
        exit_x = self.cave_exit_rect.x - 24
        exit_y = self.cave_exit_rect.y - 24
        add_obj("exit", "tiles:cave_exit", exit_x, exit_y, TILE_SIZE * 2, TILE_SIZE * 2, layer=0)

        return objs

    def _compile_editor_objects(self, editor_objects: list[dict]) -> None:
        """Populate runtime tiles, collisions, props, collectibles, and enemies from editor_objects."""
        self.editor_objects = [json.loads(json.dumps(o)) for o in editor_objects]
        self.visual_tiles.clear()
        self.ladder_tiles.clear()
        self.ladder_specs.clear()
        self.solid_rects.clear()
        self._raw_solid_rects.clear()
        self.one_way_rects.clear()
        self.ladder_rects.clear()
        self.slope_tiles.clear()
        self.spike_rects.clear()
        self.collectibles.clear()
        self.enemies.clear()
        self.projectiles.clear()
        self.particles.clear()
        self.destructibles.clear()
        self.chests.clear()
        self.levers.clear()
        self.decorations.clear()
        self.locked_door = None

        raw_solids: list[pygame.Rect] = []
        raw_ladders: list[pygame.Rect] = []

        # Sort by layer then original order so background/decorations draw behind foreground.
        sorted_objs = sorted(enumerate(editor_objects), key=lambda pair: (pair[1].get("layer", 1), pair[0]))

        for _, obj in sorted_objs:
            otype = obj.get("obj_type", "solid")
            ref = obj.get("ref", "")
            x = int(obj.get("x", 0))
            y = int(obj.get("y", 0))
            w = max(4, int(obj.get("w", TILE_SIZE)))
            h = max(4, int(obj.get("h", TILE_SIZE)))
            flip_x = bool(obj.get("flip_x", False))
            flip_y = bool(obj.get("flip_y", False))
            layer = int(obj.get("layer", 1))
            props = obj.get("props") or {}

            if otype == "spawn":
                self.spawn_pos = (x, y)
                continue
            if otype == "exit":
                self.cave_exit_rect = pygame.Rect(x + 24, y + 24, max(16, w - 48), max(16, h - 24))
                continue

            surf = self.assets.get_surface(ref, w, h, flip_x=flip_x, flip_y=flip_y)

            if otype == "solid":
                if surf is not None:
                    self.visual_tiles.append((surf, x, y))
                raw_solids.append(pygame.Rect(x, y, w, h))
            elif otype == "one_way":
                if surf is not None:
                    self.visual_tiles.append((surf, x, y))
                self.one_way_rects.append(pygame.Rect(x, y, w, min(18, h)))
            elif otype == "ladder":
                if surf is not None:
                    self.ladder_tiles.append((surf, x, y))
                raw_ladders.append(pygame.Rect(x, y, w, h))
            elif otype == "spike":
                if surf is not None:
                    self.visual_tiles.append((surf, x, y))
                raw_solids.append(pygame.Rect(x, y + 28, w, max(16, h - 16)))
                self.spike_rects.append(pygame.Rect(x + 6, y + 6, max(8, w - 12), 22))
            elif otype in ("slope_down_right", "slope_up_right"):
                if surf is not None:
                    self.visual_tiles.append((surf, x, y))
                sdir = "down_right" if otype == "slope_down_right" else "up_right"
                self.slope_tiles.append((pygame.Rect(x, y, w, h), sdir))
            elif otype == "decoration":
                if surf is not None:
                    if layer <= 0:
                        self.decorations.append((surf, x, y))
                    else:
                        self.visual_tiles.append((surf, x, y))
            elif otype == "destructible":
                kind = props.get("kind", "crate" if "barrel" not in ref else "barrel")
                if kind not in ("crate", "barrel"):
                    kind = "crate"
                drop = props.get("drop", "coin")
                self.destructibles.append(
                    {"kind": kind, "rect": pygame.Rect(x, y, w, h), "drop": drop, "ref": ref, "surf": surf}
                )
            elif otype == "chest":
                self.chests.append({"rect": pygame.Rect(x, y, w, h), "open": False})
            elif otype == "lever":
                self.levers.append({"rect": pygame.Rect(x, y, w, h), "active": False})
            elif otype == "locked_door":
                self.locked_door = {"rect": pygame.Rect(x, y, w, h), "open": False}
            elif otype == "collectible":
                kind = props.get("kind") or (ref.split(":", 1)[1] if ":" in ref else "coin")
                if kind not in self.assets.items:
                    kind = "coin"
                frames = self.assets.items.get(kind)
                if not frames and surf is not None:
                    frames = [surf]
                if frames:
                    self.collectibles.append(Collectible(x, y, kind, frames))
            elif otype == "enemy":
                kind = props.get("kind") or (ref.split(":", 1)[1] if ":" in ref else "slime")
                p_min = int(props.get("patrol_min_x", max(0, x - 128)))
                p_max = int(props.get("patrol_max_x", min(self.width, x + w + 128)))
                if p_max <= p_min + w:
                    p_max = p_min + w + 64
                self.enemies.append(Enemy(x, y + h, kind, p_min, p_max, self.assets))

        self._raw_solid_rects = [r.copy() for r in raw_solids]
        self.solid_rects = self._merge_solid_rects(raw_solids)

        # Merge vertically contiguous ladder segments into single climbable ladder rects.
        by_col = sorted(raw_ladders, key=lambda r: (r.left, r.width, r.top))
        merged_ladders: list[pygame.Rect] = []
        for r in by_col:
            if (
                merged_ladders
                and abs(merged_ladders[-1].left - r.left) <= 8
                and merged_ladders[-1].bottom >= r.top - 4
            ):
                new_bottom = max(merged_ladders[-1].bottom, r.bottom)
                merged_ladders[-1].height = new_bottom - merged_ladders[-1].top
            else:
                merged_ladders.append(r.copy())
        self.ladder_rects = merged_ladders

        # Build ladder_specs for each merged ladder and carve openings through solid platforms.
        for lr in self.ladder_rects:
            col = lr.centerx // TILE_SIZE
            top_row = lr.top // TILE_SIZE
            height_rows = max(1, round(lr.height / TILE_SIZE))
            self.ladder_specs.append((col, top_row, height_rows))
        self._carve_ladder_openings()

    def to_dict(self) -> dict:
        """Serialize the level to a JSON-compatible dictionary."""
        objs = self.extract_editor_objects()
        return {
            "version": 1,
            "level_number": self.level_number,
            "background_id": getattr(self, "background_id", self.level_number),
            "level_name": self.level_name,
            "width": self.width,
            "height": self.height,
            "ground_y": self.ground_y,
            "spawn_pos": list(self.spawn_pos),
            "banner_message": self.banner_message,
            "editor_objects": objs,
        }

    def load_from_dict(self, data: dict) -> None:
        """Load the level state from a dictionary."""
        self.level_number = int(data.get("level_number", self.level_number))
        self.background_id = int(data.get("background_id", self.level_number if self.level_number in (1, 2) else 1))
        self.level_name = str(data.get("level_name", self.level_name))
        self.width = max(1280, int(data.get("width", 56 * TILE_SIZE)))
        self.height = int(data.get("height", 720))
        self.ground_y = int(data.get("ground_y", 10 * TILE_SIZE))
        sp = data.get("spawn_pos", [96, self.ground_y - 80])
        self.spawn_pos = (int(sp[0]), int(sp[1]))
        self.banner_message = str(data.get("banner_message", ""))
        self.banner_timer = 150 if self.banner_message else 0
        self.assets.reload_custom()
        editor_objects = data.get("editor_objects", [])
        self._compile_editor_objects(editor_objects)

    def save_json(self, path: str | None = None) -> str:
        """Save the level to a JSON file and return the saved file path."""
        target = path or default_level_json_path(self.level_number)
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target

    def load_json(self, path: str) -> None:
        """Load the level from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_from_dict(data)

    def draw_background(self, surface, camera_x):
        # Draw the parallax layers of this level.
        bg_id = getattr(self, "background_id", self.level_number)
        background = self.assets.backgrounds.get(bg_id) or self.assets.backgrounds.get(1)
        if background is None:
            surface.fill((24, 28, 38))
        else:
            background.draw(surface, camera_x)

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
            dsurf = d.get("surf") or self.assets.props.get(d["kind"], self.assets.props["crate"])
            surface.blit(dsurf, (drect.x - camera_x, drect.y))

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
