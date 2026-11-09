# Menu screens with clickable buttons: main menu, pause menu, controls,
# game over and victory.
#
# Button -> a rectangle with an icon and text that can be clicked
# Menu   -> a title, some lines of text and a column of buttons in a panel.
#           It works with the mouse and with the keyboard (W/S or arrows + Enter).

import pygame

import sounds
from animation import Animation

# Same colors as the HUD in main.py.
PANEL_COLOR = (28, 34, 52)
PANEL_SELECTED_COLOR = (48, 58, 86)
BORDER_COLOR = (90, 100, 125)
HIGHLIGHT_COLOR = (255, 215, 75)
TEXT_COLOR = (235, 242, 255)
HINT_COLOR = (170, 180, 205)
SHADOW_COLOR = (10, 12, 20)

BUTTON_SIZE = (320, 52)
BUTTON_SPACING = 66   # distance between the centers of two buttons
LINE_SPACING = 32     # distance between two lines of text
PANEL_WIDTH = 660
ICON_SIZE = 26


def draw_text_with_shadow(surface, font, text, color, midtop):
    # Draw the text twice: first dark and a bit to the bottom right, then on top.
    shadow = font.render(text, True, SHADOW_COLOR)
    label = font.render(text, True, color)
    surface.blit(shadow, shadow.get_rect(midtop=(midtop[0] + 3, midtop[1] + 3)))
    surface.blit(label, label.get_rect(midtop=midtop))


class Button:
    # A rectangle with text. When it is clicked, the menu returns its action.

    def __init__(self, text, action, center, icon=None):
        self.text = text
        self.action = action  # a short string like "start" or "quit"
        self.icon = icon      # small picture on the left side, or None
        self.rect = pygame.Rect((0, 0), BUTTON_SIZE)
        self.rect.center = center

    def draw(self, surface, font, selected):
        if selected:
            pygame.draw.rect(surface, PANEL_SELECTED_COLOR, self.rect, border_radius=10)
            pygame.draw.rect(surface, HIGHLIGHT_COLOR, self.rect, 3, border_radius=10)
            color = HIGHLIGHT_COLOR
        else:
            pygame.draw.rect(surface, PANEL_COLOR, self.rect, border_radius=10)
            pygame.draw.rect(surface, BORDER_COLOR, self.rect, 2, border_radius=10)
            color = TEXT_COLOR
        if self.icon is not None:
            surface.blit(self.icon, self.icon.get_rect(midleft=(self.rect.left + 18, self.rect.centery)))
        label = font.render(self.text, True, color)
        surface.blit(label, label.get_rect(center=self.rect.center))


class Menu:
    # A panel in the middle of the screen with a title, text lines and buttons.

    def __init__(self, title, options, screen_size, lines=None, icons=None,
                 title_color=HIGHLIGHT_COLOR, title_size=42, back_action=None, overlay_alpha=195):
        # options:     list of (button text, action, icon name)
        # lines:       text shown between the title and the buttons
        # icons:       dict of icon name -> small picture for the buttons
        # back_action: action used when Esc is pressed (None = Esc does nothing)
        self.title = title
        self.title_color = title_color
        self.title_size = title_size
        self.title_font = None  # created when the menu is drawn the first time
        self.lines = lines or []
        self.back_action = back_action
        self.overlay_alpha = overlay_alpha
        self.selected = 0
        icons = icons or {}

        # Work out the height of everything, so the panel sits in the middle.
        screen_w, screen_h = screen_size
        title_height = title_size + 28
        lines_height = len(self.lines) * LINE_SPACING
        content_height = title_height + lines_height + 30 + len(options) * BUTTON_SPACING
        top = (screen_h - content_height) // 2

        center_x = screen_w // 2
        self.title_y = top
        self.lines_y = top + title_height
        y = self.lines_y + lines_height + 30 + BUTTON_SPACING // 2
        self.buttons = []
        for text, action, icon_name in options:
            self.buttons.append(Button(text, action, (center_x, y), icons.get(icon_name)))
            y += BUTTON_SPACING

        self.panel = pygame.Rect(0, 0, PANEL_WIDTH, content_height + 50)
        self.panel.midtop = (center_x, top - 30)

    def reset(self):
        # Select the first button again when the menu is opened.
        self.selected = 0

    def handle_event(self, event):
        # Returns the action of the chosen button, or None.
        if event.type == pygame.MOUSEMOTION:
            for index, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.pos):
                    self.selected = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    sounds.play("click")
                    return button.action
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                sounds.play("click")
                return self.buttons[self.selected].action
            elif event.key == pygame.K_ESCAPE:
                return self.back_action
        return None

    def handle_gamepad(self, gamepad):
        # Navigate and activate menu buttons using an Xbox / DirectInput controller.
        if gamepad.nav_up:
            self.selected = (self.selected - 1) % len(self.buttons)
        elif gamepad.nav_down:
            self.selected = (self.selected + 1) % len(self.buttons)
        if gamepad.confirm:
            sounds.play("click")
            return self.buttons[self.selected].action
        if gamepad.back:
            return self.back_action
        if gamepad.pause:
            if self.back_action is not None:
                return self.back_action
            return self.buttons[self.selected].action
        return None

    def draw(self, surface, font_sm, font_md):
        if self.title_font is None:
            self.title_font = pygame.font.SysFont("dejavusans,arial,sans-serif", self.title_size, bold=True)

        # Darken the game behind the menu.
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((12, 15, 24, self.overlay_alpha))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, PANEL_COLOR, self.panel, border_radius=14)
        pygame.draw.rect(surface, self.title_color, self.panel, 3, border_radius=14)

        center_x = self.panel.centerx
        draw_text_with_shadow(surface, self.title_font, self.title, self.title_color, (center_x, self.title_y))

        for index, line in enumerate(self.lines):
            text = font_md.render(line, True, TEXT_COLOR)
            surface.blit(text, text.get_rect(midtop=(center_x, self.lines_y + index * LINE_SPACING)))

        for index, button in enumerate(self.buttons):
            button.draw(surface, font_md, index == self.selected)

        hint_str = "Mouse  |  W/S + Enter  |  Stick/D-Pad + (A)"
        if self.back_action is not None:
            hint_str += "  |  Esc / (B) = Back"
        hint = font_sm.render(hint_str, True, HINT_COLOR)
        surface.blit(hint, hint.get_rect(midtop=(center_x, self.panel.bottom + 10)))


class MenuCharacter:
    # An animated figure that stands in the main menu and in the story scenes.
    # It reuses the Animation class from animation.py.

    def __init__(self, frames, frame_time, scale, feet_padding=0, flip=False):
        # scale_by (not smoothscale_by) keeps the pixels sharp when the figure is made bigger.
        big_frames = [pygame.transform.scale_by(frame, scale) for frame in frames]
        if flip:
            # Mirror the pictures so the figure looks the other way.
            big_frames = [pygame.transform.flip(frame, True, False) for frame in big_frames]
        self.animation = Animation(big_frames, frame_time)
        self.feet_padding = round(feet_padding * scale)  # empty space below the feet

    def draw(self, surface, feet_position):
        self.animation.update()
        frame = self.animation.get_frame()
        x, y = feet_position
        surface.blit(frame, frame.get_rect(midbottom=(x, y + self.feet_padding)))


def load_icons(assets):
    # Small pictures for the buttons, taken from the HUD and item sprites.
    pictures = {
        "key": assets.ui["key_icon"],
        "heart": assets.ui["heart_full"],
        "heart_half": assets.ui["heart_half"],
        "heart_empty": assets.ui["heart_empty"],
        "coin": assets.ui["coin_icon"],
        "gem": assets.ui["gem_icon"],
    }
    icons = {}
    for name, picture in pictures.items():
        scale = ICON_SIZE / max(picture.get_size())
        icons[name] = pygame.transform.smoothscale_by(picture, scale)
    return icons


def create_menus(screen_size, icons=None):
    # All menus of the game, by name. The names are also the game states.
    return {
        "menu": Menu(
            "KNIGHT'S QUEST",
            [
                ("Start Game", "start", "key"),
                ("Controls", "controls", "gem"),
                ("Quit", "quit", "heart_empty"),
            ],
            screen_size,
            lines=["The goblins stole the Golden Crown - bring it back!", ""],  # 2nd line: best score
            icons=icons,
            title_size=60,
            overlay_alpha=120,
        ),
        "paused": Menu(
            "PAUSED",
            [
                ("Resume", "resume", "heart"),
                ("Restart Level", "restart_level", "heart_half"),
                ("Controls", "controls", "gem"),
                ("Main Menu", "main_menu", "coin"),
                ("Quit Game", "quit", "heart_empty"),
            ],
            screen_size,
            icons=icons,
            back_action="resume",
        ),
        "controls": Menu(
            "CONTROLS",
            [
                ("Mode: Auto (Both)", "cycle_input_mode", "gem"),
                ("Back", "back", "coin"),
            ],
            screen_size,
            lines=[
                "Move:  A/D, Arrows, Left Stick or D-Pad",
                "Jump / Drop:  Space/W/(A)  |  Down + Space/(A)",
                "Climb ladders:  W/S, Up/Down, Stick or D-Pad",
                "Attack:  J/Z/X/Click  or  (X) / (B) / RB / RT",
                "Pause:  Esc / P / Start   |   Restart:  R / Back",
                "",
                "Gamepad: Not connected (plug in anytime)",
                "Input API: Auto (XInput + DirectInput)",
            ],
            icons=icons,
            back_action="back",
        ),
        "game_over": Menu(
            "GAME OVER",
            [
                ("Play Again", "start", "heart"),
                ("Main Menu", "main_menu", "coin"),
                ("Quit", "quit", "heart_empty"),
            ],
            screen_size,
            lines=[""] * 8,  # filled with the score and the highscores (see main.py)
            icons=icons,
            title_color=(245, 85, 85),
        ),
        "victory": Menu(
            "VICTORY! QUEST COMPLETE!",
            [
                ("Play Again", "start", "key"),
                ("Main Menu", "main_menu", "coin"),
                ("Quit", "quit", "heart_empty"),
            ],
            screen_size,
            lines=[""] * 8,  # filled with the score and the highscores (see main.py)
            icons=icons,
        ),
    }
