"""Collect OSM with per-cell checkpoints; preserve the existing GEOLYTIX input.

Unlike the original fresh-only collector this can resume after a request fails.
No identity, ownership, deduplication or economic decisions occur here.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import time

import geopandas as gpd
import requests
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/raw/rival_stores/overpass_cells"
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]


def query_cell(cell, session, cached_only=False):
    bounds = gpd.GeoSeries([cell], crs=27700).to_crs(4326).total_bounds
    w, s, e, n = bounds
    query = f'[out:json][timeout:45];nwr["shop"~"^(supermarket|convenience|grocery)$"]({s},{w},{n},{e});out center meta;'
    key = hashlib.sha256(query.encode()).hexdigest()[:20]
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if cached_only:
        raise RuntimeError("No cached response; network collection not attempted")
    errors = []
    for url in ENDPOINTS:
        try:
            response = session.get(url, params={"data": query}, timeout=20)
            response.raise_for_status()
            data = response.json()
            if "remark" in data or not isinstance(data.get("elements"), list):
                raise ValueError(str(data.get("remark", "Missing elements")))
            data["collection_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            data["endpoint"] = url
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(1)
            return data
        except (requests.RequestException, ValueError) as error:
            errors.append(f"{url}: {error}")
    raise RuntimeError("; ".join(errors))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cells", type=int, default=0)
    parser.add_argument("--cached-only", action="store_true", help="Assemble cached coverage without any network calls")
    args = parser.parse_args(argv)
    CACHE.mkdir(parents=True, exist_ok=True)
    area = gpd.read_file(ROOT / "data/intermediate/rival_collection_area.gpkg").to_crs(27700).geometry.union_all()
    x0, y0, x1, y1 = area.bounds
    cells = [box(x, y, x + 20000, y + 20000)
             for x in range(int(x0 // 20000) * 20000, int(x1) + 20000, 20000)
             for y in range(int(y0 // 20000) * 20000, int(y1) + 20000, 20000)
             if box(x, y, x + 20000, y + 20000).intersects(area)]
    session = requests.Session()
    session.headers["User-Agent"] = "CoopCompetitionPortfolio/1.0 (public-data research)"
    elements, failures, dates = {}, [], []
    for index, cell in enumerate(cells, 1):
        if args.max_cells and index > args.max_cells:
            failures.append({"cell": index, "error": "not attempted: max-cells"})
            continue
        try:
            data = query_cell(cell, session, args.cached_only)
            dates.append(data["collection_timestamp_utc"])
            for item in data["elements"]:
                elements[f'{item["type"]}/{item["id"]}'] = item
            print(f"OSM {index}/{len(cells)}; unique objects {len(elements)}", flush=True)
        except RuntimeError as error:
            failures.append({"cell": index, "bounds": list(cell.bounds), "error": str(error)})
            print(f"OSM {index}/{len(cells)} failed: {error}", flush=True)
    out = CACHE.parent
    metadata = {"complete": not failures, "grid_cells": len(cells), "failed_cells": failures,
                "collection_dates_utc": sorted(set(dates)), "unique_source_objects": len(elements)}
    (out / "osm_collection_status.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    # Partial retrieval is retained separately and must never masquerade as complete.
    filename = "osm_grocery_candidates_raw.json" if not failures else "osm_grocery_candidates_partial.json"
    (out / filename).write_text(json.dumps({"elements": list(elements.values()), "metadata": metadata}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"complete": metadata["complete"], "grid_cells": len(cells), "missing_cells": len(failures), "unique_source_objects": len(elements)}, indent=2), flush=True)
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
