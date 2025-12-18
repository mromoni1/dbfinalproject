import csv
import os
import json
import time 
from datetime import datetime
from api import ncaa_get   # ← SAFE, one direction only

GAME_CSV_FILE = "octdev.csv"
GAME_CSV_FIELDS = [
    "game_id",
    "home_team_id",
    "away_team_id",
    "home_score",
    "away_score",
    "location",
    "game_date",
    "game_time",
]
def normalize_contest_date(date_str):
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date format: {date_str}")


def ncaa_get_game(game_id):
    return ncaa_get(f"/game/{game_id}")    

def write_game_ids():
    sport = "soccer-women"
    division = "d3"
    season = 2025

    game_ids = set()

    for month in range(8, 12):
        month_str = f"{month:02d}"
        print(f"Fetching schedule for {season}-{month_str}")

        schedule = ncaa_get(
            f"/schedule/{sport}/{division}/{season}/{month_str}"
        )

        for day in schedule.get("gameDates", []):
            if day.get("games", 0) == 0:
                continue

            dt = normalize_contest_date(day["contest_date"])
            year, mm, dd = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")

            print(f"  Fetching scoreboard for {year}-{mm}-{dd}")

            scoreboard = ncaa_get(
                f"/scoreboard/{sport}/{division}/{year}/{mm}/{dd}/all-conf"
            )

            for g in scoreboard.get("games", []):
                game = g.get("game", {})

                url = game.get("url")  
                if not url:
                    continue

                try:
                    game_id = int(url.split("/")[-1])
                except ValueError:
                    continue

                game_ids.add(game_id)

    game_ids = sorted(game_ids)
    print(f"Found {len(game_ids)} total games")

    with open("game_ids.json", "w") as f:
        json.dump(game_ids, f)

    return game_ids


def parse_single_game_for_csv(game_data):
    contests = game_data.get("contests", [])
    if not contests:
        raise ValueError("No contest data available")
    contest = contests[0]

    teams = contest["teams"]
    home = next(t for t in teams if t["isHome"])
    away = next(t for t in teams if not t["isHome"])

    dt = datetime.fromtimestamp(contest["startTimeEpoch"])

    home_score = home.get("score")
    away_score = away.get("score")
    if home_score is None or away_score is None:
        raise ValueError("Game not completed")

    return {
        "game_id": int(contest["id"]),
        "home_team_id": int(home["teamId"]),
        "away_team_id": int(away["teamId"]),
        "home_score": home_score,
        "away_score": away_score,
        "location": contest.get("location"),
        "game_date": dt.date().isoformat(),
        "game_time": dt.time().strftime("%H:%M:%S"),
    }


def games_to_csv(games, filename=GAME_CSV_FILE):
    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GAME_CSV_FIELDS)

        if not file_exists:
            writer.writeheader()

        for game in games:
            writer.writerow(game)

def populate_games():
    with open("validated_ids/validated_oct_nov_game_ids.json", "r") as f:
        game_ids = json.load(f)

    rows = []
    for i, gid in enumerate(game_ids, 1):
        try:
            print(f"[{i}/{len(game_ids)}] Fetching game {gid}")

            game_data = ncaa_get_game(gid)

            if game_data['contests'][0].get("sportCode") != "WSO":
                continue

            if game_data['contests'][0].get("division") != 3:
                print(f"  → not D3")
                continue

            row = parse_single_game_for_csv(game_data)
            rows.append(row)

            print(f"  → saved")

        except Exception as e:
            print(f"  → skipping: {type(e).__name__}")

        time.sleep(0.15)

    games_to_csv(rows, filename=GAME_CSV_FILE)