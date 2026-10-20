# Data sources and provenance

| Input | Role | Vintage / limitation |
|---|---|---|
| GEOLYTIX grocery points | Primary shop identity, coordinates and available size band | Author reports latest release downloaded October 2026; exact release unspecified |
| OpenStreetMap | Supplementary shops and supporting observations | Archived cache from original Git commit `76d6bbe`; collection vintage/completeness unknown |
| Co-operative Group / Southern locators | Merger-party estate and operating-group information | Source snapshots retained in research workspace; locator group does not always establish legal ownership |
| OpenRouteService catchments | Cached five-minute drive areas | Existing polygons reused; one evidence-supported coordinate correction was separately routed |
| CMA published decision | Economic framework and positive benchmark of 19 locations | Outcome list used only after model scoring |
| Esri / CARTO tiles | Background context in the interactive map | External service; labels and provider terms are independent of model data |

OpenStreetMap attribution: © OpenStreetMap contributors, [copyright and licence](https://www.openstreetmap.org/copyright). GEOLYTIX attribution: [GEOLYTIX Retail Points](https://geolytix.com/). Routing attribution: [openrouteservice](https://openrouteservice.org/). Tile attribution is displayed inside the map.

The public map embeds derived store/rival records and geometries. Keeping raw inputs out of Git does not remove source-data obligations from those derived assets. Retain attribution and the applicable data-provider terms when publishing. No new licence is assigned to third-party data by this project.

## Prepared-input boundary

The numbered analysis workflow makes acquisition and preparation explicit. Steps 01–08 inspect the supplied snapshots and cached geometry by default; network refresh requires explicit flags. Step 09 clips sources to the acquisition territory, matches party observations and attaches GEOLYTIX format proxies. It records prepared-file hashes in `data/prepared/manifest.json`. Steps 10–13 resolve identities, score, render and export. The Streamlit app only reads those exported assets.

The prepared source snapshot includes `party_status`, constructed by step 09 using party branding, proximity and postcode, plus exact full address/postcode or store-link evidence for displaced points. Store-size attachment uses full postcode/address, or a unique postcode candidate within 250 m. These are observable matching rules, not verified legal ownership or net-sales-area measurements. Source categories are derived from brand, fascia and name through `retailers.py`, followed by the CMA-specific additions.

No ORS key, CARTO key, `.env` file, credential or user-specific absolute filesystem path is needed to run the public app.
