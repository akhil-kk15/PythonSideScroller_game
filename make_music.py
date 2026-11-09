"""Builds the background music and saves it to assets/music/theme.wav."""

import array
import math
import os
import wave

SAMPLE_RATE = 22050
BEATS_PER_MINUTE = 92
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music", "theme.wav")

CHORDS = [
    (110.00, (220.00, 261.63, 329.63)),
    (87.31, (174.61, 220.00, 261.63)),
    (130.81, (261.63, 329.63, 392.00)),
    (98.00, (196.00, 246.94, 293.66)),
]
ARPEGGIOS = ([0, 1, 2, 1, 2, 1, 0, 1], [2, 1, 0, 1, 2, 1, 0, 2])


def render_music():
    """Returns one loop of music as a list of samples."""
    beat = 60.0 / BEATS_PER_MINUTE
    bar = 4 * beat
    total = int(SAMPLE_RATE * bar * 2 * len(CHORDS))
    buffer = [0.0] * total

    def add_note(freq, start, length, volume, attack, fade, second_harmonic=0.0):
        first = int(start * SAMPLE_RATE)
        for i in range(int(length * SAMPLE_RATE)):
            t = i / SAMPLE_RATE
            envelope = min(1.0, t / attack) * fade(t, length)
            wave_value = math.sin(2 * math.pi * freq * t)
            if second_harmonic:
                wave_value += second_harmonic * math.sin(4 * math.pi * freq * t)
            buffer[(first + i) % total] += wave_value * envelope * volume

    def swell(t, length):
        return min(1.0, (length - t) / 0.6)

    def pluck(t, length):
        return math.exp(-t * 5.0)

    for chord_index, (bass, pad) in enumerate(CHORDS):
        chord_start = chord_index * 2 * bar
        for freq in pad:
            add_note(freq, chord_start, 2 * bar + 0.3, 0.05, 0.4, swell)
        for beat_number in range(8):
            add_note(bass, chord_start + beat_number * beat, beat * 1.2, 0.12, 0.02, pluck)
        for bar_number in range(2):
            for step, tone_index in enumerate(ARPEGGIOS[bar_number]):
                start = chord_start + bar_number * bar + step * beat / 2
                add_note(pad[tone_index] * 2, start, beat, 0.07, 0.01, pluck, 0.2)
    return buffer


def main():
    samples = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in render_music()))
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with wave.open(OUTPUT_FILE, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(samples.tobytes())
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
