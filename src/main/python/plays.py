import csv
import os
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from api import ncaa_get, NCAAAPIError
from play import extract_player_id_2

# ==========================
# Configuration
# ==========================

PLAY_CSV_FILE = "../output/AugSeptPlay.csv"
GAME_IDS_FILE = "../output/validated_ids/validated_aug_sept_game_ids.json"
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
BRACKET_TIME = re.compile(r"\[(\d{1,3}:\d{2})\]")
BRACKET_TIME_1 = re.compile(r"\[\d{1,3}:\d{2}\]")
BY_NAME_GENERIC = re.compile(
    r"\bby\s+(?:[A-Z]{2,5}\s+)?([A-Za-zÀ-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÿ'’\-]+)*)",
    re.IGNORECASE
)
ASSIST_BY = re.compile(
    r"\bassist\s+by\s+([A-Za-zÀ-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÿ'’\-]+)*)",
    re.IGNORECASE
)
SAVE_BY_GOALIE = re.compile(
    r"\bsave\s*\(by goalie\)\s*([A-Za-zÀ-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÿ'’\-]+)*)",
    re.IGNORECASE
)
FOUL_ON_LAST_FIRST = re.compile(
    r"\bfoul on\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)",
    re.IGNORECASE
)

TEAM_PREFIX_DOT = re.compile(
    r"^\s*([A-Za-z&'’\-]+(?:\s+[A-Za-z&'’\-]+){0,3})\.\s+"
)

def strip_team_prefix(name_chunk: str) -> str:
    """
    Removes leading team labels like:
      'Worcester St. Olivia Magierowski' -> 'Olivia Magierowski'
      'Westfield St. Morgan Berthiaume'  -> 'Morgan Berthiaume'
    Keeps real names that don't start with a dotted team prefix.
    """
    if not name_chunk:
        return name_chunk

    # remove ONE leading "<words>." pattern (e.g., "Worcester St.")
    return TEAM_PREFIX_DOT.sub("", name_chunk, count=1).strip()


def parse_time(clock: Optional[str]) -> Optional[str]:
    if not clock:
        return None
    try:
        return datetime.strptime(clock, "%M:%S").time().strftime("%H:%M:%S")
    except ValueError:
        return None
    


# ==========================
# Helpers
# ==========================

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

import re
from typing import Optional, Dict, Tuple


def normalize_name_phrase(name_phrase: str) -> Optional[Tuple[str, str]]:
    """
    Convert "Gabriela de Brito" -> ("gabriela", "de brito")
    Convert "Natalie Barnouw" -> ("natalie", "barnouw")
    """
    if not name_phrase:
        return None

    parts = [p.strip() for p in name_phrase.strip().split() if p.strip()]
    if len(parts) < 2:
        return None

    first = parts[0].lower()
    last = " ".join(parts[1:]).lower()
    return first, last


def extract_player_id(text: Optional[str],
                      team_id: Optional[str],
                      player_lookup: Dict[tuple, int]) -> Optional[int]:
    """
    Attempts multiple patterns and supports multi-word last names.
    team_id should be the numeric teamId string from pbp (matches university_id in Player.csv).
    """
    if not text or not team_id:
        return None

    # 1) Foul on Last, First
    m = FOUL_ON_LAST_FIRST.search(text)
    if m:
        last = m.group(1).lower()
        first = m.group(2).lower()
        return player_lookup.get((first, last, team_id))

    # 2) Save (by goalie) First Last
    m = SAVE_BY_GOALIE.search(text)
    if m:
        nm = normalize_name_phrase(m.group(1))
        if nm:
            first, last = nm
            pid = player_lookup.get((first, last, team_id))
            if pid:
                return pid

    # 3) Assist by First Last (no team token)
    m = ASSIST_BY.search(text)
    if m:
        nm = normalize_name_phrase(m.group(1))
        if nm:
            first, last = nm
            pid = player_lookup.get((first, last, team_id))
            if pid:
                return pid

    # 4) Generic "... by [TEAM] First Last[,.(...]"
    m = BY_NAME_GENERIC.search(text)
    if m:
        raw = m.group(1)
        raw = strip_team_prefix(raw)
        nm = normalize_name_phrase(raw)
        if nm:
            first, last = nm
            return player_lookup.get((first, last, team_id))


    return None


def extract_player_id_1(text: str,
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

def parse_time(clock: Optional[str]) -> Optional[str]:
    if not clock:
        return None
    try:
        return datetime.strptime(clock, "%M:%S").time().strftime("%H:%M:%S")
    except ValueError:
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


if __name__ == "__main__":
    populate_plays()