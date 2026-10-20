# Co-op merger competition screen

An independent portfolio project applying the published CMA convenience-store screening framework to Co-operative Group / Southern Co-op. GEOLYTIX-primary records are supplemented with OpenStreetMap observations, matched to local catchments and scored using weighted rival fascias.

The repository has **one numbered analysis workflow** and a **separate presentation app**. It is not an official CMA assessment.

## Repository layout

```text
analysis/
  01_collect_party_stores.py
  02_clean_party_stores.py
  03_explore_party_stores.py
  04_find_one_mile_overlaps.py
  05_generate_drive_time_catchments.py
  06_find_drive_time_overlaps.py
  07_build_analysis_areas.py
  08_collect_rival_stores.py
  09_prepare_model_inputs.py
  10_resolve_rival_identities.py
  11_run_competition_screen.py
  12_build_interactive_map.py
  13_validate_and_export.py
  competition_screen/   # Implementations: preparation, identities, rules, map
  collection/           # Source-specific API clients and field normalisation
  config/               # Current model, source policy and evidence decisions
  tests/                # Regression fixtures and software checks
streamlit_app/
  app.py                # Displays exported results; performs no analysis
  assets/               # Verified map, tables and release manifest
  docs/                 # Methodology, source attribution and limitations
  report/               # Your economics report goes here
data/                   # Local raw, cached, intermediate and prepared inputs
```

## Run the analysis

Use Python 3.12 and a virtual environment. Install `python -m pip install -r analysis/requirements.txt`, then run `analysis/01_...` through `analysis/13_...` in order. **[The analysis README](analysis/README.md)** lists every command, its inputs/outputs and refresh options.

Default commands reproduce the supplied raw snapshots and reviewed routing without API calls. Step 09 rebuilds the prepared inputs; step 10 resolves source identities; step 11 applies the economic rule; step 12 draws the explorer; step 13 checks the reviewed reference results and exports locally to the app.

The local raw data and cache are needed for a complete analysis rerun and are ignored by Git. Public hosting needs only the app and its exported assets. Live source refresh is explicit and can legitimately change the study; incomplete Overpass collection is rejected.

## View the app

```powershell
python -m pip install -r streamlit_app/requirements.txt
python -m streamlit run streamlit_app/app.py
```

The existing local environment can use `.venv-screen/Scripts/python.exe` instead of `python`. Open the URL printed by Streamlit. For Community Cloud, select `streamlit_app/app.py` as the entry point. See **[the app README](streamlit_app/README.md)** for hosting and report instructions.

Add `streamlit_app/report/economics_report.md` and/or `economics_report.pdf` when your interpretation is ready. The app detects them automatically. No economics report has been represented as the author's finished work.

## Current reviewed results

- 2,651 estate stores displayed; 861 cached candidate centroids and 1,722 catchments.
- 6,164 source observations, 4,842 resolved entities and 1,752 preserved GEOLYTIX anchors.
- **15 model-flagged stores**, including **11** of the CMA's **19** published concern centroids; four additional model flags and eight published concerns not reproduced.
- Core/inclusive flagged-store sets currently agree, although scores can differ. These are sensitivity treatments, not statistical confidence bounds.

All reviewed catchment/store scores and flags are unchanged by the repository reorganisation. Step 13 validates exact numerical parity and source integrity before exporting. Tests: `python -m pytest analysis/tests -q`; map logic: `node analysis/tests/check_map.cjs`.

## Method and interpretation

The convenience rule requires an eligible centroid, cross-party overlap and at most three weighted rival fascias excluding the parties. GEOLYTIX supplies canonical attributes for linked records; OSM supplements coverage. Identity uncertainty is separate from competitive inclusion, and named-chain branches contribute one fascia weight per catchment.

Read **[the methodology](streamlit_app/docs/methodology.md)**, **[data provenance](streamlit_app/docs/data_sources.md)** and **[code review guide](streamlit_app/docs/code_review_guide.md)**. Source vintage/completeness, ownership, specialist scope, store-format proxies and routing remain material limitations. The separate supermarket assessment is not implemented. A flag is a model screen, and a non-flag does not establish that the merger is harmless.

Superseded numbered scripts, exploratory pipelines and duplicate outputs have been removed from the active tree. An ignored local recovery archive preserves the pre-cleanup research files. Credentials, local environments and generated intermediate datasets are excluded from Git. Nothing has been uploaded or deployed remotely.
