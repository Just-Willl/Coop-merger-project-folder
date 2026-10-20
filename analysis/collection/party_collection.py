import time
import requests
import pandas as pd

SOUTHERN_URL = (
    "https://locator.uberall.com/api/storefinders/"
    "uvMckoaRcAUKR0LkkH03SVNyf7A4Lk/locations/all"
)

COOP_GROUP_URL = (
    "https://api.coop.co.uk/locationservices/finder/food/"
)

SOUTHERN_PARAMS = {
    "v": "20260101",
    "language": "en-gb",
    "country": "UK",
}

COOP_GROUP_PARAMS = {
    "location": "50.50898,-3.58478",
    "distance": 30_000_000,
    "min_distance": 0,
    "min_results": 10_000,
    "format": "json",
}

def get_southern_locations():
    """Download all locations from Southern Co-op's store finder."""

    response = requests.get(
        SOUTHERN_URL,
        params=SOUTHERN_PARAMS,
        timeout=45,
    )

    response.raise_for_status()

    data = response.json()

    locations = data["response"]["locations"]

    return pd.json_normalize(locations, sep=".")

def get_coop_group_locations():
    """Download every page from Co-op's location API."""

    all_locations = []

    response = requests.get(
        COOP_GROUP_URL,
        params=COOP_GROUP_PARAMS,
        timeout=45,
    )

    response.raise_for_status()
    data = response.json()

    all_locations.extend(data["results"])

    next_url = data["next"]

    while next_url is not None:

        time.sleep(0.15)

        response = requests.get(
            next_url,
            timeout=45,
        )

        response.raise_for_status()
        data = response.json()

        all_locations.extend(data["results"])

        next_url = data["next"]

    return pd.json_normalize(all_locations, sep=".")