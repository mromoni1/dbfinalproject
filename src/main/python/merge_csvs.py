import csv

INPUT_1 = "../output/AugSeptPlay.csv"
INPUT_2 = "../output/OctNovPlay.csv"
OUTPUT = "../output/Play.csv"

def merge_csvs():
    next_play_id = 1

    with open(OUTPUT, "w", newline="", encoding="utf-8") as out:
        writer = None

        for infile in [INPUT_1, INPUT_2]:
            with open(infile, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if writer is None:
                    writer = csv.DictWriter(out, fieldnames=reader.fieldnames)
                    writer.writeheader()

                for row in reader:
                    row["play_id"] = next_play_id
                    next_play_id += 1
                    writer.writerow(row)

    print(f"Merged CSV written to {OUTPUT} (play_id reindexed)")

if __name__ == "__main__":
    merge_csvs()
