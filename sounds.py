"""Sound effects and music."""

import array
import math
import os
import random

import pygame

MUSIC_VOLUME = 0.35
MUSIC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music", "theme.wav")

_sounds: dict[str, list[pygame.mixer.Sound]] = {}
_muted = False
_music_on = False
_music_channel = None


def _tone(notes, sample_rate, volume):
    """Returns mono samples for a list of notes."""
    samples = array.array("h")
    attack = max(1, int(sample_rate * 0.006))
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
    """Returns mono samples of soft noise."""
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
    """Mixes sample lists together."""
    mixed = array.array("h")
    for i in range(max(len(part) for part in parts)):
        total = sum(part[i] for part in parts if i < len(part))
        mixed.append(max(-32767, min(32767, total)))
    return mixed


def _to_sound(samples, channels):
    """Makes a Sound from mono samples."""
    if channels > 1:
        stereo = array.array("h")
        for value in samples:
            stereo.extend([value] * channels)
        samples = stereo
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _start_music(channels):
    """Starts the music loop."""
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
    """Turns the music on or off."""
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
    """Creates the sound effects."""
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
        "click": [_tone([(700, 520, 0.05)], sample_rate, 0.16)],
        "jump": [_tone([(240, 420, 0.14)], sample_rate, 0.16)],
        "coin": [_tone([(988, 988, 0.07), (1319, 1319, 0.12)], sample_rate, 0.13)],
        "gem": [_tone([(1319, 1319, 0.07), (1760, 1760, 0.14)], sample_rate, 0.13)],
        "pickup": [_tone([(523, 523, 0.07), (659, 659, 0.07), (784, 784, 0.14)], sample_rate, 0.14)],
        "swing": [_noise(0.13, sample_rate, 0.2, 0.3, whoosh=True)],
        "hit": [_mix(_tone([(170, 80, 0.12)], sample_rate, 0.22), _noise(0.08, sample_rate, 0.14, 0.35))],
        "hurt": [_tone([(300, 150, 0.25)], sample_rate, 0.2)],
        "step": [
            _mix(_tone([(95, 55, 0.09)], sample_rate, 0.3), _noise(0.05, sample_rate, 0.07, 0.15)),
            _mix(_tone([(80, 50, 0.09)], sample_rate, 0.3), _noise(0.05, sample_rate, 0.07, 0.15)),
        ],
    }
    mono["victory"] = [
        _mix(
            _tone([(523, 523, 0.14), (659, 659, 0.14), (784, 784, 0.14), (1047, 1047, 0.9)], sample_rate, 0.15),
            array.array("h", [0] * int(sample_rate * 0.42))
            + _mix(_tone([(659, 659, 0.9)], sample_rate, 0.08), _tone([(784, 784, 0.9)], sample_rate, 0.08)),
        )
    ]
    for name, variants in mono.items():
        _sounds[name] = [_to_sound(samples, channels) for samples in variants]

    pygame.mixer.set_reserved(1)
    _start_music(channels)


def play(name: str) -> None:
    """Plays a sound effect."""
    if _muted:
        return
    variants = _sounds.get(name)
    if variants:
        random.choice(variants).play()


def toggle_mute() -> bool:
    """Mutes or unmutes the sound. Returns True when muted."""
    global _muted
    _muted = not _muted
    if _music_channel is not None:
        _music_channel.set_volume(0.0 if _muted else MUSIC_VOLUME)
    return _muted
