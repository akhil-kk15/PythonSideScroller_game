# Highscore list that is saved in a text file, so it is kept after the game closes.
#
# Every line of the file is one entry:   score;level;date
# Example:                               4350;2;2026-11-07

import os
from datetime import date

MAX_ENTRIES = 5  # only the best five scores are kept


def load_highscores(path):
    # Read the file and return a list of entries, best score first.
    # Each entry is a dict: {"score": 4350, "level": 2, "date": "2026-11-07"}
    entries = []
    if not os.path.exists(path):
        return entries  # no game has been finished yet

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line == "":
                continue
            try:
                score, level, day = line.split(";")
                entries.append({"score": int(score), "level": int(level), "date": day})
            except ValueError:
                # A broken line should not crash the game, so we skip it.
                print("Skipping broken highscore line:", line)

    entries = sorted(entries, key=lambda entry: entry["score"], reverse=True)
    return entries[:MAX_ENTRIES]


def save_highscores(path, entries):
    with open(path, "w", encoding="utf-8") as file:
        for entry in entries:
            file.write(f"{entry['score']};{entry['level']};{entry['date']}\n")


def add_highscore(path, score, level):
    # Add a finished game to the list.
    # Returns the place in the list (1 = best), or None if the score was too low.
    new_entry = {"score": score, "level": level, "date": date.today().isoformat()}
    entries = load_highscores(path)
    entries.append(new_entry)
    entries = sorted(entries, key=lambda entry: entry["score"], reverse=True)[:MAX_ENTRIES]
    save_highscores(path, entries)

    if new_entry in entries:
        return entries.index(new_entry) + 1
    return None


def highscore_lines(entries, new_place=None):
    # Text lines for the menu: one line per place, always MAX_ENTRIES lines.
    lines = []
    for place in range(1, MAX_ENTRIES + 1):
        if place <= len(entries):
            entry = entries[place - 1]
            line = f"{place}.   {entry['score']:>5}   Level {entry['level']}   {entry['date']}"
            if place == new_place:
                line += "   << NEW!"
        else:
            line = f"{place}.   -----"
        lines.append(line)
    return lines


def best_score_text(path):
    entries = load_highscores(path)
    if len(entries) == 0:
        return "No highscore yet - be the first!"
    return f"Best score: {entries[0]['score']}"
