import csv
import json

INPUT_CSV = "Game.csv"
OUTPUT_JSON = "game_ids.json"

def extract_game_ids():
    game_ids = []

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if "game_id" not in reader.fieldnames:
            raise ValueError("CSV does not contain a 'game_id' column")

        for row in reader:
            try:
                game_ids.append(int(row["game_id"]))
            except (TypeError, ValueError):
                continue  # skip malformed rows

    print(f"Extracted {len(game_ids)} game IDs")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(game_ids, f, indent=2)

    print(f"Wrote {OUTPUT_JSON}")

if __name__ == "__main__":
    extract_game_ids()
