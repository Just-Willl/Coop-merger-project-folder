# Streamlit presentation app

This folder displays results exported by analysis step **13**. It does not collect data, resolve identities, assign weights or rerun the model for visitors.

## Run locally

From the repository root:

```powershell
python -m pip install -r streamlit_app/requirements.txt
python -m streamlit run streamlit_app/app.py
```

Use Python 3.12. The app reads its own `assets/` and documentation using file-relative paths; no API key or analysis input is required. Leaflet and basemap tiles require internet access.

## Contents

- `app.py`: four tabs for the map, methodology, results and the author's report.
- `assets/`: verified HTML, CSV results and release manifest produced by `analysis/13_validate_and_export.py`.
- `docs/`: public methodology, source attribution and limitations.
- `report/`: add `economics_report.md` and/or `economics_report.pdf`; the app detects them automatically.
- `requirements.txt` and `.streamlit/config.toml`: hosting dependencies/settings.

The standalone map is `assets/competition_map.html`. Methodology is in `docs/methodology.md`. All economic analysis code is separately organised under `../analysis/`.

## Hosting

Use `streamlit_app/app.py` as the entry point when deploying this repository to Streamlit Community Cloud. Alternatively copy this folder's contents to a separate app repository and use `app.py`. Python 3.12 and this folder's requirements are sufficient. Keep source attribution and applicable data-provider terms with the derived map. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).

No deployment or repository upload is performed by the analysis/export scripts.
