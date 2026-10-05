# Co-operative Group / Southern Co-op Local Competition Screen

> **Work in progress.** This is an independent portfolio project applying a CMA-inspired Phase 1 local competition screening approach to the Co-operative Group / Southern Co-operative transaction. It is not an official CMA assessment and does not attempt to reach a legal conclusion on the merger.

## Overview

The project asks where the two merger parties currently operate close enough to one another that they may exert a meaningful local competitive constraint on each other.

The current stage focuses on **merger-party geographic overlap**. It collects and cleans store-location data, maps the parties' footprints, and identifies local overlaps using two exploratory catchment measures:

- a **1-mile radial catchment**; and
- a **5-minute drive-time catchment** generated with OpenRouteService.

The longer-term aim is to extend this into a fuller local competition screen by adding independent rival stores / fascia counts and identifying areas where the merger could leave relatively weak remaining competitive constraints.

## Current status

| Stage | Status |
| --- | --- |
| Collect Southern Co-op and Co-operative Group store data | Complete |
| Clean and combine store records | Complete |
| Map national store footprints | Complete |
| 1-mile merger-party overlap screen | Complete |
| 8 km computational pre-screen for drive-time analysis | Complete |
| Generate 5-minute drive-time isochrones | Complete |
| Test 5-minute cross-party overlaps in both directions | Complete |
| Add independent competitors / fascia counts | Planned |
| Develop local competition flags and summary tables | Planned |
| Produce final methodology and findings report | Planned |

### Current dataset and outputs

The cleaned dataset currently contains **2,651 store records**:

- **250 Southern Co-op stores**
- **2,401 Co-operative Group stores**

For the 5-minute drive-time stage, the 8 km geographic pre-screen reduces the number of stores requiring isochrones to **861 candidate centroids**.

The committed 5-minute overlap outputs currently contain:

- **441 directional cross-party overlap pairs**
- **279 centroid stores** whose own 5-minute catchment contains at least one store belonging to the other merger party
  - 160 Co-operative Group centroids
  - 119 Southern Co-op centroids

These figures are screening outputs, not estimates of competitive harm.

## Methodology

### 1. Collect store-location data

`scr/01_collect_data.py` downloads store-location data from:

- the Southern Co-op store finder (Uberall API); and
- the Co-operative Group location-services API.

The raw responses are normalised into pandas DataFrames and saved as CSV files.

### 2. Clean and combine the data

`scr/02_clean_data.py` standardises key fields across both sources, including store IDs, names, addresses, postcodes, coordinates and party labels.

Reproducible project-level store IDs are created using:

- `SC-...` for Southern Co-op; and
- `CG-...` for Co-operative Group.

The two datasets are then combined into:

`data/cleaned/combined_stores_clean.csv`

### 3. Map the parties' geographic footprints

`scr/03_initial_exploratory_analysis.py` converts longitude / latitude coordinates from WGS84 (`EPSG:4326`) into British National Grid (`EPSG:27700`) and plots the national footprints of the two parties against the included UK boundary shapefile.

### 4. Run a 1-mile local overlap screen

`scr/04_merger_parties_1-mile_overlap.py` creates a 1-mile buffer around each Southern Co-op store and uses a GeoPandas spatial join to identify Co-operative Group stores lying inside those catchments.

This provides a simple first-pass measure of close geographic overlap and produces national and zoomed overlap maps.

The 1-mile assumption is exploratory and should not be interpreted as a formal market definition.

### 5. Pre-screen stores for drive-time analysis

Generating road-network isochrones for every store is unnecessary and API-intensive. `scr/05_merger_parties_5-min_isochrone.py` therefore first applies an **8 km straight-line pre-screen** to identify geographically plausible cross-party pairs.

The 8 km radius is only a computational filter. It is **not** treated as the competition catchment.

### 6. Generate 5-minute drive-time isochrones

Candidate stores are sent to the OpenRouteService isochrone API in batches. Each returned polygon represents the area reachable by car within **300 seconds (5 minutes)** from a store.

The script includes request throttling, retry handling and checks for failed / missing isochrones before saving the resulting geometries as GeoPackages.

### 7. Test cross-party drive-time overlaps in both directions

`scr/06_merger_parties_5-min_overlap.py` tests:

1. which Co-operative Group stores fall inside Southern Co-op 5-minute isochrones; and
2. which Southern Co-op stores fall inside Co-operative Group 5-minute isochrones.

Both directions are tested because road-network travel-time catchments are not necessarily symmetric.

The script then saves directional overlap pairs, overlap counts by centroid store and the flagged isochrone polygons.

## Repository structure

```text
Coop-merger-project-folder/
├── data/
│   ├── boundaries/
│   │   └── uk_countries_2025/
│   ├── raw/
│   │   ├── coop_group_raw.csv
│   │   └── southern_coop_raw.csv
│   ├── cleaned/
│   │   └── combined_stores_clean.csv
│   └── derived/
│       ├── party_5min_flagged_isochrones.gpkg
│       ├── party_5min_isochrone_candidates.csv
│       ├── party_5min_isochrones.gpkg
│       ├── party_5min_overlap_counts.csv
│       ├── party_5min_overlap_pairs.csv
│       └── potential_party_pairs_8km.gpkg
└── scr/
    ├── 01_collect_data.py
    ├── 02_clean_data.py
    ├── 03_initial_exploratory_analysis.py
    ├── 04_merger_parties_1-mile_overlap.py
    ├── 05_merger_parties_5-min_isochrone.py
    └── 06_merger_parties_5-min_overlap.py
```

## Tech stack

- Python
- pandas
- GeoPandas
- requests
- Matplotlib
- contextily
- OpenRouteService isochrone API
- CSV, Shapefile and GeoPackage geospatial data

There is not yet a pinned `requirements.txt` or environment file.

A basic environment for the current scripts can be installed with:

```bash
pip install pandas geopandas requests matplotlib contextily
```

## Running the current code

The project is still being refactored for full reproducibility. At present, the scripts use mixed relative-path assumptions.

`01_collect_data.py` and `02_clean_data.py` are written to run from the repository root, while scripts `03` to `06` reference `../data/...` and are written to run from inside `scr/`.

For the current structure:

```bash
# From the repository root
python scr/01_collect_data.py
python scr/02_clean_data.py

# Then run the geospatial analysis from the script directory
cd scr
python 03_initial_exploratory_analysis.py
python 04_merger_parties_1-mile_overlap.py
python 05_merger_parties_5-min_isochrone.py
python 06_merger_parties_5-min_overlap.py
```

### OpenRouteService API key

The 5-minute isochrone script requires an OpenRouteService API key. The current WIP script contains the placeholder:

```python
ORS_API_KEY = "Your_API_Key_Here"
```

Replace this locally before running the isochrone stage and **do not commit a real API key**. Moving this to an environment variable is planned as part of the reproducibility cleanup.

### Path note

`01_collect_data.py` currently uses a Windows-style `Data\Raw/...` output path, while the repository directory is `data/raw/`. This works with the current Windows-oriented workflow but should be standardised before the project is treated as cross-platform reproducible.

## Interpretation and limitations

This project is currently a **screening exercise**, not a complete merger assessment.

Important limitations include:

- Geographic proximity is only a proxy for competitive interaction.
- The 1-mile and 5-minute catchments are exploratory assumptions rather than formal product or geographic market definitions.
- The current analysis identifies overlap between the merger parties but does **not yet measure the number or strength of independent rival fascia** within each local area.
- Store size, format, sales, prices, capacity and customer switching behaviour are not yet modelled.
- Drive-time results depend on the road network and routing assumptions used by OpenRouteService.
- Store-locator API data is a snapshot and may contain closures, openings, franchises or records requiring further validation.
- The current scripts display maps interactively rather than saving a complete set of publication-ready figures.

For these reasons, a flagged overlap should be interpreted as an area for further investigation, not evidence by itself of a substantial lessening of competition.

## Next steps

The next stage is to move from **"where do the merging parties overlap?"** to **"where does that overlap occur with relatively few remaining independent competitive constraints?"**

Planned work includes:

- adding location data for major grocery competitors;
- defining fascia-based local competitor counts;
- comparing competitive conditions within 1-mile and 5-minute catchments;
- developing transparent local screening / flagging rules;
- reviewing store format and other relevant heterogeneity;
- saving reproducible maps and summary tables;
- standardising paths, configuration and dependencies; and
- writing up the economic reasoning, methodology, limitations and results.

## Disclaimer

This repository is an independent learning and portfolio project. It is not affiliated with the Competition and Markets Authority, Co-operative Group or Southern Co-operative, and the analysis should not be interpreted as an official view on the transaction.
