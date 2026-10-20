"""Promote verified local outputs into the app's static assets; no remote publishing."""
from pathlib import Path
import json
import hashlib
import shutil
import pandas as pd
import geopandas as gpd

from .paths import ANALYSIS_ROOT as ROOT, OUTPUT_DIRECTORY, APP_DIRECTORY


def main():
    """Step 13: verify source integrity, reviewed outputs and map, then export."""
    observations=gpd.read_file(OUTPUT_DIRECTORY/'source_observations.gpkg').fillna('')
    entities=gpd.read_file(OUTPUT_DIRECTORY/'resolved_entities.gpkg').fillna('')
    source_index=observations.set_index('source_id')
    member_ids=[source_id for value in entities.source_ids for source_id in value.split('|')]
    if len(member_ids)!=len(set(member_ids)) or set(member_ids)!=set(source_index.index):
        raise AssertionError('Every observation must belong to exactly one entity')
    primary_count=0
    for entity in entities.itertuples():
        primaries=[source_id for source_id in entity.source_ids.split('|') if source_index.loc[source_id,'source']=='GEOLYTIX']
        if len(primaries)>1: raise AssertionError('Multiple GEOLYTIX anchors merged')
        if not primaries: continue
        primary_count+=1
        primary=source_index.loc[primaries[0]]
        if not all(getattr(entity,column)==primary[column] for column in ['name','postcode','longitude','latitude','size_band','fascia']) or not entity.geometry.equals(primary.geometry):
            raise AssertionError('Canonical primary attributes changed')
    if primary_count!=observations.source.eq('GEOLYTIX').sum():
        raise AssertionError('GEOLYTIX anchor lost')
    # Refactoring must preserve the reviewed reference outputs. Fixtures are used
    # only as a release check, never as an input to model scoring.
    for filename,identifier,columns in [
        ('catchment_results','catchment_id',['weighted_rival_fascias_core','weighted_rival_fascias_inclusive','flag_core','flag_inclusive']),
        ('store_results','centroid_store_id',['min_score_core','min_score_inclusive','flag_core','flag_inclusive'])]:
        actual=pd.read_csv(OUTPUT_DIRECTORY/f'{filename}.csv').set_index(identifier).sort_index()
        expected=pd.read_csv(ROOT/'tests/fixtures'/f'expected_{filename}.csv').set_index(identifier).sort_index()
        pd.testing.assert_frame_equal(actual[columns],expected[columns],check_dtype=False,atol=1e-7,rtol=0)
    output=APP_DIRECTORY/'assets'
    output.mkdir(exist_ok=True)
    public_files=['competition_map.html','store_results.csv','catchment_results.csv','benchmark_comparison.csv',
                  'analysis_summary.json','map_validation.json','rival_contributions.csv']
    for filename in public_files:
        shutil.copy2(OUTPUT_DIRECTORY/filename,output/filename)
    # Serve summaries without private preparation paths or local absolute paths.
    summary=json.loads((output/'analysis_summary.json').read_text())
    summary.pop('input_sha256',None)
    (output/'analysis_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    manifest={'validation':'Exact reference parity on all catchment and store scores/flags; source identity and canonical anchors verified',
        'observations':len(observations),'entities':len(entities),'primary_anchors':primary_count,
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name!='release_manifest.json'}}
    (output/'release_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Verified reference parity and prepared local deployment assets. Nothing uploaded.')


if __name__=='__main__':
    main()
