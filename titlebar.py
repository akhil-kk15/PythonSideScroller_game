"""Title bar with minimize, fullscreen/windowed toggle, and close buttons."""

import os
import pygame

from ui import BORDER_COLOR, HINT_COLOR, PANEL_COLOR, PANEL_SELECTED_COLOR, TEXT_COLOR

BAR_HEIGHT = 32
BUTTON_WIDTH = 46
CLOSE_HOVER_COLOR = (200, 60, 60)

_DESKTOP_SIZE: tuple[int, int] | None = None
_WINDOWED_SIZE: tuple[int, int] = (1280, 720 + BAR_HEIGHT)
_IS_FULLSCREEN: bool = False
OPAQUE_RGB_MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000)


def create_opaque_surface(size: tuple[int, int]) -> pygame.Surface:
    """Create a 32-bit opaque RGB surface (amask=0) to prevent SDL2 X11/Wayland dst-alpha black-box bugs."""
    return pygame.Surface(size, 0, 32, OPAQUE_RGB_MASKS)


def get_desktop_size(fallback: tuple[int, int] = (1920, 1080)) -> tuple[int, int]:
    """Query and cache the primary monitor's native desktop resolution."""
    global _DESKTOP_SIZE
    if _DESKTOP_SIZE is not None:
        return _DESKTOP_SIZE
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and sizes[0][0] >= 640 and sizes[0][1] >= 480:
            _DESKTOP_SIZE = sizes[0]
            return _DESKTOP_SIZE
    except (AttributeError, pygame.error):
        pass
    try:
        info = pygame.display.Info()
        if info.current_w >= 640 and info.current_h >= 480:
            _DESKTOP_SIZE = (info.current_w, info.current_h)
            return _DESKTOP_SIZE
    except pygame.error:
        pass
    _DESKTOP_SIZE = fallback
    return _DESKTOP_SIZE


def is_fullscreen() -> bool:
    """Return True if the display is currently in fullscreen mode."""
    return _IS_FULLSCREEN


def create_window(width: int = 1280, height: int = 720 + BAR_HEIGHT, fullscreen: bool = True) -> pygame.Surface:
    """
    Create the game window at native desktop resolution when fullscreen (for edge-to-edge
    display with zero black bars and razor-sharp native text), or at `(width, height)` when windowed.
    """
    global _WINDOWED_SIZE, _IS_FULLSCREEN
    _WINDOWED_SIZE = (width, height)

    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        _IS_FULLSCREEN = False
        return pygame.display.set_mode((width, height), pygame.NOFRAME)

    if fullscreen:
        dw, dh = get_desktop_size(fallback=(width, height))
        try:
            win = pygame.display.set_mode((dw, dh), pygame.NOFRAME | pygame.FULLSCREEN)
            _IS_FULLSCREEN = True
            return win
        except pygame.error:
            pass

    _IS_FULLSCREEN = False
    return pygame.display.set_mode((width, height), pygame.NOFRAME)


def toggle_fullscreen() -> pygame.Surface:
    """Toggle between native-resolution fullscreen and windowed mode, returning the new window surface."""
    w, h = _WINDOWED_SIZE
    return create_window(w, h, fullscreen=not _IS_FULLSCREEN)


def shift_mouse_event(event) -> None:
    """Moves mouse positions so they match the game area below the title bar."""
    if hasattr(event, "pos"):
        event.pos = (event.pos[0], event.pos[1] - BAR_HEIGHT)


class TitleBar:
    def __init__(self, width: int, title: str):
        self.title = title
        self.width = 0
        self.minimize_rect = pygame.Rect(0, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.fullscreen_rect = pygame.Rect(0, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.close_rect = pygame.Rect(0, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.rect = pygame.Rect(0, 0, width, BAR_HEIGHT)
        self.drag_offset = None
        self.set_width(width)

    def set_width(self, width: int) -> None:
        """Update button positions to match the current window width."""
        if width == self.width:
            return
        self.width = width
        self.minimize_rect = pygame.Rect(width - 3 * BUTTON_WIDTH, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.fullscreen_rect = pygame.Rect(width - 2 * BUTTON_WIDTH, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.close_rect = pygame.Rect(width - BUTTON_WIDTH, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.rect = pygame.Rect(0, 0, width, BAR_HEIGHT)

    def handle_event(self, event) -> bool:
        """Handles clicks on the bar. Returns True if the event was used."""
        disp = pygame.display.get_surface()
        if disp is not None:
            self.set_width(disp.get_width())

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.close_rect.collidepoint(event.pos):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif self.fullscreen_rect.collidepoint(event.pos):
                win = toggle_fullscreen()
                self.set_width(win.get_width())
            elif self.minimize_rect.collidepoint(event.pos):
                pygame.display.iconify()
            else:
                self._start_drag()
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_offset is not None:
            self.drag_offset = None
            return True
        if event.type == pygame.MOUSEMOTION and self.drag_offset is not None:
            self._drag()
            return True
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and self.rect.collidepoint(event.pos)

    def _start_drag(self) -> None:
        if is_fullscreen():
            return
        window = pygame.Window.from_display_module()
        mouse_x, mouse_y = pygame.mouse.get_pos(desktop=True)
        self.drag_offset = (mouse_x - window.position[0], mouse_y - window.position[1])

    def _drag(self) -> None:
        window = pygame.Window.from_display_module()
        mouse_x, mouse_y = pygame.mouse.get_pos(desktop=True)
        window.position = (mouse_x - self.drag_offset[0], mouse_y - self.drag_offset[1])

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        self.set_width(surface.get_width())
        pygame.draw.rect(surface, PANEL_COLOR, self.rect)
        pygame.draw.line(surface, BORDER_COLOR, (0, BAR_HEIGHT - 1), (self.rect.right, BAR_HEIGHT - 1))
        title = font.render(self.title, True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midleft=(12, BAR_HEIGHT // 2)))

        mouse = pygame.mouse.get_pos()
        for rect, hover_color in (
            (self.minimize_rect, PANEL_SELECTED_COLOR),
            (self.fullscreen_rect, PANEL_SELECTED_COLOR),
            (self.close_rect, CLOSE_HOVER_COLOR),
        ):
            if rect.collidepoint(mouse):
                pygame.draw.rect(surface, hover_color, rect)

        # Minimize icon (horizontal bar).
        cx, cy = self.minimize_rect.center
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy + 3), (cx + 6, cy + 3), 2)

        # Fullscreen / Windowed icon.
        cx, cy = self.fullscreen_rect.center
        if is_fullscreen():
            # Restore / windowed icon (overlapping squares).
            pygame.draw.rect(surface, HINT_COLOR, (cx - 4, cy - 6, 10, 10), 2)
            pygame.draw.rect(surface, PANEL_COLOR, (cx - 6, cy - 3, 10, 10))
            pygame.draw.rect(surface, HINT_COLOR, (cx - 6, cy - 3, 10, 10), 2)
        else:
            # Maximize / fullscreen icon (single square).
            pygame.draw.rect(surface, HINT_COLOR, (cx - 6, cy - 6, 12, 12), 2)

        # Close icon (X).
        cx, cy = self.close_rect.center
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy + 6), (cx + 6, cy - 6), 2)
