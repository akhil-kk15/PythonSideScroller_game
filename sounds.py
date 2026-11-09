"""Soft retro sound effects, synthesized in code, plus the looping music.

Call init() once after pygame.init(). Then play("jump") anywhere. If the
computer has no audio device, every call quietly does nothing.
"""

import array
import math
import os
import random

import pygame

MUSIC_VOLUME = 0.35  # music stays quiet in the background (1.0 = full volume)
MUSIC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music", "theme.wav")

_sounds: dict[str, list[pygame.mixer.Sound]] = {}
_muted = False
_music_on = False  # the game decides when the music should play (see set_music)
_music_channel = None


def _tone(notes, sample_rate, volume):
    """Builds mono samples for soft notes given as (start_hz, end_hz, seconds)."""
    samples = array.array("h")
    attack = max(1, int(sample_rate * 0.006))  # a quick fade-in avoids clicks
    for start_hz, end_hz, seconds in notes:
        count = int(sample_rate * seconds)
        phase = 0.0
        for i in range(count):
            progress = i / count
            phase += (start_hz + (end_hz - start_hz) * progress) / sample_rate
            wave = math.sin(2 * math.pi * phase) + 0.25 * math.sin(4 * math.pi * phase)
            envelope = min(1.0, i / attack) * (1.0 - progress) ** 2
            samples.append(int(wave * envelope * volume * 0.8 * 32767))
    return samples


def _noise(seconds, sample_rate, volume, smoothness, whoosh=False):
    """Builds mono samples of softened noise. Lower smoothness = darker sound.

    A whoosh fades in and out. Otherwise the noise starts at once and fades out.
    """
    samples = array.array("h")
    count = int(sample_rate * seconds)
    filtered = 0.0
    for i in range(count):
        progress = i / count
        filtered += smoothness * (random.uniform(-1.0, 1.0) - filtered)
        envelope = math.sin(math.pi * progress) if whoosh else (1.0 - progress) ** 2
        samples.append(int(filtered * envelope * volume * 32767))
    return samples


def _mix(*parts):
    """Plays several sample lists at the same time."""
    mixed = array.array("h")
    for i in range(max(len(part) for part in parts)):
        total = sum(part[i] for part in parts if i < len(part))
        mixed.append(max(-32767, min(32767, total)))
    return mixed


def _to_sound(samples, channels):
    """Turns mono samples into a Sound that matches the mixer's channel count."""
    if channels > 1:
        stereo = array.array("h")
        for value in samples:
            stereo.extend([value] * channels)
        samples = stereo
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _start_music(channels):
    """Starts the looping music on the reserved channel, if its file exists."""
    global _music_channel
    if not os.path.exists(MUSIC_FILE):
        return
    channel = pygame.mixer.Channel(0)
    channel.set_volume(0.0 if _muted else MUSIC_VOLUME)
    channel.play(pygame.mixer.Sound(MUSIC_FILE), loops=-1)
    if not _music_on:
        channel.pause()
    _music_channel = channel


def set_music(on: bool) -> None:
    """Turns the music on or off. It keeps its place in the tune while off."""
    global _music_on
    if on == _music_on:
        return
    _music_on = on
    if _music_channel is not None:
        if on:
            _music_channel.unpause()
        else:
            _music_channel.pause()


def init() -> None:
    """Creates all sound effects. Does nothing if audio is not available."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sample_rate, size, channels = pygame.mixer.get_init()
    except (pygame.error, TypeError) as error:
        print(f"Sound is off: no audio device could be opened ({error})")
        return
    if size != -16:
        print("Sound is off: the audio device does not support 16-bit sound")
        return
    print(f"Sound is on ({sample_rate} Hz, {channels} channels). Press M to mute.")

    # Each name holds one or more variants. play() picks one at random.
    mono = {
        "click": [_tone([(700, 520, 0.05)], sample_rate, 0.16)],
        "jump": [_tone([(240, 420, 0.14)], sample_rate, 0.16)],
        "coin": [_tone([(988, 988, 0.07), (1319, 1319, 0.12)], sample_rate, 0.13)],
        "gem": [_tone([(1319, 1319, 0.07), (1760, 1760, 0.14)], sample_rate, 0.13)],
        "pickup": [_tone([(523, 523, 0.07), (659, 659, 0.07), (784, 784, 0.14)], sample_rate, 0.14)],
        "swing": [_noise(0.13, sample_rate, 0.2, 0.3, whoosh=True)],
        "hit": [_mix(_tone([(170, 80, 0.12)], sample_rate, 0.22), _noise(0.08, sample_rate, 0.14, 0.35))],
        "hurt": [_tone([(300, 150, 0.25)], sample_rate, 0.2)],
        # A footstep is a low thud with a little scuff on top.
        "step": [
            _mix(_tone([(95, 55, 0.09)], sample_rate, 0.3), _noise(0.05, sample_rate, 0.07, 0.15)),
            _mix(_tone([(80, 50, 0.09)], sample_rate, 0.3), _noise(0.05, sample_rate, 0.07, 0.15)),
        ],
    }
    # A short, happy fanfare for winning the game.
    mono["victory"] = [
        _mix(
            _tone([(523, 523, 0.14), (659, 659, 0.14), (784, 784, 0.14), (1047, 1047, 0.9)], sample_rate, 0.15),
            array.array("h", [0] * int(sample_rate * 0.42))
            + _mix(_tone([(659, 659, 0.9)], sample_rate, 0.08), _tone([(784, 784, 0.9)], sample_rate, 0.08)),
        )
    ]
    for name, variants in mono.items():
        _sounds[name] = [_to_sound(samples, channels) for samples in variants]

    # Channel 0 is kept for the music, so sound effects never cut it off.
    pygame.mixer.set_reserved(1)
    _start_music(channels)


def play(name: str) -> None:
    """Plays one sound effect by name."""
    if _muted:
        return
    variants = _sounds.get(name)
    if variants:
        random.choice(variants).play()


def toggle_mute() -> bool:
    """Switches the sound on or off. Returns True when it is now muted."""
    global _muted
    _muted = not _muted
    if _music_channel is not None:
        _music_channel.set_volume(0.0 if _muted else MUSIC_VOLUME)
    return _muted
