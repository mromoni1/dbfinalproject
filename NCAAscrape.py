import requests
import time

BASE_URL = "https://ncaa-api.henrygd.me"
RATE_LIMIT_DELAY = 0.25  # 4 requests/sec (API limit is 5/sec)

class NCAAAPIError(Exception):
    pass

def ncaa_get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise NCAAAPIError(
            f"Error {response.status_code} for {url}: {response.text}"
        )

    time.sleep(RATE_LIMIT_DELAY)
    return response.json()

def main():
    # Example parameters
    sport = "soccer-women"
    division = "d3"
    season_year = 2025
    month = "09"

    try:
        schedule = ncaa_get(
            f"/schedule/{sport}/{division}/{season_year}/{month}"
        )

        print(f"Fetched schedule for {sport}, {month}/{season_year}")

        for day in schedule.get("gameDates", []):
            date = day["contest_date"]
            games = day["games"]
            print(f"{date}: {games} games")

    except Exception as e:
        print("Error during scrape:", e)

    print("Scrape finished.")
if __name__ == "__main__":
    main()
