# ============================================================
# 5-MINUTE DRIVE-TIME CROSS-PARTY OVERLAP ANALYSIS
# ============================================================

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# 1. SET PATHS
# ============================================================

OUTPUT_DIR = Path("../data/derived")

ISOCHRONE_FILE = (
    OUTPUT_DIR / "party_5min_isochrones.gpkg"
)


# ============================================================
# 2. LOAD SAVED 5-MINUTE ISOCHRONES
# ============================================================

isochrones_5min_bng = gpd.read_file(
    ISOCHRONE_FILE
)

print(
    "Isochrone CRS:",
    isochrones_5min_bng.crs
)

print(
    "Number of isochrones:",
    len(isochrones_5min_bng)
)


# ============================================================
# 3. CHECK CRS
#
# Everything used in the spatial joins should be in
# British National Grid (EPSG:27700).
# ============================================================

# Load cleaned store data
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

# Now we load the boundary of the UK to use as a basemap for our plots
uk_boundary = gpd.read_file("../data/boundaries/uk_countries_2025/CTRY_DEC_2025_UK_BGC.shp"
)

# Now we convert the uk boundary to the british national grid crs system
uk = uk_boundary.to_crs("EPSG:27700")

# ============================================================
# 4. SPLIT STORE POINTS BY MERGER PARTY
# ============================================================

southern = stores_bng[
    stores_bng["party"] == "Southern Co-op"
].copy()

coop_group = stores_bng[
    stores_bng["party"] == "Co-operative Group"
].copy()

print(
    "\nSouthern Co-op stores:",
    len(southern)
)

print(
    "Co-operative Group stores:",
    len(coop_group)
)


# ============================================================
# 5. SPLIT 5-MINUTE ISOCHRONES BY MERGER PARTY
# ============================================================

southern_isochrones = (
    isochrones_5min_bng[
        isochrones_5min_bng["party"]
        == "Southern Co-op"
    ][
        ["store_id", "geometry"]
    ]
    .copy()
    .rename(
        columns={
            "store_id":
            "southern_centroid_id"
        }
    )
)

coop_isochrones = (
    isochrones_5min_bng[
        isochrones_5min_bng["party"]
        == "Co-operative Group"
    ][
        ["store_id", "geometry"]
    ]
    .copy()
    .rename(
        columns={
            "store_id":
            "coop_centroid_id"
        }
    )
)

print(
    "\nSouthern Co-op isochrones:",
    len(southern_isochrones)
)

print(
    "Co-operative Group isochrones:",
    len(coop_isochrones)
)


# ============================================================
# 6. SOUTHERN-CENTRED OVERLAP TEST
#
# Question:
# Which Co-operative Group stores fall inside a
# Southern Co-op 5-minute drive-time isochrone?
# ============================================================

coop_points = (
    coop_group[
        ["store_id", "geometry"]
    ]
    .copy()
    .rename(
        columns={
            "store_id":
            "coop_store_id"
        }
    )
)

southern_to_coop_5min = gpd.sjoin(
    coop_points,
    southern_isochrones,
    how="inner",
    predicate="within"
)

southern_to_coop_5min = (
    southern_to_coop_5min
    .drop(
        columns="index_right",
        errors="ignore"
    )
    .reset_index(drop=True)
)

print(
    "\nSouthern-centred "
    "cross-party store pairs:",
    len(southern_to_coop_5min)
)


# ============================================================
# 7. CO-OP GROUP-CENTRED OVERLAP TEST
#
# Question:
# Which Southern Co-op stores fall inside a
# Co-operative Group 5-minute drive-time isochrone?
#
# We test both directions because drive-time catchments
# are not necessarily symmetric.
# ============================================================

southern_points = (
    southern[
        ["store_id", "geometry"]
    ]
    .copy()
    .rename(
        columns={
            "store_id":
            "southern_store_id"
        }
    )
)

coop_to_southern_5min = gpd.sjoin(
    southern_points,
    coop_isochrones,
    how="inner",
    predicate="within"
)

coop_to_southern_5min = (
    coop_to_southern_5min
    .drop(
        columns="index_right",
        errors="ignore"
    )
    .reset_index(drop=True)
)

print(
    "Co-op Group-centred "
    "cross-party store pairs:",
    len(coop_to_southern_5min)
)


# ============================================================
# 8. PUT BOTH DIRECTIONS INTO THE SAME FORMAT
# ============================================================

southern_direction = pd.DataFrame(
    {
        "centroid_store_id":
            southern_to_coop_5min[
                "southern_centroid_id"
            ],

        "centroid_party":
            "Southern Co-op",

        "other_store_id":
            southern_to_coop_5min[
                "coop_store_id"
            ],

        "other_party":
            "Co-operative Group"
    }
)

coop_direction = pd.DataFrame(
    {
        "centroid_store_id":
            coop_to_southern_5min[
                "coop_centroid_id"
            ],

        "centroid_party":
            "Co-operative Group",

        "other_store_id":
            coop_to_southern_5min[
                "southern_store_id"
            ],

        "other_party":
            "Southern Co-op"
    }
)


# ============================================================
# 9. COMBINE DIRECTIONAL OVERLAPS
#
# Each row means:
#
# "The opposite-party store lies inside the centroid
# store's 5-minute drive-time catchment."
# ============================================================

drive_time_overlaps_5min = pd.concat(
    [
        southern_direction,
        coop_direction
    ],
    ignore_index=True
)

drive_time_overlaps_5min = (
    drive_time_overlaps_5min
    .drop_duplicates()
    .reset_index(drop=True)
)

print(
    "\nTotal directional "
    "5-minute overlap pairs:",
    len(drive_time_overlaps_5min)
)


# ============================================================
# 10. COUNT OPPOSITE-PARTY STORES IN EACH CATCHMENT
# ============================================================

overlap_counts_5min = (
    drive_time_overlaps_5min
    .groupby(
        [
            "centroid_store_id",
            "centroid_party"
        ]
    )[
        "other_store_id"
    ]
    .nunique()
    .rename(
        "other_party_stores_within_5min"
    )
    .reset_index()
)

print(
    "\nDistribution of opposite-party "
    "stores within 5 minutes:"
)

print(
    overlap_counts_5min[
        "other_party_stores_within_5min"
    ]
    .value_counts()
    .sort_index()
)


# ============================================================
# 11. IDENTIFY FLAGGED CENTROIDS
#
# These are stores whose OWN 5-minute catchment contains
# at least one store belonging to the other merger party.
# ============================================================

flagged_centroid_ids = set(
    overlap_counts_5min[
        "centroid_store_id"
    ]
)

print(
    "\nNumber of centroid stores "
    "with a cross-party 5-minute overlap:",
    len(flagged_centroid_ids)
)

print(
    "\nFlagged centroids by party:"
)

print(
    overlap_counts_5min[
        "centroid_party"
    ]
    .value_counts()
)


# ============================================================
# 12. EXTRACT FLAGGED ISOCHRONE POLYGONS
# ============================================================

flagged_isochrones_5min = (
    isochrones_5min_bng[
        isochrones_5min_bng[
            "store_id"
        ].isin(
            flagged_centroid_ids
        )
    ]
    .copy()
)

print(
    "\nFlagged 5-minute "
    "isochrones:",
    len(flagged_isochrones_5min)
)


# ============================================================
# 13. IDENTIFY ALL STORES INVOLVED
#
# This includes:
#
# - centroid stores
# - opposite-party stores lying within their catchments
# ============================================================

involved_store_ids = set(
    drive_time_overlaps_5min[
        "centroid_store_id"
    ]
).union(
    set(
        drive_time_overlaps_5min[
            "other_store_id"
        ]
    )
)

overlapping_southern_5min = (
    southern[
        southern[
            "store_id"
        ].isin(
            involved_store_ids
        )
    ]
    .copy()
)

overlapping_coop_5min = (
    coop_group[
        coop_group[
            "store_id"
        ].isin(
            involved_store_ids
        )
    ]
    .copy()
)

print(
    "\nSouthern Co-op stores "
    "involved in a 5-minute overlap:",
    len(overlapping_southern_5min)
)

print(
    "Co-operative Group stores "
    "involved in a 5-minute overlap:",
    len(overlapping_coop_5min)
)


# ============================================================
# 14. MAP THE 5-MINUTE OVERLAPS
# ============================================================

fig, ax = plt.subplots(
    figsize=(12, 10)
)


# ------------------------------------------------------------
# UK boundary
# ------------------------------------------------------------

uk.plot(
    ax=ax,
    facecolor="whitesmoke",
    edgecolor="black",
    linewidth=0.6,
    zorder=1
)


# ------------------------------------------------------------
# Background Co-operative Group stores
# ------------------------------------------------------------

coop_group.plot(
    ax=ax,
    color="cornflowerblue",
    markersize=4,
    alpha=0.16,
    zorder=2
)


# ------------------------------------------------------------
# Background Southern Co-op stores
# ------------------------------------------------------------

southern.plot(
    ax=ax,
    color="navajowhite",
    markersize=4,
    alpha=0.22,
    zorder=2
)


# ------------------------------------------------------------
# Flagged 5-minute drive-time catchments
# ------------------------------------------------------------

flagged_isochrones_5min.plot(
    ax=ax,
    facecolor="none",
    edgecolor="tab:red",
    linewidth=0.9,
    alpha=0.55,
    label="5-minute overlap catchment",
    zorder=3
)


# ------------------------------------------------------------
# Co-operative Group stores involved in overlaps
# ------------------------------------------------------------

overlapping_coop_5min.plot(
    ax=ax,
    color="tab:blue",
    markersize=10,
    alpha=0.65,
    edgecolor="white",
    linewidth=0.4,
    label=(
        "Overlapping "
        "Co-operative Group store"
    ),
    zorder=4
)


# ------------------------------------------------------------
# Southern Co-op stores involved in overlaps
# ------------------------------------------------------------

overlapping_southern_5min.plot(
    ax=ax,
    color="tab:orange",
    markersize=10,
    alpha=0.65,
    edgecolor="white",
    linewidth=0.4,
    label=(
        "Overlapping "
        "Southern Co-op store"
    ),
    zorder=5
)


# ============================================================
# 15. ZOOM TO THE RELEVANT AREA
# ============================================================

if not flagged_isochrones_5min.empty:

    minx, miny, maxx, maxy = (
        flagged_isochrones_5min
        .total_bounds
    )

    padding = 20000   # 20 km

    ax.set_xlim(
        minx - padding,
        maxx + padding
    )

    ax.set_ylim(
        miny - padding,
        maxy + padding
    )


# ============================================================
# 16. TITLE AND LEGEND
# ============================================================

ax.set_title(
    "Southern Co-op / Co-operative Group\n"
    "Five-Minute Drive-Time Local Overlap Screen",
    fontsize=15,
    pad=15
)

ax.legend(
    title="Map key",
    loc="upper left",
    frameon=True,
    fancybox=True,
    framealpha=0.95,
    facecolor="white",
    edgecolor="gray",
    borderpad=0.8,
    labelspacing=0.7
)

ax.set_axis_off()

plt.tight_layout()

plt.show()


# ============================================================
# 17. SAVE 5-MINUTE OVERLAP PAIRS
# ============================================================

drive_time_overlaps_5min.to_csv(
    OUTPUT_DIR
    / "party_5min_overlap_pairs.csv",
    index=False
)


# ============================================================
# 18. SAVE COUNTS BY CENTROID STORE
# ============================================================

overlap_counts_5min.to_csv(
    OUTPUT_DIR
    / "party_5min_overlap_counts.csv",
    index=False
)


# ============================================================
# 19. SAVE FLAGGED ISOCHRONE POLYGONS
# ============================================================

flagged_isochrones_5min.to_file(
    OUTPUT_DIR
    / "party_5min_flagged_isochrones.gpkg",
    driver="GPKG"
)


# ============================================================
# 20. FINAL SUMMARY
# ============================================================

print(
    "\n=================================="
)

print(
    "5-MINUTE DRIVE-TIME SCREEN SUMMARY"
)

print(
    "=================================="
)

print(
    "Directional overlap pairs:",
    len(drive_time_overlaps_5min)
)

print(
    "Flagged centroid stores:",
    len(flagged_centroid_ids)
)

print(
    "Southern stores involved:",
    len(overlapping_southern_5min)
)

print(
    "Co-op Group stores involved:",
    len(overlapping_coop_5min)
)

print(
    "\nSaved:"
)

print(
    OUTPUT_DIR
    / "party_5min_overlap_pairs.csv"
)

print(
    OUTPUT_DIR
    / "party_5min_overlap_counts.csv"
)

print(
    OUTPUT_DIR
    / "party_5min_flagged_isochrones.gpkg"
)