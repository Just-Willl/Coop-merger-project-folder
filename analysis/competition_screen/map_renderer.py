"""Render the explorer from this package's model outputs, without parent imports."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import geopandas as gpd
import pandas as pd
from .pipeline import ROOT, read_configuration
from .scoring import rival_weight, fascia_group
from .paths import INPUT_DIRECTORY, OUTPUT_DIRECTORY


def json_safe(value):
    if isinstance(value,dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):
        return [json_safe(v) for v in value]
    return None if isinstance(value,float) and math.isnan(value) else value


def render_map(build_directory=None):
    build = Path(build_directory) if build_directory else OUTPUT_DIRECTORY
    rules = read_configuration('model_rules.json')
    stores = pd.read_csv(INPUT_DIRECTORY/'party_stores.csv').fillna('')
    outcomes = pd.read_csv(build/'store_results.csv').set_index('centroid_store_id')
    methods = pd.read_csv(build/'catchment_results.csv')
    annex_ids = set(pd.read_csv(build/'benchmark_comparison.csv').store_id)
    source = gpd.read_file(build/'source_observations.gpkg').fillna('').set_index('source_id')
    rival_stores = gpd.read_file(build/'rival_stores.gpkg').fillna('').to_crs(4326)
    rivals = {}
    for row in rival_stores.itertuples():
        ids = row.source_ids.split('|')
        postcodes = sorted({source.loc[i,'postcode'] for i in ids if i in source.index and source.loc[i,'postcode']})
        sizes = sorted({source.loc[i,'size_band'] for i in ids if i.startswith('GEO-') and i in source.index and source.loc[i,'size_band']})
        weight, reason = rival_weight(row,rules)
        rivals[row.premises_id] = dict(id=row.premises_id,name=row.name,postcode=row.postcode,
            fascia=row.fascia,group=fascia_group(row),weight=weight,reason=reason,suspect=bool(row.is_suspect),
            suspect_reason=row.suspect_reason,sources=row.source_ids,validation=row.validation_status,
            canonical_source='GEOLYTIX' if any(i.startswith('GEO-') for i in ids) else 'OSM' if row.premises_id.startswith('SITE-') else 'Party franchise proxy',
            source_postcodes=' / '.join(postcodes),identity_note=row.identity_review_reason,
            size='; '.join(sizes) or 'Unknown — no matched GEOLYTIX size',lat=row.geometry.y,lon=row.geometry.x)
    matches = pd.read_csv(build/'catchment_rival_matches.csv')
    membership = matches.groupby('catchment_id').premises_id.apply(list).to_dict()
    geometry = gpd.read_file(INPUT_DIRECTORY/'catchments.gpkg',layer='catchments').to_crs(27700)
    points = gpd.GeoDataFrame(stores,geometry=gpd.points_from_xy(stores.longitude,stores.latitude),crs=4326).to_crs(27700)
    presence = gpd.sjoin(points,geometry[['catchment_id','centroid_party','geometry']],predicate='intersects')
    presence = presence[presence.party.ne(presence.centroid_party)&~presence.franchise_candidate]
    counterparts = presence.groupby('catchment_id').store_id.apply(list).to_dict()
    checked = 0
    for row in methods.itertuples():
        for evidence in ['core','inclusive']:
            groups = {}
            for entity_id in membership.get(row.catchment_id,[]):
                rival = rivals[entity_id]
                if evidence=='core' and rival['suspect']:
                    continue
                groups[rival['group']] = max(groups.get(rival['group'],0),rival['weight'])
            expected = getattr(row,'weighted_rival_fascias_'+evidence)
            if pd.notna(expected):
                if abs(sum(groups.values())-expected)>1e-7:
                    raise AssertionError('Map and score disagree: '+row.catchment_id)
                checked += 1
    store_rows = []
    for row in stores.itertuples():
        store_rows.append(dict(id=row.store_id,name=row.store_name,party='CG' if row.store_id.startswith('CG-') else 'SC',
            postcode=row.postcode,address=', '.join(str(s) for s in [row.street_address,row.town] if s),lat=row.latitude,lon=row.longitude,
            franchise=bool(row.franchise_candidate),format=row.format_proxy,cma=row.store_id in annex_ids,
            model=json_safe(outcomes.loc[row.store_id].to_dict()) if row.store_id in outcomes.index else None,
            methods=json_safe(methods[methods.centroid_store_id.eq(row.store_id)].to_dict('records'))))
    geometry.geometry = geometry.geometry.simplify(12,preserve_topology=True)
    boundaries = geometry[['centroid_store_id','catchment_type','geometry']].to_crs(4326)
    template = (ROOT/'competition_screen/templates/competition_map.html').read_text(encoding='utf-8')
    payloads = dict(STORES=store_rows,CATCHMENTS=json.loads(boundaries.to_json()),RIVALS=rivals,MEMBERSHIP=membership,COUNTERPARTS=counterparts)
    for key,value in payloads.items():
        template = template.replace('__'+key+'__',json.dumps(json_safe(value),allow_nan=False).replace('</','<\\/'))
    (build/'competition_map.html').write_text(template,encoding='utf-8')
    (build/'map_validation.json').write_text(json.dumps(dict(stores=len(stores),catchments=len(geometry),reconciled_score_rows=checked,
        html_sha256=hashlib.sha256(template.encode()).hexdigest()),indent=2),encoding='utf-8')
    print(f'Rendered {len(stores)} source stores; verified {checked} catchment/evidence scores.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-directory',type=Path)
    render_map(parser.parse_args().build_directory)
