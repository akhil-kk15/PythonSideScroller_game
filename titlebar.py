"""Title bar with minimize and close buttons."""

import pygame

from ui import BORDER_COLOR, HINT_COLOR, PANEL_COLOR, PANEL_SELECTED_COLOR, TEXT_COLOR

BAR_HEIGHT = 32
BUTTON_WIDTH = 46
CLOSE_HOVER_COLOR = (200, 60, 60)


def shift_mouse_event(event) -> None:
    """Moves mouse positions so they match the game area."""
    if hasattr(event, "pos"):
        event.pos = (event.pos[0], event.pos[1] - BAR_HEIGHT)


class TitleBar:
    def __init__(self, width: int, title: str):
        self.title = title
        self.minimize_rect = pygame.Rect(width - 2 * BUTTON_WIDTH, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.close_rect = pygame.Rect(width - BUTTON_WIDTH, 0, BUTTON_WIDTH, BAR_HEIGHT)
        self.rect = pygame.Rect(0, 0, width, BAR_HEIGHT)
        self.drag_offset = None

    def handle_event(self, event) -> bool:
        """Handles clicks on the bar. Returns True if the event was used."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.close_rect.collidepoint(event.pos):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
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
        if pygame.display.get_surface().get_flags() & pygame.FULLSCREEN:
            return
        window = pygame.Window.from_display_module()
        mouse_x, mouse_y = pygame.mouse.get_pos(desktop=True)
        self.drag_offset = (mouse_x - window.position[0], mouse_y - window.position[1])

    def _drag(self) -> None:
        window = pygame.Window.from_display_module()
        mouse_x, mouse_y = pygame.mouse.get_pos(desktop=True)
        window.position = (mouse_x - self.drag_offset[0], mouse_y - self.drag_offset[1])

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, PANEL_COLOR, self.rect)
        pygame.draw.line(surface, BORDER_COLOR, (0, BAR_HEIGHT - 1), (self.rect.right, BAR_HEIGHT - 1))
        title = font.render(self.title, True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midleft=(12, BAR_HEIGHT // 2)))

        mouse = pygame.mouse.get_pos()
        for rect, hover_color in ((self.minimize_rect, PANEL_SELECTED_COLOR), (self.close_rect, CLOSE_HOVER_COLOR)):
            if rect.collidepoint(mouse):
                pygame.draw.rect(surface, hover_color, rect)

        cx, cy = self.minimize_rect.center
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy + 3), (cx + 6, cy + 3), 2)
        cx, cy = self.close_rect.center
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(surface, HINT_COLOR, (cx - 6, cy + 6), (cx + 6, cy - 6), 2)
