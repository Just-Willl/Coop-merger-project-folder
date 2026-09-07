# Using the location data for Southern Co-op and the Co-operative Group, we can now examine the geographic overlap between the two merger parties. 
# We assume that in areas where both parties have stores, there is likely a competitive pressure exerted upon each other.
# If the merger is approved then this competitive pressure will become internalised possibly leading to unilateral effects on prices and quality of service.
# Especially in areas where the two parties have little or no competition from other independent stores.
# I will assume that customers are likely to either walk into a store within a 1 mile radius or drive to a store within 5 minutes of them.


import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

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


# -----------------------------------------
# 1-mile merger-party overlap analysis
# -----------------------------------------

# One mile in metres
ONE_MILE_M = 1609.344

# Split the two merger parties
southern = stores_bng[
    stores_bng["party"] == "Southern Co-op"
].copy()

coop_group = stores_bng[
    stores_bng["party"] == "Co-operative Group"
].copy()


# -----------------------------------------
# Create 1-mile radial catchments
# around Southern Co-op stores
# -----------------------------------------

southern_buffers = southern[
    ["store_id", "geometry"]
].copy()

southern_buffers["geometry"] = (
    southern_buffers.geometry.buffer(ONE_MILE_M)
)


# -----------------------------------------
# Spatial join:
# find Co-operative Group stores
# within 1 mile of Southern Co-op stores
# -----------------------------------------

party_overlaps_1mi = gpd.sjoin(
    coop_group[
        ["store_id", "geometry"]
    ],
    southern_buffers,
    how="inner",
    predicate="within",
    lsuffix="coop_group",
    rsuffix="southern"
)


# -----------------------------------------
# Clean the joined output
# -----------------------------------------

party_overlaps_1mi = (
    party_overlaps_1mi
    .rename(columns={
        "store_id_coop_group": "coop_group_store_id",
        "store_id_southern": "southern_store_id"
    })
    .drop(columns="index_southern")
    .reset_index(drop=True)
)


# -----------------------------------------
# Count how many Co-op Group stores
# are within 1 mile of each Southern store
# -----------------------------------------

overlap_counts = (
    party_overlaps_1mi
    .groupby("southern_store_id")["coop_group_store_id"]
    .nunique()
    .rename("coop_group_stores_within_1mi")
)


# -----------------------------------------
# Join the overlap counts back onto
# the Southern Co-op store GeoDataFrame
# -----------------------------------------

southern_results = southern.merge(
    overlap_counts,
    left_on="store_id",
    right_index=True,
    how="left"
)

southern_results["coop_group_stores_within_1mi"] = (
    southern_results["coop_group_stores_within_1mi"]
    .fillna(0)
    .astype(int)
)


# -----------------------------------------
# Identify Southern stores with at least
# one Co-op Group store within 1 mile
# -----------------------------------------

overlapping_southern = southern_results[
    southern_results["coop_group_stores_within_1mi"] > 0
].copy()


# -----------------------------------------
# Join overlap counts onto the buffer polygons
# so they can be mapped later
# -----------------------------------------

southern_buffers = southern_buffers.merge(
    overlap_counts,
    left_on="store_id",
    right_index=True,
    how="left"
)

southern_buffers["coop_group_stores_within_1mi"] = (
    southern_buffers["coop_group_stores_within_1mi"]
    .fillna(0)
    .astype(int)
)


# Keep only catchments where a cross-party overlap exists
overlap_buffers = southern_buffers[
    southern_buffers["coop_group_stores_within_1mi"] > 0
].copy()


# -----------------------------------------
# Basic summary outputs
# -----------------------------------------

print(
    "Number of cross-party store pairs within 1 mile:",
    len(party_overlaps_1mi)
)

print(
    "Number of Southern Co-op stores with at least one "
    "Co-operative Group store within 1 mile:",
    len(overlapping_southern)
)

print("\nDistribution of Co-op Group stores within 1 mile of a Southern Co-op store:")
print(
    southern_results[
        "coop_group_stores_within_1mi"
    ]
    .value_counts()
    .sort_index()
)



# Now we have the 1 mile overlap data, we can visualise it on a map.


# Identify Co-operative Group stores that appear
# in at least one 1-mile merger-party overlap

overlap_coop_ids = (
    party_overlaps_1mi["coop_group_store_id"]
    .unique()
)

overlapping_coop = coop_group[
    coop_group["store_id"].isin(overlap_coop_ids)
].copy()


# -----------------------------------------
# Map 1-mile merger-party overlaps
# -----------------------------------------

# Now we load the boundary of the UK to use as a basemap for our plots
uk_boundary = gpd.read_file("../data/boundaries/uk_countries_2025/CTRY_DEC_2025_UK_BGC.shp"
)

# Now we convert the uk boundary to the british national grid crs system
uk = uk_boundary.to_crs("EPSG:27700")


fig, ax = plt.subplots(figsize=(10, 12))

# UK boundary
uk.plot(
    ax=ax,
    facecolor="whitesmoke",
    edgecolor="black",
    linewidth=0.6,
    zorder=1,
)

# All Co-operative Group stores - background context
coop_group.plot(
    ax=ax,
    color="tab:blue",
    markersize=8,
    alpha=0.15,
    zorder=2,
)

# All Southern Co-op stores - background context
southern.plot(
    ax=ax,
    color="tab:orange",
    markersize=8,
    alpha=0.25,
    zorder=2,
)

# 1-mile catchments where a merger-party overlap occurs
overlap_buffers.plot(
    ax=ax,
    facecolor="none",
    edgecolor="tab:red",
    linewidth=1.2,
    alpha=0.8,
    label="1-mile overlap catchment",
    zorder=3,
)

# Co-operative Group stores involved in overlaps
overlapping_coop.plot(
    ax=ax,
    color="tab:blue",
    markersize=30,
    alpha=0.9,
    edgecolor="white",
    linewidth=0.4,
    label="Overlapping Co-operative Group store",
    zorder=4,
)

# Southern Co-op stores involved in overlaps
overlapping_southern.plot(
    ax=ax,
    color="tab:orange",
    markersize=35,
    alpha=0.95,
    edgecolor="white",
    linewidth=0.4,
    label="Overlapping Southern Co-op store",
    zorder=5,
)

ax.set_title(
    "One-Mile Geographic Overlaps Between the Proposed Merger Parties",
    fontsize=15,
    pad=15,
)

ax.legend(
    title="Local overlap screen",
    frameon=False,
)

ax.set_axis_off()

plt.tight_layout()
plt.show()


# -----------------------------------------
# Zoomed map of 1-mile overlap areas
# -----------------------------------------

fig, ax = plt.subplots(figsize=(12, 10))

# UK boundary
uk.plot(
    ax=ax,
    facecolor="whitesmoke",
    edgecolor="black",
    linewidth=0.6,
    zorder=1,
)

# Background Co-operative Group stores
coop_group.plot(
    ax=ax,
    color="cornflowerblue",
    markersize=5,
    alpha=0.18,
    zorder=2,
)

# Background Southern Co-op stores
southern.plot(
    ax=ax,
    color="navajowhite",
    markersize=5,
    alpha=0.22,
    zorder=2,
)


# Overlapping Co-operative Group stores
overlapping_coop.plot(
    ax=ax,
    color="tab:blue",
    markersize=35,
    alpha=0.95,
    edgecolor="white",
    linewidth=0.4,
    label="Overlapping Co-operative Group store",
    zorder=4,
)

# Overlapping Southern Co-op stores
overlapping_southern.plot(
    ax=ax,
    color="tab:orange",
    markersize=38,
    alpha=0.95,
    edgecolor="white",
    linewidth=0.4,
    label="Overlapping Southern Co-op store",
    zorder=5,
)

# Zoom to overlap area
minx, miny, maxx, maxy = overlap_buffers.total_bounds
padding = 20000  # 20 km

ax.set_xlim(minx - padding, maxx + padding)
ax.set_ylim(miny - padding, maxy + padding)

ax.set_title(
    "Southern Co-op / Co-operative Group\nOne-Mile Local Overlap Screen",
    fontsize=15,
    pad=15,
)

# Clearer boxed legend
legend = ax.legend(
    title="Map key",
    loc="upper left",
    frameon=True,
    fancybox=True,
    framealpha=0.95,
    facecolor="white",
    edgecolor="lightgray",
    borderpad=0.8,
    labelspacing=0.7
)

ax.set_axis_off()

plt.tight_layout()
plt.show()