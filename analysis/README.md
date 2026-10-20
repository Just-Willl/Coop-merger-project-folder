# Numbered analysis workflow

Run these scripts in order from the repository root. Every path is resolved from the code's location, so the current working directory does not change which data are used. The numbered files are the entry points; reusable implementations live in `competition_screen/` and `collection/`.

| Step | Script | Reads | Writes |
|---:|---|---|---|
| 01 | `01_collect_party_stores.py` | Supplied locator snapshots, or public APIs with `--refresh` | `data/raw/party_stores/` |
| 02 | `02_clean_party_stores.py` | Raw parties and documented coordinate decisions | `data/intermediate/party_stores_clean.csv` |
| 03 | `03_explore_party_stores.py` | Cleaned estate | Counts and an estate plot; descriptive, not a competition test |
| 04 | `04_find_one_mile_overlaps.py` | Cleaned party coordinates | Cross-party one-mile pairs |
| 05 | `05_generate_drive_time_catchments.py` | Reviewed ORS cache and cleaned coordinates | Validated five-minute polygons |
| 06 | `06_find_drive_time_overlaps.py` | Party points and drive-time polygons | Directional cross-party overlaps |
| 07 | `07_build_analysis_areas.py` | All cached candidate centroids | Both catchments for each candidate and an explicit source-collection territory |
| 08 | `08_collect_rival_stores.py` | GEOLYTIX download and reviewed OSM cache, or fresh Overpass with `--refresh` | Raw rival sources and collection metadata |
| 09 | `09_prepare_model_inputs.py` | Earlier stages and retailer sources | Observations, party matches, size proxies and catchments in `data/prepared/` |
| 10 | `10_resolve_rival_identities.py` | Prepared observations and entity policy | GEOLYTIX-primary entities, source lineage and identity links |
| 11 | `11_run_competition_screen.py` | Resolved entities, formats and polygons | Catchment/store scores, rival contributions and CMA comparison |
| 12 | `12_build_interactive_map.py` | Model outputs and original spatial membership | Interactive map and score-reconciliation checks |
| 13 | `13_validate_and_export.py` | Current outputs and reviewed regression fixtures | Verified local release in `streamlit_app/assets/` |

## Reproduce the supplied study

Install Python 3.12 dependencies with `python -m pip install -r analysis/requirements.txt`, then:

```powershell
python analysis/01_collect_party_stores.py
python analysis/02_clean_party_stores.py
python analysis/03_explore_party_stores.py
python analysis/04_find_one_mile_overlaps.py
python analysis/05_generate_drive_time_catchments.py
python analysis/06_find_drive_time_overlaps.py
python analysis/07_build_analysis_areas.py
python analysis/08_collect_rival_stores.py
python analysis/09_prepare_model_inputs.py
python analysis/10_resolve_rival_identities.py
python analysis/11_run_competition_screen.py
python analysis/12_build_interactive_map.py
python analysis/13_validate_and_export.py
```

These default commands reproduce the supplied source snapshots and reviewed catchments without network collection. Step 03 only produces descriptive outputs. If the prepared inputs already exist, steps 10–13 are sufficient to rerun the current model. If scoring outputs already exist, steps 12–13 only rebuild and export the explorer.

Steps 04 and 06 describe overlap in the supplied locator estate. Step 11 recomputes the relevant overlap after applying the franchise-ownership scope. Step 07 retains every cached candidate centroid; it does not select locations using CMA outcomes or only retain previously flagged sites.

## Refresh data deliberately

Use `01 --refresh` for current party locators; `05 --refresh` for changed/missing routing; `07 --refresh-territory` for updated acquisition coverage; `08 --geolytix-file PATH --refresh` to supply GEOLYTIX and resume Overpass; and `09 --source-mode fresh` to use the completed fresh OSM file. Here `01`, etc., mean the full numbered filenames above.

Only ORS routing requires `ORS_API_KEY`, supplied as an environment variable or the ignored repository `.env`. The supplied cache needs no key. Credentials never enter exported results. Incomplete Overpass data cannot enter step 09. The reviewed study's source territory and OSM vintage are limitations, not a claim of complete current national coverage.

Refreshing data may legitimately change the study. Step 13 rejects different scores/flags against the reference fixtures. Review and document changes before intentionally replacing those fixtures; the code does not choose weights or records to reproduce CMA outcomes.

## Naming and implementation

- Entry points: two-digit order, verb, subject, e.g. `10_resolve_rival_identities.py`.
- Helpers: descriptive `snake_case`; no alternative numbered pipelines or duplicate versions.
- Paths: centralised in `competition_screen/paths.py`.
- Configuration: one `model_rules.json`, one `entity_resolution.json`, documented manual identity decisions and coordinate corrections.
- Outputs: stable `store_id`, `centroid_store_id`, `catchment_id` and source IDs. `flag_core`/`flag_inclusive` are model results; `listed_in_annex1` is the separate published outcome.

Read `preparation.py` for steps 01–09, `entity_resolution.py` for record linkage, `scoring.py` for weights/grouping, and `pipeline.py` for aggregation and the final benchmark join. The Streamlit app imports none of these modules.

## Checks

```powershell
python -m pytest analysis/tests -q
node analysis/tests/check_map.cjs
```

Regression tests verify every reviewed catchment/store score and flag, source-resolution behaviour and app loading. The JavaScript check executes the generated map logic, including rival-total reconciliation. Step 13 exports locally and does not deploy or upload anything.
