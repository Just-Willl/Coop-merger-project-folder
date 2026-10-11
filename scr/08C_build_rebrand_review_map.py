# ============================================================
# 08C - BUILD INTERACTIVE MAP FOR STALE / REBRAND REVIEW
# ============================================================
#
# TEMPORARY QA SCRIPT
#
# PURPOSE
# -------
# Script 08B identified OSM and GEOLYTIX records that:
#
#   - are geographically very close together
#   - but appear to have different fasciae
#
# Some of these may represent:
#
#   - stale OSM records
#   - store rebrands
#   - ownership changes
#   - genuine separate nearby stores
#
#
# Looking at these records in a CSV is difficult.
#
# This script therefore creates an interactive HTML map where:
#
#   - OSM points can be clicked
#   - GEOLYTIX points can be clicked
#   - suspicious pairs are connected by a line
#   - VERY HIGH, HIGH and REVIEW cases can be toggled
#   - cases involving merger-party GEOLYTIX stores can be toggled
#
#
# OUTPUT
# ------
#
# The map is saved to:
#
# data/_temp_checks/08B_rebrand_check/
# TEMP_08C_rebrand_review_map.html
#
#
# This script DOES NOT modify any project data.
# ============================================================


from pathlib import Path

import pandas as pd
import folium

from folium import FeatureGroup
from folium.plugins import Fullscreen


# ============================================================
# 1. PROJECT PATHS
# ============================================================
#
# The script is assumed to live inside the project's `scr`
# directory.
#
# parent.parent therefore gives us the project root.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

TEMP_DIR = (
    DATA_DIR
    / "_temp_checks"
    / "08B_rebrand_check"
)


INPUT_FILE = (
    TEMP_DIR
    / "TEMP_08B_possible_rebrand_duplicates.csv"
)


OUTPUT_FILE = (
    TEMP_DIR
    / "TEMP_08C_rebrand_review_map.html"
)


# ============================================================
# 2. CHECK THAT THE 08B OUTPUT EXISTS
# ============================================================
#
# 08C depends on the review CSV created by 08B.
#
# If that file does not exist, stop immediately rather than
# creating an empty or misleading map.
# ============================================================

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        "08B review file not found:\n"
        f"{INPUT_FILE}\n\n"
        "Run 08B_check_possible_rebrands.py first."
    )


# ============================================================
# 3. LOAD THE REVIEW DATA
# ============================================================

review = pd.read_csv(
    INPUT_FILE
)


print(
    "Review rows loaded:",
    len(review)
)


print(
    "Unique OSM stores:",
    review[
        "rival_store_id"
    ].nunique()
)


# ============================================================
# 4. CHECK REQUIRED COLUMNS
# ============================================================
#
# These fields are needed to place points on the map and build
# useful popup information.
# ============================================================

required_columns = [

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

    "known_rebrand_pattern",

    "geo_removed_as_merger_party"
]


missing_columns = [

    column

    for column in required_columns

    if column not in review.columns
]


if missing_columns:

    raise ValueError(
        "The 08B CSV is missing required columns:\n"
        +
        "\n".join(
            missing_columns
        )
    )


# ============================================================
# 5. HELPER FUNCTION FOR DISPLAYING MISSING VALUES
# ============================================================
#
# Pandas displays missing values as NaN.
#
# That is useful analytically but ugly inside a map popup.
#
# This converts missing values to a simple dash.
# ============================================================

def display_value(value):

    if pd.isna(value):

        return "-"


    value = str(value)


    if value.strip() == "":

        return "-"


    return value


# ============================================================
# 6. FIND THE CENTRE OF THE MAP
# ============================================================
#
# Rather than manually specifying a city or coordinate, take the
# average location of all OSM and GEOLYTIX review points.
#
# Folium will later automatically zoom to include every review
# case anyway.
# ============================================================

all_latitudes = pd.concat(

    [
        review[
            "osm_latitude"
        ],

        review[
            "geo_latitude"
        ]
    ],

    ignore_index=True
)


all_longitudes = pd.concat(

    [
        review[
            "osm_longitude"
        ],

        review[
            "geo_longitude"
        ]
    ],

    ignore_index=True
)


map_centre = [

    all_latitudes.mean(),

    all_longitudes.mean()
]


# ============================================================
# 7. CREATE THE BASE MAP
# ============================================================
#
# OpenStreetMap provides the background basemap.
#
# zoom_start is only the initial zoom. The map will later be
# fitted automatically around all review locations.
# ============================================================

review_map = folium.Map(

    location=map_centre,

    zoom_start=7,

    tiles="OpenStreetMap",

    control_scale=True
)


# Add a full-screen button.
#
# This makes detailed inspection much easier.
Fullscreen(
    position="topright"
).add_to(
    review_map
)


# ============================================================
# 8. CREATE MAP LAYERS
# ============================================================
#
# Feature groups allow us to switch categories on and off using
# the layer-control menu.
#
# We create separate groups for:
#
#   VERY HIGH
#   HIGH
#   REVIEW
#
# and a special layer highlighting cases where GEOLYTIX says the
# nearby current store belongs to one of the merger parties.
# ============================================================

very_high_layer = FeatureGroup(
    name="VERY HIGH priority",
    show=True
)


high_layer = FeatureGroup(
    name="HIGH priority",
    show=True
)


review_layer = FeatureGroup(
    name="REVIEW priority",
    show=False
)


party_layer = FeatureGroup(
    name="Nearby merger-party stores",
    show=True
)


very_high_layer.add_to(
    review_map
)


high_layer.add_to(
    review_map
)


review_layer.add_to(
    review_map
)


party_layer.add_to(
    review_map
)


# ============================================================
# 9. SELECT A LAYER FOR EACH REVIEW ROW
# ============================================================
#
# Each suspicious pair is added to the layer corresponding to its
# review priority.
# ============================================================

def get_priority_layer(priority):

    if priority == "VERY HIGH":

        return very_high_layer


    if priority == "HIGH":

        return high_layer


    return review_layer


# ============================================================
# 10. BUILD POPUP HTML FOR OSM POINTS
# ============================================================
#
# This produces the information box that appears when an OSM
# marker is clicked.
# ============================================================

def make_osm_popup(row):

    return f"""
    <div style="width: 320px;">

        <h4 style="margin-bottom: 8px;">
            OpenStreetMap record
        </h4>

        <b>OSM ID:</b>
        {display_value(row["rival_store_id"])}
        <br>

        <b>Store name:</b>
        {display_value(row["osm_store_name"])}
        <br>

        <b>Brand:</b>
        {display_value(row["osm_brand"])}
        <br>

        <b>Operator:</b>
        {display_value(row["osm_operator"])}
        <br>

        <b>OSM shop type:</b>
        {display_value(row["osm_shop"])}
        <br>

        <b>Canonical fascia:</b>
        {display_value(row["osm_canonical_fascia_check"])}
        <br>

        <b>Postcode:</b>
        {display_value(row["osm_postcode"])}
        <br><br>

        <b>Review priority:</b>
        {display_value(row["review_priority"])}
        <br>

        <b>Distance to GEOLYTIX:</b>
        {row["distance_m"]:.2f} m
        <br>

        <b>Same postcode:</b>
        {display_value(row["same_postcode"])}
        <br>

        <b>Known rebrand pattern:</b>
        {display_value(row["known_rebrand_pattern"])}
        <br><br>

        <b>Coordinates:</b><br>
        {row["osm_latitude"]:.6f},
        {row["osm_longitude"]:.6f}

    </div>
    """


# ============================================================
# 11. BUILD POPUP HTML FOR GEOLYTIX POINTS
# ============================================================

def make_geo_popup(row):

    return f"""
    <div style="width: 320px;">

        <h4 style="margin-bottom: 8px;">
            GEOLYTIX record
        </h4>

        <b>GEOLYTIX ID:</b>
        {display_value(row["geo_id"])}
        <br>

        <b>Store name:</b>
        {display_value(row["geo_store_name"])}
        <br>

        <b>Fascia:</b>
        {display_value(row["geo_fascia"])}
        <br>

        <b>Retailer:</b>
        {display_value(row["geo_retailer"])}
        <br>

        <b>Canonical fascia:</b>
        {display_value(row["geo_canonical_fascia_check"])}
        <br>

        <b>Size band:</b>
        {display_value(row["geo_size_band"])}
        <br>

        <b>Postcode:</b>
        {display_value(row["geo_postcode"])}
        <br><br>

        <b>Removed as merger-party store:</b>
        {display_value(row["geo_removed_as_merger_party"])}
        <br>

        <b>Distance to OSM:</b>
        {row["distance_m"]:.2f} m
        <br><br>

        <b>Coordinates:</b><br>
        {row["geo_latitude"]:.6f},
        {row["geo_longitude"]:.6f}

    </div>
    """


# ============================================================
# 12. ADD EVERY SUSPICIOUS PAIR TO THE MAP
# ============================================================
#
# For each row we add:
#
#   1. an OSM marker
#   2. a GEOLYTIX marker
#   3. a line connecting the two
#
#
# Marker convention:
#
#   OSM       = circle marker
#   GEOLYTIX  = standard map pin
#
# This makes the two data sources visually distinguishable even
# when they occupy almost exactly the same location.
# ============================================================

for _, row in review.iterrows():

    layer = get_priority_layer(
        row[
            "review_priority"
        ]
    )


    osm_location = [

        row[
            "osm_latitude"
        ],

        row[
            "osm_longitude"
        ]
    ]


    geo_location = [

        row[
            "geo_latitude"
        ],

        row[
            "geo_longitude"
        ]
    ]


    # --------------------------------------------------------
    # OSM marker
    # --------------------------------------------------------

    folium.CircleMarker(

        location=osm_location,

        radius=7,

        weight=2,

        fill=True,

        fill_opacity=0.8,

        tooltip=(
            "OSM | "
            f"{display_value(row['osm_store_name'])} | "
            f"{display_value(row['osm_canonical_fascia_check'])}"
        ),

        popup=folium.Popup(
            make_osm_popup(row),
            max_width=400
        )

    ).add_to(
        layer
    )


    # --------------------------------------------------------
    # GEOLYTIX marker
    # --------------------------------------------------------

    folium.Marker(

        location=geo_location,

        tooltip=(
            "GEOLYTIX | "
            f"{display_value(row['geo_store_name'])} | "
            f"{display_value(row['geo_canonical_fascia_check'])}"
        ),

        popup=folium.Popup(
            make_geo_popup(row),
            max_width=400
        )

    ).add_to(
        layer
    )


    # --------------------------------------------------------
    # Line connecting the two records
    # --------------------------------------------------------
    #
    # This is particularly useful where two records are only one
    # or two metres apart.
    # --------------------------------------------------------

    folium.PolyLine(

        locations=[
            osm_location,
            geo_location
        ],

        weight=2,

        opacity=0.7,

        tooltip=(
            f"{row['distance_m']:.2f} metres"
        )

    ).add_to(
        layer
    )


    # --------------------------------------------------------
    # Additional merger-party highlight
    # --------------------------------------------------------
    #
    # If GEOLYTIX says the nearby record was removed from the
    # rival dataset because it belongs to one of the merging
    # parties, place an additional ring around it.
    #
    # These are particularly important because a stale OSM record
    # at that location could otherwise incorrectly be counted as
    # an independent rival.
    # --------------------------------------------------------

    if bool(
        row[
            "geo_removed_as_merger_party"
        ]
    ):

        folium.Circle(

            location=geo_location,

            radius=25,

            weight=3,

            fill=False,

            tooltip=(
                "GEOLYTIX record identified "
                "as merger-party store"
            )

        ).add_to(
            party_layer
        )


# ============================================================
# 13. ADD A LEGEND
# ============================================================
#
# Folium does not automatically create a legend for custom marker
# types, so we add a small HTML box explaining the map.
# ============================================================

legend_html = """
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    width: 250px;
    background-color: white;
    border: 2px solid grey;
    z-index: 9999;
    font-size: 13px;
    padding: 10px;
    border-radius: 5px;
">

    <b>Rebrand / stale-store review</b>

    <br><br>

    <span style="
        display:inline-block;
        width:12px;
        height:12px;
        border:2px solid black;
        border-radius:50%;
        margin-right:5px;
    "></span>

    OSM record

    <br>

    📍 GEOLYTIX record

    <br><br>

    Line = possible store match

    <br>

    Large ring = GEOLYTIX record previously
    identified as a merger-party store

    <br><br>

    Use the layer control in the top-right to
    toggle review priorities.

</div>
"""


review_map.get_root().html.add_child(
    folium.Element(
        legend_html
    )
)


# ============================================================
# 14. ADD LAYER CONTROL
# ============================================================
#
# This creates the checkbox menu in the top-right of the map.
#
# You can use it to display only:
#
#   VERY HIGH
#   HIGH
#   REVIEW
#   merger-party locations
# ============================================================

folium.LayerControl(
    collapsed=False
).add_to(
    review_map
)


# ============================================================
# 15. AUTOMATICALLY FIT THE MAP TO ALL REVIEW POINTS
# ============================================================
#
# Without this, the initial map might open too zoomed in or out.
# ============================================================

south = min(
    all_latitudes
)

north = max(
    all_latitudes
)

west = min(
    all_longitudes
)

east = max(
    all_longitudes
)


review_map.fit_bounds(

    [
        [
            south,
            west
        ],

        [
            north,
            east
        ]
    ]
)


# ============================================================
# 16. SAVE THE INTERACTIVE MAP
# ============================================================
#
# The output is a standalone HTML file.
#
# Double-click it in Windows Explorer and it should open in your
# normal web browser.
# ============================================================

review_map.save(
    OUTPUT_FILE
)


# ============================================================
# 17. FINAL SUMMARY
# ============================================================

print(
    "\n======================================"
)


print(
    "INTERACTIVE QA MAP CREATED"
)


print(
    "======================================"
)


print(
    "Rows mapped:",
    len(review)
)


print(
    "Unique OSM stores:",
    review[
        "rival_store_id"
    ].nunique()
)


print(
    "\nPriority counts:"
)


print(
    review[
        "review_priority"
    ]
    .value_counts()
)


print(
    "\nMap saved:"
)


print(
    OUTPUT_FILE
)


print(
    "\nOpen the HTML file in your browser."
)