import csv
import os
import re
from shutil import copyfile

PLAYER_CSV = "../output/Player.csv"
PLAY_CSV = "../output/Play.csv"
GAMESTATS_CSV = "../output/GameStats.csv"

FINAL_GAMESTATS_FIELDS = [
    "game_id",
    "player_id",
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



def normalize_name(name: str):
    if not name:
        return name

    name = re.sub(r"\s+", " ", name.strip().lower())

    def cap(token):
        return token[0].upper() + token[1:] if token else token

    parts = re.split(r"([\-’'])", name)
    return "".join(cap(p) if p.isalpha() else p for p in parts)


def normalize_time(t: str):
    if not t or ":" not in t:
        return t

    parts = t.split(":")
    if len(parts) >= 2:
        return f"{parts[-2]}:{parts[-1]}"
    return t

def normalize_position(pos: str):
    if not pos:
        return pos
    return pos.strip().upper()


def normalize_player_csv():
    backup = PLAYER_CSV + ".bak"
    copyfile(PLAYER_CSV, backup)
    print(f"Backup created: {backup}")

    rows = []
    with open(PLAYER_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for r in reader:
            r["first_name"] = normalize_name(r["first_name"])
            r["last_name"] = normalize_name(r["last_name"])
            r["position"] = normalize_position(r.get("position"))
            rows.append(r)

    with open(PLAYER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Normalized Player.csv ({len(rows)} rows)")


def normalize_play_csv():
    backup = PLAY_CSV + ".bak"
    copyfile(PLAY_CSV, backup)
    print(f"Backup created: {backup}")

    rows = []
    with open(PLAY_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for r in reader:
            r["time_of_play"] = normalize_time(r["time_of_play"])
            rows.append(r)

    with open(PLAY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Normalized Play.csv ({len(rows)} rows)")

def postprocess_gamestats_csv():
    backup = GAMESTATS_CSV + ".bak"
    copyfile(GAMESTATS_CSV, backup)
    print(f"Backup created: {backup}")

    cleaned_rows = []

    with open(GAMESTATS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            cleaned_rows.append({
                "game_id": r["game_id"],
                "player_id": r["player_id"],
                "played": r["played"],
                "started": r["started"],
                "shots": r["shots"],
                "shots_on_target": r["shots_on_target"],
                "goals": r["goals"],
                "assists": r["assists"],
                "minutes": r["minutes"],
                "pk_attempt": r["pk_attempt"],
                "pk_made": r["pk_made"],
                "gw": r["gw"],
                "yc": r["yc"],
                "rc": r["rc"],
            })

    with open(GAMESTATS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_GAMESTATS_FIELDS)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"Normalized GameStats.csv ({len(cleaned_rows)} rows)")


# ==========================
# Main
# ==========================

if __name__ == "__main__":
    if not os.path.exists(PLAYER_CSV) or not os.path.exists(PLAY_CSV):
        print("CSV files not found. Check paths.")
        exit(1)

    normalize_player_csv()
    normalize_play_csv()
    postprocess_gamestats_csv()

    print("✅ CSV normalization complete.")
