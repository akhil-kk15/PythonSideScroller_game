# Story scenes of the game "The Stolen Crown".
#
# A story scene is made of pages. Every page shows a background, a few
# animated figures (knight, goblins, items) standing on a strip of grass,
# and some lines of text in a panel at the bottom.
#
# FloatingFigure -> a MenuCharacter that moves up and down (for items like the key)
# StoryPage      -> one picture with text
# StoryScreen    -> a list of pages; Enter/Click goes to the next page, Esc skips all

import math
import pygame

from ui import Button, MenuCharacter, draw_text_with_shadow, PANEL_COLOR, HIGHLIGHT_COLOR, TEXT_COLOR, HINT_COLOR

GROUND_Y = 470  # y of the grass where the figures stand


class FloatingFigure(MenuCharacter):
    # Works like a MenuCharacter, but slowly floats up and down.
    # It inherits everything and only overrides draw().

    def draw(self, surface, feet_position):
        x, y = feet_position
        offset = math.sin(pygame.time.get_ticks() / 300) * 8
        super().draw(surface, (x, y + offset))


class StoryPage:
    # One page of a story: background, figures and text.

    def __init__(self, background, lines, figures, title=None):
        self.background = background  # a ParallaxBackground from background.py
        self.lines = lines            # list of strings (at most 3)
        self.figures = figures        # list of (figure, (x, feet_y))
        self.title = title            # big text at the top, or None


class StoryScreen:
    # Shows the pages one after another.

    def __init__(self, pages, screen_size, assets, button_icon=None):
        self.pages = pages
        self.index = 0
        self.camera_x = 0.0  # moves the background slowly
        screen_w, screen_h = screen_size
        self.panel = pygame.Rect(40, screen_h - 200, screen_w - 80, 180)
        self.button = Button("Continue", "continue",
                             (self.panel.right - 190, self.panel.bottom - 45), button_icon)
        self.grass = assets.tiles["grass_1"]
        self.dirt = assets.tiles["dirt_single"]

    def reset(self):
        self.index = 0

    def next_page(self):
        # Go to the next page. Returns "done" after the last page.
        self.index += 1
        if self.index >= len(self.pages):
            self.index = len(self.pages) - 1
            return "done"
        return None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button.rect.collidepoint(event.pos):
                return self.next_page()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.next_page()
            if event.key == pygame.K_ESCAPE:
                return "done"  # skip the whole story
        return None

    def draw_ground(self, surface):
        tile = self.grass.get_width()
        for x in range(0, surface.get_width(), tile):
            surface.blit(self.grass, (x, GROUND_Y))
            for y in range(GROUND_Y + tile, surface.get_height(), tile):
                surface.blit(self.dirt, (x, y))

    def draw(self, surface, font_sm, font_md, font_lg):
        page = self.pages[self.index]

        self.camera_x += 0.6
        page.background.draw(surface, int(self.camera_x))
        self.draw_ground(surface)

        for figure, position in page.figures:
            figure.draw(surface, position)

        if page.title:
            draw_text_with_shadow(surface, font_lg, page.title, HIGHLIGHT_COLOR, (surface.get_width() // 2, 40))

        # Text panel.
        pygame.draw.rect(surface, PANEL_COLOR, self.panel, border_radius=14)
        pygame.draw.rect(surface, HIGHLIGHT_COLOR, self.panel, 3, border_radius=14)
        for number, line in enumerate(page.lines):
            text = font_md.render(line, True, TEXT_COLOR)
            surface.blit(text, (self.panel.left + 30, self.panel.top + 25 + number * 34))

        mouse_on_button = self.button.rect.collidepoint(pygame.mouse.get_pos())
        self.button.draw(surface, font_md, mouse_on_button)
        hint = font_sm.render(f"Page {self.index + 1} / {len(self.pages)}     Enter = continue     Esc = skip",
                              True, HINT_COLOR)
        surface.blit(hint, (self.panel.left + 30, self.panel.bottom - 32))


def make_crown(width=120):
    # The Golden Crown, drawn with simple shapes (there is no sprite for it).
    height = int(width * 0.75)
    crown = pygame.Surface((width, height), pygame.SRCALPHA)
    gold = (255, 205, 60)
    dark_gold = (185, 125, 20)
    points = [
        (0, height), (0, height * 0.3), (width * 0.25, height * 0.6), (width * 0.5, 0),
        (width * 0.75, height * 0.6), (width, height * 0.3), (width, height),
    ]
    pygame.draw.polygon(crown, gold, points)
    pygame.draw.polygon(crown, dark_gold, points, 4)
    band = pygame.Rect(0, int(height * 0.72), width, int(height * 0.28))
    pygame.draw.rect(crown, dark_gold, band)
    gem_colors = [(220, 50, 60), (70, 150, 255), (60, 200, 110)]
    for number, color in enumerate(gem_colors):
        center = (int(width * (0.25 + number * 0.25)), band.centery)
        pygame.draw.circle(crown, color, center, max(4, width // 14))
    for tip in (points[1], points[3], points[5]):
        pygame.draw.circle(crown, (255, 245, 200), (int(tip[0]), int(tip[1]) + 4), max(3, width // 20))
    return crown


def create_stories(assets, player_sprites, screen_size, feet_padding, button_icon=None):
    # All story scenes of the game, by name.
    grasslands = assets.backgrounds[1]
    stronghold = assets.backgrounds[2]
    enemies = assets.enemies
    props = assets.props
    items = assets.items

    # Figures: (pictures, ticks per picture, scale, ...)
    def knight():
        return MenuCharacter(player_sprites["idle"], 20, 2, feet_padding)

    crown = FloatingFigure([make_crown(120)], 60, 1)
    small_crown = FloatingFigure([make_crown(70)], 60, 1)
    key = FloatingFigure(items["key"], 25, 1.6)

    intro = StoryScreen([
        StoryPage(grasslands, [
            "For a hundred years, the Golden Crown kept the kingdom safe and peaceful.",
            "Its light protected every village from the dark creatures beyond the mountains.",
        ], [
            (MenuCharacter([props["campfire"]], 60, 1.4), (400, GROUND_Y)),
            (MenuCharacter([props["loot_bag"]], 60, 1.4), (880, GROUND_Y)),
            (crown, (640, 380)),
            (FloatingFigure(items["coin"], 10, 1.2), (520, 420)),
            (FloatingFigure(items["gem"], 14, 1.2), (760, 420)),
        ], title="THE STOLEN CROWN"),
        StoryPage(stronghold, [
            "But one dark night, a band of goblins crept into the castle and stole the crown!",
            "They carried it to their Stronghold, led by the mighty Goblin Brute.",
        ], [
            (MenuCharacter(enemies["goblin_warrior_walk"], 10, 2), (480, GROUND_Y)),
            (MenuCharacter(enemies["goblin_brute"][:1], 60, 1.7), (680, GROUND_Y)),
            (small_crown, (680, 300)),
            (MenuCharacter(enemies["goblin_archer"][:1], 60, 2), (880, GROUND_Y)),
            (MenuCharacter(enemies["bat"], 12, 1.4), (1050, 260)),
        ]),
        StoryPage(grasslands, [
            "Young knight Aldric swears to bring the crown back home.",
            "First he must cross the Emerald Grasslands and find the Gold Key",
            "that opens the gate to the cave.",
        ], [
            (knight(), (380, GROUND_Y)),
            (key, (680, 400)),
            (MenuCharacter([props["door_locked"]], 60, 1.6), (880, GROUND_Y)),
            (MenuCharacter(enemies["slime"], 18, 2), (1060, GROUND_Y)),
        ]),
    ], screen_size, assets, button_icon)

    level_2 = StoryScreen([
        StoryPage(stronghold, [
            "The cave leads Aldric straight into the Goblin Stronghold.",
            "Archers guard the walls, and the Goblin Brute keeps the key to the treasure room.",
            "Be careful, Aldric!",
        ], [
            (knight(), (360, GROUND_Y)),
            (MenuCharacter(enemies["goblin_archer"][:1], 60, 2, flip=True), (780, GROUND_Y)),
            (MenuCharacter(enemies["goblin_brute"][:1], 60, 1.7, flip=True), (980, GROUND_Y)),
            (FloatingFigure(items["key"], 25, 1.6), (980, 290)),
        ], title="THE GOBLIN STRONGHOLD"),
    ], screen_size, assets, button_icon)

    ending = StoryScreen([
        StoryPage(grasslands, [
            "Deep inside the Stronghold, Aldric finds the Golden Crown.",
            "He brings it home, and the whole kingdom celebrates its new hero!",
        ], [
            (MenuCharacter([props["campfire"]], 60, 1.4), (330, GROUND_Y)),
            (knight(), (560, GROUND_Y)),
            (FloatingFigure([make_crown(90)], 60, 1), (560, 300)),
            (MenuCharacter([props["chest_open"]], 60, 1.5), (780, GROUND_Y)),
            (FloatingFigure(items["coin"], 10, 1.2), (720, 380)),
            (FloatingFigure(items["gem"], 14, 1.2), (850, 380)),
            (MenuCharacter([props["loot_bag"]], 60, 1.4), (960, GROUND_Y)),
        ], title="THE KINGDOM IS SAVED"),
    ], screen_size, assets, button_icon)

    return {"intro": intro, "level_2": level_2, "ending": ending}
