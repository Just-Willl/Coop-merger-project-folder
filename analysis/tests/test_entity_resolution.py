import sys
import json
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import pytest

ROOT = Path(__file__).resolve().parents[1]
from competition_screen.entity_resolution import resolve_entities as resolve

POLICY = json.loads((ROOT / 'config/entity_resolution.json').read_text())


def sources(rows):
    output = []
    for row in rows:
        d = dict(source_id='', source='OSM', name='Tesco Express', fascia='Tesco', retailer_type='major',
                 postcode='', address='', website='', is_suspect=False, suspect_reason='',
                 source_conflict_id='', identity_review_reason='')
        d.update(row)
        d['geometry'] = Point(d.pop('x'), 0)
        output.append(d)
    return gpd.GeoDataFrame(output, crs=27700)


def test_conflicting_postcodes_and_abbreviated_names_do_not_erase_primary():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',name='Tesco Haywards Heath Express',postcode='RH16 3PH',x=0),
                 dict(source_id='OSM-a',postcode='RH16 3TH',x=4)])
    out, _ = resolve(s, {}, POLICY)
    assert out.premises_id.nunique() == 1
    assert out.primary_source_id.eq('GEO-a').all()
    assert not out.is_suspect.any()
    assert 'postcode_disagreement' in out.iloc[0].identity_review_reason


def test_many_osm_observations_attach_to_one_geo_anchor():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=0),
                 dict(source_id='OSM-node',x=10),dict(source_id='OSM-way',x=12)])
    out, _ = resolve(s, {}, POLICY)
    assert out.premises_id.nunique() == 1
    assert not out.is_suspect.any()


def test_two_plausible_anchors_stay_separate_and_present():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=-2),
                 dict(source_id='GEO-b',source='GEOLYTIX',x=2),dict(source_id='OSM-a',x=0)])
    out, _ = resolve(s, {}, POLICY)
    assert out.premises_id.nunique() == 3
    assert not out.loc[out.source.eq('GEOLYTIX'),'is_suspect'].any()
    assert out.loc[out.source.eq('OSM'),'is_suspect'].all()


def test_different_fascia_osm_cannot_poison_geo_primary():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=0),
                 dict(source_id='OSM-a',name='Morrisons',fascia='Morrisons',x=3)])
    out, _ = resolve(s, {}, POLICY)
    assert out.premises_id.nunique() == 2
    assert not out.iloc[0].is_suspect
    assert out.iloc[1].is_suspect


def test_no_transitive_osm_bridge_to_distant_geo():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=0),
                 dict(source_id='OSM-a',x=29),dict(source_id='OSM-b',x=33)])
    out, _ = resolve(s, {}, POLICY)
    assert out.iloc[1].premises_id == 'SITE-GEO-a'
    assert out.iloc[2].premises_id != 'SITE-GEO-a'


def test_explicit_distinct_decision_blocks_matching():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=0),dict(source_id='OSM-a',x=1)])
    out, _ = resolve(s, {('GEO-a','OSM-a'):'distinct_premises'}, POLICY)
    assert out.premises_id.nunique() == 2
    assert not out.is_suspect.any()


def test_no_merge_of_separate_primary_records_even_with_manual_bridge():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',x=0),dict(source_id='GEO-b',source='GEOLYTIX',x=1)])
    with pytest.raises(ValueError,match='two primary-source'):
        resolve(s, {('GEO-a','GEO-b'):'same_premises'}, POLICY)


def test_adjacent_independent_businesses_are_not_merged():
    s = sources([dict(source_id='GEO-a',source='GEOLYTIX',name='Alpha Foods',fascia='Independent / unclassified',retailer_type='independent',x=0),
                 dict(source_id='OSM-a',name='Beta Foods',fascia='Independent / unclassified',retailer_type='independent',x=1)])
    out, _ = resolve(s, {}, POLICY)
    assert out.premises_id.nunique() == 2


def test_osm_only_duplicate_does_not_disappear():
    out, _ = resolve(sources([dict(source_id='OSM-node',x=0),dict(source_id='OSM-way',x=1)]), {}, POLICY)
    assert out.premises_id.nunique() == 1
    assert not out.is_suspect.any()
