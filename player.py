"""Player movement, combat, animation, and collision handling."""

import os
import pygame

from animation import Animation, OneShotAnimation, Animator

# Height of the knight's body (top of the plume to the feet) in the sprite
# sheets. idle/run/slash come from base.jpg, the rest from knight.jpg, and the
# knight is drawn a bit bigger in base.jpg.
BASE_SHEET_BODY = 233
KNIGHT_SHEET_BODY = 215
BASE_SHEET_FRAMES = ["idle_1", "idle_2", "run_1", "run_2", "slash", "jump_attack"]

BODY_HEIGHT = 68     # body height on screen in pixels
FEET_PADDING = 20    # room below the feet for sword trails


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
        self.active_ladder: pygame.Rect | None = None
        self.ladder_cooldown = 0
        self.touching_ladder = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0

        # Combat state.
        self.attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.combo_step = 0
        self.last_attack_time = 0  # milliseconds, from pygame.time.get_ticks()
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

        # Animations. The number is how many ticks each frame is shown.
        # An attack lasts 16 ticks, so its frames add up to about 16.
        self.animator = Animator({
            "idle": Animation(sprites["idle"], 20),
            "run": Animation(sprites["run"], 7),
            "climb": Animation(sprites["climb"], 8),
            "jump": Animation(sprites["jump"], 8),
            "fall": Animation(sprites["fall"], 8),
            "land": OneShotAnimation(sprites["land"], 6),
            "attack_1": OneShotAnimation(sprites["attack_1"], 4),
            "attack_2": OneShotAnimation(sprites["attack_2"], 4),
            "attack_0": OneShotAnimation(sprites["attack_0"], 5),
            "air_attack": OneShotAnimation(sprites["air_attack"], 8),
        }, "idle")

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
        self.active_ladder = None
        self.ladder_cooldown = 0
        self.attacking = False
        self.attack_timer = 0
        self.hp = self.max_hp
        self.invuln_timer = 60
        self.dead = False

    def trigger_jump(self) -> None:
        """Queues a jump press (with jump buffering)."""
        self.jump_buffer_timer = 8

    def find_climbable_ladder_up(self, ladder_rects: list[pygame.Rect]) -> pygame.Rect | None:
        """Returns a ladder the player can climb upward from their current position, or None."""
        for l_rect in ladder_rects:
            if (
                abs(self.rect.centerx - l_rect.centerx) <= 28
                and self.rect.bottom > l_rect.top + 2
                and self.rect.top < l_rect.bottom
            ):
                return l_rect
        return None

    def find_climbable_ladder_down(self, ladder_rects: list[pygame.Rect]) -> pygame.Rect | None:
        """Returns a ladder the player can climb downward (including from on top of it), or None."""
        for l_rect in ladder_rects:
            if (
                abs(self.rect.centerx - l_rect.centerx) <= 28
                and self.rect.bottom >= l_rect.top - 4
                and self.rect.bottom < l_rect.bottom - 2
            ):
                return l_rect
        return None

    def trigger_attack(self) -> bool:
        """Starts a sword slash or air strike if cooldown allows."""
        if self.attack_cooldown > 0 or self.attacking:
            return False
        self.attacking = True
        self.attack_timer = 16
        self.attack_cooldown = 20
        # After a short pause the combo starts again with the first swing.
        now = pygame.time.get_ticks()
        if now - self.last_attack_time > 700:
            self.combo_step = 0
        self.last_attack_time = now
        self.combo_step = (self.combo_step + 1) % 3
        self.hit_targets_this_swing.clear()
        # Start the swing animation from its first frame, even if it is the
        # same animation as the last swing.
        self.animator.play(self._get_attack_animation(), restart=True)
        return True

    def _get_attack_animation(self):
        if not self.on_ground:
            return "air_attack"
        return "attack_" + str(self.combo_step)

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
        if self.ladder_cooldown > 0:
            self.ladder_cooldown -= 1
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

        # Read movement input.
        move_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        move_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        move_up = keys[pygame.K_UP] or keys[pygame.K_w]
        move_down = keys[pygame.K_DOWN] or keys[pygame.K_s]

        # Check for a ladder and handle grabbing / staying on it.
        up_ladder = self.find_climbable_ladder_up(ladder_rects)
        down_ladder = self.find_climbable_ladder_down(ladder_rects)
        self.touching_ladder = (up_ladder is not None) or (down_ladder is not None)

        if self.on_ladder:
            # Verify we are still horizontally & vertically within an active ladder
            still_on = None
            for l_rect in ladder_rects:
                if (
                    abs(self.rect.centerx - l_rect.centerx) <= 28
                    and self.rect.bottom >= l_rect.top - 2
                    and self.rect.top < l_rect.bottom
                ):
                    still_on = l_rect
                    break
            if still_on is None:
                self.on_ladder = False
                self.active_ladder = None
            else:
                self.active_ladder = still_on
        elif self.ladder_cooldown == 0:
            target_ladder = None
            if move_up and up_ladder is not None:
                target_ladder = up_ladder
            elif move_down and down_ladder is not None:
                target_ladder = down_ladder

            if target_ladder is not None:
                self.on_ladder = True
                self.active_ladder = target_ladder
                self.vel_x = 0.0
                self.vel_y = 0.0
                self.jump_buffer_timer = 0
                # Ensure the player fits cleanly inside the 64px carved ladder shaft
                max_offset = 11
                dx = self.rect.centerx - target_ladder.centerx
                if abs(dx) > max_offset:
                    self.rect.centerx = target_ladder.centerx + (max_offset if dx > 0 else -max_offset)

        # Update horizontal velocity.
        if self.on_ladder and self.active_ladder is not None and (move_up or move_down):
            # Keep aligned on the ladder rungs while actively climbing up/down so holding
            # A/D + W smoothly climbs to the top platform and then runs onto it without
            # accidentally sliding off mid-climb.
            self.vel_x = 0.0
            if move_left and not move_right and not self.attacking:
                self.facing_right = False
            elif move_right and not move_left and not self.attacking:
                self.facing_right = True
            dx = self.active_ladder.centerx - self.rect.centerx
            if abs(dx) <= 4:
                self.rect.centerx = self.active_ladder.centerx
            else:
                self.rect.centerx += 4 if dx > 0 else -4
        elif move_left and not move_right:
            self.vel_x = -self.speed * (0.65 if self.on_ladder else 1.0)
            if not self.attacking:
                self.facing_right = False
        elif move_right and not move_left:
            self.vel_x = self.speed * (0.65 if self.on_ladder else 1.0)
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
                        self.active_ladder = None
                        self.coyote_timer = 0
                        self.jump_buffer_timer = 0
                        events["jumped"] = True
                else:
                    was_climbing = self.on_ladder
                    self.vel_y = self.jump_power
                    self.on_ground = False
                    self.on_ladder = False
                    self.active_ladder = None
                    if was_climbing:
                        self.ladder_cooldown = 14
                    self.coyote_timer = 0
                    self.jump_buffer_timer = 0
                    events["jumped"] = True

        # Shorten the jump when the button is released.
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        if not jump_held and self.vel_y < -4.5 and not self.on_ladder:
            self.vel_y *= 0.62

        # Apply ladder movement or gravity.
        if self.on_ladder:
            if move_up and not move_down:
                self.vel_y = -self.climb_speed
            elif move_down and not move_up:
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

        # Clean top/bottom emergence when climbing a ladder
        if self.on_ladder and self.active_ladder is not None:
            if self.vel_y < 0 and self.rect.bottom <= self.active_ladder.top:
                self.rect.bottom = self.active_ladder.top
                self.vel_y = 0.0
                self.on_ladder = False
                self.active_ladder = None
                self.on_ground = True
            elif self.vel_y > 0 and self.rect.bottom >= self.active_ladder.bottom:
                self.rect.bottom = self.active_ladder.bottom
                self.vel_y = 0.0
                self.on_ladder = False
                self.active_ladder = None
                self.on_ground = True

        for tile in solid_rects:
            if self.rect.colliderect(tile):
                if self.vel_y >= 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0.0
                    self.on_ground = True
                    self.on_ladder = False
                    self.active_ladder = None
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0.0

        # Handle one-way platforms.
        if self.vel_y >= 0 and not self.on_ladder:
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

    def _update_animation(self):
        # Pick the animation that matches what the knight is doing.
        previous = self.animator.get_name()
        if self.attacking:
            # trigger_attack() already started the right swing animation.
            name = previous
        elif self.on_ladder:
            name = "climb"
        elif not self.on_ground:
            if self.vel_y < 0:
                name = "jump"
            else:
                name = "fall"
        elif abs(self.vel_x) > 0.6:
            name = "run"
        elif previous == "jump" or previous == "fall":
            # Just touched the ground: show the landing pose once.
            name = "land"
        elif previous == "land" and not self.animator.is_finished():
            name = "land"
        else:
            name = "idle"

        self.animator.play(name)

        # On a ladder the knight only moves while he is climbing.
        if name == "climb" and abs(self.vel_y) < 0.1:
            return
        self.animator.update()

    def draw(self, surface, camera_x, camera_y=0):
        # Blink while invulnerable.
        if self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 1:
            return

        frame = self.animator.get_frame(self.facing_right)
        # In every frame the head is in the middle and the feet are
        # FEET_PADDING pixels above the bottom (see load_knight_frame).
        x = self.rect.centerx - frame.get_width() // 2 - camera_x
        y = self.rect.bottom + FEET_PADDING - frame.get_height() + 2 - camera_y
        surface.blit(frame, (x, y))


def find_head(image):
    # The red plume and scarf show where the knight's head is.
    # Returns the middle of the red pixels (x) and the top of the plume (y).
    red = pygame.mask.from_threshold(image, (190, 40, 45, 255), (60, 45, 45, 255))
    if red.count() == 0:
        return image.get_width() // 2, 0
    head_x = red.centroid()[0]
    head_top = min(rect.top for rect in red.get_bounding_rects())
    return head_x, head_top


def load_knight_frame(sliced_dir, name):
    path = os.path.join(sliced_dir, "knight", name + ".png")
    image = pygame.image.load(path).convert_alpha()
    head_x, head_top = find_head(image)

    # Scale every frame by the same factor, so the knight keeps his size.
    if name in BASE_SHEET_FRAMES:
        scale = BODY_HEIGHT / BASE_SHEET_BODY
    else:
        scale = BODY_HEIGHT / KNIGHT_SHEET_BODY
    width = round(image.get_width() * scale)
    height = round(image.get_height() * scale)
    image = pygame.transform.smoothscale(image, (width, height))
    head_x = round(head_x * scale)
    head_top = round(head_top * scale)

    # Put the frame on a canvas where the head is always in the middle and
    # the feet are always FEET_PADDING pixels above the bottom. Then the
    # knight does not jump around when the animation changes frames.
    half_width = max(head_x, width - head_x)
    canvas_height = head_top + BODY_HEIGHT + FEET_PADDING
    canvas = pygame.Surface((half_width * 2, canvas_height), pygame.SRCALPHA)
    canvas.blit(image, (half_width - head_x, 0))
    return canvas


def load_player_sprites(sliced_dir="assets/sliced"):
    # Which sliced images belong to which animation, in playing order.
    # Swings go attack_1 -> attack_2 -> attack_0 (see trigger_attack).
    animation_frames = {
        "idle": ["idle_1", "idle_2"],
        "run": ["run_1", "run_2"],
        "climb": ["run_1", "run_2"],  # the sprite sheets have no climbing pose
        "jump": ["jump_start"],
        "fall": ["jump_start"],
        "land": ["jump_land"],
        "attack_1": ["combo_1", "combo_2", "combo_3", "combo_recover"],
        "attack_2": ["chop_raise", "chop_strike", "chop_extend", "chop_recover"],
        "attack_0": ["heavy_raise", "heavy_crescent", "heavy_recover"],
        "air_attack": ["jump_peak", "jump_slash"],
    }

    loaded = {}  # load every image only once, even if two animations use it
    sprites = {}
    for animation_name, frame_names in animation_frames.items():
        sprites[animation_name] = []
        for frame_name in frame_names:
            if frame_name not in loaded:
                loaded[frame_name] = load_knight_frame(sliced_dir, frame_name)
            sprites[animation_name].append(loaded[frame_name])
    return sprites


if __name__ == "__main__":
    from main import run_game

    run_game()
