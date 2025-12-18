# players.py
import csv
import os

PLAYERS_CSV = "../output/Player.csv"
GAMESTATS_CSV = "../output/GameStats.csv"

PLAYER_FIELDS = [
    "player_id",
    "first_name",
    "last_name",
    "class_grade",
    "position",
    "university_id",
]

def load_existing_players():
    """
    Returns a set of (first_name, last_name, university_id)
    """
    if not os.path.isfile(PLAYERS_CSV):
        return set()

    seen = set()
    with open(PLAYERS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (
                r["first_name"].strip().lower(),
                r["last_name"].strip().lower(),
                str(r["university_id"]),
            )
            seen.add(key)
    return seen


def populate_players_from_gamestats():
    seen_players = load_existing_players()
    rows = []

    with open(GAMESTATS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            key = (
                r["first_name"].strip().lower(),
                r["last_name"].strip().lower(),
                str(r["university_id"]),
            )

            # Deduplicate by natural key
            if key in seen_players:
                continue

            seen_players.add(key)

            rows.append({
                "player_id": int(r["player_id"]),
                "first_name": r["first_name"].strip(),
                "last_name": r["last_name"].strip(),
                "class_grade": "",
                "position": r["position"],
                "university_id": int(r["university_id"]),
            })

    write_players(rows)


def write_players(players):
    file_exists = os.path.isfile(PLAYERS_CSV)

    with open(PLAYERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerows(players)

