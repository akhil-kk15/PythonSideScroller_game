# Story scenes of the game "The Stolen Crown".
#
# Simple and dark: every page shows a dark night sky with twinkling stars,
# a warm light in the middle, one big main figure (plus a few small ones)
# and some lines of text below it.
#
# FloatingFigure -> a MenuCharacter that moves up and down (for items like the crown)
# StoryPage      -> one picture with text
# StoryScreen    -> a list of pages; Enter/Click goes to the next page, Esc skips all

import math
import random
import pygame

from ui import Button, MenuCharacter, draw_text_with_shadow, HIGHLIGHT_COLOR, TEXT_COLOR, HINT_COLOR

FEET_Y = 440                     # where the figures stand
BACKGROUND_COLOR = (14, 16, 26)
GLOW_COLOR = (255, 200, 90)

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


def make_crown(pixel_size):
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
    # Two frames for a figure that stands still: normal and a little taller.
    # Played one after another, the figure looks like it is breathing.
    width, height = picture.get_size()
    return [picture, pygame.transform.scale(picture, (width, height + 2))]


class FloatingFigure(MenuCharacter):
    # Works like a MenuCharacter, but slowly floats up and down.
    # It inherits everything and only overrides draw().

    def draw(self, surface, feet_position):
        x, y = feet_position
        offset = math.sin(pygame.time.get_ticks() / 300) * 8
        super().draw(surface, (x, y + offset))


class StoryPage:
    # One page of a story: figures and text.

    def __init__(self, lines, figures, title=None):
        self.lines = lines      # list of strings (at most 3)
        self.figures = figures  # list of (figure, (x, feet y))
        self.title = title      # big text at the top, or None


def make_background(screen_size):
    # Dark background with a warm light in the middle and a light spot on the floor.
    # It is drawn once and then reused for every page.
    width, height = screen_size
    background = pygame.Surface(screen_size)
    background.fill(BACKGROUND_COLOR)

    glow = pygame.Surface(screen_size, pygame.SRCALPHA)
    max_radius = 340
    for radius in range(max_radius, 0, -4):
        # Circles from the outside to the inside. Every smaller circle is a bit less
        # see-through, so the light is strongest in the middle and fades out smoothly.
        alpha = int(45 * (1 - radius / max_radius))
        pygame.draw.circle(glow, (*GLOW_COLOR, alpha), (width // 2, FEET_Y - 110), radius)
    pygame.draw.ellipse(glow, (*GLOW_COLOR, 35), (width // 2 - 260, FEET_Y - 18, 520, 36))
    background.blit(glow, (0, 0))
    return background


class StoryScreen:
    # Shows the pages one after another.

    def __init__(self, pages, screen_size, background, button_icon=None):
        self.pages = pages
        self.index = 0
        self.background = background
        width, height = screen_size
        self.button = Button("Continue", "continue", (width // 2, height - 75), button_icon)

        # Stars: random places, but always the same ones (fixed seed).
        generator = random.Random(7)
        self.stars = []
        for _ in range(70):
            self.stars.append((generator.randint(0, width), generator.randint(0, FEET_Y - 40),
                               generator.uniform(0, 6.3)))

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

    def draw_stars(self, surface):
        time = pygame.time.get_ticks() / 600
        for x, y, phase in self.stars:
            brightness = int(120 + 90 * math.sin(time + phase))  # between 30 and 210
            surface.fill((brightness, brightness, brightness + 30 if brightness < 225 else 255), (x, y, 2, 2))

    def draw(self, surface, font_sm, font_md, font_lg):
        page = self.pages[self.index]
        center_x = surface.get_width() // 2

        surface.blit(self.background, (0, 0))
        self.draw_stars(surface)

        for figure, position in page.figures:
            figure.draw(surface, position)

        if page.title:
            draw_text_with_shadow(surface, font_lg, page.title, HIGHLIGHT_COLOR, (center_x, 40))

        text_y = FEET_Y + 45
        for line in page.lines:
            text = font_md.render(line, True, TEXT_COLOR)
            surface.blit(text, text.get_rect(midtop=(center_x, text_y)))
            text_y += 32

        mouse_on_button = self.button.rect.collidepoint(pygame.mouse.get_pos())
        self.button.draw(surface, font_md, mouse_on_button)
        hint = font_sm.render(f"Page {self.index + 1} / {len(self.pages)}     Enter = continue     Esc = skip",
                              True, HINT_COLOR)
        surface.blit(hint, hint.get_rect(midtop=(center_x, self.button.rect.bottom + 10)))


def create_stories(assets, player_sprites, screen_size, feet_padding, button_icon=None):
    # All story scenes of the game, by name.
    background = make_background(screen_size)
    enemies = assets.enemies
    items = assets.items
    center_x = screen_size[0] // 2

    def knight(scale):
        return MenuCharacter(player_sprites["idle"], 20, scale, feet_padding)

    def goblin(name, scale, flip=False):
        # Every goblin stands still and breathes (first picture of its sprites).
        return MenuCharacter(breathing(enemies[name][0]), 30, scale, flip=flip)

    def item(name, frame_time, scale):
        return FloatingFigure(items[name], frame_time, scale)

    def crown(pixel_size):
        return FloatingFigure([make_crown(pixel_size)], 60, 1)

    intro = StoryScreen([
        StoryPage([
            "For a hundred years, the Golden Crown kept the kingdom safe and peaceful.",
            "Its light protected every village from the dark creatures beyond the mountains.",
        ], [
            (crown(10), (center_x, FEET_Y - 60)),
            (item("coin", 10, 2), (center_x - 190, FEET_Y - 20)),
            (item("gem", 14, 2), (center_x + 190, FEET_Y - 20)),
        ], title="THE STOLEN CROWN"),
        StoryPage([
            "But one dark night, a band of goblins crept into the castle and stole the crown!",
            "They carried it to their Stronghold, led by the mighty Goblin Brute.",
        ], [
            (goblin("goblin_warrior_walk", 2), (center_x - 230, FEET_Y)),
            (goblin("goblin_archer", 2), (center_x + 230, FEET_Y)),
            (goblin("goblin_brute", 3), (center_x, FEET_Y)),
            (crown(4), (center_x, FEET_Y - 275)),
            (MenuCharacter(enemies["bat"], 12, 2), (center_x + 420, FEET_Y - 200)),
        ]),
        StoryPage([
            "Young knight Aldric swears to bring the crown back home.",
            "First he must cross the Emerald Grasslands and find the Gold Key",
            "that opens the gate to the cave.",
        ], [
            (knight(3), (center_x - 80, FEET_Y)),
            (item("key", 25, 2), (center_x + 150, FEET_Y - 100)),
        ]),
    ], screen_size, background, button_icon)

    level_2 = StoryScreen([
        StoryPage([
            "The cave leads Aldric straight into the Goblin Stronghold.",
            "Archers guard the walls, and the Goblin Brute keeps the key to the treasure room.",
        ], [
            (knight(2), (center_x - 260, FEET_Y)),
            (goblin("goblin_archer", 2, flip=True), (center_x + 30, FEET_Y)),
            (goblin("goblin_brute", 2.5, flip=True), (center_x + 250, FEET_Y)),
            (item("key", 25, 1.5), (center_x + 250, FEET_Y - 230)),
        ], title="THE GOBLIN STRONGHOLD"),
    ], screen_size, background, button_icon)

    ending = StoryScreen([
        StoryPage([
            "Deep inside the Stronghold, Aldric finds the Golden Crown.",
            "He brings it home, and the whole kingdom celebrates its new hero!",
        ], [
            (knight(3), (center_x, FEET_Y)),
            (crown(5), (center_x, FEET_Y - 230)),
            (item("coin", 10, 2), (center_x - 200, FEET_Y - 30)),
            (item("gem", 14, 2), (center_x + 200, FEET_Y - 30)),
        ], title="THE KINGDOM IS SAVED"),
    ], screen_size, background, button_icon)

    return {"intro": intro, "level_2": level_2, "ending": ending}
