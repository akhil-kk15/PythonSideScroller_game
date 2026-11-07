# Story scenes of the game "The Stolen Crown".
#
# A story scene is made of pages. Every page shows a small part of a real
# level (same tiles and background as in the game) with a few animated
# figures. This part is zoomed in 2x with sharp pixels, like a camera zoom
# in a cutscene. The text is shown in a panel at the top of the screen.
#
# FloatingFigure -> a MenuCharacter that moves up and down (for items like the key)
# StoryPage      -> one picture with text
# StoryScreen    -> a list of pages; Enter/Click goes to the next page, Esc skips all

import math
import pygame

from level import Level, TILE_SIZE
from ui import Button, MenuCharacter, draw_text_with_shadow, PANEL_COLOR, HIGHLIGHT_COLOR, TEXT_COLOR, HINT_COLOR

GROUND = 10 * TILE_SIZE  # y of the normal ground in both levels (640)
ZOOM = 2
VIEW_TOP = 320           # top of the zoomed part (so the ground is near the bottom)

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


def make_crown(pixel_size=3):
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


def breathing(picture):
    # Two frames for a figure that stands still: normal and 2 pixels taller.
    # Played one after another, the figure looks like it is breathing.
    width, height = picture.get_size()
    return [picture, pygame.transform.scale(picture, (width, height + 2))]


class FloatingFigure(MenuCharacter):
    # Works like a MenuCharacter, but slowly floats up and down.
    # It inherits everything and only overrides draw().

    def draw(self, surface, feet_position):
        x, y = feet_position
        offset = math.sin(pygame.time.get_ticks() / 300) * 4
        super().draw(surface, (x, y + offset))


class StoryPage:
    # One page of a story: a part of a level, figures and text.

    def __init__(self, level, camera_x, focus_x, lines, figures, title=None):
        self.level = level        # a Level that is drawn as the picture
        self.camera_x = camera_x  # which part of the level is drawn
        self.focus_x = focus_x    # x in the middle of the zoomed part
        self.lines = lines        # list of strings (at most 3)
        self.figures = figures    # list of (figure, (x, feet y)) before zooming
        self.title = title        # big text at the top, or None


class StoryScreen:
    # Shows the pages one after another.

    def __init__(self, pages, screen_size, button_icon=None):
        self.pages = pages
        self.index = 0
        screen_w, screen_h = screen_size
        self.scene = pygame.Surface(screen_size)  # the picture is drawn here first
        self.view_size = (screen_w // ZOOM, screen_h // ZOOM)
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

    def draw_zoomed_scene(self, surface, page, font):
        # 1. Draw the level and the figures in normal size.
        page.level.draw(self.scene, page.camera_x, font)
        for figure, position in page.figures:
            figure.draw(self.scene, position)

        # 2. Cut out a small part around focus_x ...
        view_w, view_h = self.view_size
        left = max(0, min(self.scene.get_width() - view_w, page.focus_x - view_w // 2))
        view = self.scene.subsurface((left, VIEW_TOP, view_w, view_h))

        # 3. ... and make it 2x bigger. scale() (not smoothscale) keeps the pixels sharp.
        surface.blit(pygame.transform.scale(view, surface.get_size()), (0, 0))

    def draw(self, surface, font_sm, font_md, font_lg):
        page = self.pages[self.index]
        self.draw_zoomed_scene(surface, page, font_sm)

        # Text panel at the top. Its height fits the title and the lines of this page.
        title_height = 58 if page.title else 0
        self.panel.height = max(150, 18 + title_height + len(page.lines) * 30 + 55)
        self.button.rect.centery = self.panel.bottom - 45
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


def make_story_level(level_number, assets):
    # A copy of a level that is only used as a picture: no enemies, items,
    # chests, levers, crates or decorations, so only the figures of the story are seen.
    level = Level(level_number, assets)
    level.enemies = []
    level.collectibles = []
    level.chests = []
    level.levers = []
    level.destructibles = []
    level.decorations = []
    return level


def create_stories(assets, player_sprites, screen_size, feet_padding, button_icon=None):
    # All story scenes of the game, by name. Figures use their normal game size.
    grasslands = make_story_level(1, assets)
    stronghold = make_story_level(2, assets)
    enemies = assets.enemies
    items = assets.items
    props = assets.props

    def knight():
        return MenuCharacter(player_sprites["idle"], 20, 1, feet_padding)

    def goblin(name, flip=False):
        # Every goblin stands still and breathes (first picture of its sprites).
        return MenuCharacter(breathing(enemies[name][0]), 30, 1, flip=flip)

    def crown():
        return FloatingFigure([make_crown()], 60, 1)

    def item(name, frame_time):
        return FloatingFigure(items[name], frame_time, 1)

    intro = StoryScreen([
        StoryPage(grasslands, 0, 470, [
            "For a hundred years, the Golden Crown kept the kingdom safe and peaceful.",
            "Its light protected every village from the dark creatures beyond the mountains.",
        ], [
            (MenuCharacter([props["campfire"]], 60, 1), (240, GROUND)),
            (crown(), (510, 590)),
            (item("coin", 10), (440, 615)),
            (item("gem", 14), (580, 615)),
        ], title="THE STOLEN CROWN"),
        StoryPage(stronghold, 15 * TILE_SIZE, 470, [
            "But one dark night, a band of goblins crept into the castle and stole the crown!",
            "They carried it to their Stronghold, led by the mighty Goblin Brute.",
        ], [
            (goblin("goblin_warrior_walk"), (360, GROUND)),
            (goblin("goblin_brute"), (480, GROUND)),
            (crown(), (480, 545)),
            (goblin("goblin_archer"), (600, GROUND)),
            (MenuCharacter(enemies["bat"], 12, 1), (680, 560)),
        ]),
        StoryPage(grasslands, 0, 330, [
            "Young knight Aldric swears to bring the crown back home.",
            "First he must cross the Emerald Grasslands and find the Gold Key",
            "that opens the gate to the cave.",
        ], [
            (knight(), (120, GROUND)),
            (item("key", 25), (300, 605)),
            (MenuCharacter(enemies["slime"], 18, 1), (500, GROUND)),
        ]),
    ], screen_size, button_icon)

    level_2 = StoryScreen([
        StoryPage(stronghold, 27 * TILE_SIZE, 400, [
            "The cave leads Aldric straight into the Goblin Stronghold.",
            "Archers guard the walls, and the Goblin Brute keeps the key to the treasure room.",
        ], [
            (knight(), (200, 9 * TILE_SIZE)),
            (goblin("goblin_archer", flip=True), (480, 9 * TILE_SIZE)),
            (goblin("goblin_brute", flip=True), (590, 9 * TILE_SIZE)),
            (item("key", 25), (590, 485)),
        ], title="THE GOBLIN STRONGHOLD"),
    ], screen_size, button_icon)

    ending = StoryScreen([
        StoryPage(grasslands, 0, 330, [
            "Deep inside the Stronghold, Aldric finds the Golden Crown.",
            "He brings it home, and the whole kingdom celebrates its new hero!",
        ], [
            (MenuCharacter([props["campfire"]], 60, 1), (170, GROUND)),
            (knight(), (300, GROUND)),
            (crown(), (300, 560)),
            (MenuCharacter([props["chest_open"]], 60, 1), (420, GROUND)),
            (item("coin", 10), (480, 600)),
            (item("gem", 14), (530, 610)),
        ], title="THE KINGDOM IS SAVED"),
    ], screen_size, button_icon)

    return {"intro": intro, "level_2": level_2, "ending": ending}
