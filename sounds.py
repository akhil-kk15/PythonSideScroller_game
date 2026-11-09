"""Small retro sound effects, synthesized in code (no audio files needed).

Call init() once after pygame.init(). Then play("jump") anywhere. If the
computer has no audio device, every call quietly does nothing.
"""

import array
import math
import random

import pygame

VOLUME = 0.3

_sounds: dict[str, pygame.mixer.Sound] = {}
_muted = False


def _square_notes(notes, sample_rate):
    """Builds mono samples for notes given as (start_hz, end_hz, seconds)."""
    samples = array.array("h")
    for start_hz, end_hz, seconds in notes:
        count = int(sample_rate * seconds)
        phase = 0.0
        for i in range(count):
            progress = i / count
            phase += (start_hz + (end_hz - start_hz) * progress) / sample_rate
            wave = 1.0 if (phase % 1.0) < 0.5 else -1.0
            samples.append(int(wave * (1.0 - progress) * VOLUME * 32767))
    return samples


def _noise(seconds, sample_rate, loudness=0.7):
    """Builds mono samples of a fading burst of noise."""
    samples = array.array("h")
    count = int(sample_rate * seconds)
    for i in range(count):
        fade = 1.0 - i / count
        samples.append(int(random.uniform(-1.0, 1.0) * fade * VOLUME * loudness * 32767))
    return samples


def _mix(first, second):
    """Plays two sample lists at the same time."""
    length = max(len(first), len(second))
    mixed = array.array("h")
    for i in range(length):
        a = first[i] if i < len(first) else 0
        b = second[i] if i < len(second) else 0
        mixed.append(max(-32767, min(32767, a + b)))
    return mixed


def _to_sound(samples, channels):
    """Turns mono samples into a Sound that matches the mixer's channel count."""
    if channels > 1:
        stereo = array.array("h")
        for value in samples:
            stereo.extend([value] * channels)
        samples = stereo
    return pygame.mixer.Sound(buffer=samples.tobytes())


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

    mono = {
        "click": _square_notes([(880, 660, 0.05)], sample_rate),
        "step": _noise(0.04, sample_rate, 0.35),
        "jump": _square_notes([(260, 520, 0.12)], sample_rate),
        "coin": _square_notes([(988, 988, 0.06), (1319, 1319, 0.1)], sample_rate),
        "gem": _square_notes([(1319, 1319, 0.06), (1760, 1760, 0.12)], sample_rate),
        "pickup": _square_notes([(523, 523, 0.07), (659, 659, 0.07), (784, 784, 0.12)], sample_rate),
        "swing": _noise(0.08, sample_rate),
        "hit": _mix(_square_notes([(180, 90, 0.12)], sample_rate), _noise(0.1, sample_rate)),
        "hurt": _square_notes([(330, 110, 0.25)], sample_rate),
    }
    for name, samples in mono.items():
        _sounds[name] = _to_sound(samples, channels)


def play(name: str) -> None:
    """Plays one sound effect by name."""
    if _muted:
        return
    sound = _sounds.get(name)
    if sound is not None:
        sound.play()


def toggle_mute() -> bool:
    """Switches the sound on or off. Returns True when it is now muted."""
    global _muted
    _muted = not _muted
    return _muted
