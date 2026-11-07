# Parallax background: several picture layers that scroll at different speeds.
# Layers that are far away move slowly and layers close to the player move
# faster. That makes the flat 2D level look like it has depth ("2.5D").

import os
import pygame

# Layers of each level, from the back to the front:
# (file name, scroll speed, height on screen, y of the bottom edge)
# Speed 0 means the layer stands still, 1 means it moves with the level.
BACKGROUND_LAYERS = {
    1: [
        ("grasslands_sky.png", 0.03, 720, 720),
        ("grasslands_far.png", 0.15, 400, 680),
        ("grasslands_mid.png", 0.4, 350, 720),
    ],
    2: [
        ("stronghold_sky.png", 0.03, 720, 720),
        ("stronghold_far.png", 0.15, 400, 680),
        ("stronghold_mid.png", 0.4, 350, 720),
    ],
}


class ParallaxLayer:
    # One picture of the background that repeats sideways.

    def __init__(self, image, speed, y):
        self.__image = image
        # Every second copy is mirrored, so the edges of two copies always match.
        self.__mirrored = pygame.transform.flip(image, True, False)
        self.__speed = speed
        self.__y = y

    def draw(self, surface, camera_x):
        width = self.__image.get_width()
        offset = camera_x * self.__speed
        tile = int(offset // width)   # number of the first copy on the screen
        x = tile * width - offset
        while x < surface.get_width():
            if tile % 2 == 0:
                surface.blit(self.__image, (x, self.__y))
            else:
                surface.blit(self.__mirrored, (x, self.__y))
            x += width
            tile += 1


class ParallaxBackground:
    # All layers of one level, drawn from the back to the front.

    def __init__(self, layers, color):
        self.__layers = layers
        self.__color = color  # fills the screen if an image is missing

    def draw(self, surface, camera_x):
        surface.fill(self.__color)
        for layer in self.__layers:
            layer.draw(surface, camera_x)


def load_layer(folder, file_name, speed, height, bottom):
    image = pygame.image.load(os.path.join(folder, file_name)).convert_alpha()
    width = round(image.get_width() * height / image.get_height())
    image = pygame.transform.smoothscale(image, (width, height))
    return ParallaxLayer(image, speed, bottom - height)


def load_background(folder, level_number):
    layers = []
    for file_name, speed, height, bottom in BACKGROUND_LAYERS[level_number]:
        try:
            layers.append(load_layer(folder, file_name, speed, height, bottom))
        except FileNotFoundError:
            # A missing picture should not crash the game.
            print("Background image not found:", file_name)
    return ParallaxBackground(layers, (24, 28, 38))
