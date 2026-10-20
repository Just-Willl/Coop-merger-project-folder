# Release validation

The numbered workflow was run from supplied raw party/rival snapshots and reviewed routing/source-territory caches, including rebuilding stage 09's prepared inputs, and compared with the reviewed current-model outputs. No model result was intentionally changed during reorganisation.

| Check | Result |
|---|---|
| Every core/inclusive catchment score and flag | Exact reference parity across 1,722 catchments |
| Every core/inclusive store score and flag | Exact reference parity across 861 assessed candidates |
| Map rival-group sums | 804 scored catchment/evidence rows reconciled |
| Generated map behaviour | Node checks pass for filters, source resolution, scores, overlap, selection and empty states |
| Current Python tests | Sixteen tests cover reference outputs, source-resolution invariants and Streamlit AppTest loading all four tabs |
| Runtime independence | No imports from the parent research scripts |
| Asset integrity | SHA-256 hashes recorded in `assets/release_manifest.json` |

The rebuild retains 6,164 observations, 4,842 resolved entities, 2,651 displayed estate stores and 15 flagged stores. Eleven flags overlap with the 19 CMA published concern centroids; four are additional model flags.

The Streamlit smoke test checks application execution and element construction. The Node test executes the map logic using DOM/Leaflet doubles. Neither substitutes for checking external tile availability in the eventual hosting environment. Passing these checks establishes software/refactor consistency; it does not validate the economic assumptions against confidential CMA evidence.

From the repository root, run `python -m pytest analysis/tests -q` and `node analysis/tests/check_map.cjs` after changes. The numbered workflow is documented in `analysis/README.md`; step 13 validates and exports the release locally.
