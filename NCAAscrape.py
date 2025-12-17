import requests
import time
import json
from datetime import datetime
from games import populate_games, write_game_ids
from gamestats import populate_game_stats

BASE_URL = "http://localhost:3000"
RATE_LIMIT_DELAY = 0.0
_session = requests.Session()

GAMES_CSV_FILE = "games.csv"
GAMES_CSV_FIELDS = [
    "game_id",
    "home_team_id",
    "away_team_id",
    "home_score",
    "away_score",
    "location",
    "game_date",
    "game_time",
]

class NCAAAPIError(Exception):
    pass

def ncaa_get(path, params=None, headers=None, timeout=30):
    url = f"{BASE_URL}{path}"
    r = _session.get(url, params=params, headers=headers, timeout=timeout)
    if r.status_code != 200:
        raise NCAAAPIError(f"Error {r.status_code} for {url}: {r.text}")
    if RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY)
    return r.json()


def main():
    # COLLECT GAME IDS 
    # write_game_ids()

    # GAMES
    populate_games()

    # GAMESTATS 
    #populate_game_stats()
    

if __name__ == "__main__":
    main()
