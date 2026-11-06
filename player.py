"""Player movement, combat, animation, and collision handling."""

import os
import pygame


class Player:
    """Controllable knight with platformer physics and combat."""

    def __init__(self, x: int, y: int, sprites: dict[str, list[pygame.Surface]]):
        # Keep the collision box tight around the body.
        self.rect = pygame.Rect(x, y, 38, 62)
        self.spawn_x = x
        self.spawn_y = y

        # Movement constants.
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.speed = 5.2
        self.jump_power = -13.2
        self.gravity = 0.58
        self.max_fall_speed = 14.0
        self.climb_speed = 4.2

        # Movement state.
        self.facing_right = True
        self.on_ground = False
        self.on_ladder = False
        self.touching_ladder = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0

        # Combat state.
        self.attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.combo_step = 0
        self.attack_hitbox_active = False
        self.hit_targets_this_swing: set[int] = set()

        # Stats and inventory.
        self.max_hp = 6  # Three hearts, two HP each.
        self.hp = 6
        self.lives = 3
        self.score = 0
        self.coins = 0
        self.gems = 0
        self.has_key = False
        self.invuln_timer = 0
        self.dead = False

        # Pre-generate frames for both directions.
        self.sprites_right = sprites
        self.sprites_left: dict[str, list[pygame.Surface]] = {}
        for state_name, frame_list in sprites.items():
            self.sprites_left[state_name] = [
                pygame.transform.flip(frame, True, False) for frame in frame_list
            ]

        self.anim_state = "idle"
        self.anim_index = 0
        self.anim_timer = 0.0

    def respawn(self, x: int | None = None, y: int | None = None) -> None:
        """Resets the player at the level spawn point."""
        if x is not None:
            self.spawn_x = x
        if y is not None:
            self.spawn_y = y
        self.rect.topleft = (self.spawn_x, self.spawn_y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.on_ladder = False
        self.attacking = False
        self.attack_timer = 0
        self.hp = self.max_hp
        self.invuln_timer = 60
        self.dead = False

    def trigger_jump(self) -> None:
        """Queues a jump press (with jump buffering)."""
        self.jump_buffer_timer = 8

    def trigger_attack(self) -> bool:
        """Starts a sword slash or air strike if cooldown allows."""
        if self.attack_cooldown > 0 or self.attacking:
            return False
        self.attacking = True
        self.attack_timer = 16
        self.attack_cooldown = 20
        self.combo_step = (self.combo_step + 1) % 3
        self.hit_targets_this_swing.clear()
        self.anim_index = 0
        self.anim_timer = 0.0
        return True

    def get_attack_rect(self) -> pygame.Rect | None:
        """Returns the active sword hitbox in world coordinates when attacking."""
        if not self.attacking or self.attack_timer < 4 or self.attack_timer > 14:
            return None
        reach = 56
        if self.facing_right:
            return pygame.Rect(
                self.rect.right - 8,
                self.rect.top - 6,
                reach,
                self.rect.height + 10,
            )
        return pygame.Rect(
            self.rect.left - reach + 8,
            self.rect.top - 6,
            reach,
            self.rect.height + 10,
        )

    def take_damage(self, amount: int = 1, knockback_dir: int = 0) -> bool:
        """Applies damage if not currently invulnerable. Returns True if damaged."""
        if self.invuln_timer > 0 or self.dead:
            return False
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = 65
        self.on_ladder = False
        self.vel_y = -6.5
        if knockback_dir != 0:
            self.vel_x = 5.0 * knockback_dir
        if self.hp <= 0:
            self.dead = True
        return True

    def heal(self, amount: int = 2) -> bool:
        """Heals the player up to max_hp."""
        if self.hp >= self.max_hp:
            return False
        self.hp = min(self.max_hp, self.hp + amount)
        return True

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        solid_rects: list[pygame.Rect],
        one_way_rects: list[pygame.Rect],
        ladder_rects: list[pygame.Rect],
        slope_tiles: list[tuple[pygame.Rect, str]],
        level_width: int,
    ) -> dict[str, bool]:
        """Update movement, collisions, animations, and jump/land events."""
        events = {"jumped": False, "landed": False}
        was_on_ground = self.on_ground

        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

        # Read movement input.
        move_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        move_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        move_up = keys[pygame.K_UP] or keys[pygame.K_w]
        move_down = keys[pygame.K_DOWN] or keys[pygame.K_s]

        # Check for a ladder.
        self.touching_ladder = any(self.rect.colliderect(l_rect) for l_rect in ladder_rects)
        if not self.touching_ladder:
            self.on_ladder = False
        elif (move_up or move_down) and not self.attacking:
            # Start climbing when a direction is pressed.
            for l_rect in ladder_rects:
                if self.rect.colliderect(l_rect):
                    self.on_ladder = True
                    self.vel_y = 0.0
                    break

        # Update horizontal velocity.
        if move_left and not move_right:
            self.vel_x = -self.speed
            if not self.attacking:
                self.facing_right = False
        elif move_right and not move_left:
            self.vel_x = self.speed
            if not self.attacking:
                self.facing_right = True
        else:
            self.vel_x *= 0.65
            if abs(self.vel_x) < 0.3:
                self.vel_x = 0.0

        # Apply coyote time and jump buffering.
        if self.on_ground or self.on_ladder:
            self.coyote_timer = 7
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1
            if self.coyote_timer > 0:
                # Drop through a one-way platform when requested.
                if move_down and self.on_ground and not self.on_ladder:
                    on_one_way = any(
                        self.rect.bottom == ow.top
                        and self.rect.right > ow.left
                        and self.rect.left < ow.right
                        for ow in one_way_rects
                    )
                    if on_one_way:
                        self.rect.y += 6
                        self.on_ground = False
                        self.coyote_timer = 0
                        self.jump_buffer_timer = 0
                    else:
                        self.vel_y = self.jump_power
                        self.on_ground = False
                        self.on_ladder = False
                        self.coyote_timer = 0
                        self.jump_buffer_timer = 0
                        events["jumped"] = True
                else:
                    self.vel_y = self.jump_power
                    self.on_ground = False
                    self.on_ladder = False
                    self.coyote_timer = 0
                    self.jump_buffer_timer = 0
                    events["jumped"] = True

        # Shorten the jump when the button is released.
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        if not jump_held and self.vel_y < -4.5 and not self.on_ladder:
            self.vel_y *= 0.62

        # Apply ladder movement or gravity.
        if self.on_ladder:
            if move_up:
                self.vel_y = -self.climb_speed
            elif move_down:
                self.vel_y = self.climb_speed
            else:
                self.vel_y = 0.0
        else:
            self.vel_y = min(self.max_fall_speed, self.vel_y + self.gravity)

        # Move horizontally and resolve solid collisions.
        self.rect.x += int(round(self.vel_x))
        if self.rect.left < 0:
            self.rect.left = 0
        elif self.rect.right > level_width:
            self.rect.right = level_width

        # Detect slopes before resolving horizontal collisions.
        on_slope = False
        for s_rect, _ in slope_tiles:
            if self.rect.colliderect(s_rect):
                on_slope = True
                break

        for tile in solid_rects:
            if self.rect.colliderect(tile):
                # Step over small ledges and slope edges.
                if on_slope and self.rect.bottom - tile.top <= 18:
                    self.rect.bottom = tile.top
                    continue
                if self.vel_x > 0:
                    self.rect.right = tile.left
                elif self.vel_x < 0:
                    self.rect.left = tile.right

        # Move vertically and resolve collisions.
        prev_bottom = self.rect.bottom
        self.rect.y += int(round(self.vel_y))
        self.on_ground = False

        for tile in solid_rects:
            if self.rect.colliderect(tile):
                if self.vel_y >= 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0.0
                    self.on_ground = True
                    self.on_ladder = False
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0.0

        # Handle one-way platforms.
        if self.vel_y >= 0 and not (self.on_ladder and move_down):
            for ow in one_way_rects:
                if self.rect.colliderect(ow) and prev_bottom <= ow.top + 10:
                    self.rect.bottom = ow.top
                    self.vel_y = 0.0
                    self.on_ground = True
                    break

        # Handle sloped hills.
        for s_rect, slope_dir in slope_tiles:
            if self.rect.right > s_rect.left and self.rect.left < s_rect.right:
                foot_x = self.rect.centerx
                rel_x = max(0.0, min(1.0, (foot_x - s_rect.left) / max(1, s_rect.width)))
                if slope_dir == "down_right":
                    surface_y = int(s_rect.top + rel_x * s_rect.height)
                else:
                    surface_y = int(s_rect.bottom - rel_x * s_rect.height)
                if self.vel_y >= 0 and self.rect.bottom >= surface_y - 10 and self.rect.top < s_rect.bottom:
                    self.rect.bottom = surface_y
                    self.vel_y = 0.0
                    self.on_ground = True

        if not was_on_ground and self.on_ground:
            events["landed"] = True

        self._update_animation()
        return events

    def _update_animation(self) -> None:
        """Selects and advances the appropriate Knight animation frame."""
        if self.attacking:
            if not self.on_ground:
                new_state = "air_attack"
            else:
                new_state = f"attack_{self.combo_step}"
        elif self.on_ladder:
            new_state = "climb"
        elif not self.on_ground:
            new_state = "jump" if self.vel_y < 0 else "fall"
        elif abs(self.vel_x) > 0.6:
            new_state = "run"
        else:
            new_state = "idle"

        if new_state != self.anim_state:
            self.anim_state = new_state
            self.anim_index = 0
            self.anim_timer = 0.0

        frames = self.sprites_right.get(self.anim_state, self.sprites_right["idle"])
        if self.on_ladder and abs(self.vel_y) < 0.1:
            return

        speed_map = {
            "idle": 0.06,
            "run": 0.16,
            "jump": 0.12,
            "fall": 0.10,
            "climb": 0.14,
            "air_attack": 0.18,
            "attack_0": 0.20,
            "attack_1": 0.20,
            "attack_2": 0.20,
        }
        self.anim_timer += speed_map.get(self.anim_state, 0.12)
        if self.anim_timer >= len(frames):
            self.anim_timer = 0.0
        self.anim_index = int(self.anim_timer) % len(frames)

    def draw(self, surface: pygame.Surface, camera_x: int, camera_y: int = 0) -> None:
        """Draws the Knight sprite aligned to his collision box."""
        # Blink while invulnerable.
        if self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 1:
            return

        bank = self.sprites_right if self.facing_right else self.sprites_left
        frames = bank.get(self.anim_state, bank["idle"])
        frame = frames[self.anim_index % len(frames)]

        fw, fh = frame.get_size()
        draw_y = self.rect.bottom - fh - camera_y + 2

        # Keep the body centered when the sword extends forward.
        if self.attacking:
            if self.facing_right:
                draw_x = self.rect.left - 10 - camera_x
            else:
                draw_x = self.rect.right + 10 - fw - camera_x
        else:
            draw_x = self.rect.centerx - (fw // 2) - camera_x

        surface.blit(frame, (draw_x, draw_y))


def load_player_sprites(sliced_dir: str = "assets/sliced") -> dict[str, list[pygame.Surface]]:
    """Loads and scales the sliced Knight sprites for all animation states."""
    knight_dir = os.path.join(sliced_dir, "knight")

    def _load(name: str, target_h: int = 68) -> pygame.Surface:
        path = os.path.join(knight_dir, f"{name}.png")
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        scale = target_h / max(1, h)
        new_w = max(1, int(round(w * scale)))
        return pygame.transform.smoothscale(img, (new_w, target_h))

    idle_1 = _load("idle_1", 68)
    idle_2 = _load("idle_2", 68)
    run_1 = _load("run_1", 68)
    run_2 = _load("run_2", 68)
    jump_start = _load("jump_start", 72)
    jump_peak = _load("jump_peak", 72)
    slash = _load("slash", 70)
    combo_1 = _load("combo_1", 70)
    combo_2 = _load("combo_2", 70)
    combo_3 = _load("combo_3", 70)
    jump_attack = _load("jump_attack", 78)
    jump_slash = _load("jump_slash", 76)

    return {
        "idle": [idle_1, idle_2],
        "run": [run_1, run_2],
        "jump": [jump_start, jump_peak],
        "fall": [jump_peak],
        "climb": [run_1, run_2],
        "attack_0": [slash, combo_1],
        "attack_1": [combo_2, combo_3],
        "attack_2": [combo_1, slash],
        "air_attack": [jump_attack, jump_slash],
    }


if __name__ == "__main__":
    from main import run_game

    run_game()
