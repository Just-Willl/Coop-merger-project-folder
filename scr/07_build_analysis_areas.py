# ============================================================
# 07 - BUILD COMPETITOR ANALYSIS AREAS
# ============================================================
#
# PURPOSE
#
# We have already identified where Southern Co-op and
# Co-operative Group overlap.
#
# This script now creates the local catchments that will be
# used to assess the competitive constraint from rival stores.
#
# It uses:
#
#   1. Stores involved in a 1-mile merger-party overlap
#   2. Stores whose 5-minute drive-time catchment contains
#      the other merger party
#
# For each relevant store we retain its own individual
# catchment.
#
# We DO NOT merge Southern and Co-op catchments together for
# competition analysis.
#
# A dissolved version is created only to define the geographic
# area from which rival grocery-store data will later be
# collected.
# ============================================================


import pandas as pd
import geopandas as gpd
from pathlib import Path


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
CLEANED_DIR = DATA_DIR / "cleaned"
DERIVED_DIR = DATA_DIR / "derived"


STORES_FILE = (
    CLEANED_DIR
    / "combined_stores_clean.csv"
)

ONE_MILE_PAIRS_FILE = (
    DERIVED_DIR
    / "party_1mi_overlap_pairs.csv"
)

FIVE_MIN_FLAGGED_FILE = (
    DERIVED_DIR
    / "party_5min_flagged_isochrones.gpkg"
)


# ============================================================
# 2. CHECK REQUIRED INPUT FILES EXIST
# ============================================================

required_files = [
    STORES_FILE,
    ONE_MILE_PAIRS_FILE,
    FIVE_MIN_FLAGGED_FILE
]

for file in required_files:

    if not file.exists():

        raise FileNotFoundError(
            f"Required input file not found:\n{file}"
        )


# ============================================================
# 3. LOAD CLEANED MERGER-PARTY STORE DATA
# ============================================================

stores_df = pd.read_csv(
    STORES_FILE
)

print(
    "Total merger-party stores:",
    len(stores_df)
)


# ============================================================
# 4. CREATE STORE POINT GEODATAFRAME
#
# Longitude and latitude are WGS84.
#
# British National Grid is then used because the one-mile
# catchments require distances measured in metres.
# ============================================================

stores_gdf = gpd.GeoDataFrame(
    stores_df,
    geometry=gpd.points_from_xy(
        stores_df["longitude"],
        stores_df["latitude"]
    ),
    crs="EPSG:4326"
)

stores_bng = stores_gdf.to_crs(
    "EPSG:27700"
)


# ============================================================
# 5. LOAD SAVED ONE-MILE OVERLAP PAIRS
#
# Each row represents one Southern / Co-op Group pair that
# lies within one mile.
#
# Example:
#
# Southern A <-> Co-op X
# Southern A <-> Co-op Y
#
# Those are TWO pairs but only THREE unique stores.
# ============================================================

one_mile_pairs = pd.read_csv(
    ONE_MILE_PAIRS_FILE
)

print(
    "\nOne-mile cross-party pairs:",
    len(one_mile_pairs)
)


# ============================================================
# 6. IDENTIFY UNIQUE STORES INVOLVED IN A ONE-MILE OVERLAP
#
# One-mile distance is symmetric.
#
# Therefore both members of each pair require their own
# one-mile local competition catchment.
# ============================================================

southern_1mi_ids = set(
    one_mile_pairs[
        "southern_store_id"
    ]
    .dropna()
    .unique()
)

coop_1mi_ids = set(
    one_mile_pairs[
        "coop_group_store_id"
    ]
    .dropna()
    .unique()
)

one_mile_centroid_ids = (
    southern_1mi_ids
    | coop_1mi_ids
)


print(
    "Unique Southern stores in 1-mile overlaps:",
    len(southern_1mi_ids)
)

print(
    "Unique Co-op Group stores in 1-mile overlaps:",
    len(coop_1mi_ids)
)

print(
    "Unique one-mile centroids:",
    len(one_mile_centroid_ids)
)


# ============================================================
# 7. EXTRACT THOSE STORES FROM THE MASTER STORE DATA
# ============================================================

one_mile_centroids = (
    stores_bng[
        stores_bng[
            "store_id"
        ].isin(
            one_mile_centroid_ids
        )
    ]
    .copy()
)


# ============================================================
# 8. VALIDATE THAT EVERY ONE-MILE STORE WAS FOUND
# ============================================================

found_1mi_ids = set(
    one_mile_centroids[
        "store_id"
    ]
)

missing_1mi_ids = (
    one_mile_centroid_ids
    - found_1mi_ids
)

if missing_1mi_ids:

    raise ValueError(
        "Some one-mile centroid IDs were not found "
        "in combined_stores_clean.csv:\n"
        f"{sorted(missing_1mi_ids)}"
    )


# ============================================================
# 9. CREATE ONE-MILE CATCHMENTS
#
# Every unique merger-party store involved in a one-mile
# overlap receives its OWN 1-mile catchment.
# ============================================================

ONE_MILE_M = 1609.344


one_mile_catchments = (
    one_mile_centroids[
        [
            "store_id",
            "party",
            "store_name",
            "postcode",
            "geometry"
        ]
    ]
    .copy()
)


one_mile_catchments[
    "geometry"
] = (
    one_mile_catchments
    .geometry
    .buffer(
        ONE_MILE_M
    )
)


# ============================================================
# 10. STANDARDISE ONE-MILE CATCHMENT COLUMNS
# ============================================================

one_mile_catchments = (
    one_mile_catchments
    .rename(
        columns={
            "store_id":
                "centroid_store_id",

            "party":
                "centroid_party",

            "store_name":
                "centroid_store_name",

            "postcode":
                "centroid_postcode"
        }
    )
)


one_mile_catchments[
    "catchment_type"
] = "1_mile"


one_mile_catchments[
    "catchment_id"
] = (
    one_mile_catchments[
        "centroid_store_id"
    ].astype(str)
    + "__1mi"
)


print(
    "\nOne-mile competition catchments:",
    len(one_mile_catchments)
)


# ============================================================
# 11. LOAD SAVED FLAGGED FIVE-MINUTE ISOCHRONES
#
# Script 06 already identified which centroid catchments
# contain the other merger party.
#
# Therefore we DO NOT repeat the five-minute spatial joins
# here.
# ============================================================

five_min_catchments = gpd.read_file(
    FIVE_MIN_FLAGGED_FILE
)


if (
    five_min_catchments.crs.to_epsg()
    != 27700
):

    five_min_catchments = (
        five_min_catchments
        .to_crs(
            "EPSG:27700"
        )
    )


print(
    "Five-minute flagged catchments:",
    len(five_min_catchments)
)


# ============================================================
# 12. CHECK FOR DUPLICATE FIVE-MINUTE CENTROIDS
#
# There should normally be one polygon per centroid store.
# ============================================================

duplicate_5min = (
    five_min_catchments[
        "store_id"
    ]
    .duplicated()
)

if duplicate_5min.any():

    print(
        "\nWARNING:"
    )

    print(
        "Duplicate five-minute centroid polygons detected."
    )

    print(
        five_min_catchments.loc[
            duplicate_5min,
            "store_id"
        ].tolist()
    )


# ============================================================
# 13. ADD STORE DETAILS TO FIVE-MINUTE CATCHMENTS
#
# We already have the geometry.
#
# We only add descriptive information from the cleaned
# merger-party store dataset.
# ============================================================

store_details = (
    stores_df[
        [
            "store_id",
            "store_name",
            "postcode"
        ]
    ]
    .drop_duplicates(
        subset="store_id"
    )
)


five_min_catchments = (
    five_min_catchments
    .merge(
        store_details,
        on="store_id",
        how="left"
    )
)


# ============================================================
# 14. STANDARDISE FIVE-MINUTE CATCHMENT COLUMNS
# ============================================================

five_min_catchments = (
    five_min_catchments
    .rename(
        columns={
            "store_id":
                "centroid_store_id",

            "party":
                "centroid_party",

            "store_name":
                "centroid_store_name",

            "postcode":
                "centroid_postcode"
        }
    )
)


five_min_catchments[
    "catchment_type"
] = "5_min_drive"


five_min_catchments[
    "catchment_id"
] = (
    five_min_catchments[
        "centroid_store_id"
    ].astype(str)
    + "__5min"
)


# ============================================================
# 15. KEEP ONLY COLUMNS NEEDED FOR DOWNSTREAM ANALYSIS
# ============================================================

catchment_columns = [
    "catchment_id",
    "centroid_store_id",
    "centroid_party",
    "centroid_store_name",
    "centroid_postcode",
    "catchment_type",
    "geometry"
]


one_mile_catchments = (
    one_mile_catchments[
        catchment_columns
    ]
    .copy()
)


five_min_catchments = (
    five_min_catchments[
        catchment_columns
    ]
    .copy()
)


# ============================================================
# 16. COMBINE THE INDIVIDUAL CATCHMENTS
#
# IMPORTANT:
#
# pd.concat here combines rows into one GeoDataFrame.
#
# It DOES NOT geometrically combine the catchments.
#
# Every row remains a separate local competition screen.
# ============================================================

analysis_catchments = gpd.GeoDataFrame(
    pd.concat(
        [
            one_mile_catchments,
            five_min_catchments
        ],
        ignore_index=True
    ),
    geometry="geometry",
    crs="EPSG:27700"
)


# ============================================================
# 17. CHECK FOR DUPLICATE CATCHMENT IDs
# ============================================================

duplicate_catchments = (
    analysis_catchments[
        "catchment_id"
    ]
    .duplicated()
)

if duplicate_catchments.any():

    duplicates = (
        analysis_catchments.loc[
            duplicate_catchments,
            "catchment_id"
        ]
        .tolist()
    )

    raise ValueError(
        "Duplicate catchment IDs detected:\n"
        f"{duplicates}"
    )


# ============================================================
# 18. SORT CATCHMENTS FOR READABILITY
# ============================================================

analysis_catchments = (
    analysis_catchments
    .sort_values(
        [
            "centroid_store_id",
            "catchment_type"
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 19. SUMMARY OF INDIVIDUAL COMPETITION SCREENS
# ============================================================

print(
    "\n======================================"
)

print(
    "INDIVIDUAL LOCAL COMPETITION SCREENS"
)

print(
    "======================================"
)


print(
    "\nTotal catchments:",
    len(analysis_catchments)
)


print(
    "\nCatchments by type:"
)

print(
    analysis_catchments[
        "catchment_type"
    ]
    .value_counts()
)


print(
    "\nUnique centroid stores:",
    analysis_catchments[
        "centroid_store_id"
    ]
    .nunique()
)


# ============================================================
# 20. CHECK HOW MANY STORES HAVE BOTH TYPES OF CATCHMENT
# ============================================================

catchments_per_centroid = (
    analysis_catchments
    .groupby(
        "centroid_store_id"
    )[
        "catchment_type"
    ]
    .nunique()
)


stores_with_both = (
    catchments_per_centroid
    == 2
).sum()


stores_with_one = (
    catchments_per_centroid
    == 1
).sum()


print(
    "\nCentroids with both "
    "1-mile and 5-minute screens:",
    stores_with_both
)

print(
    "Centroids with only one "
    "relevant screen:",
    stores_with_one
)


# ============================================================
# 21. CREATE DISSOLVED RIVAL-STORE COLLECTION AREA
#
# This is the ONLY point where the catchments are
# geometrically merged.
#
# This geometry will simply tell script 08:
#
# "Download potentially relevant rival grocery stores
# anywhere within this territory."
#
# It will NOT be used as the geographic market for the
# competition analysis.
# ============================================================

collection_area = (
    analysis_catchments[
        [
            "geometry"
        ]
    ]
    .copy()
)


collection_area[
    "collection_area"
] = (
    "all_relevant_local_catchments"
)


collection_area = (
    collection_area
    .dissolve(
        by="collection_area"
    )
    .reset_index()
)


# ============================================================
# 22. SAVE INDIVIDUAL COMPETITION CATCHMENTS
#
# This is the important analytical dataset.
# ============================================================

ANALYSIS_CATCHMENTS_FILE = (
    DERIVED_DIR
    / "competitor_analysis_catchments.gpkg"
)


analysis_catchments.to_file(
    ANALYSIS_CATCHMENTS_FILE,
    driver="GPKG"
)


# ============================================================
# 23. SAVE DISSOLVED DATA-COLLECTION AREA
#
# This is only for efficient rival-store data collection.
# ============================================================

COLLECTION_AREA_FILE = (
    DERIVED_DIR
    / "rival_store_collection_area.gpkg"
)


collection_area.to_file(
    COLLECTION_AREA_FILE,
    driver="GPKG"
)

# ============================================================
# 25. VISUALISE DISSOLVED CATCHMENT AREAS BY MERGER PARTY
# ============================================================

import matplotlib.pyplot as plt


# ------------------------------------------------------------
# Load UK boundary
# ------------------------------------------------------------

UK_BOUNDARY_FILE = (
    DATA_DIR
    / "boundaries"
    / "uk_countries_2025"
    / "CTRY_DEC_2025_UK_BGC.shp"
)

uk_boundary = gpd.read_file(
    UK_BOUNDARY_FILE
)

# Convert to British National Grid so it matches the
# competition catchments
uk = uk_boundary.to_crs(
    "EPSG:27700"
)


# ------------------------------------------------------------
# Dissolve catchments separately by centroid party
#
# This is only for visualisation.
# Individual catchments remain separate in
# competitor_analysis_catchments.gpkg.
# ------------------------------------------------------------

party_collection_areas = (
    analysis_catchments[
        [
            "centroid_party",
            "geometry"
        ]
    ]
    .dissolve(
        by="centroid_party"
    )
    .reset_index()
)


# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(11, 11)
)


# UK background
uk.plot(
    ax=ax,
    facecolor="whitesmoke",
    edgecolor="black",
    linewidth=0.6,
    zorder=1
)


# Southern Co-op-centred catchment territory
party_collection_areas[
    party_collection_areas[
        "centroid_party"
    ] == "Southern Co-op"
].plot(
    ax=ax,
    color="tab:orange",
    alpha=0.40,
    edgecolor="tab:orange",
    linewidth=1.0,
    label="Southern Co-op-centred catchments",
    zorder=2
)


# Co-operative Group-centred catchment territory
party_collection_areas[
    party_collection_areas[
        "centroid_party"
    ] == "Co-operative Group"
].plot(
    ax=ax,
    color="tab:blue",
    alpha=0.30,
    edgecolor="tab:blue",
    linewidth=1.0,
    label="Co-operative Group-centred catchments",
    zorder=3
)


# ------------------------------------------------------------
# Zoom to the competitor collection territory
# ------------------------------------------------------------

minx, miny, maxx, maxy = (
    analysis_catchments
    .total_bounds
)

padding = 30000  # 30 km

ax.set_xlim(
    minx - padding,
    maxx + padding
)

ax.set_ylim(
    miny - padding,
    maxy + padding
)


# ------------------------------------------------------------
# Title and legend
# ------------------------------------------------------------

ax.set_title(
    "Geographic Area Covered by Local Competition Catchments",
    fontsize=15,
    pad=15
)

ax.legend(
    title="Catchment centroid",
    loc="upper left",
    frameon=True,
    fancybox=True,
    framealpha=0.95,
    facecolor="white",
    edgecolor="lightgray"
)

ax.set_axis_off()

plt.tight_layout()

plt.show()


# ============================================================
# 26. FINAL SUMMARY
# ============================================================

print(
    "\n======================================"
)

print(
    "COMPETITOR ANALYSIS AREAS COMPLETE"
)

print(
    "======================================"
)


print(
    "One-mile pairs:",
    len(one_mile_pairs)
)

print(
    "Unique one-mile centroids:",
    len(one_mile_centroid_ids)
)

print(
    "Five-minute catchments:",
    len(five_min_catchments)
)

print(
    "Total individual catchments:",
    len(analysis_catchments)
)

print(
    "Unique centroid stores overall:",
    analysis_catchments[
        "centroid_store_id"
    ]
    .nunique()
)


print(
    "\nSaved:"
)

print(
    ANALYSIS_CATCHMENTS_FILE
)

print(
    COLLECTION_AREA_FILE
)


