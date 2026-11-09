"""Start the game and run its main loop."""

import argparse
import os
import sys
import pygame

from slice_assets import slice_all_assets
from player import FEET_PADDING, Player, load_player_sprites
from level import AssetLibrary, Collectible, Level, VFXParticle
from ui import MenuCharacter, create_menus, load_icons
from story import create_stories
from highscores import add_highscore, best_score_text, highscore_lines, load_highscores
from joystick import MODE_AUTO, MODES, Gamepad, configure_sdl_hints
from titlebar import BAR_HEIGHT, TitleBar, shift_mouse_event
import sounds

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
WINDOW_TITLE = "Knight's Quest - The Stolen Crown"


def draw_hud(
    surface: pygame.Surface,
    player: Player,
    level: Level,
    assets: AssetLibrary,
    font_sm: pygame.font.Font,
    font_md: pygame.font.Font,
    font_lg: pygame.font.Font,
    gamepad: Gamepad | None = None,
) -> None:
    """Draw the HUD."""
    # HUD background.
    hud_bar = pygame.Surface((SCREEN_WIDTH, 58), pygame.SRCALPHA)
    hud_bar.fill((18, 22, 32, 205))
    surface.blit(hud_bar, (0, 0))
    pygame.draw.line(surface, (75, 90, 120), (0, 58), (SCREEN_WIDTH, 58), 2)

    # Hearts.
    for i in range(3):
        hx = 20 + i * 38
        hy = 14
        heart_hp = player.hp - i * 2
        if heart_hp >= 2:
            surface.blit(assets.ui["heart_full"], (hx, hy))
        elif heart_hp == 1:
            surface.blit(assets.ui["heart_half"], (hx, hy))
        else:
            surface.blit(assets.ui["heart_empty"], (hx, hy))

    # Lives.
    lives_txt = font_sm.render(f"x{player.lives}", True, (240, 240, 255))
    surface.blit(lives_txt, (138, 20))

    # Coins and gems.
    surface.blit(assets.ui["coin_icon"], (195, 14))
    coin_txt = font_md.render(f"{player.coins:02d}", True, (255, 220, 75))
    surface.blit(coin_txt, (226, 16))

    surface.blit(assets.ui["gem_icon"], (285, 13))
    gem_txt = font_md.render(f"{player.gems:02d}", True, (110, 215, 255))
    surface.blit(gem_txt, (316, 16))

    # Key status.
    key_box = pygame.Rect(380, 9, 175, 40)
    if player.has_key:
        pygame.draw.rect(surface, (55, 85, 45), key_box, border_radius=8)
        pygame.draw.rect(surface, (255, 215, 70), key_box, 2, border_radius=8)
        surface.blit(assets.ui["key_icon"], (388, 13))
        k_txt = font_sm.render("KEY READY!", True, (255, 235, 110))
        surface.blit(k_txt, (426, 20))
    else:
        pygame.draw.rect(surface, (38, 42, 56), key_box, border_radius=8)
        pygame.draw.rect(surface, (90, 100, 125), key_box, 1, border_radius=8)
        k_txt = font_sm.render("FIND GOLD KEY", True, (170, 180, 205))
        surface.blit(k_txt, (402, 20))

    # Level and score.
    lvl_txt = font_md.render(level.level_name, True, (235, 242, 255))
    surface.blit(lvl_txt, (585, 16))

    score_txt = font_md.render(f"SCORE: {player.score:05d}", True, (255, 240, 150))
    surface.blit(score_txt, (SCREEN_WIDTH - 210, 16))

    # Controls.
    if gamepad is not None and gamepad.is_connected():
        controls_hint = (
            "Move: Stick/D-Pad or A/D | Jump: (A)/Space | Climb: Up/Down | "
            "Attack: (X)/(B)/RB/RT | Restart: Back/R | Pause: Start/Esc"
        )
    else:
        controls_hint = (
            "Move: A/D or Arrows | Jump: Space/W | Climb: W/S | "
            "Attack: J/Z/Click | Restart: R | Pause: Esc/P"
        )
    ctrl_txt = font_sm.render(
        controls_hint,
        True,
        (215, 225, 240),
    )
    ctrl_bg = pygame.Surface((ctrl_txt.get_width() + 16, 26), pygame.SRCALPHA)
    ctrl_bg.fill((15, 18, 26, 165))
    surface.blit(ctrl_bg, (10, SCREEN_HEIGHT - 32))
    surface.blit(ctrl_txt, (18, SCREEN_HEIGHT - 27))

    # Banner notification.
    if level.banner_timer > 0 and level.banner_message:
        b_txt = font_md.render(level.banner_message, True, (255, 235, 120))
        bw = max(560, b_txt.get_width() + 48)
        bh = 42
        bx = (SCREEN_WIDTH - bw) // 2
        by = 72
        banner_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        banner_surf.fill((22, 28, 45, 225))
        surface.blit(banner_surf, (bx, by))
        pygame.draw.rect(surface, (255, 210, 75), (bx, by, bw, bh), 2, border_radius=6)
        surface.blit(b_txt, (bx + (bw - b_txt.get_width()) // 2, by + 9))


def handle_level_interactions(
    player: Player,
    level: Level,
    assets: AssetLibrary,
) -> str | None:
    """Handle interactions and return ``"next_level"`` when the exit is reached."""
    if level.banner_timer > 0:
        level.banner_timer -= 1

    attack_rect = player.get_attack_rect()

    # Sword interactions.
    if attack_rect:
        # Break destructibles.
        remaining_destructibles = []
        for d in level.destructibles:
            if attack_rect.colliderect(d["rect"]):
                cx, cy = d["rect"].center
                level.particles.append(VFXParticle(cx, cy, image=assets.vfx["dust_2"], duration=18))
                level.particles.append(VFXParticle(cx, cy, image=assets.vfx["hit_burst"], duration=14))
                drop_kind = d.get("drop", "coin")
                level.collectibles.append(
                    Collectible(d["rect"].x + 8, d["rect"].y + 10, drop_kind, assets.items[drop_kind])
                )
                player.score += 50
            else:
                remaining_destructibles.append(d)
        level.destructibles = remaining_destructibles

        # Open chests.
        for idx, ch in enumerate(level.chests):
            if not ch["open"] and attack_rect.colliderect(ch["rect"]):
                ch["open"] = True
                sounds.play("pickup")
                cx, cy = ch["rect"].center
                player.score += 300
                player.coins += 3
                player.gems += 1
                level.particles.append(VFXParticle(cx, cy - 10, image=assets.vfx["star_hit"], duration=20))
                level.particles.append(
                    VFXParticle(cx - 24, cy - 32, text="+300 CHEST!", color=(255, 225, 80), duration=38)
                )

        # Pull levers.
        for lv in level.levers:
            if not lv["active"] and attack_rect.colliderect(lv["rect"]):
                lv["active"] = True
                lx, ly = lv["rect"].center
                level.particles.append(VFXParticle(lx, ly, image=assets.vfx["star_hit"], duration=20))
                level.banner_message = "LEVER PULLED! Bonus Blue Gems appeared nearby!"
                level.banner_timer = 150
                for i in range(3):
                    level.collectibles.append(
                        Collectible(lx + 50 + i * 48, ly - 20, "gem", assets.items["gem"])
                    )

    # Chests and levers can also be activated by touch.
    for ch in level.chests:
        if not ch["open"] and player.rect.colliderect(ch["rect"]):
            ch["open"] = True
            sounds.play("pickup")
            cx, cy = ch["rect"].center
            player.score += 300
            player.coins += 3
            player.gems += 1
            level.particles.append(VFXParticle(cx, cy - 10, image=assets.vfx["star_hit"], duration=20))
            level.particles.append(
                VFXParticle(cx - 24, cy - 32, text="+300 CHEST!", color=(255, 225, 80), duration=38)
            )

    # Collectibles.
    for item in level.collectibles:
        if item.collected:
            continue
        item.update()
        if player.rect.colliderect(item.rect):
            item.collected = True
            ix, iy = item.rect.center
            if item.kind == "coin":
                sounds.play("coin")
                player.coins += 1
                player.score += 100
                level.particles.append(VFXParticle(ix, iy, image=assets.vfx["star_hit"], duration=14))
                level.particles.append(VFXParticle(ix - 12, iy - 16, text="+100", duration=24))
            elif item.kind == "gem":
                sounds.play("gem")
                player.gems += 1
                player.score += 250
                level.particles.append(VFXParticle(ix, iy, image=assets.vfx["star_hit"], duration=18))
                level.particles.append(
                    VFXParticle(ix - 14, iy - 16, text="+250", color=(110, 225, 255), duration=28)
                )
            elif item.kind == "potion":
                sounds.play("pickup")
                player.heal(2)
                player.score += 150
                level.particles.append(
                    VFXParticle(ix - 18, iy - 16, text="+HEART", color=(255, 110, 120), duration=28)
                )
            elif item.kind == "key":
                sounds.play("pickup")
                player.has_key = True
                player.score += 500
                level.particles.append(VFXParticle(ix, iy, image=assets.vfx["hit_burst"], duration=24))
                level.particles.append(
                    VFXParticle(ix - 24, iy - 24, text="KEY GOT!", color=(255, 235, 90), duration=40)
                )
                level.banner_message = "KEY COLLECTED! Go through the Locked Door to the Cave Exit!"
                level.banner_timer = 210

    # Locked door.
    if level.locked_door and not level.locked_door["open"]:
        drect = level.locked_door["rect"]
        # Include the front edge of the door.
        trigger_zone = drect.inflate(24, 12)
        if player.rect.colliderect(trigger_zone) or (attack_rect and attack_rect.colliderect(trigger_zone)):
            if player.has_key:
                level.locked_door["open"] = True
                level.particles.append(
                    VFXParticle(drect.centerx, drect.centery, image=assets.vfx["smoke_puff"], duration=25)
                )
                level.banner_message = "DOOR UNLOCKED! Enter the Cave Exit!"
                level.banner_timer = 150
            else:
                level.banner_message = "DOOR LOCKED! Climb the tower to find the Gold Key!"
                level.banner_timer = 60

    # Spikes.
    for s_rect in level.spike_rects:
        if player.rect.colliderect(s_rect):
            if player.take_damage(1, knockback_dir=-1 if player.facing_right else 1):
                level.particles.append(
                    VFXParticle(player.rect.centerx, player.rect.centery, image=assets.vfx["hit_burst"], duration=16)
                )

    # Enemies and combat.
    for idx, enemy in enumerate(level.enemies):
        enemy.update(player.rect, level.projectiles)
        if enemy.dead:
            continue

        # Check sword hits.
        if attack_rect and attack_rect.colliderect(enemy.rect) and idx not in player.hit_targets_this_swing:
            player.hit_targets_this_swing.add(idx)
            defeated = enemy.take_hit(1)
            ex, ey = enemy.rect.center
            level.particles.append(VFXParticle(ex, ey, image=assets.vfx["hit_burst"], duration=15))
            if defeated:
                player.score += enemy.score_value
                level.particles.append(VFXParticle(ex, ey, image=assets.vfx["smoke_puff"], duration=22))
                level.particles.append(
                    VFXParticle(ex - 16, ey - 24, text=f"+{enemy.score_value}", duration=30)
                )
            continue

        # Check stomps and contact damage.
        stomped = False
        if player.rect.colliderect(enemy.rect):
            is_stomp = player.vel_y > 0 and (player.rect.bottom - player.vel_y) <= enemy.rect.top + 22
            if is_stomp:
                stomped = True
                player.vel_y = -10.8
                player.on_ground = False
                defeated = enemy.take_hit(1)
                ex, ey = enemy.rect.center
                level.particles.append(VFXParticle(ex, enemy.rect.top, image=assets.vfx["star_hit"], duration=16))
                if defeated:
                    player.score += enemy.score_value
                    level.particles.append(
                        VFXParticle(ex - 16, ey - 24, text=f"+{enemy.score_value}", duration=30)
                    )
            else:
                kb = -1 if player.rect.centerx < enemy.rect.centerx else 1
                if player.take_damage(1, knockback_dir=kb):
                    level.particles.append(
                        VFXParticle(
                            player.rect.centerx,
                            player.rect.centery,
                            image=assets.vfx["hit_burst"],
                            duration=16,
                        )
                    )

        # Check enemy weapon swings (they reach further than the enemy's body).
        weapon_rect = enemy.get_attack_rect()
        if weapon_rect and not stomped and player.rect.colliderect(weapon_rect):
            kb = -1 if player.rect.centerx < enemy.rect.centerx else 1
            if player.take_damage(enemy.attack_damage, knockback_dir=kb):
                level.particles.append(
                    VFXParticle(
                        player.rect.centerx,
                        player.rect.centery,
                        image=assets.vfx["hit_burst"],
                        duration=16,
                    )
                )

    # Projectiles.
    active_solids = level.get_active_solid_rects()
    remaining_proj = []
    for proj in level.projectiles:
        proj.update(active_solids)
        if not proj.alive:
            continue
        if attack_rect and attack_rect.colliderect(proj.rect):
            level.particles.append(
                VFXParticle(proj.rect.centerx, proj.rect.centery, image=assets.vfx["fire_spark"], duration=14)
            )
            continue
        if player.rect.colliderect(proj.rect):
            kb = 1 if proj.direction > 0 else -1
            if player.take_damage(1, knockback_dir=kb):
                level.particles.append(
                    VFXParticle(
                        player.rect.centerx, player.rect.centery, image=assets.vfx["hit_burst"], duration=16
                    )
                )
            continue
        remaining_proj.append(proj)
    level.projectiles = remaining_proj

    # Visual effects.
    level.particles = [p for p in level.particles if p.update()]

    # Pitfall.
    if player.rect.top > level.height + 80:
        player.dead = True

    # Cave exit.
    if player.rect.colliderect(level.cave_exit_rect):
        return "next_level"

    return None


def new_game(assets: AssetLibrary, player_sprites) -> tuple[Level, Player]:
    """Start a fresh game in level 1 with full lives and no score."""
    level = Level(1, assets)
    player = Player(level.spawn_pos[0], level.spawn_pos[1], player_sprites)
    return level, player


def get_stats(player: Player) -> tuple[int, int, int]:
    """Score, coins and gems of the player as one tuple."""
    return (player.score, player.coins, player.gems)


def set_stats(player: Player, stats: tuple[int, int, int]) -> None:
    """Put back score, coins and gems that were saved with get_stats()."""
    player.score, player.coins, player.gems = stats


def show_results(menu, player: Player, level_num: int, highscore_path: str, save: bool = True) -> None:
    """Save the finished game as a highscore and show the results in the menu."""
    if save:
        new_place = add_highscore(highscore_path, player.score, level_num)
        note = "TOP 5 HIGHSCORES"
    else:
        # Runs where levels were skipped with 1/2 do not count.
        new_place = None
        note = "Level skip (1/2) used - score not saved"
    menu.lines = [
        f"Score: {player.score}   |   Coins: {player.coins}   |   Gems: {player.gems}",
        "",
        note,
    ] + highscore_lines(load_highscores(highscore_path), new_place)


def load_level(level_num: int, assets: AssetLibrary, player: Player) -> Level:
    """Build a level and put the player at its start. Score and lives are kept."""
    level = Level(level_num, assets)
    player.has_key = False
    player.respawn(*level.spawn_pos)
    return level


def run_game(max_frames: int | None = None, controller_mode: str = MODE_AUTO) -> None:
    """Initializes Pygame, slices sprite sheets if needed, and runs the main game loop."""
    configure_sdl_hints(controller_mode)
    pygame.init()
    window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT + BAR_HEIGHT), pygame.NOFRAME | pygame.SCALED)
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    titlebar = TitleBar(SCREEN_WIDTH, WINDOW_TITLE)
    sounds.init()
    clock = pygame.time.Clock()
    gamepad = Gamepad(mode=controller_mode)

    # Slice sprite sheets when needed.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    sliced_dir = slice_all_assets(assets_dir, force=False)
    highscore_path = os.path.join(base_dir, "highscores.txt")

    # Load fonts.
    font_sm = pygame.font.SysFont("dejavusans,arial,sans-serif", 15, bold=True)
    font_md = pygame.font.SysFont("dejavusans,arial,sans-serif", 20, bold=True)
    font_lg = pygame.font.SysFont("dejavusans,arial,sans-serif", 42, bold=True)

    # Load sprites.
    assets = AssetLibrary(sliced_dir)
    player_sprites = load_player_sprites(sliced_dir)

    current_level_num = 1
    level, player = new_game(assets, player_sprites)

    # Level 1 slowly scrolls by behind the main menu.
    menu_level = Level(1, assets)
    menu_camera_x = 0.0

    icons = load_icons(assets)
    menus = create_menus((SCREEN_WIDTH, SCREEN_HEIGHT), icons)

    # Story scenes: before level 1, before level 2 and after the last level.
    stories = create_stories(assets, player_sprites, (SCREEN_WIDTH, SCREEN_HEIGHT), FEET_PADDING, icons["key"])
    current_story = stories["intro"]
    story_next_state = "playing"  # state after the story is finished

    # The knight and a slime stand left and right of the main menu buttons.
    menu_knight = MenuCharacter(player_sprites["idle"], 20, 2, FEET_PADDING)
    menu_slime = MenuCharacter(assets.enemies["slime"], 18, 2)
    main_panel = menus["menu"].panel
    menu_feet_y = menus["menu"].buttons[-1].rect.bottom
    camera_x = 0.0
    # Game states: menu, story, playing, paused, controls, game_over, victory.
    game_state = "menu"
    controls_return_state = "menu"  # where "Back" in the controls screen goes
    frame_count = 0
    # Score, coins and gems when the current level started. Restarting the
    # level sets them back, so the same coins cannot be collected twice.
    level_start_stats = (0, 0, 0)
    level_skip_used = False  # True after 1/2 was pressed; then no highscore

    def refresh_controls_menu() -> None:
        menus["controls"].lines[-2] = gamepad.status_line()
        menus["controls"].lines[-1] = gamepad.mode_line()
        menus["controls"].buttons[0].text = gamepad.mode_button_text()

    def open_menu(name: str) -> str:
        menus[name].reset()
        if name == "menu":
            # Second line of the main menu shows the best score so far.
            menus["menu"].lines[1] = best_score_text(highscore_path)
        elif name == "controls":
            refresh_controls_menu()
        return name

    def apply_menu_action(action: str | None) -> bool:
        """Execute a menu button action. Returns True if game_state changed."""
        nonlocal current_level_num, level, player, level_start_stats, level_skip_used
        nonlocal camera_x, current_story, story_next_state, game_state
        nonlocal controls_return_state, running
        if action is None:
            return False
        if action == "start":
            current_level_num = 1
            level, player = new_game(assets, player_sprites)
            level_start_stats = (0, 0, 0)
            level_skip_used = False
            camera_x = 0.0
            # Show the intro story first, then start playing.
            current_story = stories["intro"]
            current_story.reset()
            story_next_state = "playing"
            game_state = "story"
            return True
        if action == "resume":
            game_state = "playing"
            return True
        if action == "restart_level":
            level = load_level(current_level_num, assets, player)
            set_stats(player, level_start_stats)
            game_state = "playing"
            return True
        if action == "controls":
            controls_return_state = game_state
            game_state = open_menu("controls")
            return True
        if action == "cycle_input_mode":
            gamepad.cycle_mode()
            refresh_controls_menu()
            return False
        if action == "back":
            game_state = open_menu(controls_return_state)
            return True
        if action == "main_menu":
            game_state = open_menu("menu")
            return True
        if action == "quit":
            running = False
            return True
        return False

    game_state = open_menu("menu")

    step_timer = 0
    running = True
    while running:
        state_changed_by_event = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if titlebar.handle_event(event):
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                try:
                    pygame.display.toggle_fullscreen()
                except pygame.error:
                    pass
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                sounds.toggle_mute()
                continue
            shift_mouse_event(event)

            if gamepad.handle_event(event):
                if game_state == "controls":
                    refresh_controls_menu()
                continue

            if game_state == "story":
                if current_story.handle_event(event) == "done":
                    if story_next_state == "playing":
                        game_state = "playing"
                    else:
                        game_state = open_menu(story_next_state)
                    state_changed_by_event = True
                continue

            if game_state != "playing":
                # Menus get all input while they are open.
                action = menus[game_state].handle_event(event)
                if apply_menu_action(action):
                    state_changed_by_event = True
                continue

            # Gameplay input.
            if event.type == pygame.WINDOWFOCUSLOST:
                # Pause automatically when the player switches to another window.
                game_state = open_menu("paused")
                state_changed_by_event = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    game_state = open_menu("paused")
                    state_changed_by_event = True
                elif event.key == pygame.K_SPACE:
                    player.trigger_jump()
                elif event.key in (pygame.K_w, pygame.K_UP):
                    if not player.on_ladder and player.find_climbable_ladder_up(level.ladder_rects) is None:
                        player.trigger_jump()
                elif event.key in (pygame.K_j, pygame.K_z, pygame.K_x, pygame.K_f, pygame.K_k):
                    player.trigger_attack()
                elif event.key in (pygame.K_r, pygame.K_RETURN):
                    level = load_level(current_level_num, assets, player)
                    set_stats(player, level_start_stats)
                elif event.key in (pygame.K_1, pygame.K_2):
                    # Jump to a level (for testing). This run will not be saved as a highscore.
                    current_level_num = 1 if event.key == pygame.K_1 else 2
                    level = load_level(current_level_num, assets, player)
                    level_start_stats = get_stats(player)
                    level_skip_used = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                player.trigger_attack()

        # Poll controller state once per frame and dispatch discrete actions.
        gamepad.update()
        if running and not state_changed_by_event:
            if game_state == "story":
                if current_story.handle_gamepad(gamepad) == "done":
                    if story_next_state == "playing":
                        game_state = "playing"
                    else:
                        game_state = open_menu(story_next_state)
            elif game_state != "playing":
                apply_menu_action(menus[game_state].handle_gamepad(gamepad))
            else:
                if gamepad.pause:
                    game_state = open_menu("paused")
                else:
                    if gamepad.jump:
                        player.trigger_jump()
                    if gamepad.attack:
                        player.trigger_attack()
                    if gamepad.restart:
                        level = load_level(current_level_num, assets, player)
                        set_stats(player, level_start_stats)

        if game_state == "playing":
            keys = pygame.key.get_pressed()
            move_events = player.update(
                keys,
                level.get_active_solid_rects(),
                level.one_way_rects,
                level.ladder_rects,
                level.slope_tiles,
                level.width,
                gamepad=gamepad,
            )
            walking = player.on_ground and not player.on_ladder and abs(player.vel_x) > 1.5
            step_timer = step_timer - 1 if walking else 0
            if walking and step_timer <= 0:
                sounds.play("step")
                step_timer = 16

            if move_events["jumped"]:
                sounds.play("jump")
                level.particles.append(
                    VFXParticle(
                        player.rect.centerx,
                        player.rect.bottom - 6,
                        image=assets.vfx["dust_1"],
                        duration=14,
                    )
                )
            elif move_events["landed"]:
                level.particles.append(
                    VFXParticle(
                        player.rect.centerx,
                        player.rect.bottom - 6,
                        image=assets.vfx["dust_2"],
                        duration=14,
                    )
                )

            status = handle_level_interactions(player, level, assets)
            if status == "next_level":
                player.score += 1000
                if current_level_num == 1:
                    current_level_num = 2
                    level = load_level(2, assets, player)
                    level_start_stats = get_stats(player)
                    camera_x = 0.0
                    current_story = stories["level_2"]
                    current_story.reset()
                    story_next_state = "playing"
                    game_state = "story"
                else:
                    sounds.play("victory")
                    show_results(menus["victory"], player, current_level_num, highscore_path,
                                 save=not level_skip_used)
                    # Show the ending story first, then the victory screen.
                    current_story = stories["ending"]
                    current_story.reset()
                    story_next_state = "victory"
                    game_state = "story"

            if player.dead:
                player.lives -= 1
                if player.lives > 0:
                    player.respawn(*level.spawn_pos)
                    level.banner_message = f"TRY AGAIN! {player.lives} Lives Remaining"
                    level.banner_timer = 120
                else:
                    game_state = open_menu("game_over")
                    show_results(menus["game_over"], player, current_level_num, highscore_path,
                                 save=not level_skip_used)

            # Smoothly follow the player.
            target_cam_x = player.rect.centerx - SCREEN_WIDTH * 0.38
            target_cam_x = max(0.0, min(float(level.width - SCREEN_WIDTH), target_cam_x))
            camera_x += (target_cam_x - camera_x) * 0.14

        # Render.
        show_menu_background = game_state == "menu" or (
            game_state == "controls" and controls_return_state == "menu"
        )
        if game_state == "story":
            current_story.draw(screen, font_sm, font_md, font_lg)
        elif show_menu_background:
            # Scroll through level 1 and start again at the end.
            menu_camera_x = (menu_camera_x + 0.8) % (menu_level.width - SCREEN_WIDTH)
            menu_level.draw(screen, int(menu_camera_x), font_sm)
        else:
            cam_int = int(round(camera_x))
            level.draw(screen, cam_int, font_sm)
            player.draw(screen, cam_int)
            for p in level.particles:
                p.draw(screen, cam_int, font_sm)
            draw_hud(screen, player, level, assets, font_sm, font_md, font_lg, gamepad=gamepad)

        if game_state not in ("playing", "story"):
            menu = menus[game_state]
            menu.draw(screen, font_sm, font_md)
            if game_state == "menu":
                menu_knight.draw(screen, (main_panel.left + 85, menu_feet_y))
                menu_slime.draw(screen, (main_panel.right - 85, menu_feet_y))

        sounds.set_music(game_state == "menu" or (game_state == "story" and story_next_state == "playing"))

        window.blit(screen, (0, BAR_HEIGHT))
        titlebar.draw(window, font_sm)
        pygame.display.flip()
        clock.tick(FPS)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    gamepad.quit()
    pygame.quit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Knight's Quest - The Stolen Crown")
    parser.add_argument(
        "--controller-mode",
        choices=MODES,
        default=MODE_AUTO,
        help="Controller input backend/mapping mode (default: auto accepts both XInput and DirectInput).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    run_game(controller_mode=args.controller_mode)
