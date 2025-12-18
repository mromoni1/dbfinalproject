import csv

INPUT_1 = "games_augsept.csv"
INPUT_2 = "games_octnov.csv"
OUTPUT = "games.csv"


def merge_csvs():
    with open(OUTPUT, "w", newline="", encoding="utf-8") as out:
        writer = None

        for i, infile in enumerate([INPUT_1, INPUT_2]):
            with open(infile, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)

                if i == 0:
                    # Write header only once
                    writer = csv.writer(out)
                    writer.writerow(header)

                # Write data rows
                for row in reader:
                    writer.writerow(row)

    print(f"Merged CSV written to {OUTPUT}")


if __name__ == "__main__":
    merge_csvs()
