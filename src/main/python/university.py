import csv
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime

BASE_URL = "https://ncaa-api.henrygd.me"
RATE_LIMIT_DELAY = 0.25  # stay under 5 req/sec

SPORT = "soccer-women"
DIVISION = "d3"
CONF = "all-conf"

# D3 women's soccer season typically spans Aug–Nov (+ some postseason in Dec)
MONTHS = ["08", "09", "10", "11"]
YEAR = "2025"

UNIVERSITY_CSV = "../output/University.csv"
CONFERENCE_CSV = "./output/Conference.csv"


class NCAAAPIError(Exception):
    pass


def ncaa_get(endpoint: str):
    url = f"{BASE_URL}{endpoint}"
    r = requests.get(url)
    if r.status_code != 200:
        raise NCAAAPIError(f"Error {r.status_code} for {url}: {r.text[:200]}")
    time.sleep(RATE_LIMIT_DELAY)
    return r.json()


def parse_mmddyyyy(date_str: str) -> Tuple[str, str, str]:
    """
    schedule returns contest_date like '02-01-2023' (MM-DD-YYYY)
    convert to ('YYYY','MM','DD')
    """
    dt = datetime.strptime(date_str, "%m-%d-%Y")
    return dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")


def get_game_dates_for_month(year: str, month: str) -> List[Tuple[str, str, str]]:
    sched = ncaa_get(f"/schedule/{SPORT}/{DIVISION}/{year}/{month}")
    dates: List[Tuple[str, str, str]] = []
    for gd in sched.get("gameDates", []):
        contest_date = gd.get("contest_date")
        if not contest_date:
            continue
        try:
            dates.append(parse_mmddyyyy(contest_date))
        except Exception:
            continue
    return dates


def pick_primary_conference(confs: list) -> Tuple[Optional[str], Optional[str]]:
    """
    Prefer non-'Top 25' conference when present.
    """
    if not isinstance(confs, list) or not confs:
        return None, None

    for c in confs:
        name = c.get("conferenceName")
        seo = c.get("conferenceSeo")
        if name and name.lower() != "top 25":
            return name, seo

    c0 = confs[0]
    return c0.get("conferenceName"), c0.get("conferenceSeo")


def extract_team(team: dict) -> Optional[dict]:
    if not isinstance(team, dict):
        return None

    team_id = team.get("teamId")
    names = team.get("names") or {}

    full = names.get("full") or names.get("short")

    if not team_id or not full:
        return None

    conf_name, conf_seo = pick_primary_conference(team.get("conferences", []))

    return {
        "university_id": int(team_id),   # ✅ INTEGER TEAM ID
        "name": full,
        "conference_name": conf_name,
        "conference_seo": conf_seo,
    }



def write_conferences_csv(conferences: Dict[str, dict], filename=CONFERENCE_CSV):
    fieldnames = ["conference_id", "name", "seo"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for conf in sorted(conferences.values(), key=lambda x: x["conference_id"]):
            w.writerow(conf)


def write_universities_csv(universities: Dict[int, dict], filename=UNIVERSITY_CSV):
    fieldnames = ["university_id", "name", "conference_id"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for uid in sorted(universities.keys()):
            u = universities[uid]
            w.writerow({
                "university_id": u["university_id"],
                "name": u["name"],
                "conference_id": u.get("conference_id"),
            })


def populate_university_conf():
    # 1) Collect all dates with games
    all_dates: List[Tuple[str, str, str]] = []
    for month in MONTHS:
        try:
            month_dates = get_game_dates_for_month(YEAR, month)
            print(f"{YEAR}-{month}: {len(month_dates)} game dates")
            all_dates.extend(month_dates)
        except Exception as e:
            print(f"Schedule fetch failed for {YEAR}-{month}: {e}")

    all_dates = sorted(set(all_dates))
    print(f"Total unique game dates: {len(all_dates)}")

    # 2) Crawl scoreboards and extract teams
    universities: Dict[str, dict] = {}
    conferences: Dict[str, dict] = {}
    next_conf_id = 1

    for (y, m, d) in all_dates:
        endpoint = f"/scoreboard/{SPORT}/{DIVISION}/{y}/{m}/{d}/{CONF}"
        try:
            board = ncaa_get(endpoint)
        except NCAAAPIError:
            continue

        for item in board.get("games", []):
            game = (item or {}).get("game", {})
            for side in ("home", "away"):
                t = extract_team(game.get(side))
                if not t:
                    continue

                uid = t["university_id"]

                # conference → integer id
                conf_id = None
                if t["conference_name"]:
                    if t["conference_name"] not in conferences:
                        conferences[t["conference_name"]] = {
                            "conference_id": next_conf_id,
                            "name": t["conference_name"],
                            "seo": t["conference_seo"],
                        }
                        next_conf_id += 1
                    conf_id = conferences[t["conference_name"]]["conference_id"]

                if uid not in universities:
                    universities[uid] = {
                        "university_id": uid,
                        "name": t["name"],
                        "conference_id": conf_id,
                    }
                else:
                    # fill missing conference if discovered later
                    if not universities[uid].get("conference_id") and conf_id:
                        universities[uid]["conference_id"] = conf_id

    # 3) Write outputs
    write_conferences_csv(conferences, UNIVERSITY_CSV)
    write_universities_csv(universities, CONFERENCE_CSV)

    print(f"Universities written: {len(universities)}")
    print(f"Conferences written: {len(conferences)}")
    print("Done.")
