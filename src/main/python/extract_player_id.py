import re
from typing import Dict, Optional

# Regex patterns (some potential duplicates because I combined two different extraction files into one)

BY_FIRST_LAST = re.compile(r"\bby\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")
BY_LAST_FIRST = re.compile(r"\bby\s+[A-Z]{2,4}\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)")
FOUL_ON = re.compile(r"Foul on\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)")
SAVE_BY = re.compile(r"Save by\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")
SUB_IN_OUT = re.compile(r"Sub (?:in|out)\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)")
BRACKET_TIME = re.compile(r"\[(\d{1,3}:\d{2})\]")
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

FOUL_ON_LAST_FIRST_1 = re.compile(r"\bfoul on\s+([^,]+),\s*([^.]+)", re.I)  # Foul on Last, First.
FOUL_ON_TEAM_1 = re.compile(r"\bfoul on\s+([A-Za-z].+?)\.\s*$", re.I)       # Foul on Springfield.
SAVE_BY_GOALIE_1 = re.compile(r"\bsave\s*\(by goalie\)\s*([^.]+)", re.I)    # Save (by goalie) First Last
ASSIST_BY_1 = re.compile(r"\bassist\s+by\s+([^.]+)", re.I)                  # Assist by First Last
BY_LAST_FIRST_1 = re.compile(r"\bby\s+[A-Z]{2,5}\s+([A-Za-zÀ-ÿ'’\-]+),\s*([A-Za-zÀ-ÿ'’\-]+)", re.I)
SAVE_BY_1 = re.compile(r"\bsave\s+by\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)", re.I)  # “Save  by …” too
SUB_IN_OUT_1 = re.compile(r"\bsub\s+(?:in|out)\s+([A-Za-zÀ-ÿ'’\-]+)\s+([A-Za-zÀ-ÿ'’\-]+)", re.I)
GENERIC_BY = re.compile(r"\bby\s+(.+)", re.I)  # everything after "by "
BRACKET_TIME_1 = re.compile(r"\[\s*\d{1,3}:\d{2}\s*\]")
LEADING_ALLCAPS_TEAM = re.compile(r"^\s*([A-Z]{2,5})\s+(.+)$")


# Helpers

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

def strip_allcaps_team_prefix(raw: str) -> str:
    """
    Removes leading ALLCAPS token like:
      'MIT Natalie Barnouw' -> 'Natalie Barnouw'
      'WAY Ngugi, Abby' is handled by comma patterns, but this helps too.
    """
    if not raw:
        return raw
    m = LEADING_ALLCAPS_TEAM.match(raw.strip())
    if not m:
        return raw
    # Heuristic: if remainder looks like a name (>= 2 tokens), drop token
    remainder = m.group(2).strip()
    if len(remainder.split()) >= 2:
        return remainder
    return raw

def cleanup_name_fragment(raw: str) -> str:
    """
    Aggressively trims name chunks:
      - removes [mm:ss]
      - removes trailing punctuation/clauses after , ( .
      - collapses whitespace
    """
    if not raw:
        return raw
    s = BRACKET_TIME_1.sub("", raw)
    s = s.strip()
    # cut off extra clauses: ", Wide." "(goalmouth:...)" etc.
    s = re.split(r"[,\(\.]", s, maxsplit=1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_name(name: str) -> Optional[tuple[str, str]]:
    """
    Turn 'Olivia Magierowski' -> ('olivia', 'magierowski')
    Turn 'Gabriela de Brito' -> ('gabriela', 'de brito')
    """
    if not name:
        return None
    parts = [p.strip() for p in name.split() if p.strip()]
    if len(parts) < 2:
        return None
    first = parts[0].lower()
    last = " ".join(parts[1:]).lower()
    return first, last

# Player lookup

def try_lookup(players: Dict[tuple, int], team_id: str, name_candidate: str) -> Optional[int]:
    """
    Try a sequence of normalizations:
      1) raw cleanup
      2) strip dot team prefix then cleanup
      3) strip ALLCAPS team prefix then cleanup
      4) strip both, then cleanup
    """
    if not name_candidate:
        return None

    attempts = []

    raw = cleanup_name_fragment(name_candidate)
    attempts.append(raw)

    dot_stripped = cleanup_name_fragment(strip_team_prefix(name_candidate))
    attempts.append(dot_stripped)

    allcaps_stripped = cleanup_name_fragment(strip_allcaps_team_prefix(name_candidate))
    attempts.append(allcaps_stripped)

    both = cleanup_name_fragment(strip_allcaps_team_prefix(strip_team_prefix(name_candidate)))
    attempts.append(both)

    for cand in attempts:
        nm = normalize_name(cand)
        if nm:
            pid = players.get((*nm, team_id))
            if pid:
                return pid

    return None


# Extract IDs

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
        nm = normalize_name(m.group(1))
        if nm:
            first, last = nm
            pid = player_lookup.get((first, last, team_id))
            if pid:
                return pid

    # 3) Assist by First Last (no team token)
    m = ASSIST_BY.search(text)
    if m:
        nm = normalize_name(m.group(1))
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
        nm = normalize_name(raw)
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


def extract_player_id_2(text: Optional[str],
                        team_id: Optional[str],
                        players: Dict[tuple, int]) -> Optional[int]:

    if not text or not team_id:
        return None

    # If it's a team foul with no player (e.g., "Foul on Springfield."), bail early.
    if FOUL_ON_TEAM_1.search(text):
        return None

    # Priority order: most explicit → most generic
    # Each returns either (first,last) or "name chunk" to be normalized.
    # 1) Foul on Last, First
    m = FOUL_ON_LAST_FIRST_1.search(text)
    if m:
        name_chunk = f"{m.group(2)} {m.group(1)}"
        pid = try_lookup(players, team_id, name_chunk)
        if pid:
            return pid

    # 2) Save (by goalie) Name
    m = SAVE_BY_GOALIE_1.search(text)
    if m:
        pid = try_lookup(players, team_id, m.group(1))
        if pid:
            return pid

    # 3) Assist by Name
    m = ASSIST_BY_1.search(text)
    if m:
        pid = try_lookup(players, team_id, m.group(1))
        if pid:
            return pid

    # 4) “Save by First Last” (handles double spaces too)
    m = SAVE_BY_1.search(text)
    if m:
        pid = try_lookup(players, team_id, f"{m.group(1)} {m.group(2)}")
        if pid:
            return pid

    # 5) “Sub in/out First Last”
    m = SUB_IN_OUT_1.search(text)
    if m:
        pid = try_lookup(players, team_id, f"{m.group(1)} {m.group(2)}")
        if pid:
            return pid

    # 6) “Foul on Last, First” (short token version)
    m = FOUL_ON.search(text)
    if m:
        pid = try_lookup(players, team_id, f"{m.group(2)} {m.group(1)}")
        if pid:
            return pid

    # 7) “by TEAM Last, First” (e.g., "Shot by WAY Ngugi, Abby, ...")
    m = BY_LAST_FIRST_1.search(text)
    if m:
        pid = try_lookup(players, team_id, f"{m.group(2)} {m.group(1)}")
        if pid:
            return pid

    # 8) “by First Last”
    m = BY_FIRST_LAST.search(text)
    if m:
        pid = try_lookup(players, team_id, f"{m.group(1)} {m.group(2)}")
        if pid:
            return pid

    # 9) Generic “by ...” (covers: "Shot by Westfield St. Morgan Berthiaume", "Corner kick by MIT Natalie Barnouw")
    m = GENERIC_BY.search(text)
    if m:
        pid = try_lookup(players, team_id, m.group(1))
        if pid:
            return pid

    return None

