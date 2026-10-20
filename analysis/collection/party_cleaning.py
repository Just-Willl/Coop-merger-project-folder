import pandas as pd

def clean_stores(southern_df, coop_group_df):
    southern_clean = southern_df[
        [
            "id",
            "identifier",
            "businessId",
            "name",
            "streetAndNumber",
            "city",
            "province",
            "zip",
            "lat",
            "lng",
        ]
    ].copy()
    
    southern_clean = southern_clean.rename(
        columns={
            "id": "source_store_id",
            "identifier": "source_identifier",
            "businessId": "operator_id",
            "name": "store_name",
            "streetAndNumber": "street_address",
            "city": "town",
            "province": "county",
            "zip": "postcode",
            "lat": "latitude",
            "lng": "longitude",
        }
    )
    
    southern_clean["party"] = "Southern Co-op"
    
    southern_clean["source"] = "Southern Co-op Uberall API"
    
    southern_clean["store_id"] = (
        "SC-" + southern_clean["source_store_id"].astype(str)
    )
    
    coop_group_clean = coop_group_df[
        [
            "cedar",
            "hubnumber",
            "name",
            "location_type",
            "society",
            "public",
            "street_address",
            "street_address2",
            "street_address3",
            "town",
            "county",
            "postcode",
            "temporarily_closed",
            "permanently_closed",
            "position.x",
            "position.y",
        ]
    ].copy()
    
    coop_group_clean = coop_group_clean.rename(
        columns={
            "cedar": "source_store_id",
            "hubnumber": "source_identifier",
            "name": "store_name",
            "society": "operator_id",
            "position.x": "longitude",
            "position.y": "latitude",
        }
    )
    
    coop_group_clean["party"] = "Co-operative Group"
    
    coop_group_clean["source"] = "Co-op location-services API"
    
    coop_group_clean["store_id"] = (
        "CG-" + coop_group_clean["source_store_id"].astype(str)
    )
    
    southern_clean = southern_clean[
        [
            "store_id",
            "party",
            "source_store_id",
            "source_identifier",
            "store_name",
            "operator_id",
            "street_address",
            "town",
            "county",
            "postcode",
            "latitude",
            "longitude",
            "source",
        ]
    ]
    
    coop_group_clean = coop_group_clean[
        [
            "store_id",
            "party",
            "source_store_id",
            "source_identifier",
            "store_name",
            "operator_id",
            "location_type",
            "public",
            "street_address",
            "street_address2",
            "street_address3",
            "town",
            "county",
            "postcode",
            "latitude",
            "longitude",
            "temporarily_closed",
            "permanently_closed",
            "source",
        ]
    ]
    
    stores_df = pd.concat(
        [southern_clean, coop_group_clean],
        ignore_index=True
    )
    return stores_df
