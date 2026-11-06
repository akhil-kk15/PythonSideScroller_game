"""Start the game and run its main loop."""

import os
import sys
import pygame

from slice_assets import slice_all_assets
from player import Player, load_player_sprites
from level import AssetLibrary, Collectible, Level, VFXParticle

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60


def draw_hud(
    surface: pygame.Surface,
    player: Player,
    level: Level,
    assets: AssetLibrary,
    font_sm: pygame.font.Font,
    font_md: pygame.font.Font,
    font_lg: pygame.font.Font,
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
    ctrl_bg = pygame.Surface((650, 26), pygame.SRCALPHA)
    ctrl_bg.fill((15, 18, 26, 165))
    surface.blit(ctrl_bg, (10, SCREEN_HEIGHT - 32))
    ctrl_txt = font_sm.render(
        "Move: A/D or Arrows | Jump: Space/W | Climb: W/S | Attack: J/Z/Click | Level: 1/2 | Restart: R",
        True,
        (215, 225, 240),
    )
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


def draw_overlay_screen(
    surface: pygame.Surface,
    title: str,
    subtitle: str,
    player: Player,
    title_color: tuple[int, int, int],
    font_md: pygame.font.Font,
    font_lg: pygame.font.Font,
) -> None:
    """Draw the game-over or victory screen."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((12, 15, 24, 195))
    surface.blit(overlay, (0, 0))

    card = pygame.Rect((SCREEN_WIDTH - 540) // 2, (SCREEN_HEIGHT - 280) // 2, 540, 280)
    pygame.draw.rect(surface, (28, 34, 52), card, border_radius=14)
    pygame.draw.rect(surface, title_color, card, 3, border_radius=14)

    t_surf = font_lg.render(title, True, title_color)
    surface.blit(t_surf, (card.centerx - t_surf.get_width() // 2, card.top + 36))

    stats_str = f"Final Score: {player.score}   |   Coins: {player.coins}   |   Gems: {player.gems}"
    st_surf = font_md.render(stats_str, True, (235, 242, 255))
    surface.blit(st_surf, (card.centerx - st_surf.get_width() // 2, card.top + 115))

    sub_surf = font_md.render(subtitle, True, (255, 225, 115))
    surface.blit(sub_surf, (card.centerx - sub_surf.get_width() // 2, card.top + 185))


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
                player.coins += 1
                player.score += 100
                level.particles.append(VFXParticle(ix, iy, image=assets.vfx["star_hit"], duration=14))
                level.particles.append(VFXParticle(ix - 12, iy - 16, text="+100", duration=24))
            elif item.kind == "gem":
                player.gems += 1
                player.score += 250
                level.particles.append(VFXParticle(ix, iy, image=assets.vfx["star_hit"], duration=18))
                level.particles.append(
                    VFXParticle(ix - 14, iy - 16, text="+250", color=(110, 225, 255), duration=28)
                )
            elif item.kind == "potion":
                player.heal(2)
                player.score += 150
                level.particles.append(
                    VFXParticle(ix - 18, iy - 16, text="+HEART", color=(255, 110, 120), duration=28)
                )
            elif item.kind == "key":
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
        if player.rect.colliderect(enemy.rect):
            is_stomp = player.vel_y > 0 and (player.rect.bottom - player.vel_y) <= enemy.rect.top + 22
            if is_stomp:
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


def run_game(max_frames: int | None = None) -> None:
    """Initializes Pygame, slices sprite sheets if needed, and runs the main game loop."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Knight's Quest - Side-Scroller (Dangerous Dave / Mario Style)")
    clock = pygame.time.Clock()

    # Slice sprite sheets when needed.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    sliced_dir = slice_all_assets(assets_dir, force=False)

    # Load fonts.
    font_sm = pygame.font.SysFont("dejavusans,arial,sans-serif", 15, bold=True)
    font_md = pygame.font.SysFont("dejavusans,arial,sans-serif", 20, bold=True)
    font_lg = pygame.font.SysFont("dejavusans,arial,sans-serif", 42, bold=True)

    # Load sprites.
    assets = AssetLibrary(sliced_dir)
    player_sprites = load_player_sprites(sliced_dir)

    current_level_num = 1
    level = Level(current_level_num, assets)
    player = Player(level.spawn_pos[0], level.spawn_pos[1], player_sprites)

    camera_x = 0.0
    game_state = "playing"  # playing, game_over, or victory.
    frame_count = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if game_state == "playing":
                        player.trigger_jump()
                elif event.key in (pygame.K_j, pygame.K_z, pygame.K_x, pygame.K_f, pygame.K_k):
                    if game_state == "playing":
                        player.trigger_attack()
                elif event.key in (pygame.K_r, pygame.K_RETURN):
                    if game_state in ("game_over", "victory"):
                        current_level_num = 1
                        level = Level(current_level_num, assets)
                        player = Player(level.spawn_pos[0], level.spawn_pos[1], player_sprites)
                        game_state = "playing"
                    else:
                        level = Level(current_level_num, assets)
                        player.has_key = False
                        player.respawn(*level.spawn_pos)
                elif event.key == pygame.K_1:
                    current_level_num = 1
                    level = Level(1, assets)
                    player.has_key = False
                    player.respawn(*level.spawn_pos)
                    game_state = "playing"
                elif event.key == pygame.K_2:
                    current_level_num = 2
                    level = Level(2, assets)
                    player.has_key = False
                    player.respawn(*level.spawn_pos)
                    game_state = "playing"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == "playing":
                    player.trigger_attack()

        if game_state == "playing":
            keys = pygame.key.get_pressed()
            move_events = player.update(
                keys,
                level.get_active_solid_rects(),
                level.one_way_rects,
                level.ladder_rects,
                level.slope_tiles,
                level.width,
            )
            if move_events["jumped"]:
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
                    level = Level(2, assets)
                    player.has_key = False
                    player.respawn(*level.spawn_pos)
                    camera_x = 0.0
                else:
                    game_state = "victory"

            if player.dead:
                player.lives -= 1
                if player.lives > 0:
                    player.respawn(*level.spawn_pos)
                    level.banner_message = f"TRY AGAIN! {player.lives} Lives Remaining"
                    level.banner_timer = 120
                else:
                    game_state = "game_over"

            # Smoothly follow the player.
            target_cam_x = player.rect.centerx - SCREEN_WIDTH * 0.38
            target_cam_x = max(0.0, min(float(level.width - SCREEN_WIDTH), target_cam_x))
            camera_x += (target_cam_x - camera_x) * 0.14

        # Render.
        cam_int = int(round(camera_x))
        level.draw(screen, cam_int, font_sm)
        player.draw(screen, cam_int)
        for p in level.particles:
            p.draw(screen, cam_int, font_sm)

        draw_hud(screen, player, level, assets, font_sm, font_md, font_lg)

        if game_state == "game_over":
            draw_overlay_screen(
                screen,
                "GAME OVER",
                "Press ENTER or R to Play Again",
                player,
                (245, 85, 85),
                font_md,
                font_lg,
            )
        elif game_state == "victory":
            draw_overlay_screen(
                screen,
                "VICTORY! QUEST COMPLETE!",
                "Press ENTER or R to Play Again",
                player,
                (255, 215, 75),
                font_md,
                font_lg,
            )

        pygame.display.flip()
        clock.tick(FPS)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    run_game()
