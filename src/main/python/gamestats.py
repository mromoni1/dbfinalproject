# gamestats.py
import csv
import os
import json
import hashlib
from math import floor
from api import ncaa_get, NCAAAPIError

GAMESTATS_CSV = "gamestats.csv"

GAMESTATS_FIELDS = [
    "game_id",
    "player_id",

    # player metadata (for players.py)
    "first_name",
    "last_name",
    "position",
    "university_id",

    # per-game stats
    "played",
    "started",
    "shots",
    "shots_on_target",
    "goals",
    "assists",
    "minutes",
    "pk_attempt",
    "pk_made",
    "gw",
    "yc",
    "rc",
]

def ncaa_get_gamestats(game_id):
    return ncaa_get(f"/game/{game_id}")["boxscore"]

def to_int(val, default=0):
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default

def gamestats_to_csv(rows, filename=GAMESTATS_CSV):
    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GAMESTATS_FIELDS)

        if not file_exists:
            writer.writeheader()

        for row in rows:
            writer.writerow(row)

def make_player_id(team_id, first, last):
    key = f"{team_id}:{first}:{last}".encode("utf-8")
    return int(hashlib.md5(key).hexdigest()[:8], 16)

def parse_boxscore_to_gamestats(boxscore_json):
    game_id = int(boxscore_json["contestId"])
    rows = []

    for team in boxscore_json.get("teamBoxscore", []):
        university_id = int(team["teamId"])

        for p in team.get("playerStats", []):
            first = p.get("firstName", "").strip()
            last = p.get("lastName", "").strip()
            position = p.get("position")

            player_id = make_player_id(university_id, first, last)

            penalties = p.get("penalties", {})
            goal_types = p.get("goalTypes", {})
            minutes = p.get("minutesPlayed")

            row = {
                "game_id": game_id,
                "player_id": player_id,

                # player metadata
                "first_name": first,
                "last_name": last,
                "position": position,
                "university_id": university_id,

                # stats
                "played": bool(p.get("participated")),
                "started": bool(p.get("starter")),
                "shots": to_int(p.get("shots")),
                "shots_on_target": to_int(p.get("shotsOnGoal")),
                "goals": to_int(p.get("goals")),
                "assists": to_int(p.get("assists")),
                "minutes": floor(float(minutes)) if minutes not in ("", None) else 0,
                "pk_attempt": to_int(p.get("penaltyShotAttempts")),
                "pk_made": to_int(p.get("penaltyShotGoals")),
                "gw": to_int(goal_types.get("gameWinningGoals")) > 0,
                "yc": to_int(penalties.get("yellowCards")),
                "rc": to_int(penalties.get("redCards")),
            }

            rows.append(row)

    return rows

def populate_game_stats():
    with open("game_ids.json", "r") as f:
        game_ids = json.load(f)

    for i, gid in enumerate(game_ids, 1):
        try:
            print(f"[{i}/{len(game_ids)}] Processing game {gid}")
            boxscore = ncaa_get_gamestats(gid)

            if not boxscore or "teamBoxscore" not in boxscore:
                print(f"Skipping game {gid}: no boxscore")
                continue

            rows = parse_boxscore_to_gamestats(boxscore)
            gamestats_to_csv(rows)

        except NCAAAPIError as e:
            print(f"Skipping game {gid}: API error {e}")
        except Exception as e:
            print(f"Skipping game {gid}: {e}")
