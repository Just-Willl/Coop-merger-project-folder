# ============================================================
# 08B - CHECK FOR POSSIBLE STALE / REBRANDED STORE DUPLICATES
# ============================================================
#
# TEMPORARY QA SCRIPT
#
# PURPOSE
# -------
# Script 08 already removes most duplicate stores where OSM and
# GEOLYTIX appear to represent the same physical location.
#
# However, there is another possible data-quality problem:
#
# one source may contain an OLD fascia while another contains the
# CURRENT fascia at effectively the same physical shop.
#
# Example:
#
#     OSM:
#         McColl's
#
#     GEOLYTIX:
#         Morrisons Daily
#
#     distance:
#         1 metre
#
# Those two records could represent the same physical store before
# and after a rebrand / change of ownership.
#
# A normal "same fascia" duplicate rule would not necessarily catch
# this because McColl's and Morrisons are different fascia labels.
#
#
# WHAT THIS SCRIPT DOES
# ---------------------
# 1. Loads the final OSM rival stores that survived Script 08.
#
# 2. Loads ALL relevant GEOLYTIX stores in the collection area.
#
# 3. Finds OSM and GEOLYTIX stores within 30 metres of each other.
#
# 4. Looks specifically for cases where the two records have:
#
#       - different fasciae
#       - or an unknown fascia in one source
#
# 5. Gives those cases a review priority.
#
# 6. Saves them into a temporary CSV for us to inspect manually.
#
#
# IMPORTANT
# ---------
# This script DOES NOT remove or modify any stores.
#
# If we confirm any genuine stale/rebrand duplicates:
#
#       - we document the reasoning in 08A
#       - we add the confirmed OSM IDs to Script 08
#       - we rerun Script 08
#
#
# TEMPORARY OUTPUT LOCATION
# -------------------------
# Everything created here goes into:
#
#     data/_temp_checks/08B_rebrand_check/
#
# Once we have finished this QA exercise, that folder can be
# deleted without affecting the main project outputs.
# ============================================================


from pathlib import Path
from difflib import SequenceMatcher

import re
import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# 1. PROJECT PATHS
# ============================================================
#
# The script is assumed to live inside the project's `scr` folder.
#
# parent.parent therefore takes us back to the project root.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

CLEANED_DIR = DATA_DIR / "cleaned"

DERIVED_DIR = DATA_DIR / "derived"


# Temporary folder used only for one-off QA outputs.
TEMP_DIR = (
    DATA_DIR
    / "_temp_checks"
    / "08B_rebrand_check"
)


TEMP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Final cleaned rival dataset produced by Script 08.
RIVAL_FILE = (
    CLEANED_DIR
    / "rival_stores_clean.gpkg"
)


# Original GEOLYTIX source file.
GEOLYTIX_FILE = (
    DATA_DIR
    / "GEOLYTIX data"
    / "GEOLYTIX Grocery Stores.csv"
)


# Catchments created earlier in the project.
#
# These are used here only to recreate the overall geographic area
# for which we collected rival-store data.
CATCHMENTS_FILE = (
    DERIVED_DIR
    / "competitor_analysis_catchments.gpkg"
)


# Audit file created by Script 08 containing candidate stores that
# were removed because they were identified as merger-party stores.
MERGER_REMOVED_FILE = (
    DERIVED_DIR
    / "merger_party_stores_removed.csv"
)


# Temporary review CSV produced by this script.
OUTPUT_FILE = (
    TEMP_DIR
    / "TEMP_08B_possible_rebrand_duplicates.csv"
)


# ============================================================
# 2. SETTINGS
# ============================================================
#
# We search within 30 metres.
#
# This is deliberately wider than the "almost certainly the same
# point" range because OSM and GEOLYTIX may place the same shop at
# slightly different positions within a building or retail site.
#
# We do NOT automatically call everything within 30m a duplicate.
# The distance is only used to create a shortlist for manual review.
# ============================================================

SEARCH_DISTANCE_M = 30


# ============================================================
# 3. HELPER FUNCTION: NORMALISE TEXT
# ============================================================
#
# Different data sources can spell or punctuate the same name in
# different ways.
#
# For example:
#
#     "Sainsbury's"
#     "Sainsburys"
#
# Normalising text makes comparisons easier.
# ============================================================

def normalise_text(value):

    if pd.isna(value):

        return ""


    value = str(value).lower()


    value = value.replace(
        "&",
        " and "
    )


    # Replace punctuation and special characters with spaces.
    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )


    # Collapse repeated spaces.
    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()


    return value


# ============================================================
# 4. HELPER FUNCTION: CLEAN POSTCODES
# ============================================================
#
# Postcodes are converted to a common format so that:
#
#     "EX8 1QD"
#
# and
#
#     "EX81QD"
#
# can be treated as equal.
# ============================================================

def clean_postcode(value):

    if pd.isna(value):

        return ""


    return (
        str(value)
        .upper()
        .replace(
            " ",
            ""
        )
        .strip()
    )


# ============================================================
# 5. HELPER FUNCTION: CANONICAL FASCIA
# ============================================================
#
# This converts several raw store names into broader standardised
# fascia labels.
#
# Example:
#
#     Tesco Express
#     Tesco Express Esso
#
# both become:
#
#     Tesco
#
#
# This is useful because we want to know whether two nearby stores
# belong to the same fascia or apparently different fasciae.
# ============================================================

def canonical_fascia(text):

    text = normalise_text(
        text
    )


    if not text:

        return ""


    if "tesco" in text:

        return "Tesco"


    if "sainsbury" in text:

        return "Sainsbury's"


    if "asda" in text:

        return "Asda"


    if (
        "morrisons" in text
        or "morrison s" in text
    ):

        return "Morrisons"


    if (
        "mccoll" in text
        or "mc coll" in text
    ):

        return "McColl's"


    if "waitrose" in text:

        return "Waitrose"


    if "whole foods" in text:

        return "Whole Foods"


    if (
        "co op" in text
        or "coop" in text
        or "co operative" in text
        or "cooperative" in text
    ):

        return "Co-op"


    if "aldi" in text:

        return "Aldi"


    if "lidl" in text:

        return "Lidl"


    if (
        "marks and spencer" in text
        or "m and s" in text
        or "m s simply food" in text
        or "m s foodhall" in text
    ):

        return "Marks & Spencer"


    if (
        "iceland" in text
        or "food warehouse" in text
    ):

        return "Iceland"


    if "spar" in text:

        return "Spar"


    if "nisa" in text:

        return "Nisa"


    if "premier" in text:

        return "Premier"


    if "londis" in text:

        return "Londis"


    if "budgens" in text:

        return "Budgens"


    if "costcutter" in text:

        return "Costcutter"


    if "one stop" in text:

        return "One Stop"


    if "best one" in text:

        return "Best-one"


    if "central convenience" in text:

        return "Central Convenience"


    if "family shopper" in text:

        return "Family Shopper"


    if "go local" in text:

        return "Go Local"


    if "booker" in text:

        return "Booker"


    if "centra" in text:

        return "Centra"


    if "key store" in text:

        return "Key Store"


    if "key shop" in text:

        return "Key Shop"


    if "ck supermarket" in text:

        return "CK Supermarkets"


    return ""


# ============================================================
# 6. LOAD THE FINAL RIVAL DATASET
# ============================================================
#
# Script 08 has already removed:
#
#     - normal OSM / GEOLYTIX duplicates
#     - manually confirmed duplicates
#     - merger-party stores
#
# We only care about OSM records that STILL survive in the final
# rival dataset.
#
# If an OSM record was already removed, it cannot create a
# double-counting problem in the final analysis.
# ============================================================

rivals = gpd.read_file(
    RIVAL_FILE
)


# All distance calculations should use British National Grid.
#
# EPSG:27700 measures coordinates in metres.
if rivals.crs.to_epsg() != 27700:

    rivals = rivals.to_crs(
        "EPSG:27700"
    )


# Keep only OSM records.
osm = (
    rivals[
        rivals[
            "source"
        ]
        ==
        "OpenStreetMap"
    ]
    .copy()
)


print(
    "Final OSM rival records:",
    len(osm)
)


# ============================================================
# 7. LOAD THE ANALYSIS CATCHMENTS
# ============================================================
#
# We combine the 522 individual catchments into one overall
# collection boundary.
#
# IMPORTANT:
#
# This combined geometry is NOT being treated as one competition
# market.
#
# It is only used to determine which GEOLYTIX stores are relevant
# to the area covered by the project.
# ============================================================

catchments = gpd.read_file(
    CATCHMENTS_FILE
)


if catchments.crs.to_epsg() != 27700:

    catchments = catchments.to_crs(
        "EPSG:27700"
    )


collection_geometry = (
    catchments[
        ["geometry"]
    ]
    .dissolve()
    .geometry
    .iloc[0]
)


# ============================================================
# 8. LOAD THE FULL GEOLYTIX DATASET
# ============================================================
#
# We deliberately load GEOLYTIX directly from the original source
# rather than using only the GEOLYTIX records that survived in the
# final rival dataset.
#
# Why?
#
# Imagine:
#
#     OSM says:
#         Old McColl's
#
#     GEOLYTIX says:
#         Current Co-op
#
# If the current Co-op is one of the merger parties, Script 08 may
# correctly remove the GEOLYTIX record from the rival dataset.
#
# But the stale McColl's OSM record could potentially survive and
# wrongly appear as an independent competitor.
#
# Comparing against ALL relevant GEOLYTIX stores allows us to find
# that kind of problem.
# ============================================================

geo_raw = pd.read_csv(
    GEOLYTIX_FILE
)


# Remove stores without usable coordinates.
geo_raw = (
    geo_raw
    .dropna(
        subset=[
            "bng_e",
            "bng_n"
        ]
    )
    .copy()
)


# Convert GEOLYTIX coordinates into a GeoDataFrame.
geo = gpd.GeoDataFrame(

    geo_raw,

    geometry=gpd.points_from_xy(
        geo_raw[
            "bng_e"
        ],
        geo_raw[
            "bng_n"
        ]
    ),

    crs="EPSG:27700"
)


# Keep only GEOLYTIX stores located somewhere inside the overall
# collection area.
geo = (
    geo[
        geo
        .geometry
        .intersects(
            collection_geometry
        )
    ]
    .copy()
)


# Create the same style of source ID used elsewhere in the project.
geo[
    "geo_id"
] = (
    "GEO-"
    +
    geo[
        "id"
    ].astype(str)
)


print(
    "Relevant GEOLYTIX records:",
    len(geo)
)


# ============================================================
# 9. CREATE STANDARDISED FASCIA FOR OSM
# ============================================================
#
# OSM may store useful identity information across several fields:
#
#     osm_brand
#     osm_operator
#     store_name
#
# We combine them before running the canonical fascia function.
# ============================================================

osm[
    "osm_classification_text"
] = (
    osm[
        [
            "osm_brand",
            "osm_operator",
            "store_name"
        ]
    ]
    .fillna("")
    .astype(str)
    .agg(
        " ".join,
        axis=1
    )
)


osm[
    "osm_canonical_fascia_check"
] = (
    osm[
        "osm_classification_text"
    ]
    .apply(
        canonical_fascia
    )
)


# ============================================================
# 10. CREATE STANDARDISED FASCIA FOR GEOLYTIX
# ============================================================
#
# GEOLYTIX has several potentially useful identity fields:
#
#     fascia
#     retailer
#     store_name
#
# Again, they are combined before standardisation.
# ============================================================

geo[
    "geo_classification_text"
] = (
    geo[
        [
            "fascia",
            "retailer",
            "store_name"
        ]
    ]
    .fillna("")
    .astype(str)
    .agg(
        " ".join,
        axis=1
    )
)


geo[
    "geo_canonical_fascia_check"
] = (
    geo[
        "geo_classification_text"
    ]
    .apply(
        canonical_fascia
    )
)


# ============================================================
# 11. CLEAN POSTCODES
# ============================================================
#
# Postcodes provide useful secondary evidence.
#
# A different-fascia pair that is:
#
#     3 metres apart
#     AND
#     has the same postcode
#
# is particularly worth investigating.
# ============================================================

osm[
    "osm_postcode_clean"
] = (
    osm[
        "postcode"
    ]
    .apply(
        clean_postcode
    )
)


geo[
    "geo_postcode_clean"
] = (
    geo[
        "postcode"
    ]
    .apply(
        clean_postcode
    )
)


# ============================================================
# 12. STORE ORIGINAL POINT COORDINATES
# ============================================================
#
# We will shortly turn the OSM points into 30m buffers.
#
# Before doing that, we save their actual easting and northing so
# we can calculate the true distance between the original points.
# ============================================================

osm[
    "osm_easting"
] = osm.geometry.x


osm[
    "osm_northing"
] = osm.geometry.y


geo[
    "geo_easting"
] = geo.geometry.x


geo[
    "geo_northing"
] = geo.geometry.y


# ============================================================
# 13. ALSO CREATE LATITUDE / LONGITUDE
# ============================================================
#
# British National Grid is best for measuring distance.
#
# Latitude / longitude is more convenient for manual checking in
# Google Maps or another map service.
#
# So we keep both.
# ============================================================

osm_wgs = osm.to_crs(
    "EPSG:4326"
)


osm[
    "osm_latitude"
] = (
    osm_wgs.geometry.y.values
)


osm[
    "osm_longitude"
] = (
    osm_wgs.geometry.x.values
)


geo_wgs = geo.to_crs(
    "EPSG:4326"
)


geo[
    "geo_latitude"
] = (
    geo_wgs.geometry.y.values
)


geo[
    "geo_longitude"
] = (
    geo_wgs.geometry.x.values
)


# ============================================================
# 14. CREATE A SMALL GEOLYTIX MATCHING TABLE
# ============================================================
#
# We keep only the columns useful for this QA exercise.
# ============================================================

geo_reference = (
    geo[
        [
            "geo_id",
            "store_name",
            "fascia",
            "retailer",
            "postcode",
            "size_band",

            "geo_canonical_fascia_check",
            "geo_postcode_clean",

            "geo_easting",
            "geo_northing",

            "geo_latitude",
            "geo_longitude",

            "geometry"
        ]
    ]
    .copy()
)


geo_reference = (
    geo_reference
    .rename(
        columns={

            "store_name":
                "geo_store_name",

            "fascia":
                "geo_fascia",

            "retailer":
                "geo_retailer",

            "postcode":
                "geo_postcode",

            "size_band":
                "geo_size_band"
        }
    )
)


# ============================================================
# 15. CREATE A SMALL OSM MATCHING TABLE
# ============================================================

osm_reference = (
    osm[
        [
            "rival_store_id",

            "store_name",
            "osm_brand",
            "osm_operator",
            "osm_shop",
            "postcode",

            "osm_canonical_fascia_check",
            "osm_postcode_clean",

            "osm_easting",
            "osm_northing",

            "osm_latitude",
            "osm_longitude",

            "geometry"
        ]
    ]
    .copy()
)


osm_reference = (
    osm_reference
    .rename(
        columns={

            "store_name":
                "osm_store_name",

            "postcode":
                "osm_postcode"
        }
    )
)


# ============================================================
# 16. CREATE 30-METRE SEARCH AREAS AROUND OSM STORES
# ============================================================
#
# Each OSM point is temporarily converted into a 30m-radius circle.
#
# Any GEOLYTIX point falling inside that circle becomes a possible
# match.
#
# This method returns ALL nearby GEOLYTIX stores rather than only
# the nearest one.
#
# That is important because dense retail areas can contain several
# genuine stores.
# ============================================================

osm_search = (
    osm_reference.copy()
)


osm_search[
    "geometry"
] = (
    osm_search
    .geometry
    .buffer(
        SEARCH_DISTANCE_M
    )
)


# ============================================================
# 17. FIND ALL NEARBY OSM / GEOLYTIX PAIRS
# ============================================================
#
# The spatial join asks:
#
#     Which GEOLYTIX points fall inside each OSM 30m buffer?
#
# One OSM store may therefore appear several times if several
# GEOLYTIX stores are nearby.
# ============================================================

pairs = gpd.sjoin(

    osm_search,

    geo_reference,

    how="inner",

    predicate="intersects"
)


# ============================================================
# 18. CALCULATE TRUE POINT-TO-POINT DISTANCE
# ============================================================
#
# The spatial join only tells us that the points are within 30m.
#
# We now calculate the exact distance in metres between the
# original OSM and GEOLYTIX coordinates.
# ============================================================

pairs[
    "distance_m"
] = np.hypot(

    pairs[
        "osm_easting"
    ]
    -
    pairs[
        "geo_easting"
    ],

    pairs[
        "osm_northing"
    ]
    -
    pairs[
        "geo_northing"
    ]
)


print(
    f"All OSM / GEOLYTIX pairs within "
    f"{SEARCH_DISTANCE_M}m:",
    len(pairs)
)


# ============================================================
# 19. IDENTIFY WHETHER BOTH FASCIAE ARE KNOWN
# ============================================================
#
# We distinguish between:
#
#     Tesco vs Sainsbury's
#
# and:
#
#     Unknown OSM store vs Tesco
#
# Both can be worth checking, but the evidence is different.
# ============================================================

pairs[
    "both_fascia_known"
] = (

    (
        pairs[
            "osm_canonical_fascia_check"
        ]
        != ""
    )

    &

    (
        pairs[
            "geo_canonical_fascia_check"
        ]
        != ""
    )
)


# ============================================================
# 20. IDENTIFY DIFFERENT-FASCIA PAIRS
# ============================================================
#
# These are the key cases for this script.
#
# Example:
#
#     OSM fascia:
#         McColl's
#
#     GEOLYTIX fascia:
#         Morrisons
#
# ============================================================

pairs[
    "different_fascia"
] = (

    pairs[
        "both_fascia_known"
    ]

    &

    (
        pairs[
            "osm_canonical_fascia_check"
        ]
        !=
        pairs[
            "geo_canonical_fascia_check"
        ]
    )
)


# ============================================================
# 21. IDENTIFY CASES WHERE ONE FASCIA IS UNKNOWN
# ============================================================
#
# These are weaker signals, but still worth reviewing where the
# two store points are extremely close together.
# ============================================================

pairs[
    "fascia_missing"
] = (
    ~pairs[
        "both_fascia_known"
    ]
)


# ============================================================
# 22. CHECK WHETHER POSTCODES MATCH
# ============================================================

pairs[
    "same_postcode"
] = (

    (
        pairs[
            "osm_postcode_clean"
        ]
        != ""
    )

    &

    (
        pairs[
            "geo_postcode_clean"
        ]
        != ""
    )

    &

    (
        pairs[
            "osm_postcode_clean"
        ]
        ==
        pairs[
            "geo_postcode_clean"
        ]
    )
)


# ============================================================
# 23. CALCULATE STORE-NAME SIMILARITY
# ============================================================
#
# This is not expected to catch every rebrand because a rebrand can
# completely change the retailer name.
#
# But it may help where a location name is still shared.
#
# Score:
#
#     0 = completely different
#     1 = identical
# ============================================================

def calculate_name_similarity(row):

    osm_name = normalise_text(
        row[
            "osm_store_name"
        ]
    )


    geo_name = normalise_text(
        row[
            "geo_store_name"
        ]
    )


    if (
        not osm_name
        or not geo_name
    ):

        return 0.0


    return round(

        SequenceMatcher(
            None,
            osm_name,
            geo_name
        ).ratio(),

        3
    )


pairs[
    "name_similarity"
] = (
    pairs.apply(
        calculate_name_similarity,
        axis=1
    )
)


# ============================================================
# 24. FLAG KNOWN REBRAND / SUCCESSOR PATTERNS
# ============================================================
#
# McColl's / Morrisons is especially relevant.
#
# Many former McColl's stores were converted to Morrisons Daily,
# so a very close McColl's + Morrisons pair deserves attention.
#
# This is only a flag.
#
# It does NOT mean every McColl's / Morrisons pair is automatically
# the same physical store.
# ============================================================

def identify_known_rebrand_pattern(row):

    fascia_pair = {

        row[
            "osm_canonical_fascia_check"
        ],

        row[
            "geo_canonical_fascia_check"
        ]
    }


    if fascia_pair == {
        "McColl's",
        "Morrisons"
    }:

        return "McColl's / Morrisons"


    return ""


pairs[
    "known_rebrand_pattern"
] = (
    pairs.apply(
        identify_known_rebrand_pattern,
        axis=1
    )
)


# ============================================================
# 25. CHECK WHETHER THE GEOLYTIX STORE WAS REMOVED AS A PARTY STORE
# ============================================================
#
# This is particularly useful.
#
# Suppose:
#
#     stale OSM record = old retailer
#
#     current GEOLYTIX record = Co-op Group store
#
# Script 08 might correctly remove the GEOLYTIX store because it is
# one of the merger parties.
#
# But the stale OSM record might remain and incorrectly appear to
# be an independent competitor.
#
# This flag helps us identify that scenario.
# ============================================================

merger_removed_ids = set()


if MERGER_REMOVED_FILE.exists():

    merger_removed = pd.read_csv(
        MERGER_REMOVED_FILE
    )


    merger_removed_ids = set(

        merger_removed[
            "rival_store_id"
        ]
        .dropna()
        .astype(str)
    )


pairs[
    "geo_removed_as_merger_party"
] = (

    pairs[
        "geo_id"
    ]
    .isin(
        merger_removed_ids
    )
)


# ============================================================
# 26. ASSIGN REVIEW PRIORITY
# ============================================================
#
# We deliberately do NOT automatically classify anything as a
# duplicate.
#
# Instead, the script tells us which cases are most suspicious.
#
#
# VERY HIGH
# ---------
#
# Different known fasciae
# AND
# <=3 metres apart
#
#
# HIGH
# ----
#
# Known McColl's / Morrisons pairing
#
# OR
#
# different known fasciae <=10 metres apart
#
# OR
#
# different known fasciae with the same postcode
#
#
# REVIEW
# ------
#
# Other different-fascia or unknown-fascia pairs within 30m.
# ============================================================

def assign_review_priority(row):

    distance = row[
        "distance_m"
    ]


    if (
        row[
            "different_fascia"
        ]
        and
        distance <= 3
    ):

        return "VERY HIGH"


    if (
        row[
            "known_rebrand_pattern"
        ]
        != ""
    ):

        return "HIGH"


    if (
        row[
            "different_fascia"
        ]
        and
        distance <= 10
    ):

        return "HIGH"


    if (
        row[
            "different_fascia"
        ]
        and
        row[
            "same_postcode"
        ]
    ):

        return "HIGH"


    if (
        row[
            "different_fascia"
        ]
        or
        row[
            "fascia_missing"
        ]
    ):

        return "REVIEW"


    return ""


pairs[
    "review_priority"
] = (
    pairs.apply(
        assign_review_priority,
        axis=1
    )
)


# ============================================================
# 27. KEEP ONLY CASES THAT REQUIRE REVIEW
# ============================================================
#
# Same-fascia pairs are not the purpose of this script because
# Script 08 has already dealt with those.
# ============================================================

review = (
    pairs[
        pairs[
            "review_priority"
        ]
        != ""
    ]
    .copy()
)


# ============================================================
# 28. SORT THE REVIEW TABLE
# ============================================================
#
# Most suspicious cases appear first:
#
#     VERY HIGH
#     HIGH
#     REVIEW
#
# Within each priority, the closest pairs appear first.
# ============================================================

priority_order = {

    "VERY HIGH": 1,

    "HIGH": 2,

    "REVIEW": 3
}


review[
    "priority_sort"
] = (
    review[
        "review_priority"
    ]
    .map(
        priority_order
    )
)


review = (
    review
    .sort_values(
        [
            "priority_sort",
            "distance_m"
        ]
    )
    .drop(
        columns=[
            "priority_sort"
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 29. SELECT THE COLUMNS USEFUL FOR MANUAL REVIEW
# ============================================================
#
# Latitude and longitude are included so any suspicious pair can be
# pasted directly into a map.
# ============================================================

output_columns = [

    "review_priority",

    "distance_m",

    "rival_store_id",

    "osm_store_name",

    "osm_brand",

    "osm_operator",

    "osm_shop",

    "osm_postcode",

    "osm_canonical_fascia_check",

    "osm_latitude",

    "osm_longitude",

    "geo_id",

    "geo_store_name",

    "geo_fascia",

    "geo_retailer",

    "geo_size_band",

    "geo_postcode",

    "geo_canonical_fascia_check",

    "geo_latitude",

    "geo_longitude",

    "same_postcode",

    "name_similarity",

    "known_rebrand_pattern",

    "geo_removed_as_merger_party"
]


# ============================================================
# 30. SAVE THE TEMPORARY REVIEW CSV
# ============================================================

review[
    output_columns
].to_csv(

    OUTPUT_FILE,

    index=False
)


# ============================================================
# 31. PRINT SUMMARY STATISTICS
# ============================================================
#
# These give us a quick indication of whether this is actually a
# significant problem in the dataset.
# ============================================================

print(
    "\n======================================"
)


print(
    "POSSIBLE REBRAND / STALE RECORD CHECK"
)


print(
    "======================================"
)


print(
    "OSM rival stores checked:",
    len(osm)
)


print(
    "Potential different-fascia / stale pairs:",
    len(review)
)


print(
    "\nReview priority:"
)


print(
    review[
        "review_priority"
    ]
    .value_counts()
)


print(
    "\nUnique OSM stores requiring review:",
    review[
        "rival_store_id"
    ]
    .nunique()
)


print(
    "Known McColl's / Morrisons cases:",
    (
        review[
            "known_rebrand_pattern"
        ]
        != ""
    ).sum()
)


print(
    "Cases where nearby GEOLYTIX store was removed "
    "as a merger-party store:",
    review[
        "geo_removed_as_merger_party"
    ].sum()
)


# ============================================================
# 32. PRINT THE FIRST 40 REVIEW CASES
# ============================================================
#
# Usually the high-priority rows are enough for us to determine
# whether the issue is widespread.
# ============================================================

print(
    "\n======================================"
)


print(
    "FIRST 40 CASES TO REVIEW"
)


print(
    "======================================"
)


print(

    review[
        output_columns
    ]
    .head(40)
    .to_string(
        index=False
    )
)


# ============================================================
# 33. OUTPUT LOCATION
# ============================================================

print(
    "\nTemporary review file saved:"
)


print(
    OUTPUT_FILE
)


print(
    "\nThis script has NOT changed the final rival dataset."
)


print(
    "Once this QA exercise is finished, you can delete:"
)


print(
    TEMP_DIR.parent
)