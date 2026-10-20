"""Reproduce the released reference model from the documented prepared inputs.

Steps 01–09 construct observations, party matches and format proxies.
Step 10 resolves entity identity using GEOLYTIX anchors and canonical attributes.
Step 11 applies ownership/scope decisions, intersects rivals/opposite-party stores
with catchments, scores both evidence treatments, and aggregates store outcomes.
Published CMA outcomes enter only after every model score has been calculated.

Steps 11–13 score, render, validate and export. The hosting application reads
the exported results only. No API keys or network access are needed here.
"""
from pathlib import Path
import argparse
import hashlib
import json
import geopandas as gpd
import pandas as pd
from .entity_resolution import resolve_entities
from .retailers import normalize_text, classify_source_observation, classify_for_cma
from .scoring import score_catchment, is_concern
from .paths import INPUT_DIRECTORY, OUTPUT_DIRECTORY, REPOSITORY_ROOT

ROOT = Path(__file__).resolve().parents[1]


def read_configuration(name):
    return json.loads((ROOT / 'config' / name).read_text(encoding='utf-8'))


def resolve_source_observations():
    """Reset old derived flags, retaining the input's explicit party matches."""
    observations = gpd.read_file(INPUT_DIRECTORY / 'source_observations.gpkg',layer='source_observations').fillna('')
    observations = observations.sort_values('source_id').reset_index(drop=True)
    categories = observations.apply(classify_source_observation,axis=1)
    observations['fascia'] = categories.map(lambda value:value[0])
    observations['retailer_type'] = categories.map(lambda value:value[1])
    for key in ['suspect_reason', 'source_conflict_id', 'identity_review_reason']:
        observations[key] = ''
    observations['is_suspect'] = False
    decisions = {}
    for row in pd.read_csv(ROOT / 'config/manual_identity_decisions.csv').fillna('').itertuples():
        if row.decision not in {'same_premises','distinct_premises'} or not row.evidence_url or not row.reason:
            raise ValueError('Manual decisions require a valid decision and recorded evidence')
        pair=tuple(sorted([row.left_id,row.right_id]))
        if pair in decisions:
            raise ValueError(f'Duplicate manual decision: {pair}')
        decisions[pair] = row.decision
    observations, links = resolve_entities(observations, decisions, read_configuration('entity_resolution.json'))
    # These are inclusion uncertainties, distinct from duplicate identity notes.
    for i, row in observations.iterrows():
        reasons = list(filter(None, row.suspect_reason.split(';')))
        if row.party_status != 'matched_party':
            if row.fascia == 'Co-op unresolved society':
                reasons.append('cooperative_society_unresolved')
            if 'welcome' in normalize_text(row['name']):
                reasons.append('welcome_affiliation_unresolved')
        if row.retailer_type == 'independent' and not normalize_text(row['name']):
            reasons.append('unnamed_grocery_candidate')
        observations.at[i,'is_suspect'] = bool(reasons)
        observations.at[i,'suspect_reason'] = ';'.join(sorted(set(reasons)))
    rows = []
    for entity_id, group in observations.groupby('premises_id',sort=True):
        primary_rows = group[group.source.eq('GEOLYTIX')]
        chosen = (primary_rows if len(primary_rows) else group).sort_values('source_id').iloc[0].copy()
        presence_rows = primary_rows if len(primary_rows) else group
        chosen['source_ids'] = '|'.join(group.source_id)
        chosen['is_suspect'] = bool(presence_rows.is_suspect.any())
        chosen['suspect_reason'] = ';'.join(sorted(set(filter(None, presence_rows.suspect_reason))))
        chosen['identity_review_reason'] = ';'.join(sorted(set(filter(None, group.identity_review_reason))))
        chosen['party_status'] = 'matched_party' if group.party_status.eq('matched_party').any() else 'no_match'
        chosen['validation_status'] = ('unresolved' if chosen.is_suspect else
            'geolytix_primary_osm_supported' if len(primary_rows) and group.source.nunique()>1 else
            'geolytix_primary' if len(primary_rows) else 'osm_supplement')
        rows.append(chosen)
    entities = gpd.GeoDataFrame(pd.DataFrame(rows), geometry='geometry',crs=observations.crs).reset_index(drop=True)
    return observations, entities, pd.DataFrame(links).drop(columns=['i','j'])


def create_rival_universe(entities, stores):
    """Remove acquired parties and add the explicit franchise ownership proxy."""
    rivals = entities[entities.party_status.ne('matched_party')].copy()
    classes = rivals.apply(classify_for_cma,axis=1)
    rivals['fascia'] = classes.map(lambda v:v[0])
    rivals['retailer_type'] = classes.map(lambda v:v[1])
    franchises = stores[stores.franchise_candidate].copy()
    additional = gpd.GeoDataFrame(franchises,
        geometry=gpd.points_from_xy(franchises.longitude,franchises.latitude),crs=4326).to_crs(entities.crs)
    additional['premises_id'] = 'FRANCHISE-' + additional.store_id
    additional['source_ids'] = additional.store_id
    additional['name'] = additional.store_name
    additional['fascia'] = 'Southern Welcome franchise'
    additional['retailer_type'] = 'party_franchise'
    additional['is_suspect'] = False
    additional['suspect_reason'] = 'ownership_proxy_not_verified_register'
    additional['identity_review_reason'] = ''
    additional['validation_status'] = 'ownership_proxy_sensitivity'
    columns = ['premises_id','source_ids','name','postcode','fascia','retailer_type','is_suspect',
               'suspect_reason','identity_review_reason','validation_status','geometry']
    return gpd.GeoDataFrame(pd.concat([rivals[columns],additional[columns]],ignore_index=True),crs=entities.crs)


def run_entity_resolution(output_directory=None):
    """Step 10: resolve observations once, before any economic calculations."""
    output = Path(output_directory) if output_directory else OUTPUT_DIRECTORY
    output.mkdir(parents=True,exist_ok=True)
    observations,entities,links=resolve_source_observations()
    observations.to_file(output/'source_observations.gpkg',driver='GPKG')
    entities.to_file(output/'resolved_entities.gpkg',driver='GPKG')
    links.to_csv(output/'identity_links.csv',index=False)
    print(f'Resolved {len(observations)} observations into {len(entities)} entities')


def run_analysis(output_directory=None):
    """Step 11: score step 10's resolved entities, then join CMA outcomes."""
    output = Path(output_directory) if output_directory else OUTPUT_DIRECTORY
    output.mkdir(parents=True,exist_ok=True)
    rules = read_configuration('model_rules.json')
    stores = pd.read_csv(INPUT_DIRECTORY / 'party_stores.csv').fillna('')
    catchments = gpd.read_file(INPUT_DIRECTORY / 'catchments.gpkg',layer='catchments').to_crs(27700)
    observations=gpd.read_file(output/'source_observations.gpkg').fillna('')
    entities=gpd.read_file(output/'resolved_entities.gpkg').fillna('')
    rivals = create_rival_universe(entities,stores)
    matches = gpd.sjoin(rivals,catchments[['catchment_id','geometry']],predicate='intersects').drop(columns='index_right')
    local = {key:group for key,group in matches.groupby('catchment_id')}
    store_points = gpd.GeoDataFrame(stores,geometry=gpd.points_from_xy(stores.longitude,stores.latitude),crs=4326).to_crs(27700)
    presence = gpd.sjoin(store_points[['store_id','party','franchise_candidate','geometry']],
        catchments[['catchment_id','centroid_party','geometry']],predicate='intersects')
    presence = presence[presence.party.ne(presence.centroid_party) & ~presence.franchise_candidate]
    overlap = presence.groupby('catchment_id').store_id.nunique()
    rows, contributions = [], []
    for catchment in catchments.itertuples():
        other_count = int(overlap.get(catchment.catchment_id,0))
        eligible = not catchment.franchise_candidate and catchment.format_proxy == 'convenience_proxy'
        row = dict(catchment_id=catchment.catchment_id,centroid_store_id=catchment.centroid_store_id,
            centroid_store_name=catchment.centroid_store_name,centroid_party=catchment.centroid_party,
            centroid_postcode=catchment.centroid_postcode,catchment_type=catchment.catchment_type,
            format_proxy=catchment.format_proxy,eligible_convenience_centroid=eligible,corporate_other_party_stores=other_count)
        for evidence in ['core','inclusive']:
            score, audit = score_catchment(local.get(catchment.catchment_id,rivals.iloc[:0]),evidence,rules)
            if not other_count:
                score, audit = float('nan'), []
            row['weighted_rival_fascias_'+evidence] = score
            row['flag_'+evidence] = is_concern(score,eligible,other_count,rules)
            contributions.extend(dict(item,catchment_id=catchment.catchment_id,evidence=evidence) for item in audit)
        rows.append(row)
    catchment_results = pd.DataFrame(rows)
    store_results = catchment_results.groupby('centroid_store_id').agg(
        store_name=('centroid_store_name','first'),party=('centroid_party','first'),postcode=('centroid_postcode','first'),
        eligible=('eligible_convenience_centroid','any'),flag_core=('flag_core','any'),flag_inclusive=('flag_inclusive','any'),
        min_score_core=('weighted_rival_fascias_core','min'),min_score_inclusive=('weighted_rival_fascias_inclusive','min'),
        format_proxy=('format_proxy','first')).reset_index()
    # Published outcomes first enter here, after the complete model calculation.
    benchmark = pd.read_csv(ROOT / 'config/cma_concern_locations.csv')
    lookup = stores.assign(postcode_key=stores.postcode.map(normalize_text))
    benchmark['postcode_key'] = benchmark.postcode.map(normalize_text)
    lookup = lookup.merge(benchmark[['party_code','postcode_key']],on=['party_code','postcode_key'],how='inner')
    benchmark = benchmark.merge(lookup,on=['party_code','postcode_key'],suffixes=('_cma',''),validate='one_to_one')
    if len(benchmark)!=19:
        raise AssertionError('CMA benchmark matching must recover all 19 published centroids')
    store_results['listed_in_annex1'] = store_results.centroid_store_id.isin(benchmark.store_id)
    benchmark = benchmark[['annex_row','store_id','store_name','postcode_cma','party_code']].merge(
        store_results,left_on='store_id',right_on='centroid_store_id',suffixes=('_source',''),validate='one_to_one')
    benchmark['comparison'] = ['not_assessed' if not e else 'flag_both_data_treatments' if b else 'flag_core_only' if a else 'not_flagged'
        for e,a,b in zip(benchmark.eligible,benchmark.flag_core,benchmark.flag_inclusive)]
    for name,frame in [('catchment_results',catchment_results),('store_results',store_results),
                       ('benchmark_comparison',benchmark),('rival_contributions',pd.DataFrame(contributions))]:
        frame.to_csv(output / (name+'.csv'),index=False)
    rivals.to_file(output / 'rival_stores.gpkg',driver='GPKG')
    observations.to_file(output / 'source_observations.gpkg',driver='GPKG')
    matches.drop(columns='geometry').to_csv(output / 'catchment_rival_matches.csv',index=False)
    summary = dict(source_observations=len(observations),entities=len(entities),party_stores=len(stores),
        assessed_candidate_stores=len(store_results),catchments=len(catchments),
        flagged_stores_core=int(store_results.flag_core.sum()),flagged_stores_inclusive=int(store_results.flag_inclusive.sum()),
        cma_concern_locations=19,cma_locations_flagged_core=int(benchmark.flag_core.sum()),
        additional_model_flags=int((store_results.flag_core & ~store_results.listed_in_annex1).sum()),
        benchmark_comparison=benchmark.comparison.value_counts().to_dict())
    summary['input_sha256'] = {str(p.relative_to(REPOSITORY_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in [INPUT_DIRECTORY,ROOT/'config'] for p in sorted(folder.glob('*')) if p.is_file()}
    (output/'analysis_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},indent=2))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory',type=Path)
    run_analysis(parser.parse_args().output_directory)
