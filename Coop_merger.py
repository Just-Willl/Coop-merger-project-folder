# In which local grocery areas would the Co-operative Group/Southern Co-operative merger have the most impact on competition?
# As measured by the number of independent rival parties providing a competitive coinstraint,
# in areas where Co-operative Group/Southern Co-operative currently operarte and assumedly compete.

# First I must collect the location data for the Co-operative Group/Southern Co-operative using the location APIs from their store locator websites.
import time
import requests
import pandas as pd

# ============================================================
# API URLs
# ============================================================

SOUTHERN_URL = (
    "https://locator.uberall.com/api/storefinders/"
    "uvMckoaRcAUKR0LkkH03SVNyf7A4Lk/locations/all"
)

COOP_GROUP_URL = (
    "https://api.coop.co.uk/locationservices/finder/food/"
)


# ============================================================
# API PARAMETERS
# ============================================================

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


# ============================================================
# SOUTHERN CO-OP
# ============================================================

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


southern_df = get_southern_locations()


# ============================================================
# CO-OPERATIVE GROUP
# ============================================================

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


coop_group_df = get_coop_group_locations()


# ============================================================
# QUICK CHECK
# ============================================================

print(f"Southern Co-op: {len(southern_df):,} rows")
print(f"Co-operative Group API: {len(coop_group_df):,} rows")