# Animation classes used by the knight (and later the enemies).
#
# Animation         -> a list of frames that plays in a loop (idle, run)
# OneShotAnimation  -> plays once and stops on the last frame (attacks, landing)
# Animator          -> holds all animations of one character and plays the right one

import pygame


class Animation:
    # A list of frames that plays in a loop.

    def __init__(self, frames, frame_time):
        self._frames = frames          # list of pygame.Surface
        self._frame_time = frame_time  # how many game ticks each frame stays on screen
        self._index = 0                # which frame is shown right now
        self._timer = 0                # ticks the current frame has been shown

    def reset(self):
        self._index = 0
        self._timer = 0

    def update(self):
        # Called once per game tick: go to the next frame when its time is up.
        self._timer += 1
        if self._timer >= self._frame_time:
            self._timer = 0
            self._index = (self._index + 1) % len(self._frames)

    def get_frame(self):
        return self._frames[self._index]

    def is_finished(self):
        # A looping animation never finishes.
        return False


class OneShotAnimation(Animation):
    # Plays once and then stays on the last frame.

    def update(self):
        if self._index < len(self._frames) - 1:
            super().update()
        elif self._timer < self._frame_time:
            # Last frame: count its time, but do not start over.
            self._timer += 1

    def is_finished(self):
        on_last_frame = self._index == len(self._frames) - 1
        return on_last_frame and self._timer >= self._frame_time


class Animator:
    # Keeps all animations of one character and plays the right one.

    def __init__(self, animations, start_name):
        self.__animations = animations  # dict: name -> Animation
        self.__current_name = start_name
        self.__flipped = {}             # mirrored frames, created once and reused

    def play(self, name, restart=False):
        # Switch to another animation. Every switch starts it from the
        # beginning; restart=True also does that for the same animation
        # (needed when the same attack is used twice in a row).
        if name != self.__current_name or restart:
            self.__current_name = name
            self.__animations[name].reset()

    def update(self):
        self.__animations[self.__current_name].update()

    def get_name(self):
        return self.__current_name

    def is_finished(self):
        return self.__animations[self.__current_name].is_finished()

    def get_frame(self, facing_right):
        frame = self.__animations[self.__current_name].get_frame()
        if facing_right:
            return frame
        # The sprites look to the right, so mirror them when walking left.
        if frame not in self.__flipped:
            self.__flipped[frame] = pygame.transform.flip(frame, True, False)
        return self.__flipped[frame]
