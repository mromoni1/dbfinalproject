import requests
import time
import json
from datetime import datetime
from university import populate_university_conf
from rankings import populate_rankings
from games import populate_games, write_game_ids
from gamestats import populate_game_stats
from players import populate_players_from_gamestats
from plays import populate_plays

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
    # UNIVERSITY + CONFERENCE
    populate_university_conf()

    # RANKINGS
    populate_rankings()

    # GAMES
    populate_games()

    # GAMESTATS 
    populate_game_stats()
    
    # PLAYERS
    populate_players_from_gamestats()

    # PLAY-BY-PLAY
    populate_plays()



if __name__ == "__main__":
    main()
