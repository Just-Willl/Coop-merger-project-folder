# Data layout

| Directory | Purpose |
|---|---|
| `raw/party_stores/` | Original locator snapshots from step 01 |
| `raw/rival_stores/` | GEOLYTIX, reviewed historical OSM, collection checkpoints and provenance |
| `cache/` | Reviewed five-minute polygons, source-collection footprint and estate reference |
| `intermediate/` | Cleaned estate, overlap tables and candidate geometry from steps 02–08 |
| `prepared/` | Step 09's explicit model inputs and hashes |
| `reference/` | Official CMA source documents retained for the study |

Source and generated datasets are ignored in Git by default. The public release is `streamlit_app/assets/`; regression fixtures are `analysis/tests/fixtures/`. Preserve provider attribution and redistribution terms for derived outputs as well as raw data.

Raw/prepared local snapshots and the reviewed routing cache are needed to reproduce the complete study. They are not needed to run the Streamlit app. Current GEOLYTIX vintage is recorded as an October 2026 download reported by the author; reviewed OSM age/completeness remains unspecified.
