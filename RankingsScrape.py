import requests
import csv
import time
from bs4 import BeautifulSoup

URL = "https://unitedsoccercoaches.org/rankings/college-rankings/ncaa-diii-women/"
RATE_LIMIT_DELAY = 1.0  # be polite


def fetch_html(url):
    r = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RankingsScrape/1.0)"
        },
        timeout=30,
    )
    r.raise_for_status()
    time.sleep(RATE_LIMIT_DELAY)
    return r.text


def extract_week_tables(soup):
    """
    United Soccer Coaches uses multiple ranking tables on the page,
    one per week. Each table contains a Top 25.
    """
    tables = soup.find_all("table")
    ranking_tables = []

    for table in tables:
        # Heuristic: ranking tables have Rank + School columns
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "rank" in headers and "school" in headers:
            ranking_tables.append(table)

    return ranking_tables


def parse_ranking_table(table):
    """
    Parse a single Top 25 table into {rank: school}
    """
    rankings = {}

    rows = table.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        rank_text = cols[0].get_text(strip=True)
        school_text = cols[1].get_text(strip=True)

        try:
            rank = int(rank_text)
        except ValueError:
            continue

        if 1 <= rank <= 25:
            rankings[rank] = school_text

    return rankings


def main():
    html = fetch_html(URL)
    soup = BeautifulSoup(html, "html.parser")

    ranking_tables = extract_week_tables(soup)
    if not ranking_tables:
        print("No ranking tables found.")
        return

    rows = []

    for week_idx, table in enumerate(ranking_tables, start=1):
        rankings = parse_ranking_table(table)
        if not rankings:
            continue

        row = {"rank_week": week_idx}
        for i in range(1, 26):
            row[f"rank_{i}"] = rankings.get(i)

        rows.append(row)

    # Write CSV
    fieldnames = ["rank_week"] + [f"rank_{i}" for i in range(1, 26)]
    with open("./csv_files/rankings.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} weeks of D3 Women's Soccer rankings to ./csv_files/rankings.csv")


if __name__ == "__main__":
    main()
