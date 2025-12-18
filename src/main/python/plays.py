import csv
import os
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from api import ncaa_get, NCAAAPIError
from extract_player_id import extract_player_id, extract_player_id_1, extract_player_id_2

# Configuration

PLAY_CSV_FILE = "../output/OctNovPlay.csv"
GAME_IDS_FILE = "../output/validated_ids/validated_oct_nov_game_ids.json"
PLAYER_CSV_FILE = "../output/Player.csv"

RATE_LIMIT_DELAY = 0.25  # 5 req/sec

PLAY_FIELDS = [
    "play_id",
    "game_id",
    "player_id",
    "time_of_play",
    "event_type",
    "description",
]

# Helpers

def parse_time(clock: Optional[str]) -> Optional[str]:
    if not clock:
        return None
    try:
        return datetime.strptime(clock, "%M:%S").time().strftime("%H:%M:%S")
    except ValueError:
        return None

def classify_event(text: Optional[str]) -> str:
    if not text:
        return "OTHER"

    t = text.lower()

    # Order matters — most specific first
    if re.search(r"\bgoal\b", t):
        return "GOAL"
    if re.search(r"\bshot\b", t):
        return "SHOT"
    if re.search(r"\bsave\b", t):
        return "SAVE"
    if re.search(r"\bfoul\b", t):
        return "FOUL"
    if re.search(r"\bfoulwon\b", t):
        return "FOUL_WON"
    if re.search(r"\bcardred\b", t):
        return "RED_CARD"
    if re.search(r"\bcardyellow\b", t):
        return "YELLOW_CARD"
    if re.search(r"\bsub\b", t):
        return "SUBSTITUTION"
    if re.search(r"\bcorner\b", t):
        return "CORNER"
    if re.search(r"\bfree\s*kick\b", t):
        return "FREE_KICK"
    if re.search(r"\bthrow\s*in\b|\bthrowin\b", t):
        return "THROW_IN"
    if re.search(r"\boffside\b", t):
        return "OFFSIDE"
    if re.search(r"\bcard\b", t):
        return "CARD"
    if re.search(r"\bkickoff\b", t):
        return "KICKOFF"

    return "OTHER"


def load_players() -> Dict[tuple, int]:
    lookup: Dict[tuple, int] = {}
    with open(PLAYER_CSV_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lookup[
                (
                    r["first_name"].lower().strip(),
                    r["last_name"].lower().strip(),
                    str(r["university_id"]).strip(),
                )
            ] = int(r["player_id"])
    return lookup


# API

def ncaa_get_play_by_play(game_id: int) -> dict:
    return ncaa_get(f"/game/{game_id}/play-by-play")


def parse_game_plays(pbp: dict,
                     player_lookup: Dict[tuple, int],
                     play_id_start: int) -> List[dict]:

    contest_id = pbp.get("contestId")
    if not contest_id:
        return []

    team_map = {
        str(t.get("teamId")): str(t.get("teamId"))
        for t in pbp.get("teams", [])
    }

    rows: List[dict] = []
    play_id = play_id_start

    for period in pbp.get("periods", []):
        for stat in period.get("playbyplayStats", []):
            team_id = team_map.get(str(stat.get("teamId")))

            for play in stat.get("plays", []):
                text = play.get("playText")

                clock = play.get("clock")
                if not clock: 
                    clock = parse_time(clock)

                event_type = classify_event(text)

                pid = extract_player_id_1(text, team_id, player_lookup)
                if not pid:
                    pid = extract_player_id(text, team_id, player_lookup)
                if not pid: 
                    pid = extract_player_id_2(text, team_id, player_lookup)

                # Explicit exclusions
                if event_type in {"THROW_IN", "OTHER"}:
                    continue

                rows.append({
                    "play_id": play_id,
                    "game_id": contest_id,
                    "player_id": pid,
                    "time_of_play": clock,
                    "event_type": event_type,
                    "description": text,
                })

                play_id += 1


    return rows


def write_plays(rows: List[dict]):
    file_exists = os.path.isfile(PLAY_CSV_FILE)

    with open(PLAY_CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAY_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def populate_plays():
    player_lookup = load_players()
    print(f"Loaded {len(player_lookup)} players")

    with open(GAME_IDS_FILE) as f:
        game_ids = json.load(f)

    total = 0
    play_id_counter = 1

    for i, gid in enumerate(game_ids, 1):
        try:
            print(f"[{i}/{len(game_ids)}] Game {gid}")
            pbp = ncaa_get_play_by_play(gid)

            rows = parse_game_plays(
                pbp,
                player_lookup,
                play_id_counter
            )

            play_id_counter += len(rows)
            write_plays(rows)
            total += len(rows)

        except NCAAAPIError:
            print(f"Skipping game {gid}: API error")
        except Exception as e:
            print(f"Skipping game {gid}: {e}")

        time.sleep(RATE_LIMIT_DELAY)

    print(f"Done. Total plays written: {total}")
