import sqlite3
import csv
import os
import re

DB_FILE = "D3WomensSoccer.db"
SCHEMA_FILE = "D3WomensSoccerSchema.sql"

CSV_TABLES = {
    "src/main/output/Conference.csv": "Conference",
    "src/main/output/University.csv": "University",
    "src/main/output/Rankings.csv": "Rankings",
    "src/main/output/Game.csv": "Game",
    "src/main/output/GameStats.csv": "GameStats",
    "src/main/output/Play.csv": "Play",
}

CREATION_ORDER = [
    "Conference",
    "University",
    "Rankings",
    "Game",
    "GameStats",
    "Player",
    "Play",
]


# Connect to db

def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Schema execution

def execute_schema(conn):
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = f.read()

    statements = [s.strip() for s in schema.split(";") if s.strip()]

    drops = []
    creates = {}

    for stmt in statements:
        if stmt.upper().startswith("DROP"):
            drops.append(stmt + ";")
        elif stmt.upper().startswith("CREATE"):
            for table in CREATION_ORDER:
                if re.search(rf"\bCREATE\s+(TABLE|VIEW)\s+{table}\b", stmt, re.I):
                    creates[table] = stmt + ";"

    cur = conn.cursor()

    print("Disabling foreign keys for DROP...")
    cur.execute("PRAGMA foreign_keys = OFF;")

    print("Dropping existing objects...")
    for d in drops:
        cur.execute(d)
    conn.commit()

    print("Re-enabling foreign keys...")
    cur.execute("PRAGMA foreign_keys = ON;")

    print("Creating schema in enforced order...")
    for table in CREATION_ORDER:
        if table in creates:
            print(f"Creating {table}")
            cur.execute(creates[table])

    conn.commit()

# Helpers to populate Player from GameStats and Play

def populate_player_from_gamestats(conn):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO Player (
            player_id,
            first_name,
            last_name,
            class_grade,
            position,
            university_id
        )
        SELECT DISTINCT
            player_id,
            first_name,
            last_name,
            NULL,
            position,
            university_id
        FROM GameStats
        WHERE player_id IS NOT NULL
    """)
    conn.commit()
    print("Inserted Player rows from GameStats")


def populate_player_from_play(conn):
    """
    Inserts players who appear only in Play (e.g. substitutions with no stats).
    Does NOT duplicate existing players because of INSERT OR IGNORE.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO Player (
            player_id,
            first_name,
            last_name,
            class_grade,
            position,
            university_id
        )
        SELECT DISTINCT
            p.player_id,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL
        FROM Play p
        WHERE p.player_id IS NOT NULL
    """)
    conn.commit()
    print("Inserted missing Players from Play")


# CSV insertion

def insert_csv(conn, csv_file, table):
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames

        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"

        cur = conn.cursor()

        valid_universities = set()
        if table == "Game":
            cur.execute("SELECT university_id FROM University")
            valid_universities = {row[0] for row in cur.fetchall()}

        inserted = 0
        skipped = 0

        for row in reader:
            try:
                if table == "Game":
                    home = int(row["home_team_id"])
                    away = int(row["away_team_id"])
                    if home not in valid_universities or away not in valid_universities:
                        skipped += 1
                        continue

                values = tuple(None if row[c] == "" else row[c] for c in cols)
                cur.execute(sql, values)
                inserted += 1

            except sqlite3.IntegrityError as e:
                skipped += 1

        conn.commit()

        print(f"Inserted {inserted} rows into {table}")
        if skipped:
            print(f"Skipped {skipped} invalid rows in {table}")

#
def main():
    conn = connect()
    execute_schema(conn)

    # Insert all tables EXCEPT Play
    for csv_file, table in CSV_TABLES.items():
        if table != "Play" and os.path.exists(csv_file):
            insert_csv(conn, csv_file, table)

    # Populate Player from both sources
    populate_player_from_gamestats(conn)
    populate_player_from_play(conn)

    # Insert Play last (FKs now satisfied)
    insert_csv(conn, "src/main/output/Play.csv", "Play")

    conn.close()
    print("Database build complete.")

if __name__ == "__main__":
    main()
