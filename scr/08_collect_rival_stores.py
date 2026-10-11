# ============================================================
# 08 - COLLECT, DEDUPLICATE AND CLEAN RIVAL STORE DATA
# ============================================================
#
# PURPOSE
# -------
# Build the rival-store dataset used in the local competition
# analysis.
#
# The script combines two public data sources:
#   1. GEOLYTIX Grocery Retail Points
#   2. OpenStreetMap (OSM), queried through Overpass
#
# The script then:
#   - restricts both sources to the geographic area relevant to
#     the merger analysis;
#   - standardises common fascia names for matching purposes;
#   - removes cross-source duplicates conservatively;
#   - applies a small number of manually reviewed decisions;
#   - removes stores belonging to the merger parties;
#   - saves the final independent-rival dataset;
#   - links each rival store to every competition catchment in
#     which it is located.
#
# IMPORTANT REPRODUCIBILITY NOTE
# ------------------------------
# Script 08A documents the manual review methodology and the
# reasoning behind the small number of judgement-based KEEP / DROP
# decisions applied here.
#
# This script applies those decisions automatically. Therefore the
# final dataset can be rebuilt from the raw inputs without manually
# editing a GeoPackage or CSV.
#
# IMPORTANT API NOTE
# ------------------
# OSM data have already been collected and saved to:
#     data/raw/osm_rival_candidates.gpkg
#
# REFRESH_OSM is therefore False by default. If that file exists,
# NO Overpass API requests are made.
# ============================================================

from pathlib import Path
from difflib import SequenceMatcher
import re
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import box


# %%
# ============================================================
# 1. PROJECT PATHS
# ============================================================
#
# __file__ is this Python script. The script is assumed to live in
# the project's `scr` directory, so parent.parent is the project
# root.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
DERIVED_DIR = DATA_DIR / "derived"

GEOLYTIX_FILE = (
    DATA_DIR
    / "GEOLYTIX data"
    / "GEOLYTIX Grocery Stores.csv"
)

CATCHMENTS_FILE = (
    DERIVED_DIR
    / "competitor_analysis_catchments.gpkg"
)

MERGER_STORES_FILE = (
    CLEANED_DIR
    / "combined_stores_clean.csv"
)

# Raw OSM cache.
#
# This is important because it contains the original OSM candidate
# stores BEFORE cross-source deduplication.
OSM_CACHE_FILE = (
    RAW_DIR
    / "osm_rival_candidates.gpkg"
)

# Final cleaned independent-rival dataset.
RIVAL_STORES_FILE = (
    CLEANED_DIR
    / "rival_stores_clean.gpkg"
)

# Long-form table linking rival stores to individual competition
# catchments.
CATCHMENT_MATCH_FILE = (
    DERIVED_DIR
    / "catchment_rival_matches.csv"
)

# Cleaning / QA outputs.
DUPLICATES_REMOVED_FILE = (
    DERIVED_DIR
    / "osm_geolytix_duplicates_removed.csv"
)

DUPLICATES_REVIEW_FILE = (
    DERIVED_DIR
    / "osm_geolytix_duplicates_review.csv"
)

MERGER_PARTY_REMOVED_FILE = (
    DERIVED_DIR
    / "merger_party_stores_removed.csv"
)


# %%
# ============================================================
# 2. SETTINGS
# ============================================================

# Leave False during normal use.
#
# If the OSM cache exists, setting this to False means NO Overpass
# API request will be made.
REFRESH_OSM = False


# ------------------------------------------------------------
# Settings only used if OSM has to be downloaded again
# ------------------------------------------------------------

INITIAL_GRID_SIZE_M = 20_000

MIN_GRID_SIZE_M = 5_000

REQUEST_DELAY_SECONDS = 1.5

OVERPASS_QUERY_TIMEOUT = 45

HTTP_REQUEST_TIMEOUT = 75


# ------------------------------------------------------------
# Duplicate matching distances
# ------------------------------------------------------------

# Search for possible GEOLYTIX / OSM matches within 100 metres.
DUPLICATE_REVIEW_DISTANCE_M = 100

# Most automatic rules are capped at 75 metres.
DUPLICATE_MAX_DISTANCE_M = 75


# %%
# ============================================================
# 3. MANUALLY REVIEWED DUPLICATE DECISIONS
# ============================================================
#
# Script 08A explains how these decisions were reached.
#
#
# REMOVE
# ------
#
# These OSM records were judged to represent the SAME physical
# store as an existing GEOLYTIX record.
#
# The OSM record is therefore removed and the GEOLYTIX record is
# retained.
#
# GEOLYTIX is preferred where a duplicate exists because it
# generally provides more structured information, including
# fascia and store size_band.
#
#
# KEEP
# ----
#
# These OSM records were manually reviewed and judged to represent
# genuine separate stores.
#
# They are explicitly protected from the automatic duplicate rule.
#
# This matters particularly in dense locations such as railway
# stations where multiple genuine stores belonging to the same
# fascia can operate only a few metres apart.
#
# See:
#     08A_manual_duplicate_review.py
# ============================================================


MANUAL_OSM_DUPLICATES_TO_REMOVE = {

    # --------------------------------------------------------
    # Morrisons
    # --------------------------------------------------------

    "OSM-node-10587211657",
    "OSM-node-10587211665",

    "OSM-way-1380072962",
    "OSM-way-240323961",


    # --------------------------------------------------------
    # Marks & Spencer
    # --------------------------------------------------------

    # London Bridge / Shard
    "OSM-node-14132060498",
    "OSM-node-5760381482",

    # Liverpool Street
    "OSM-way-377488601",

    # Liverpool Street West Mall
    "OSM-way-377595859",

    # King's Cross
    "OSM-way-416601711",


    # --------------------------------------------------------
    # Other fasciae
    # --------------------------------------------------------

    # Heron Foods, Bedminster
    "OSM-node-12923053147",

    # Tesco / Rowner Express
    "OSM-node-1938101529",

    # Sainsbury's, Pentonville Road
    "OSM-node-425442524",

    # Asda, Wolverton
    "OSM-node-4866277724",

    # Aldi, Chichester
    "OSM-node-4944511321",

    # Lidl, Shepherd's Bush
    "OSM-node-610453006",

    # Co-op, Newport Pagnell
    "OSM-way-223332358",

    # Sainsbury's, Bristol Hippodrome
    "OSM-way-291700163",

    # Budgens, Thanet
    "OSM-way-451971783",

    # Co-op, Upminster Road
    "OSM-way-855193700",

    # Little Waitrose / Shell Blendon
    "OSM-way-954251425",
}


MANUAL_OSM_CONFIRMED_KEEP = {

    # Different Sainsbury's store from nearby GEOLYTIX record
    "OSM-node-26659113",

    # Separate M&S outlet inside St Pancras
    "OSM-node-647011555",

    # Separate Co-op at Royal Albert Wharf
    "OSM-node-8176629229",

    # Morrisons Daily / PFS rather than main supermarket
    "OSM-way-1395332597",
}


# Safety check:
#
# No store should ever appear in both the KEEP and REMOVE lists.
if (
    MANUAL_OSM_DUPLICATES_TO_REMOVE
    &
    MANUAL_OSM_CONFIRMED_KEEP
):

    raise ValueError(
        "A manually reviewed OSM ID appears in both "
        "REMOVE and KEEP sets."
    )


# %%
# ============================================================
# 4. OVERPASS ENDPOINTS
# ============================================================
#
# These are only used if:
#
#   REFRESH_OSM = True
#
# OR
#
#   osm_rival_candidates.gpkg does not exist.
#
# Multiple endpoints are available because public Overpass
# services occasionally time out or reject large requests.
# ============================================================

OVERPASS_ENDPOINTS = [

    (
        "Britain & Ireland",
        "https://overpass.atownsend.org.uk/api/interpreter"
    ),

    (
        "Private.coffee",
        "https://overpass.private.coffee/api/interpreter"
    ),

    (
        "VK Maps",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
    ),

    (
        "FOSSGIS z",
        "https://z.overpass-api.de/api/interpreter"
    ),

    (
        "FOSSGIS lz4",
        "https://lz4.overpass-api.de/api/interpreter"
    ),
]


HEADERS = {

    "User-Agent":
        "CoopMergerCompetitionResearch/1.0"

}


# %%
# ============================================================
# 5. CREATE DIRECTORIES AND CHECK INPUT FILES
# ============================================================

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CLEANED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DERIVED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


required_files = [

    GEOLYTIX_FILE,

    CATCHMENTS_FILE,

    MERGER_STORES_FILE,

]


for file in required_files:

    if not file.exists():

        raise FileNotFoundError(
            f"Required input file not found:\n{file}"
        )


# %%
# ============================================================
# 6. HELPER FUNCTIONS FOR TEXT AND POSTCODES
# ============================================================
#
# Raw source fields are NOT overwritten.
#
# These functions create simplified versions used only for
# matching stores across datasets.
# ============================================================


def normalise_text(value):

    """
    Convert text into a simple lower-case alphanumeric form.

    Example:

        "Sainsbury's Local"
            ->
        "sainsbury s local"

    This allows minor punctuation / formatting differences between
    OSM and GEOLYTIX to be ignored.
    """

    if pd.isna(value):

        return ""


    value = str(value).lower()


    value = value.replace(
        "&",
        " and "
    )


    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )


    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()


    return value



def clean_postcode(value):

    """
    Standardise UK postcodes for exact comparison.

    Example:

        "SO31 7GE"
            ->
        "SO317GE"
    """

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


# %%
# ============================================================
# 7. CANONICAL FASCIA FUNCTION
# ============================================================
#
# Different sources often use different names for the same fascia.
#
# Examples:
#
#   Tesco Express
#   Tesco Express Esso
#       ->
#   Tesco
#
#
#   Sainsburys Local
#   Sainsbury's Local
#       ->
#   Sainsbury's
#
#
#   M&S Foodhall
#   Marks and Spencer Simply Food
#       ->
#   Marks & Spencer
#
#
# This field is useful for DUPLICATE MATCHING.
#
# It should NOT automatically be interpreted as the final economic
# ownership / fascia classification.
#
# In particular, "Co-op" requires further care because several
# independent regional co-operative societies may use similar
# branding while remaining separate competitors.
# ============================================================


def canonical_fascia(text):

    text = normalise_text(
        text
    )


    if not text:

        return ""


    # --------------------------------------------------------
    # Major grocery fasciae
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Co-op
    # --------------------------------------------------------

    if (
        "co op" in text
        or "coop" in text
        or "co operative" in text
        or "cooperative" in text
    ):

        return "Co-op"


    # --------------------------------------------------------
    # Discounters
    # --------------------------------------------------------

    if "aldi" in text:

        return "Aldi"


    if "lidl" in text:

        return "Lidl"


    # --------------------------------------------------------
    # Marks & Spencer
    # --------------------------------------------------------

    if (
        "marks and spencer" in text
        or "m and s" in text
        or "m s simply food" in text
        or "m s foodhall" in text
    ):

        return "Marks & Spencer"


    # --------------------------------------------------------
    # Iceland
    # --------------------------------------------------------

    if (
        "iceland" in text
        or "food warehouse" in text
    ):

        return "Iceland"


    # --------------------------------------------------------
    # Symbol / convenience fasciae
    # --------------------------------------------------------

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


# %%
# ============================================================
# 8. LOAD THE COMPETITION CATCHMENTS
# ============================================================
#
# Script 07 created the individual competition-analysis catchments.
#
# These catchments serve two purposes here:
#
#   1. They tell us where rival-store data need to be collected.
#
#   2. They are later used to determine which rivals are located
#      inside each individual competition screen.
#
#
# EPSG:27700 = British National Grid.
#
# We use it because coordinates and distances are measured in
# metres, which makes distance calculations straightforward.
# ============================================================


catchments = gpd.read_file(
    CATCHMENTS_FILE
)


if catchments.crs.to_epsg() != 27700:

    catchments = catchments.to_crs(
        "EPSG:27700"
    )


print(
    "Competition catchments:",
    len(catchments)
)


# Dissolve all individual catchments into one overall collection
# geometry.
#
# IMPORTANT:
#
# This is ONLY a data-collection boundary.
#
# It is NOT being treated as a single competition market.
collection_geometry = (
    catchments[
        ["geometry"]
    ]
    .dissolve()
    .geometry
    .iloc[0]
)


# %%
# ============================================================
# 9. LOAD AND PREPARE GEOLYTIX
# ============================================================
#
# GEOLYTIX provides useful structured grocery-retail information,
# particularly:
#
#   - fascia
#   - retailer
#   - store_name
#   - postcode
#   - size_band
#
# Because of this, when the same physical store is present in both
# OSM and GEOLYTIX, we generally prefer the GEOLYTIX record.
# ============================================================


geolytix = pd.read_csv(
    GEOLYTIX_FILE
)


print(
    "\nTotal GEOLYTIX records:",
    len(geolytix)
)


# Records without coordinates cannot be used spatially.
geolytix = (
    geolytix
    .dropna(
        subset=[
            "bng_e",
            "bng_n"
        ]
    )
    .copy()
)


geo = gpd.GeoDataFrame(

    geolytix,

    geometry=gpd.points_from_xy(
        geolytix[
            "bng_e"
        ],
        geolytix[
            "bng_n"
        ]
    ),

    crs="EPSG:27700"
)


# Restrict GEOLYTIX to stores located somewhere within the overall
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


# Create a source-specific unique ID.
geo[
    "rival_store_id"
] = (
    "GEO-"
    +
    geo[
        "id"
    ].astype(str)
)


geo[
    "source"
] = "GEOLYTIX"


geo[
    "source_id"
] = (
    geo[
        "id"
    ].astype(str)
)


print(
    "Relevant GEOLYTIX stores:",
    len(geo)
)


# Combine several GEOLYTIX fields to give the fascia classifier as
# much useful information as possible.
geo[
    "classification_text"
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
    "canonical_fascia"
] = (
    geo[
        "classification_text"
    ]
    .apply(
        canonical_fascia
    )
)


# Choose the best available original label for exact-name matching.
geo[
    "match_label"
] = (

    geo[
        "fascia"
    ]

    .fillna(
        geo[
            "retailer"
        ]
    )

    .fillna(
        geo[
            "store_name"
        ]
    )
)


geo[
    "match_label_normalised"
] = (
    geo[
        "match_label"
    ]
    .apply(
        normalise_text
    )
)


geo[
    "postcode_clean"
] = (
    geo[
        "postcode"
    ]
    .apply(
        clean_postcode
    )
)


# %%
# ============================================================
# 10. OSM DOWNLOAD HELPER FUNCTIONS
# ============================================================
#
# Under normal use these functions will NOT run because the raw OSM
# cache already exists.
#
# They remain in the script so the full data collection process is
# reproducible if the raw cache ever needs to be rebuilt.
# ============================================================


def build_grid():

    """
    Divide the overall collection area into manageable rectangular
    cells for Overpass queries.
    """

    minx, miny, maxx, maxy = (
        catchments.total_bounds
    )


    geometries = []

    ids = []

    grid_id = 1


    for x in np.arange(
        minx,
        maxx,
        INITIAL_GRID_SIZE_M
    ):

        for y in np.arange(
            miny,
            maxy,
            INITIAL_GRID_SIZE_M
        ):

            cell = box(
                x,
                y,
                x + INITIAL_GRID_SIZE_M,
                y + INITIAL_GRID_SIZE_M
            )


            if cell.intersects(
                collection_geometry
            ):

                geometries.append(
                    cell
                )

                ids.append(
                    grid_id
                )

                grid_id += 1


    return gpd.GeoDataFrame(

        {
            "grid_id":
                ids
        },

        geometry=geometries,

        crs="EPSG:27700"
    )



def build_overpass_query(
    geometry
):

    """
    Create an Overpass query for OSM objects tagged as:

        shop=supermarket
        shop=convenience
        shop=grocery
    """

    wgs = gpd.GeoSeries(
        [geometry],
        crs="EPSG:27700"
    ).to_crs(
        "EPSG:4326"
    )


    west, south, east, north = (
        wgs.total_bounds
    )


    return f"""
    [out:json][timeout:{OVERPASS_QUERY_TIMEOUT}];
    nwr
        ["shop"~"^(supermarket|convenience|grocery)$"]
        ({south},{west},{north},{east});
    out center tags;
    """



def send_overpass_query(
    query
):

    """
    Try several public Overpass endpoints until one successfully
    responds.
    """

    errors = []


    for (
        endpoint_name,
        endpoint_url
    ) in OVERPASS_ENDPOINTS:

        try:

            response = requests.post(

                endpoint_url,

                data={
                    "data":
                        query
                },

                headers=HEADERS,

                timeout=HTTP_REQUEST_TIMEOUT
            )


            response.raise_for_status()


            return response.json()


        except (
            requests.RequestException,
            ValueError
        ) as error:

            errors.append(
                (
                    endpoint_name,
                    str(error)
                )
            )


    raise RuntimeError(

        "All Overpass endpoints failed:\n"

        +

        "\n".join(

            f"{name}: {error}"

            for name, error
            in errors
        )
    )



def split_cell(
    geometry
):

    """
    Split a failed query cell into four smaller cells.

    This helps when an Overpass server struggles with a query that
    returns too much data.
    """

    minx, miny, maxx, maxy = (
        geometry.bounds
    )


    midx = (
        minx
        +
        maxx
    ) / 2


    midy = (
        miny
        +
        maxy
    ) / 2


    return [

        box(
            minx,
            miny,
            midx,
            midy
        ),

        box(
            midx,
            miny,
            maxx,
            midy
        ),

        box(
            minx,
            midy,
            midx,
            maxy
        ),

        box(
            midx,
            midy,
            maxx,
            maxy
        )

    ]



def query_cell(
    geometry
):

    """
    Query one OSM grid cell.

    If the query fails, recursively divide the cell into smaller
    areas and try again.
    """

    try:

        result = send_overpass_query(

            build_overpass_query(
                geometry
            )
        )


        time.sleep(
            REQUEST_DELAY_SECONDS
        )


        return result.get(
            "elements",
            []
        )


    except RuntimeError:

        minx, _, maxx, _ = (
            geometry.bounds
        )


        width = (
            maxx
            -
            minx
        )


        if width <= MIN_GRID_SIZE_M:

            raise


        print(
            f"  Query failed at "
            f"{width / 1000:.1f} km. "
            f"Splitting cell..."
        )


        elements = []


        for child in split_cell(
            geometry
        ):

            if child.intersects(
                collection_geometry
            ):

                elements.extend(

                    query_cell(
                        child
                    )
                )


        return elements



def osm_element_to_record(
    element
):

    """
    Convert one Overpass node, way or relation into a point-based
    rival-store record.
    """

    osm_type = element.get(
        "type"
    )


    osm_id = element.get(
        "id"
    )


    if osm_type == "node":

        latitude = element.get(
            "lat"
        )

        longitude = element.get(
            "lon"
        )


    else:

        centre = element.get(
            "center",
            {}
        )


        latitude = centre.get(
            "lat"
        )


        longitude = centre.get(
            "lon"
        )


    if (
        latitude is None
        or longitude is None
    ):

        return None


    tags = element.get(
        "tags",
        {}
    )


    return {

        "rival_store_id":
            f"OSM-{osm_type}-{osm_id}",

        "source":
            "OpenStreetMap",

        "source_id":
            f"{osm_type}-{osm_id}",

        "retailer":
            pd.NA,

        "fascia":
            tags.get(
                "brand"
            ),

        "store_name":
            tags.get(
                "name"
            ),

        "postcode":
            tags.get(
                "addr:postcode"
            ),

        "long_wgs":
            longitude,

        "lat_wgs":
            latitude,

        "size_band":
            pd.NA,

        "pqi":
            pd.NA,

        "open_date":
            pd.NA,

        "osm_type":
            osm_type,

        "osm_shop":
            tags.get(
                "shop"
            ),

        "osm_brand":
            tags.get(
                "brand"
            ),

        "osm_operator":
            tags.get(
                "operator"
            ),

        "website":
            (
                tags.get(
                    "website"
                )
                or
                tags.get(
                    "contact:website"
                )
            )
    }


# %%
# ============================================================
# 11. LOAD THE EXISTING OSM CACHE OR DOWNLOAD OSM
# ============================================================
#
# Normal behaviour:
#
#   OSM cache exists
#   REFRESH_OSM = False
#
# Therefore the existing 4,412 raw OSM candidates are loaded and
# NO internet request is made.
# ============================================================


if (
    OSM_CACHE_FILE.exists()
    and not REFRESH_OSM
):

    print(
        "\nLoading existing OSM cache."
    )


    print(
        "No Overpass requests will be made."
    )


    osm = gpd.read_file(
        OSM_CACHE_FILE
    )


    if osm.crs.to_epsg() != 27700:

        osm = osm.to_crs(
            "EPSG:27700"
        )


else:

    print(
        "\nNo usable OSM cache found, "
        "or REFRESH_OSM=True."
    )


    print(
        "Downloading OSM rival candidates..."
    )


    grid = build_grid()


    records = []


    for row_number, row in grid.iterrows():

        print(
            f"Grid cell "
            f"{row_number + 1}/{len(grid)}"
        )


        elements = query_cell(
            row.geometry
        )


        for element in elements:

            record = osm_element_to_record(
                element
            )


            if record is not None:

                records.append(
                    record
                )


    osm_df = (

        pd.DataFrame(
            records
        )

        .drop_duplicates(
            subset="rival_store_id"
        )
    )


    osm = gpd.GeoDataFrame(

        osm_df,

        geometry=gpd.points_from_xy(

            osm_df[
                "long_wgs"
            ],

            osm_df[
                "lat_wgs"
            ]
        ),

        crs="EPSG:4326"

    ).to_crs(
        "EPSG:27700"
    )


    # Restrict newly downloaded data to the actual project
    # collection area.
    osm = (

        osm[
            osm
            .geometry
            .intersects(
                collection_geometry
            )
        ]

        .copy()
    )


    # Save BEFORE cross-source deduplication.
    #
    # This gives us a reusable raw OSM cache.
    osm.to_file(

        OSM_CACHE_FILE,

        driver="GPKG"
    )


print(
    "Relevant OSM stores:",
    len(osm)
)


# %%
# ============================================================
# 12. PREPARE OSM MATCHING FIELDS
# ============================================================

osm[
    "classification_text"
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
    "canonical_fascia"
] = (

    osm[
        "classification_text"
    ]

    .apply(
        canonical_fascia
    )
)


osm[
    "match_label"
] = (

    osm[
        "osm_brand"
    ]

    .fillna(
        osm[
            "store_name"
        ]
    )

    .fillna(
        osm[
            "osm_operator"
        ]
    )
)


osm[
    "match_label_normalised"
] = (

    osm[
        "match_label"
    ]

    .apply(
        normalise_text
    )
)


osm[
    "postcode_clean"
] = (

    osm[
        "postcode"
    ]

    .apply(
        clean_postcode
    )
)


# %%
# ============================================================
# 13. BUILD CROSS-SOURCE MATCHING TABLES
# ============================================================
#
# We create smaller reference tables containing only the variables
# needed to compare GEOLYTIX and OSM.
#
# Easting and northing are stored separately before buffering the
# OSM geometries so we can later calculate the TRUE point-to-point
# distance.
# ============================================================


geo_reference = (

    geo[
        [
            "rival_store_id",
            "store_name",
            "fascia",
            "retailer",
            "postcode",
            "size_band",
            "canonical_fascia",
            "match_label",
            "match_label_normalised",
            "postcode_clean",
            "geometry"
        ]
    ]

    .rename(

        columns={

            "rival_store_id":
                "geo_id",

            "store_name":
                "geo_store_name",

            "fascia":
                "geo_fascia",

            "retailer":
                "geo_retailer",

            "postcode":
                "geo_postcode",

            "size_band":
                "geo_size_band",

            "canonical_fascia":
                "geo_canonical_fascia",

            "match_label":
                "geo_match_label",

            "match_label_normalised":
                "geo_match_label_normalised",

            "postcode_clean":
                "geo_postcode_clean"
        }
    )
)


geo_reference = (
    geo_reference.copy()
)


geo_reference[
    "geo_easting"
] = (
    geo_reference
    .geometry
    .x
)


geo_reference[
    "geo_northing"
] = (
    geo_reference
    .geometry
    .y
)


osm_reference = (

    osm[
        [
            "rival_store_id",
            "store_name",
            "postcode",
            "osm_brand",
            "osm_operator",
            "osm_shop",
            "canonical_fascia",
            "match_label",
            "match_label_normalised",
            "postcode_clean",
            "geometry"
        ]
    ]

    .rename(

        columns={

            "store_name":
                "osm_store_name",

            "postcode":
                "osm_postcode",

            "canonical_fascia":
                "osm_canonical_fascia",

            "match_label":
                "osm_match_label",

            "match_label_normalised":
                "osm_match_label_normalised",

            "postcode_clean":
                "osm_postcode_clean"
        }
    )
)


osm_reference[
    "osm_easting"
] = (
    osm_reference
    .geometry
    .x
)


osm_reference[
    "osm_northing"
] = (
    osm_reference
    .geometry
    .y
)


# %%
# ============================================================
# 14. FIND EVERY OSM / GEOLYTIX PAIR WITHIN 100 METRES
# ============================================================
#
# Each OSM point is temporarily given a 100m buffer.
#
# GEOLYTIX points inside that buffer are then found using a spatial
# join.
#
# This returns ALL nearby pairs, rather than simply the nearest
# GEOLYTIX store.
#
# That is important because dense locations may contain several
# genuine stores of the same fascia.
#
# Example:
#
#   London Bridge
#   St Pancras
#
# both contained multiple M&S stores very close together.
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
        DUPLICATE_REVIEW_DISTANCE_M
    )
)


pairs = gpd.sjoin(

    osm_search,

    geo_reference,

    how="inner",

    predicate="intersects"
)


# Calculate the TRUE distance between the original points.
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


# %%
# ============================================================
# 15. CREATE DUPLICATE-MATCHING SIGNALS
# ============================================================
#
# No single variable is reliable enough to identify duplicates.
#
# Instead we use several pieces of evidence:
#
#   - same normalised source label
#   - same canonical fascia
#   - same postcode
#   - similarity between names
#   - physical distance
# ============================================================


pairs[
    "same_raw_name"
] = (

    (
        pairs[
            "osm_match_label_normalised"
        ]
        != ""
    )

    &

    (
        pairs[
            "osm_match_label_normalised"
        ]
        ==
        pairs[
            "geo_match_label_normalised"
        ]
    )
)


pairs[
    "same_canonical_fascia"
] = (

    (
        pairs[
            "osm_canonical_fascia"
        ]
        != ""
    )

    &

    (
        pairs[
            "osm_canonical_fascia"
        ]
        ==
        pairs[
            "geo_canonical_fascia"
        ]
    )
)


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


# ------------------------------------------------------------
# Name similarity
# ------------------------------------------------------------

def name_similarity(row):

    """
    Return a score between 0 and 1 measuring how similar the two
    source labels are.
    """

    a = row[
        "osm_match_label_normalised"
    ]


    b = row[
        "geo_match_label_normalised"
    ]


    if (
        not a
        or not b
    ):

        return 0.0


    return round(

        SequenceMatcher(
            None,
            a,
            b
        ).ratio(),

        3
    )


pairs[
    "name_similarity"
] = (

    pairs
    .apply(
        name_similarity,
        axis=1
    )
)


# %%
# ============================================================
# 16. AUTOMATIC DUPLICATE RULE
# ============================================================
#
# A pair becomes an automatic duplicate candidate if ANY of the
# following conditions is true:
#
#
# RULE A
#
# Same normalised raw name
# AND
# <=75 metres apart
#
#
# RULE B
#
# Same canonical fascia
# AND
# <=30 metres apart
#
#
# RULE C
#
# Same canonical fascia
# AND
# same postcode
# AND
# <=75 metres apart
#
#
# These rules improve substantially on the original Script 08,
# which relied heavily on exact source-name matching.
#
# However, a candidate is NOT automatically removed if one OSM
# record has multiple plausible GEOLYTIX matches.
#
# Those cases are treated as ambiguous.
# ============================================================


same_raw_close = (

    (
        pairs[
            "distance_m"
        ]
        <= DUPLICATE_MAX_DISTANCE_M
    )

    &

    pairs[
        "same_raw_name"
    ]
)


same_fascia_very_close = (

    (
        pairs[
            "distance_m"
        ]
        <= 30
    )

    &

    pairs[
        "same_canonical_fascia"
    ]
)


same_fascia_postcode_close = (

    (
        pairs[
            "distance_m"
        ]
        <= DUPLICATE_MAX_DISTANCE_M
    )

    &

    pairs[
        "same_canonical_fascia"
    ]

    &

    pairs[
        "same_postcode"
    ]
)


pairs[
    "automatic_duplicate_candidate"
] = (

    same_raw_close

    |

    same_fascia_very_close

    |

    same_fascia_postcode_close
)


# ------------------------------------------------------------
# Less-certain cases
# ------------------------------------------------------------
#
# These are NOT automatically deleted.
#
# They are retained in the review CSV so there is an audit trail.
# ------------------------------------------------------------


pairs[
    "medium_duplicate_candidate"
] = (

    ~pairs[
        "automatic_duplicate_candidate"
    ]

    &

    pairs[
        "same_canonical_fascia"
    ]

    &

    (
        pairs[
            "distance_m"
        ]
        <= DUPLICATE_MAX_DISTANCE_M
    )
)


pairs[
    "other_review_candidate"
] = (

    ~pairs[
        "automatic_duplicate_candidate"
    ]

    &

    (

        (
            (
                pairs[
                    "distance_m"
                ]
                <= 30
            )

            &

            (
                pairs[
                    "name_similarity"
                ]
                >= 0.65
            )
        )

        |

        (
            pairs[
                "same_postcode"
            ]

            &

            (
                pairs[
                    "name_similarity"
                ]
                >= 0.55
            )
        )
    )
)


# %%
# ============================================================
# 17. IDENTIFY AMBIGUOUS AUTOMATIC MATCHES
# ============================================================
#
# Suppose one OSM point is close to TWO GEOLYTIX M&S stores.
#
# Even if both satisfy an automatic rule, deleting the OSM point
# without further investigation could be unsafe.
#
# Therefore:
#
#   one plausible GEOLYTIX match
#       -> may be automatically removed
#
#   more than one plausible GEOLYTIX match
#       -> ambiguous, retain for review
#
# This is exactly the type of issue found around railway stations.
# ============================================================


candidate_counts = (

    pairs.loc[
        pairs[
            "automatic_duplicate_candidate"
        ]
    ]

    .groupby(
        "rival_store_id"
    )

    [
        "geo_id"
    ]

    .nunique()
)


pairs[
    "automatic_match_count"
] = (

    pairs[
        "rival_store_id"
    ]

    .map(
        candidate_counts
    )

    .fillna(0)

    .astype(int)
)


pairs[
    "ambiguous_automatic_match"
] = (

    pairs[
        "automatic_match_count"
    ]
    > 1
)


# Start with automatic matches which are NOT ambiguous.
automatic_matches = (

    pairs[

        pairs[
            "automatic_duplicate_candidate"
        ]

        &

        ~pairs[
            "ambiguous_automatic_match"
        ]
    ]

    .copy()
)


# ------------------------------------------------------------
# MANUAL KEEP OVERRIDE
# ------------------------------------------------------------
#
# If we have already manually established that an OSM record is a
# genuine separate store, the automatic rule must not subsequently
# delete it.
# ------------------------------------------------------------

automatic_matches = (

    automatic_matches[

        ~automatic_matches[
            "rival_store_id"
        ]

        .isin(
            MANUAL_OSM_CONFIRMED_KEEP
        )
    ]

    .copy()
)


# If several rows somehow remain for one OSM record, retain the
# closest pair in the audit output.
automatic_matches = (

    automatic_matches

    .sort_values(
        "distance_m"
    )

    .drop_duplicates(
        subset="rival_store_id"
    )
)


osm_automatic_duplicate_ids = set(

    automatic_matches[
        "rival_store_id"
    ]
)


print(
    "\n======================================"
)

print(
    "GEOLYTIX / OSM AUTOMATIC DEDUPLICATION"
)

print(
    "======================================"
)


print(
    "Automatic OSM duplicates identified:",
    len(
        osm_automatic_duplicate_ids
    )
)


print(

    "Ambiguous OSM stores not automatically removed:",

    pairs.loc[
        pairs[
            "ambiguous_automatic_match"
        ],
        "rival_store_id"
    ]
    .nunique()
)


print(

    "Manually confirmed KEEP records protected "
    "from automatic removal:",

    len(

        set(
            osm[
                "rival_store_id"
            ]
        )

        &

        MANUAL_OSM_CONFIRMED_KEEP
    )
)


# %%
# ============================================================
# 18. SAVE AUTOMATIC DUPLICATE AUDIT TABLE
# ============================================================
#
# This file records which OSM stores were automatically considered
# duplicates and which GEOLYTIX record they matched.
#
# It makes the automatic cleaning process inspectable.
# ============================================================


duplicate_audit_columns = [

    "rival_store_id",

    "geo_id",

    "distance_m",

    "osm_store_name",

    "osm_brand",

    "osm_operator",

    "osm_shop",

    "osm_postcode",

    "osm_canonical_fascia",

    "geo_store_name",

    "geo_fascia",

    "geo_retailer",

    "geo_size_band",

    "geo_postcode",

    "geo_canonical_fascia",

    "same_raw_name",

    "same_canonical_fascia",

    "same_postcode",

    "name_similarity"
]


automatic_matches[
    duplicate_audit_columns
].to_csv(

    DUPLICATES_REMOVED_FILE,

    index=False
)


# %%
# ============================================================
# 19. SAVE UNCERTAIN PAIRS FOR QA / AUDIT
# ============================================================
#
# This file contains the cases which the automatic system regarded
# as sufficiently uncertain to warrant review.
#
# It is a diagnostic output.
#
# It is NOT directly used to build the final dataset.
#
# The manual conclusions reached from reviewing these cases are
# documented in Script 08A and encoded in Section 3 above.
# ============================================================


review_pairs = (

    pairs[

        pairs[
            "ambiguous_automatic_match"
        ]

        |

        pairs[
            "medium_duplicate_candidate"
        ]

        |

        pairs[
            "other_review_candidate"
        ]
    ]

    .copy()
)


review_pairs = (

    review_pairs

    .sort_values(

        [
            "ambiguous_automatic_match",
            "distance_m",
            "name_similarity"
        ],

        ascending=[
            False,
            True,
            False
        ]
    )
)


review_columns = [

    "rival_store_id",

    "geo_id",

    "distance_m",

    "osm_store_name",

    "osm_brand",

    "osm_operator",

    "osm_shop",

    "osm_postcode",

    "osm_canonical_fascia",

    "geo_store_name",

    "geo_fascia",

    "geo_retailer",

    "geo_size_band",

    "geo_postcode",

    "geo_canonical_fascia",

    "same_raw_name",

    "same_canonical_fascia",

    "same_postcode",

    "name_similarity",

    "automatic_duplicate_candidate",

    "automatic_match_count",

    "ambiguous_automatic_match",

    "medium_duplicate_candidate",

    "other_review_candidate"
]


review_pairs[
    review_columns
].to_csv(

    DUPLICATES_REVIEW_FILE,

    index=False
)


# %%
# ============================================================
# 20. REMOVE AUTOMATIC CROSS-SOURCE DUPLICATES
# ============================================================
#
# When an OSM store and GEOLYTIX store represent the same physical
# location, GEOLYTIX is retained and OSM is removed.
#
# This avoids double-counting the same competitor.
# ============================================================


osm_unique = (

    osm[

        ~osm[
            "rival_store_id"
        ]

        .isin(
            osm_automatic_duplicate_ids
        )
    ]

    .copy()
)


print(
    "\nOSM records before automatic deduplication:",
    len(osm)
)


print(
    "OSM records after automatic deduplication:",
    len(osm_unique)
)


# %%
# ============================================================
# 21. APPLY MANUALLY REVIEWED DUPLICATE DECISIONS
# ============================================================
#
# The automatic rules deliberately err on the side of caution.
#
# The remaining uncertain cases were reviewed manually using:
#
#   - distance
#   - fascia
#   - store name
#   - postcode
#   - retailer/store information
#   - map inspection where necessary
#
# Full methodology and case-by-case reasoning:
#
#     08A_manual_duplicate_review.py
#
#
# IMPORTANT
# ---------
#
# We do NOT manually edit rival_stores_clean.gpkg.
#
# Instead, the confirmed duplicate IDs are encoded here so the
# same decisions are reproduced automatically every time this
# script runs.
# ============================================================


manual_remove_present = (

    set(
        osm_unique[
            "rival_store_id"
        ]
    )

    &

    MANUAL_OSM_DUPLICATES_TO_REMOVE
)


manual_remove_not_present = (

    MANUAL_OSM_DUPLICATES_TO_REMOVE

    -

    set(
        osm_unique[
            "rival_store_id"
        ]
    )
)


print(

    "\nManually reviewed OSM duplicates "
    "available to remove:",

    len(
        manual_remove_present
    )
)


# If this is non-zero in future, it may simply mean a revised
# automatic rule has already removed one of the same stores.
if manual_remove_not_present:

    print(

        "Manual REMOVE IDs not present after "
        "automatic deduplication:",

        len(
            manual_remove_not_present
        )
    )


# Apply all manually confirmed REMOVE decisions.
osm_unique = (

    osm_unique[

        ~osm_unique[
            "rival_store_id"
        ]

        .isin(
            MANUAL_OSM_DUPLICATES_TO_REMOVE
        )
    ]

    .copy()
)


print(

    "OSM records retained after manual duplicate review:",

    len(
        osm_unique
    )
)


# Confirm our manually reviewed KEEP records have survived.
manual_keep_surviving = (

    set(
        osm_unique[
            "rival_store_id"
        ]
    )

    &

    MANUAL_OSM_CONFIRMED_KEEP
)


print(

    "Manually reviewed KEEP records still present:",

    f"{len(manual_keep_surviving)}"
    f"/{len(MANUAL_OSM_CONFIRMED_KEEP)}"
)


# %%
# ============================================================
# 22. STANDARDISE THE TWO SOURCES TO A COMMON SCHEMA
# ============================================================
#
# GEOLYTIX and OSM contain different columns.
#
# Before combining them, we select a common set of variables.
#
# Source-specific fields are retained where they may later be
# useful for classification or QA.
# ============================================================


# GEOLYTIX does not naturally contain these OSM fields.
#
# Add blank versions so both datasets can be concatenated using
# the same schema.
for column in [

    "osm_type",

    "osm_shop",

    "osm_brand",

    "osm_operator",

    "website"

]:

    if column not in geo.columns:

        geo[
            column
        ] = pd.NA


standard_columns = [

    "rival_store_id",

    "source",

    "source_id",

    "retailer",

    "fascia",

    "store_name",

    "postcode",

    "long_wgs",

    "lat_wgs",

    "size_band",

    "pqi",

    "open_date",

    "osm_type",

    "osm_shop",

    "osm_brand",

    "osm_operator",

    "website",

    "canonical_fascia",

    "geometry"
]


geo_clean = (

    geo[
        standard_columns
    ]

    .copy()
)


osm_clean = (

    osm_unique[
        standard_columns
    ]

    .copy()
)


# Combine the two cleaned sources.
rival_candidates = gpd.GeoDataFrame(

    pd.concat(

        [
            geo_clean,
            osm_clean
        ],

        ignore_index=True
    ),

    geometry="geometry",

    crs="EPSG:27700"
)


print(

    "\nCombined candidate stores after "
    "cross-source deduplication:",

    len(
        rival_candidates
    )
)


# %%
# ============================================================
# 23. LOAD THE MERGER-PARTY STORES
# ============================================================
#
# The rival-store dataset must exclude:
#
#   - Co-operative Group stores
#   - Southern Co-operative stores
#
# because these are the merging parties rather than independent
# competitive constraints.
# ============================================================


party_stores = pd.read_csv(
    MERGER_STORES_FILE
)


party = gpd.GeoDataFrame(

    party_stores,

    geometry=gpd.points_from_xy(

        party_stores[
            "longitude"
        ],

        party_stores[
            "latitude"
        ]
    ),

    crs="EPSG:4326"

).to_crs(
    "EPSG:27700"
)


if "postcode" not in party.columns:

    party[
        "postcode"
    ] = ""


party[
    "party_postcode_clean"
] = (

    party[
        "postcode"
    ]

    .apply(
        clean_postcode
    )
)


party[
    "party_name_normalised"
] = (

    party[
        "store_name"
    ]

    .apply(
        normalise_text
    )
)


party[
    "party_easting"
] = (
    party
    .geometry
    .x
)


party[
    "party_northing"
] = (
    party
    .geometry
    .y
)


# %%
# ============================================================
# 24. PREPARE RIVAL CANDIDATES FOR PARTY-STORE MATCHING
# ============================================================


candidate_party_check = (
    rival_candidates.copy()
)


candidate_party_check[
    "candidate_name_normalised"
] = (

    candidate_party_check[
        "store_name"
    ]

    .fillna(
        candidate_party_check[
            "fascia"
        ]
    )

    .fillna(
        candidate_party_check[
            "osm_brand"
        ]
    )

    .apply(
        normalise_text
    )
)


candidate_party_check[
    "candidate_postcode_clean"
] = (

    candidate_party_check[
        "postcode"
    ]

    .apply(
        clean_postcode
    )
)


candidate_party_check[
    "candidate_easting"
] = (
    candidate_party_check
    .geometry
    .x
)


candidate_party_check[
    "candidate_northing"
] = (
    candidate_party_check
    .geometry
    .y
)


# Create a 75m search radius around each candidate rival record.
candidate_search = (
    candidate_party_check.copy()
)


candidate_search[
    "geometry"
] = (

    candidate_search
    .geometry
    .buffer(
        75
    )
)


party_reference = (

    party[
        [
            "store_id",
            "party",
            "store_name",
            "party_postcode_clean",
            "party_name_normalised",
            "party_easting",
            "party_northing",
            "geometry"
        ]
    ]

    .rename(

        columns={

            "store_id":
                "party_store_id",

            "store_name":
                "party_store_name"
        }
    )
)


party_pairs = gpd.sjoin(

    candidate_search,

    party_reference,

    how="inner",

    predicate="intersects"
)


party_pairs[
    "distance_m"
] = np.hypot(

    party_pairs[
        "candidate_easting"
    ]
    -
    party_pairs[
        "party_easting"
    ],

    party_pairs[
        "candidate_northing"
    ]
    -
    party_pairs[
        "party_northing"
    ]
)


party_pairs[
    "same_postcode"
] = (

    (
        party_pairs[
            "candidate_postcode_clean"
        ]
        != ""
    )

    &

    (
        party_pairs[
            "party_postcode_clean"
        ]
        != ""
    )

    &

    (
        party_pairs[
            "candidate_postcode_clean"
        ]
        ==
        party_pairs[
            "party_postcode_clean"
        ]
    )
)


party_pairs[
    "same_name"
] = (

    (
        party_pairs[
            "candidate_name_normalised"
        ]
        != ""
    )

    &

    (
        party_pairs[
            "candidate_name_normalised"
        ]
        ==
        party_pairs[
            "party_name_normalised"
        ]
    )
)


# %%
# ============================================================
# 25. IDENTIFY AND REMOVE MERGER-PARTY STORES
# ============================================================
#
# A candidate is treated as one of the merger-party stores if:
#
#
# RULE A
#
# It is classified as Co-op
# AND
# <=30m from a known merger-party store.
#
#
# RULE B
#
# It is classified as Co-op
# AND
# has the same postcode as a party store
# AND
# <=75m away.
#
#
# RULE C
#
# It has the same normalised store name as a party store
# AND
# <=75m away.
#
#
# This deliberately does NOT remove every store with "Co-op" in
# its branding.
#
# Other regional co-operative societies may be genuine independent
# competitors and should not automatically be attributed to the
# merging parties.
# ============================================================


party_pairs[
    "is_merger_party_store"
] = (

    (

        (
            party_pairs[
                "canonical_fascia"
            ]
            ==
            "Co-op"
        )

        &

        (

            (
                party_pairs[
                    "distance_m"
                ]
                <= 30
            )

            |

            (

                party_pairs[
                    "same_postcode"
                ]

                &

                (
                    party_pairs[
                        "distance_m"
                    ]
                    <= 75
                )
            )
        )
    )

    |

    (

        party_pairs[
            "same_name"
        ]

        &

        (
            party_pairs[
                "distance_m"
            ]
            <= 75
        )
    )
)


party_removed_ids = set(

    party_pairs.loc[

        party_pairs[
            "is_merger_party_store"
        ],

        "rival_store_id"
    ]
)


print(

    "\nCandidate stores identified as merger-party stores:",

    len(
        party_removed_ids
    )
)


# Save a record of exactly which candidate rival stores were
# classified as merger-party locations.
party_pairs.loc[

    party_pairs[
        "is_merger_party_store"
    ],

    [
        "rival_store_id",

        "source",

        "store_name",

        "fascia",

        "osm_brand",

        "canonical_fascia",

        "postcode",

        "party_store_id",

        "party",

        "party_store_name",

        "distance_m",

        "same_postcode",

        "same_name"
    ]

].to_csv(

    MERGER_PARTY_REMOVED_FILE,

    index=False
)


# %%
# ============================================================
# 26. BUILD THE FINAL INDEPENDENT-RIVAL DATASET
# ============================================================
#
# Remove merger-party stores from the cleaned cross-source dataset.
#
# What remains should represent independent rival grocery stores
# relevant to at least one competition-analysis area.
# ============================================================


rival_stores = (

    rival_candidates[

        ~rival_candidates[
            "rival_store_id"
        ]

        .isin(
            party_removed_ids
        )
    ]

    .copy()
)


# Each source-specific ID should occur only once in the final
# point dataset.
rival_stores = (

    rival_stores

    .drop_duplicates(
        subset="rival_store_id"
    )

    .reset_index(
        drop=True
    )
)


rival_stores.to_file(

    RIVAL_STORES_FILE,

    driver="GPKG"
)


print(
    "Final independent rival stores:",
    len(rival_stores)
)


# %%
# ============================================================
# 27. LINK RIVAL STORES TO INDIVIDUAL COMPETITION CATCHMENTS
# ============================================================
#
# A single rival store may fall inside several competition
# catchments.
#
# Therefore this produces a LONG-FORM many-to-many table.
#
# Each row means:
#
#     this rival store is located inside this individual
#     competition catchment.
#
# This will become the input for later:
#
#   - fascia counting
#   - store-format classification
#   - CMA-style weighting
#   - local competition screening
# ============================================================


catchment_reference = (

    catchments[
        [
            "catchment_id",
            "centroid_store_id",
            "centroid_party",
            "catchment_type",
            "geometry"
        ]
    ]

    .copy()
)


catchment_matches = gpd.sjoin(

    rival_stores,

    catchment_reference,

    how="inner",

    predicate="intersects"
)


catchment_rival_matches = (

    catchment_matches[
        [
            "catchment_id",

            "centroid_store_id",

            "centroid_party",

            "catchment_type",

            "rival_store_id",

            "source",

            "retailer",

            "fascia",

            "store_name",

            "postcode",

            "canonical_fascia",

            "size_band",

            "osm_shop",

            "osm_brand",

            "osm_operator"
        ]
    ]

    .drop_duplicates()

    .sort_values(
        [
            "catchment_id",
            "rival_store_id"
        ]
    )

    .reset_index(
        drop=True
    )
)


catchment_rival_matches.to_csv(

    CATCHMENT_MATCH_FILE,

    index=False
)


# %%
# ============================================================
# 28. FINAL QA SUMMARY
# ============================================================
#
# These counts provide an easy way to spot unexpected changes if
# the cleaning methodology is modified later.
# ============================================================


print(
    "\n======================================"
)

print(
    "RIVAL STORE CLEANING COMPLETE"
)

print(
    "======================================"
)


print(

    "GEOLYTIX stores in collection area:",

    len(
        geo
    )
)


print(

    "OSM stores in collection area:",

    len(
        osm
    )
)


print(

    "Automatic OSM duplicates removed:",

    len(
        osm_automatic_duplicate_ids
    )
)


print(

    "Manual OSM duplicates removed:",

    len(
        manual_remove_present
    )
)


print(

    "OSM stores retained after all "
    "cross-source deduplication:",

    len(
        osm_unique
    )
)


print(
    "Automatic-screen ambiguous cases documented in 08A:",
    pairs.loc[
        pairs["ambiguous_automatic_match"],
        "rival_store_id"
    ].nunique()
)

print(
    "Automatic-screen review cases documented in 08A:",
    review_pairs["rival_store_id"].nunique()
)

print(

    "Merger-party stores removed:",

    len(
        party_removed_ids
    )
)


print(

    "Final independent rival stores:",

    len(
        rival_stores
    )
)


print(

    "Catchment / rival relationships:",

    len(
        catchment_rival_matches
    )
)


print(

    "Catchments containing at least one rival:",

    catchment_rival_matches[
        "catchment_id"
    ].nunique()
)


print(

    "Total competition catchments:",

    len(
        catchments
    )
)


print(
    "\nSaved:"
)


print(
    OSM_CACHE_FILE
)


print(
    DUPLICATES_REMOVED_FILE
)


print(
    DUPLICATES_REVIEW_FILE
)


print(
    MERGER_PARTY_REMOVED_FILE
)


print(
    RIVAL_STORES_FILE
)


print(
    CATCHMENT_MATCH_FILE
)