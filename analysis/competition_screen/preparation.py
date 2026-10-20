"""Steps 01–09: acquisition, geometry and explicit prepared-input construction.

Default runs use the supplied source snapshots/catchments. Network collection
requires --refresh. Refreshed data are not assumed to reproduce the frozen study.
"""
import json
import os
import hashlib
import shutil
import pandas as pd
import geopandas as gpd
from .paths import ANALYSIS_ROOT, REPOSITORY_ROOT, DATA_DIRECTORY, INPUT_DIRECTORY, INTERMEDIATE_DIRECTORY
from .retailers import normalize_text, classify_source_observation


def point_geometry(frame, longitude='longitude', latitude='latitude'):
    return gpd.GeoDataFrame(frame.copy(),geometry=gpd.points_from_xy(frame[longitude],frame[latitude]),crs=4326).to_crs(27700)


def collect_party_stores(refresh=False):
    directory=DATA_DIRECTORY/'raw/party_stores'
    directory.mkdir(parents=True,exist_ok=True)
    if refresh:
        from collection.party_collection import get_southern_locations, get_coop_group_locations
        get_southern_locations().to_csv(directory/'southern_cooperative.csv',index=False)
        get_coop_group_locations().to_csv(directory/'cooperative_group.csv',index=False)
    for filename in ['southern_cooperative.csv','cooperative_group.csv']:
        frame=pd.read_csv(directory/filename)
        print(f'{filename}: {len(frame)} source rows ({"refreshed" if refresh else "supplied snapshot"})')


def clean_party_stores():
    from collection.party_cleaning import clean_stores
    raw=DATA_DIRECTORY/'raw/party_stores'
    stores=clean_stores(pd.read_csv(raw/'southern_cooperative.csv'),pd.read_csv(raw/'cooperative_group.csv'))
    for decision in pd.read_csv(ANALYSIS_ROOT/'config/coordinate_corrections.csv').itertuples():
        if decision.resolution=='retain_existing':
            continue
        if decision.resolution!='use_geolytix' or not decision.evidence_url or not decision.reason:
            raise ValueError('Coordinate changes require a documented decision')
        match=stores.store_id.eq(decision.store_id)
        if match.sum()!=1: raise ValueError('Coordinate correction store is missing or ambiguous')
        stores.loc[match,['longitude','latitude']]=[decision.longitude,decision.latitude]
    if stores.store_id.duplicated().any(): raise ValueError('Duplicate party store IDs')
    INTERMEDIATE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    stores.to_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv',index=False)
    print(f'Cleaned {len(stores)} party records, with documented coordinate decisions applied.')


def explore_party_stores():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stores=pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv')
    stores.groupby('party').size().rename('stores').to_csv(INTERMEDIATE_DIRECTORY/'party_store_counts.csv')
    fig,axis=plt.subplots(figsize=(7,8))
    for party,rows in stores.groupby('party'):
        axis.scatter(rows.longitude,rows.latitude,s=4,label=party,alpha=.5)
    axis.set(xlabel='Longitude',ylabel='Latitude',title='Supplied merger-party estate')
    axis.legend();fig.tight_layout();fig.savefig(INTERMEDIATE_DIRECTORY/'party_estate.png',dpi=150);plt.close(fig)
    print(stores.party.value_counts().to_string())


def one_mile_overlaps():
    stores=point_geometry(pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv'))
    group=stores[stores.party.eq('Co-operative Group')]
    southern=stores[stores.party.eq('Southern Co-op')]
    circles=southern[['store_id','geometry']].copy().rename(columns={'store_id':'southern_store_id'})
    circles.geometry=circles.geometry.buffer(1609.344)
    pairs=gpd.sjoin(group[['store_id','geometry']],circles,predicate='intersects')
    pairs=pairs.rename(columns={'store_id':'cooperative_group_store_id'})[['cooperative_group_store_id','southern_store_id']].drop_duplicates()
    pairs.to_csv(INTERMEDIATE_DIRECTORY/'one_mile_overlaps.csv',index=False)
    print(f'{len(pairs)} cross-party one-mile pairs')


def drive_time_catchments(refresh=False):
    stores=pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv')
    cache=DATA_DIRECTORY/'cache/drive_time_catchments.gpkg'
    if cache.exists():
        existing=gpd.read_file(cache).to_crs(27700)
    elif refresh:
        existing=gpd.GeoDataFrame({column:[] for column in ['store_id','party','isochrone_minutes','centroid_longitude','centroid_latitude']},geometry=[],crs=27700)
    else:
        raise FileNotFoundError('Reviewed routing cache is missing. Supply the study cache or explicitly use step 05 --refresh.')
    indexed=stores.set_index('store_id')
    estate_reference=DATA_DIRECTORY/'cache/reviewed_party_stores.csv'
    reviewed_ids=set(pd.read_csv(estate_reference).store_id) if estate_reference.exists() else set()
    if not refresh and set(stores.store_id)!=reviewed_ids:
        raise ValueError('The party estate changed; run step 05 --refresh to rebuild candidate coverage')
    changed=[r.store_id for r in existing.itertuples() if r.store_id not in indexed.index or
        abs(indexed.loc[r.store_id,'longitude']-r.centroid_longitude)>1e-7 or
        abs(indexed.loc[r.store_id,'latitude']-r.centroid_latitude)>1e-7]
    if not refresh:
        if changed: raise ValueError('Cached routing does not match cleaned coordinates; run step 05 --refresh after reviewing the input change')
        existing.to_file(INTERMEDIATE_DIRECTORY/'drive_time_catchments.gpkg',driver='GPKG')
        print(f'Reused {len(existing)} reviewed 300-second catchments; no API calls')
        return
    import requests
    from shapely.geometry import shape
    points=point_geometry(stores)
    southern=points[points.party.eq('Southern Co-op')][['store_id','geometry']].rename(columns={'store_id':'other_id'})
    southern.geometry=southern.geometry.buffer(8000)
    pairs=gpd.sjoin(points[points.party.eq('Co-operative Group')][['store_id','geometry']],southern,predicate='intersects')
    ids=set(pairs.store_id)|set(pairs.other_id)
    result=existing[existing.store_id.isin(ids)&~existing.store_id.isin(changed)].copy()
    key=os.environ.get('ORS_API_KEY','')
    env=REPOSITORY_ROOT/'.env'
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith('ORS_API_KEY='): key=line.split('=',1)[1].strip().strip('"\'')
    missing=ids-set(result.store_id)
    if missing and not key: raise RuntimeError('Set ORS_API_KEY locally to request missing catchments')
    rows=[]
    for store_id in sorted(missing):
        row=indexed.loc[store_id]
        response=requests.post('https://api.openrouteservice.org/v2/isochrones/driving-car',
            json={'locations':[[float(row.longitude),float(row.latitude)]],'range':[300],'range_type':'time'},
            headers={'Authorization':key},timeout=60)
        if response.status_code!=200: raise RuntimeError(f'Routing failed: HTTP {response.status_code}; credentials omitted')
        geometry=gpd.GeoSeries([shape(response.json()['features'][0]['geometry'])],crs=4326).to_crs(27700).iloc[0]
        rows.append(dict(store_id=store_id,party=row.party,isochrone_minutes=5,centroid_longitude=row.longitude,centroid_latitude=row.latitude,geometry=geometry))
    if rows: result=gpd.GeoDataFrame(pd.concat([result,gpd.GeoDataFrame(rows,crs=27700)],ignore_index=True),crs=27700)
    result.to_file(INTERMEDIATE_DIRECTORY/'drive_time_catchments.gpkg',driver='GPKG')
    print(f'{len(result)} catchments; {len(missing)} newly requested. The inherited 8 km candidate filter remains an assumption.')


def drive_time_overlaps():
    stores=point_geometry(pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv'))
    catchments=gpd.read_file(INTERMEDIATE_DIRECTORY/'drive_time_catchments.gpkg').to_crs(27700)
    polygons=catchments[['store_id','party','geometry']].rename(columns={'store_id':'centroid_store_id','party':'centroid_party'})
    matches=gpd.sjoin(stores[['store_id','party','geometry']],polygons,predicate='intersects')
    matches=matches[matches.party.ne(matches.centroid_party)]
    matches.drop(columns=['geometry','index_right']).to_csv(INTERMEDIATE_DIRECTORY/'drive_time_overlaps.csv',index=False)
    print(f'{len(matches)} directional drive-time overlaps')


def build_analysis_areas(refresh_territory=False):
    stores=pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv')
    drive=gpd.read_file(INTERMEDIATE_DIRECTORY/'drive_time_catchments.gpkg').to_crs(27700)
    circles=point_geometry(stores[stores.store_id.isin(drive.store_id)])
    circles.geometry=circles.geometry.buffer(1609.344)
    circles['catchment_type']='1_mile';circles['catchment_id']=circles.store_id+'__1mi'
    drive=drive[['store_id','geometry']].merge(stores,on='store_id',validate='one_to_one')
    drive['catchment_type']='5_min_drive';drive['catchment_id']=drive.store_id+'__5min'
    columns=['store_id','party','store_name','postcode','catchment_id','catchment_type','geometry']
    candidates=gpd.GeoDataFrame(pd.concat([circles[columns],drive[columns]],ignore_index=True),crs=27700)
    candidates=candidates.rename(columns={'store_id':'centroid_store_id','party':'centroid_party','store_name':'centroid_store_name','postcode':'centroid_postcode'})
    candidates.to_file(INTERMEDIATE_DIRECTORY/'candidate_catchments.gpkg',driver='GPKG')
    # Acquisition territory is separate from centroid population. Keep the
    # supplied study's reviewed collection footprint explicit for reproduction.
    area=(gpd.GeoDataFrame({'territory':['updated_candidates']},geometry=[candidates.geometry.union_all()],crs=27700)
          if refresh_territory else gpd.read_file(DATA_DIRECTORY/'cache/reviewed_collection_area.gpkg'))
    area.to_file(INTERMEDIATE_DIRECTORY/'rival_collection_area.gpkg',driver='GPKG')
    print(f'{len(candidates)} candidate catchments; source territory: {"updated" if refresh_territory else "reviewed snapshot"}')


def collect_rival_stores(refresh=False, geolytix_file=None):
    directory=DATA_DIRECTORY/'raw/rival_stores'
    if geolytix_file:
        shutil.copy2(geolytix_file,directory/'geolytix_grocery_retail_points.csv')
    if refresh:
        from collection.osm_collection import main
        main([])
    print(f"GEOLYTIX source: {len(pd.read_csv(directory/'geolytix_grocery_retail_points.csv'))} rows")
    print('Reviewed OSM source: historical_osm_candidates.gpkg; age/completeness unknown')
    print('A fresh Overpass file is usable only when its metadata reports complete coverage.')


def prepare_model_inputs(source_mode='reviewed'):
    from .source_evidence import normalize_identity_text
    stores=pd.read_csv(INTERMEDIATE_DIRECTORY/'party_stores_clean.csv').fillna('')
    rules=json.loads((ANALYSIS_ROOT/'config/model_rules.json').read_text())
    stores['party_code']=stores.store_id.str.split('-').str[0]
    stores['franchise_candidate']=(stores.party.eq('Southern Co-op') & stores.operator_id.astype(str).eq(rules['southern_franchise_business_id_proxy']))|stores.store_name.str.contains(r'\bINDF\b',case=False,regex=True)
    stores['postcode_key']=stores.postcode.map(normalize_text);stores['address_key']=stores.street_address.map(normalize_text)
    directory=DATA_DIRECTORY/'raw/rival_stores'
    geo=pd.read_csv(directory/'geolytix_grocery_retail_points.csv').fillna('')
    geo_points=point_geometry(geo,'long_wgs','lat_wgs')
    by_postcode={key:group for key,group in geo_points[geo_points.retailer.map(normalize_text).eq('coop')].groupby(geo_points.postcode.map(normalize_text))}
    formats=[]
    for row in point_geometry(stores).itertuples():
        candidates=by_postcode.get(row.postcode_key,geo_points.iloc[:0]) if row.postcode_key else geo_points.iloc[:0]
        exact=candidates[candidates.add_one.map(normalize_text).eq(row.address_key)] if row.address_key else candidates.iloc[:0]
        chosen,method=None,'unmatched'
        if len(exact)==1: chosen,method=exact.iloc[0],'exact_postcode_and_address'
        elif len(candidates)==1 and row.geometry.distance(candidates.iloc[0].geometry)<=250: chosen,method=candidates.iloc[0],'unique_postcode_within_250m'
        band=chosen.size_band if chosen is not None else 'unknown'
        category='convenience_proxy' if str(band).startswith('<') and '280' in str(band) else 'mss_proxy' if '280 < 1,400' in str(band) else 'oss_proxy' if '2,800' in str(band) else 'unknown'
        formats.append(dict(store_id=row.store_id,size_band=band,format_proxy=category,format_match=method))
    stores=stores.merge(pd.DataFrame(formats),on='store_id',validate='one_to_one')
    area=gpd.read_file(INTERMEDIATE_DIRECTORY/'rival_collection_area.gpkg').to_crs(27700).geometry.union_all()
    source=gpd.GeoDataFrame(dict(source_id='GEO-'+geo.id.astype(str),source='GEOLYTIX',name=geo.store_name,brand_raw=geo.retailer,
        fascia_raw=geo.fascia,postcode=geo.postcode,longitude=geo.long_wgs,latitude=geo.lat_wgs,size_band=geo.size_band,
        address=geo.add_one,website=''),geometry=geo_points.geometry,crs=27700)
    source=source[source.intersects(area)]
    if source_mode=='reviewed':
        cache=gpd.read_file(directory/'historical_osm_candidates.gpkg').to_crs(27700).fillna('')
        osm=gpd.GeoDataFrame(dict(source_id=cache.rival_store_id,source='OSM',name=cache.store_name,brand_raw=cache.osm_brand,
            fascia_raw=cache.fascia,postcode=cache.postcode,longitude=cache.long_wgs,latitude=cache.lat_wgs,size_band=cache.size_band,address='',website=cache.website),geometry=cache.geometry,crs=27700)
    else:
        payload=json.loads((directory/'osm_grocery_candidates_raw.json').read_text())
        if not payload.get('metadata',{}).get('complete'): raise ValueError('Incomplete OSM data cannot enter the model')
        rows=[]
        for item in payload['elements']:
            tags=item.get('tags',{});point=item if item['type']=='node' else item.get('center',{})
            if 'lat' not in point: continue
            rows.append(dict(source_id=f"OSM-{item['type']}-{item['id']}",source='OSM',name=tags.get('name',''),brand_raw=tags.get('brand',''),fascia_raw='',postcode=tags.get('addr:postcode',''),longitude=point['lon'],latitude=point['lat'],size_band='unknown',address=' '.join([tags.get('addr:housenumber',''),tags.get('addr:street','')]),website=tags.get('website',tags.get('contact:website',''))))
        osm=point_geometry(pd.DataFrame(rows))
    observations=gpd.GeoDataFrame(pd.concat([source,osm[osm.intersects(area)]],ignore_index=True),crs=27700).fillna('').sort_values('source_id').reset_index(drop=True)
    classes=observations.apply(classify_source_observation,axis=1)
    observations['fascia']=classes.map(lambda value:value[0]);observations['retailer_type']=classes.map(lambda value:value[1])
    observations['party_status']='no_match'
    parties=point_geometry(stores)
    for i,row in observations.iterrows():
        if row.fascia!='Co-op unresolved society' and 'welcome' not in normalize_text(row['name']): continue
        nearby=parties.sindex.query(row.geometry.buffer(60),predicate='intersects')
        for j in nearby:
            party=parties.iloc[j];distance=row.geometry.distance(party.geometry)
            if distance<=20 or (normalize_text(row.postcode) and normalize_text(row.postcode)==normalize_text(party.postcode)):
                observations.at[i,'party_status']='matched_party'
        for party in parties[parties.postcode_key.eq(normalize_text(row.postcode))].itertuples() if normalize_text(row.postcode) else []:
            address=normalize_text(party.street_address)
            if address and (address==normalize_text(row.address) or (len(address)>=8 and address in normalize_text(row.website))):
                observations.at[i,'party_status']='matched_party'
    geometry=gpd.read_file(INTERMEDIATE_DIRECTORY/'candidate_catchments.gpkg')
    geometry=geometry.merge(stores[['store_id','franchise_candidate','format_proxy']],left_on='centroid_store_id',right_on='store_id',validate='many_to_one').drop(columns='store_id')
    INPUT_DIRECTORY.mkdir(parents=True,exist_ok=True)
    stores.to_csv(INPUT_DIRECTORY/'party_stores.csv',index=False)
    # Replace generated containers completely. Appending a new default layer to
    # a copied GeoPackage can otherwise leave an older layer first in the file.
    for filename,frame in [('source_observations',observations),('catchments',geometry)]:
        target=INPUT_DIRECTORY/(filename+'.gpkg')
        if target.exists(): target.unlink()
        frame.to_file(target,layer=filename,driver='GPKG')
    manifest={'source_mode':source_mode,'upstream_steps':'01–08','limitations':['Historical OSM age/completeness unknown' if source_mode=='reviewed' else 'Fresh Overpass metadata verified complete','Reviewed collection footprint and inherited routing assumptions retained'],
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUT_DIRECTORY.iterdir() if p.suffix in {'.csv','.gpkg'}}}
    (INPUT_DIRECTORY/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Prepared {len(observations)} observations, {len(stores)} stores and {len(geometry)} catchments from stages 01–08')
