import csv
import os
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from api import ncaa_get, NCAAAPIError

# ==========================
# Configuration
# ==========================

PLAY_CSV_FILE = "../output/Play.csv"
GAME_IDS_FILE = "../output/test_game_id.json"
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

# ==========================
# Regex patterns (player extraction only)
# ==========================

BY_FIRST_LAST = re.compile(r"\bby\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")
BY_LAST_FIRST = re.compile(r"\bby\s+[A-Z]{2,4}\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)")
FOUL_ON = re.compile(r"Foul on\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)")
SAVE_BY = re.compile(r"Save by\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")
SUB_IN_OUT = re.compile(r"Sub (?:in|out)\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")

# ==========================
# Helpers
# ==========================

def parse_time(clock: Optional[str]) -> Optional[str]:
    if not clock:
        return None
    for fmt in ("%H:%M:%S", "%M:%S"):
        try:
            return datetime.strptime(clock, fmt).time().strftime("%H:%M:%S")
        except ValueError:
            pass
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
    lookup = {}
    with open(PLAYER_CSV_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (
                r["first_name"].lower(),
                r["last_name"].lower(),
                str(r["university_id"]),
            )
            lookup[key] = int(r["player_id"])
    return lookup


def extract_player_id(text: str,
                      team_id: Optional[str],
                      player_lookup: Dict[tuple, int]) -> Optional[int]:
    if not text or not team_id:
        return None

    for regex, order in [
        (BY_LAST_FIRST, ("last", "first")),
        (FOUL_ON, ("last", "first")),
        (BY_FIRST_LAST, ("first", "last")),
        (SAVE_BY, ("first", "last")),
        (SUB_IN_OUT, ("first", "last")),
    ]:
        m = regex.search(text)
        if m:
            if order[0] == "first":
                first, last = m.group(1), m.group(2)
            else:
                last, first = m.group(1), m.group(2)

            return player_lookup.get(
                (first.lower(), last.lower(), team_id)
            )

    return None


# ==========================
# API
# ==========================

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

                event_type = classify_event(text)

                # Explicit exclusions
                if event_type in {"THROW_IN", "OTHER"}:
                    continue

                rows.append({
                    "play_id": play_id,
                    "game_id": contest_id,
                    "player_id": extract_player_id(
                        text, team_id, player_lookup
                    ),
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


if __name__ == "__main__":
    populate_plays()