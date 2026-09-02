import pandas as pd


# ============================================================
# 1. LOAD RAW DATA
# ============================================================

southern_df = pd.read_csv(
    "data/raw/southern_coop_raw.csv"
)

coop_group_df = pd.read_csv(
    "data/raw/coop_group_raw.csv"
)


# ============================================================
# 2. CLEAN SOUTHERN CO-OP
# ============================================================

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


# identify where the record came from
southern_clean["party"] = "Southern Co-op"
southern_clean["source"] = "Southern Co-op Uberall API"


# create our own reproducible unique ID
southern_clean["store_id"] = (
    "SC-" + southern_clean["source_store_id"].astype(str)
)


# ============================================================
# 3. CLEAN CO-OPERATIVE GROUP
# ============================================================

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


# ============================================================
# 4. PUT IMPORTANT COLUMNS FIRST
# ============================================================

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


# ============================================================
# 5. QUICK INSPECTION
# ============================================================

print("Southern Co-op:")
print(southern_clean.shape)
print(southern_clean.head())

print("\nCo-operative Group:")
print(coop_group_clean.shape)
print(coop_group_clean.head())


# Now to combine the two dataframes into one one dataframe for further analysis
stores_df = pd.concat(
    [southern_clean, coop_group_clean],
    ignore_index=True
)

stores_df.head()
stores_df.shape
stores_df["party"].value_counts()

# And save the cleaned data to a CSV file for further analysis
stores_df.to_csv("data/cleaned/combined_stores_clean.csv", index=False)
