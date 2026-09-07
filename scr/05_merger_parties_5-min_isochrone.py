# ============================================================
# 5-MINUTE DRIVE-TIME MERGER-PARTY ISOCHRONE ANALYSIS
# ============================================================

import os
import time
import requests
import pandas as pd
import geopandas as gpd


# ============================================================
# 1. SETTINGS
# ============================================================

# Computational pre-screen only.
# This is NOT the competition catchment.
PRE_SCREEN_M = 8000

# 300 seconds = 5 minutes
ISOCHRONE_TIME = 300

# ORS permits up to 5 locations per isochrone request
BATCH_SIZE = 5

# Keep comfortably below the per-minute request limit
REQUEST_DELAY = 4

# Number of retry attempts for temporary API failures
MAX_RETRIES = 3

ISOCHRONE_URL = (
    "https://api.heigit.org/openrouteservice/"
    "v2/isochrones/driving-car"
)


# ============================================================
# 2. LOAD ORS API KEY
# ============================================================

ORS_API_KEY = "Your_API_Key_Here"  # Replace with your actual ORS API key

# ============================================================
# 3. Load BNG store data
# ============================================================

stores_df = pd.read_csv("../data/cleaned/combined_stores_clean.csv")

# Create geometry from longitude/latitude
stores_gdf = gpd.GeoDataFrame(
    stores_df,
    geometry=gpd.points_from_xy(
        stores_df["longitude"],
        stores_df["latitude"]
    ),
    crs="EPSG:4326"
)

# Project to British National Grid
stores_bng = stores_gdf.to_crs("EPSG:27700")

# ============================================================
# 4. SPLIT THE TWO MERGER PARTIES
# ============================================================

southern = stores_bng[
    stores_bng["party"] == "Southern Co-op"
].copy()

coop_group = stores_bng[
    stores_bng["party"] == "Co-operative Group"
].copy()

print("\nSouthern Co-op stores:", len(southern))
print("Co-operative Group stores:", len(coop_group))


# ============================================================
# 5. CREATE 8 KM SOUTHERN PRE-SCREEN AREAS
#
# These buffers are ONLY used to identify geographically
# plausible cross-party pairs.
# ============================================================

southern_prescreen = southern[
    ["store_id", "geometry"]
].copy()

southern_prescreen = southern_prescreen.rename(
    columns={
        "store_id": "southern_store_id"
    }
)

southern_prescreen["geometry"] = (
    southern_prescreen.geometry.buffer(PRE_SCREEN_M)
)


# ============================================================
# 6. FIND ALL CO-OP GROUP STORES WITHIN 8 KM
#    OF A SOUTHERN CO-OP STORE
# ============================================================

coop_for_join = coop_group[
    ["store_id", "geometry"]
].copy()

coop_for_join = coop_for_join.rename(
    columns={
        "store_id": "coop_group_store_id"
    }
)

potential_pairs_8km = gpd.sjoin(
    coop_for_join,
    southern_prescreen,
    how="inner",
    predicate="within"
)

potential_pairs_8km = (
    potential_pairs_8km
    .drop(columns="index_right")
    .reset_index(drop=True)
)

print(
    "\nNumber of cross-party store pairs within 8 km:",
    len(potential_pairs_8km)
)


# ============================================================
# 7. IDENTIFY UNIQUE STORES THAT NEED ISOCHRONES
# ============================================================

southern_candidate_ids = (
    potential_pairs_8km[
        "southern_store_id"
    ]
    .unique()
)

coop_candidate_ids = (
    potential_pairs_8km[
        "coop_group_store_id"
    ]
    .unique()
)

southern_candidates = southern[
    southern["store_id"].isin(
        southern_candidate_ids
    )
].copy()

coop_candidates = coop_group[
    coop_group["store_id"].isin(
        coop_candidate_ids
    )
].copy()

print(
    "Unique Southern Co-op candidates:",
    len(southern_candidates)
)

print(
    "Unique Co-operative Group candidates:",
    len(coop_candidates)
)

print(
    "Total candidate centroids:",
    len(southern_candidates)
    + len(coop_candidates)
)


# ============================================================
# 8. CREATE SINGLE CANDIDATE TABLE FOR ORS
#
# ORS expects longitude / latitude in WGS84:
#
# [longitude, latitude]
#
# We use the original longitude and latitude columns rather
# than the EPSG:27700 geometry.
# ============================================================

isochrone_candidates = pd.concat(
    [
        southern_candidates[
            [
                "store_id",
                "party",
                "longitude",
                "latitude"
            ]
        ],
        coop_candidates[
            [
                "store_id",
                "party",
                "longitude",
                "latitude"
            ]
        ]
    ],
    ignore_index=True
)

# Safety check against accidental duplicate centroids
isochrone_candidates = (
    isochrone_candidates
    .drop_duplicates(subset="store_id")
    .reset_index(drop=True)
)

total_stores = len(isochrone_candidates)

total_batches = (
    total_stores + BATCH_SIZE - 1
) // BATCH_SIZE

print("\nTotal candidate stores:", total_stores)
print("Batch size:", BATCH_SIZE)
print("Total ORS requests required:", total_batches)


# ============================================================
# 9. API HEADERS
# ============================================================

headers = {
    "Authorization": ORS_API_KEY,
    "Content-Type": "application/json"
}


# ============================================================
# 10. FUNCTION TO REQUEST ONE BATCH
# ============================================================

def request_isochrone_batch(batch):

    locations = (
        batch[
            ["longitude", "latitude"]
        ]
        .astype(float)
        .values
        .tolist()
    )

    body = {
        "locations": locations,
        "range": [ISOCHRONE_TIME],
        "range_type": "time"
    }

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.post(
                ISOCHRONE_URL,
                headers=headers,
                json=body,
                timeout=60
            )

            # ----------------------------------------
            # Rate limit response
            # ----------------------------------------

            if response.status_code == 429:

                wait_time = 60

                print(
                    f"Rate limit reached. "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue


            # ----------------------------------------
            # Temporary server-side errors
            # ----------------------------------------

            if response.status_code >= 500:

                wait_time = 15 * attempt

                print(
                    f"ORS server error "
                    f"{response.status_code}. "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue


            # Raise error for other unsuccessful codes
            response.raise_for_status()

            return response.json()


        except requests.RequestException as e:

            print(
                f"Request attempt "
                f"{attempt}/{MAX_RETRIES} failed:"
            )

            print(e)

            if attempt < MAX_RETRIES:

                wait_time = 15 * attempt

                print(
                    f"Waiting {wait_time} seconds "
                    "before retry..."
                )

                time.sleep(wait_time)


    # If every retry fails
    return None


# ============================================================
# 11. GENERATE ALL ISOCHRONES IN BATCHES OF FIVE
# ============================================================

isochrone_list = []

failed_batches = []

for batch_number, start in enumerate(
    range(
        0,
        total_stores,
        BATCH_SIZE
    ),
    start=1
):

    batch = (
        isochrone_candidates
        .iloc[
            start:start + BATCH_SIZE
        ]
        .reset_index(drop=True)
    )

    print(
        f"\nRequest "
        f"{batch_number}/{total_batches} "
        f"— {len(batch)} stores"
    )

    data = request_isochrone_batch(
        batch
    )


    # ========================================================
    # FAILED BATCH
    # ========================================================

    if data is None:

        failed_ids = (
            batch["store_id"]
            .tolist()
        )

        failed_batches.append(
            failed_ids
        )

        print(
            "Batch failed:",
            failed_ids
        )

        time.sleep(REQUEST_DELAY)

        continue


    # ========================================================
    # PROCESS RETURNED ISOCHRONE FEATURES
    #
    # group_index identifies which input location generated
    # each returned polygon.
    # ========================================================

    features = data.get(
        "features",
        []
    )

    if len(features) == 0:

        failed_ids = (
            batch["store_id"]
            .tolist()
        )

        failed_batches.append(
            failed_ids
        )

        print(
            "No features returned for batch:",
            failed_ids
        )

        time.sleep(REQUEST_DELAY)

        continue


    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        group_index = properties.get(
            "group_index"
        )

        if group_index is None:

            print(
                "Warning: returned feature "
                "has no group_index."
            )

            continue


        source_store = batch.iloc[
            int(group_index)
        ]

        feature_gdf = (
            gpd.GeoDataFrame.from_features(
                [feature],
                crs="EPSG:4326"
            )
        )

        # Attach our identifiers
        feature_gdf["store_id"] = (
            source_store["store_id"]
        )

        feature_gdf["party"] = (
            source_store["party"]
        )

        feature_gdf[
            "isochrone_minutes"
        ] = 5

        feature_gdf[
            "centroid_longitude"
        ] = source_store[
            "longitude"
        ]

        feature_gdf[
            "centroid_latitude"
        ] = source_store[
            "latitude"
        ]

        isochrone_list.append(
            feature_gdf
        )


    # ========================================================
    # RATE LIMIT PROTECTION
    # ========================================================

    time.sleep(REQUEST_DELAY)


# ============================================================
# 12. COMBINE ALL RETURNED POLYGONS
# ============================================================

if len(isochrone_list) == 0:

    raise ValueError(
        "No isochrones were successfully generated."
    )

isochrones_5min = gpd.GeoDataFrame(
    pd.concat(
        isochrone_list,
        ignore_index=True
    ),
    crs="EPSG:4326"
)


# ============================================================
# 13. VALIDATION
# ============================================================

successful_store_count = (
    isochrones_5min[
        "store_id"
    ]
    .nunique()
)

print("\n===================================")
print("ISOCHRONE GENERATION COMPLETE")
print("===================================")

print(
    "Candidate stores:",
    total_stores
)

print(
    "Unique stores with isochrones:",
    successful_store_count
)

print(
    "Returned polygon rows:",
    len(isochrones_5min)
)

print(
    "Failed batches:",
    len(failed_batches)
)


# Flatten failed store IDs for easier inspection
failed_store_ids = [
    store_id
    for batch in failed_batches
    for store_id in batch
]

print(
    "Stores in failed batches:",
    len(failed_store_ids)
)

if failed_store_ids:

    print(
        "\nFailed store IDs:"
    )

    print(
        failed_store_ids
    )


# ============================================================
# 14. CHECK FOR ANY MISSING STORES
# ============================================================

successful_ids = set(
    isochrones_5min[
        "store_id"
    ]
)

candidate_ids = set(
    isochrone_candidates[
        "store_id"
    ]
)

missing_ids = (
    candidate_ids
    - successful_ids
)

print(
    "\nCandidate stores missing an isochrone:",
    len(missing_ids)
)

if missing_ids:

    print(
        sorted(missing_ids)
    )


# ============================================================
# 15. PROJECT ISOCHRONES TO BRITISH NATIONAL GRID
#
# This makes them compatible with stores_bng and your UK
# boundary for spatial joins and mapping.
# ============================================================

isochrones_5min_bng = (
    isochrones_5min
    .to_crs("EPSG:27700")
)

print(
    "\nProjected isochrone CRS:",
    isochrones_5min_bng.crs
)


# ============================================================
# 16. SET OUTPUT DIRECTORY
# ============================================================

from pathlib import Path

OUTPUT_DIR = Path("../data/derived")


# ============================================================
# 17. SAVE ISOCHRONES
# ============================================================

isochrones_5min_bng.to_file(
    OUTPUT_DIR / "party_5min_isochrones.gpkg",
    driver="GPKG"
)


# ============================================================
# 18. SAVE 8 KM PRE-SCREEN PAIRS
# ============================================================

potential_pairs_8km.to_file(
    OUTPUT_DIR / "potential_party_pairs_8km.gpkg",
    driver="GPKG"
)


# ============================================================
# 19. SAVE CANDIDATE TABLE
# ============================================================

isochrone_candidates.to_csv(
    OUTPUT_DIR / "party_5min_isochrone_candidates.csv",
    index=False
)


print("\nFiles saved successfully:")

print(OUTPUT_DIR / "party_5min_isochrones.gpkg")
print(OUTPUT_DIR / "potential_party_pairs_8km.gpkg")
print(OUTPUT_DIR / "party_5min_isochrone_candidates.csv")