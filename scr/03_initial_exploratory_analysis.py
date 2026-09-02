import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx

# Load cleaned data 
stores_df = pd.read_csv(
    "../data/cleaned/combined_stores_clean.csv"
)


# Create geographic point geometry
stores_gdf = gpd.GeoDataFrame(
    stores_df,
    geometry=gpd.points_from_xy(
        stores_df["longitude"],
        stores_df["latitude"]
    ),
    crs="EPSG:4326"
)

# Now we create a new gedo-dataframe with the british national grid crs system
stores_bng = stores_gdf.to_crs("EPSG:27700")



# Now we load the boundary of the UK to use as a basemap for our plots
uk_boundary = gpd.read_file("../data/boundaries/uk_countries_2025/CTRY_DEC_2025_UK_BGC.shp"
)

# Now we convert the uk boundary to the british national grid crs system
uk = uk_boundary.to_crs("EPSG:27700")

# And now we plot the geographic footprints of the two merger parties on a map of the UK
fig, ax = plt.subplots(figsize=(10, 12))

# UK boundary
uk.plot(
    ax=ax,
    facecolor="whitesmoke",
    edgecolor="black",
    linewidth=0.6,
    zorder=1,
)

# Co-operative Group
stores_bng[
    stores_bng["party"] == "Co-operative Group"
].plot(
    ax=ax,
    color="tab:blue",
    markersize=10,
    alpha=0.55,
    label="Co-operative Group",
    zorder=2,
)

# Southern Co-op
stores_bng[
    stores_bng["party"] == "Southern Co-op"
].plot(
    ax=ax,
    color="tab:orange",
    markersize=10,
    alpha=0.85,
    edgecolor="white",
    linewidth=0.3,
    label="Southern Co-op",
    zorder=2,
)

ax.set_title(
    "Geographic Footprints of the Proposed Merger Parties",
    fontsize=15,
    pad=15,
)

ax.legend(
    title="Merger party",
    frameon=False,
)

ax.set_axis_off()

plt.tight_layout()
plt.show()
