import time
import requests

BASE_URL = "https://ncaa-api.henrygd.me"
RATE_LIMIT_DELAY = 0.25  # 4 req/sec

class NCAAAPIError(Exception):
    pass

def ncaa_get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        raise NCAAAPIError(
            f"Error {response.status_code} for {url}: {response.text}"
        )

    time.sleep(RATE_LIMIT_DELAY)
    return response.json()
