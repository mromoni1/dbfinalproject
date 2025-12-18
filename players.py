# players.py
import csv
import os

PLAYERS_CSV = "players.csv"
GAMESTATS_CSV = "gamestats.csv"

PLAYER_FIELDS = [
    "player_id",
    "first_name",
    "last_name",
    "class_grade",
    "position",
    "university_id",
]

def load_existing_player_ids():
    if not os.path.isfile(PLAYERS_CSV):
        return set()

    with open(PLAYERS_CSV, newline="", encoding="utf-8") as f:
        return {int(r["player_id"]) for r in csv.DictReader(f)}

def populate_players_from_gamestats():
    seen = load_existing_player_ids()
    rows = []

    with open(GAMESTATS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            pid = int(r["player_id"])
            if pid in seen:
                continue

            seen.add(pid)

            rows.append({
                "player_id": pid,
                "first_name": r["first_name"],
                "last_name": r["last_name"],
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

        for p in players:
            writer.writerow(p)
