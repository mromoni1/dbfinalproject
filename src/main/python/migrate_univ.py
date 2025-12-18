import csv
import json
import time
from typing import Dict
from api import ncaa_get

RATE_LIMIT_DELAY = 0.25

OLD_UNIV_CSV = "universities.csv"          # char6-based
NEW_UNIV_CSV = "universities_teamid.csv"  # teamId-based
GAME_IDS_FILE = "../validated_ids/validated_aug_sept_game_ids.json"


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .replace(".", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("&", "and")
        .strip()
    )


def load_old_universities() -> Dict[str, dict]:
    """
    char6 -> university row
    """
    lookup = {}
    with open(OLD_UNIV_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            lookup[r["university_id"]] = {
                "char6": r["university_id"],
                "name": r["name"],
                "conference_id": r.get("conference_id"),
                "norm_name": normalize_name(r["name"]),
            }
    return lookup


def main():
    old_univs = load_old_universities()

    # name -> teamId
    name_to_teamid: Dict[str, int] = {}

    with open(GAME_IDS_FILE) as f:
        game_ids = json.load(f)

    for i, gid in enumerate(game_ids, 1):
        print(f"[{i}/{len(game_ids)}] Fetching game {gid}")

        try:
            data = ncaa_get(f"/game/{gid}")
            contest = data["contests"][0]

            if contest.get("sportCode") != "WSO" or contest.get("division") != 3:
                continue

            for t in contest.get("teams", []):
                team_id = t.get("teamId")
                name = t.get("nameFull") or t.get("nameShort")

                if team_id and name:
                    norm = normalize_name(name)
                    name_to_teamid[norm] = int(team_id)

        except Exception:
            pass

        time.sleep(RATE_LIMIT_DELAY)

    # Build new universities
    new_rows = []
    unmatched = []

    for char6, u in old_univs.items():
        team_id = name_to_teamid.get(u["norm_name"])
        if not team_id:
            unmatched.append(u["name"])
            continue

        new_rows.append({
            "university_id": team_id,
            "name": u["name"],
            "conference_id": u["conference_id"],
        })

    # Write new CSV
    with open(NEW_UNIV_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["university_id", "name", "conference_id"]
        )
        writer.writeheader()
        for r in sorted(new_rows, key=lambda x: x["university_id"]):
            writer.writerow(r)

    print(f"\nConverted universities: {len(new_rows)}")
    print(f"Unmatched universities: {len(unmatched)}")

    if unmatched:
        print("\n⚠️ Unmatched schools (manual review):")
        for u in unmatched:
            print("  -", u)


if __name__ == "__main__":
    main()
