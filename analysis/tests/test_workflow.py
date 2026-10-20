"""Release checks focus on unchanged outcomes, source identity and portability."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT.parent/'streamlit_app'
from competition_screen.entity_resolution import resolve_entities
from competition_screen.scoring import score_catchment, is_concern
from competition_screen.source_evidence import corroborates_store_url

RULES=json.loads((ROOT/'config/model_rules.json').read_text())
POLICY=json.loads((ROOT/'config/entity_resolution.json').read_text())


def test_all_reference_catchment_and_store_outputs_are_unchanged():
    for name,key,columns in [
        ('catchment_results','catchment_id',['weighted_rival_fascias_core','weighted_rival_fascias_inclusive','flag_core','flag_inclusive']),
        ('store_results','centroid_store_id',['min_score_core','min_score_inclusive','flag_core','flag_inclusive'])]:
        actual=pd.read_csv(APP/'assets'/f'{name}.csv').set_index(key).sort_index()
        expected=pd.read_csv(ROOT/'tests/fixtures'/f'expected_{name}.csv').set_index(key).sort_index()
        pd.testing.assert_frame_equal(actual[columns],expected[columns],check_dtype=False,atol=1e-7,rtol=0)


def test_named_chain_contributes_once_and_independents_contribute_separately():
    rows=pd.DataFrame([
        dict(premises_id='tesco-1',source_ids='a',name='Tesco',postcode='',fascia='Tesco',retailer_type='major',is_suspect=False),
        dict(premises_id='tesco-2',source_ids='b',name='Tesco',postcode='',fascia='Tesco',retailer_type='major',is_suspect=False),
        dict(premises_id='independent-1',source_ids='c',name='Alpha',postcode='',fascia='Independent / unclassified',retailer_type='independent',is_suspect=False),
        dict(premises_id='independent-2',source_ids='d',name='Beta',postcode='',fascia='Independent / unclassified',retailer_type='independent',is_suspect=False)])
    assert score_catchment(rows,'core',RULES)[0]==2.0


def test_flags_require_format_overlap_and_threshold():
    assert is_concern(3.0,True,1,RULES)
    assert not is_concern(3.1,True,1,RULES)
    assert not is_concern(0,False,1,RULES)
    assert not is_concern(float('nan'),True,0,RULES)


def test_multiple_osm_records_and_postcode_conflict_keep_one_primary():
    frame=gpd.GeoDataFrame([
        dict(source_id='GEO-1',source='GEOLYTIX',name='Tesco Haywards Heath Express',fascia='Tesco',retailer_type='major',postcode='RH16 3PH',address='Orchards Shopping Centre',website='',geometry=Point(0,0)),
        dict(source_id='OSM-node',source='OSM',name='Tesco Express',fascia='Tesco',retailer_type='major',postcode='RH16 3TH',address='',website='',geometry=Point(4,0)),
        dict(source_id='OSM-way',source='OSM',name='Tesco Express',fascia='Tesco',retailer_type='major',postcode='',address='',website='',geometry=Point(5,0))],crs=27700)
    for column in ['suspect_reason','source_conflict_id','identity_review_reason']:
        frame[column]=''
    frame['is_suspect']=False
    actual,_=resolve_entities(frame,{},POLICY)
    assert actual.premises_id.nunique()==1
    assert actual.primary_source_id.eq('GEO-1').all()
    assert not actual.is_suspect.any()


def test_branch_address_without_a_number_can_corroborate():
    a=pd.Series(dict(fascia='Tesco',name='Tesco Haywards Heath Express',address='Orchards Shopping Centre',website=''))
    b=pd.Series(dict(fascia='Tesco',name='Tesco Express',address='',website='https://www.tesco.com/store-locator/haywards-heath/orchards-shopping-centre'))
    assert corroborates_store_url(a,b)


def test_release_file_hashes_and_no_parent_runtime_imports():
    manifest=json.loads((APP/'assets/release_manifest.json').read_text())
    for filename,digest in manifest['files'].items():
        assert hashlib.sha256((APP/'assets'/filename).read_bytes()).hexdigest()==digest
    for path in (ROOT/'competition_screen').glob('*.py'):
        text=path.read_text()
        assert 'from rival_pipeline import' not in text
        assert 'from cma_comparison import' not in text
    assert not list((APP/'assets').rglob('.env'))
    assert not list((APP/'assets').rglob('secrets.toml'))


def test_streamlit_app_loads_without_an_exception():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(APP/'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==4
    if not any((APP/'report'/name).exists() for name in ['economics_report.md','economics_report.pdf']):
        assert any('economics report will be added' in message.value for message in app.info)
