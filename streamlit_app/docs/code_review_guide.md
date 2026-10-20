# Code review guide

Start with `competition_screen/pipeline.py`, whose module docstring describes the six analysis stages. Then read `scoring.py` to see exactly how a rival becomes a weight, a group and a flag. `entity_resolution.py` operates earlier and has no access to CMA benchmark outcomes.

## Key invariants

- A source observation belongs to exactly one entity; no raw source IDs are silently dropped.
- Every GEOLYTIX anchor retains its canonical attributes and geometry.
- No automatic link merges two GEOLYTIX anchors or reaches a distant anchor via OSM chains.
- Duplicate identity uncertainty is separate from competitor inclusion.
- Recognised fascia weights are counted once per catchment; independents are separate premises.
- No overlap produces no competition score, rather than a fabricated zero.
- Ineligible centroids do not receive convenience flags.
- Store flags combine methods; counts do not confuse catchments with stores.
- Benchmark labels enter only after every score has been computed.
- Refactoring must preserve every reviewed catchment/store score and flag before assets are promoted.

## Intentional boundaries

The repository has one ordered `analysis/01_...` through `analysis/13_...` workflow. Those scripts call named implementation functions in `analysis/competition_screen/` and `analysis/collection/`. Paths are centralised in `analysis/competition_screen/paths.py`.

`streamlit_app/app.py` reads immutable `streamlit_app/assets/`; it neither collects data nor reruns the model for visitors. `data/raw/` holds source observations, `data/intermediate/` contains stages 02–08, `data/prepared/` contains stage 09's input contract, and `analysis/outputs/` contains stages 10–12. Step 13 validates and exports locally to the app. It does not upload anything. No migration helpers or old numbered scripts are runtime dependencies.

Changing weights, scope, source priorities or entity rules is a methodological change. Review changed outputs and explain the change before replacing the reference fixtures. Passing a fixture is a refactor check, not proof that the economic model matches the CMA.

The Streamlit explorer embeds only the project's generated HTML in an isolated iframe. Store names and other source-derived content are escaped in the template. There is no arbitrary HTML upload or external message-sending feature.
