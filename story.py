# Story scenes of the game "The Stolen Crown".
#
# A story scene is made of pages. Every page shows a part of a real level
# (same tiles and background as in the game), a few animated figures
# (knight, goblins, items) in their normal game size, and some text in a
# panel at the top of the screen.
#
# FloatingFigure -> a MenuCharacter that moves up and down (for items like the key)
# StoryPage      -> one picture with text
# StoryScreen    -> a list of pages; Enter/Click goes to the next page, Esc skips all

import math
import pygame

from level import Level, TILE_SIZE
from ui import Button, MenuCharacter, draw_text_with_shadow, PANEL_COLOR, HIGHLIGHT_COLOR, TEXT_COLOR, HINT_COLOR

GROUND = 10 * TILE_SIZE  # y of the normal ground in both levels (640)

# The Golden Crown as pixel art, so it looks like the other sprites.
# Every letter is one pixel, "." means transparent.
CROWN_PIXELS = [
    "..O....O....O..",
    ".OWO..OWO..OWO.",
    ".OYO..OYO..OYO.",
    ".OYYOOYYYOOYYO.",
    ".OYYYYYWYYYYYO.",
    ".OYYYYYYYYYYYO.",
    ".OOOOOOOOOOOOO.",
    ".ODDRDDBDDRDDO.",
    ".ODDDDDDDDDDDO.",
    ".OOOOOOOOOOOOO.",
]
CROWN_COLORS = {
    "O": (70, 40, 15),     # dark outline
    "Y": (255, 200, 50),   # gold
    "W": (255, 245, 190),  # shine
    "D": (205, 140, 30),   # darker gold band
    "R": (220, 50, 60),    # red gem
    "B": (70, 150, 255),   # blue gem
}


def make_crown(pixel_size=4):
    # Draw the crown pixel by pixel from CROWN_PIXELS.
    width = len(CROWN_PIXELS[0]) * pixel_size
    height = len(CROWN_PIXELS) * pixel_size
    crown = pygame.Surface((width, height), pygame.SRCALPHA)
    for row, line in enumerate(CROWN_PIXELS):
        for column, letter in enumerate(line):
            if letter in CROWN_COLORS:
                pixel = (column * pixel_size, row * pixel_size, pixel_size, pixel_size)
                crown.fill(CROWN_COLORS[letter], pixel)
    return crown


class FloatingFigure(MenuCharacter):
    # Works like a MenuCharacter, but slowly floats up and down.
    # It inherits everything and only overrides draw().

    def draw(self, surface, feet_position):
        x, y = feet_position
        offset = math.sin(pygame.time.get_ticks() / 300) * 5
        super().draw(surface, (x, y + offset))


class StoryPage:
    # One page of a story: a part of a level, figures and text.

    def __init__(self, level, camera_x, lines, figures, title=None):
        self.level = level        # a Level that is drawn as the picture
        self.camera_x = camera_x  # which part of the level is shown
        self.lines = lines        # list of strings (at most 3)
        self.figures = figures    # list of (figure, (x on screen, feet y))
        self.title = title        # big text at the top, or None


class StoryScreen:
    # Shows the pages one after another.

    def __init__(self, pages, screen_size, button_icon=None):
        self.pages = pages
        self.index = 0
        screen_w, screen_h = screen_size
        self.panel = pygame.Rect(40, 20, screen_w - 80, 200)
        self.button = Button("Continue", "continue",
                             (self.panel.right - 190, self.panel.bottom - 45), button_icon)

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

    def draw(self, surface, font_sm, font_md, font_lg):
        page = self.pages[self.index]
        page.level.draw(surface, page.camera_x, font_sm)

        for figure, position in page.figures:
            figure.draw(surface, position)

        # Text panel at the top (the figures stand on the ground below it).
        pygame.draw.rect(surface, PANEL_COLOR, self.panel, border_radius=14)
        pygame.draw.rect(surface, HIGHLIGHT_COLOR, self.panel, 3, border_radius=14)
        text_y = self.panel.top + 18
        if page.title:
            draw_text_with_shadow(surface, font_lg, page.title, HIGHLIGHT_COLOR, (self.panel.centerx, text_y))
            text_y += 58
        for line in page.lines:
            text = font_md.render(line, True, TEXT_COLOR)
            surface.blit(text, (self.panel.left + 30, text_y))
            text_y += 30

        mouse_on_button = self.button.rect.collidepoint(pygame.mouse.get_pos())
        self.button.draw(surface, font_md, mouse_on_button)
        hint = font_sm.render(f"Page {self.index + 1} / {len(self.pages)}     Enter = continue     Esc = skip",
                              True, HINT_COLOR)
        surface.blit(hint, (self.panel.left + 30, self.panel.bottom - 28))


def make_story_level(level_number, assets, door_open=False):
    # A copy of a level without enemies and items, used only as a picture.
    level = Level(level_number, assets)
    level.enemies = []
    level.collectibles = []
    if door_open and level.locked_door:
        level.locked_door["open"] = True
    return level


def create_stories(assets, player_sprites, screen_size, feet_padding, button_icon=None):
    # All story scenes of the game, by name. Figures use their normal game size.
    grasslands = make_story_level(1, assets)
    grasslands_end = make_story_level(1, assets, door_open=True)
    stronghold = make_story_level(2, assets)
    enemies = assets.enemies
    items = assets.items

    def knight():
        return MenuCharacter(player_sprites["idle"], 20, 1, feet_padding)

    def crown():
        return FloatingFigure([make_crown()], 60, 1)

    intro = StoryScreen([
        StoryPage(grasslands, 0, [
            "For a hundred years, the Golden Crown kept the kingdom safe and peaceful.",
            "Its light protected every village from the dark creatures beyond the mountains.",
        ], [
            (crown(), (800, 560)),
            (FloatingFigure(items["coin"], 10, 1), (720, 600)),
            (FloatingFigure(items["gem"], 14, 1), (880, 600)),
        ], title="THE STOLEN CROWN"),
        StoryPage(stronghold, 15 * TILE_SIZE, [
            "But one dark night, a band of goblins crept into the castle and stole the crown!",
            "They carried it to their Stronghold, led by the mighty Goblin Brute.",
        ], [
            (MenuCharacter(enemies["goblin_warrior_walk"], 10, 1), (360, GROUND)),
            (MenuCharacter(enemies["goblin_brute"][:1], 60, 1), (490, GROUND)),
            (crown(), (490, 545)),
            (MenuCharacter(enemies["goblin_archer"][:1], 60, 1), (605, GROUND)),
            (MenuCharacter(enemies["bat"], 12, 1), (820, 470)),
        ]),
        StoryPage(grasslands, 0, [
            "Young knight Aldric swears to bring the crown back home.",
            "First he must cross the Emerald Grasslands and find the Gold Key",
            "that opens the gate to the cave.",
        ], [
            (knight(), (70, GROUND)),
            (FloatingFigure(items["key"], 25, 1), (470, 600)),
            (MenuCharacter(enemies["slime"], 18, 1), (740, GROUND)),
        ]),
    ], screen_size, button_icon)

    level_2 = StoryScreen([
        StoryPage(stronghold, 27 * TILE_SIZE, [
            "The cave leads Aldric straight into the Goblin Stronghold.",
            "Archers guard the walls, and the Goblin Brute keeps the key to the treasure room.",
        ], [
            (knight(), (140, 9 * TILE_SIZE)),
            (MenuCharacter(enemies["goblin_archer"][:1], 60, 1, flip=True), (490, 9 * TILE_SIZE)),
            (MenuCharacter(enemies["goblin_brute"][:1], 60, 1, flip=True), (600, 9 * TILE_SIZE)),
            (FloatingFigure(items["key"], 25, 1), (600, 470)),
        ], title="THE GOBLIN STRONGHOLD"),
    ], screen_size, button_icon)

    ending = StoryScreen([
        StoryPage(grasslands_end, 56 * TILE_SIZE - screen_size[0], [
            "Deep inside the Stronghold, Aldric finds the Golden Crown.",
            "He brings it home, and the whole kingdom celebrates its new hero!",
        ], [
            (knight(), (620, GROUND)),
            (crown(), (620, 560)),
            (MenuCharacter([assets.props["chest_open"]], 60, 1), (720, GROUND)),
            (FloatingFigure(items["coin"], 10, 1), (560, 610)),
            (FloatingFigure(items["gem"], 14, 1), (690, 570)),
        ], title="THE KINGDOM IS SAVED"),
    ], screen_size, button_icon)

    return {"intro": intro, "level_2": level_2, "ending": ending}
