# ============================================================
# 08A - MANUAL REVIEW OF AMBIGUOUS OSM / GEOLYTIX DUPLICATES
# ============================================================
#
# PURPOSE
#
# Script 08 performs conservative automatic cross-source
# deduplication between OpenStreetMap and GEOLYTIX.
#
# That process deliberately leaves uncertain cases unresolved
# rather than deleting records where two genuine nearby stores
# might exist.
#
# The remaining review cases were inspected manually. This file
# documents that review and explains the decisions subsequently
# implemented automatically in Script 08.
#
#
# ============================================================
# REVIEW PROCESS
# ============================================================
#
# The automatic diagnostic identified 24 unique OSM stores
# requiring further review.
#
# Each case was assessed using a combination of:
#
#   - distance between the OSM and GEOLYTIX points
#   - fascia / brand agreement
#   - store names
#   - postcode agreement
#   - GEOLYTIX store descriptions
#   - retailer/store information where necessary
#   - visual inspection of maps for unusually dense locations
#
# Proximity alone was NOT treated as proof of duplication.
#
# This was particularly important in:
#
#   - railway stations
#   - shopping centres
#   - petrol filling stations
#   - dense town/city centres
#
# where two stores belonging to the same fascia can genuinely
# operate only a few metres apart.
#
#
# ============================================================
# DECISION RULE
# ============================================================
#
# REMOVE:
#
# An OSM record was classified as a duplicate when the evidence
# indicated that it represented the same physical store already
# represented by a GEOLYTIX record.
#
# In these cases the GEOLYTIX record was preferred because it
# generally provides more structured information, including
# fascia and size_band.
#
#
# KEEP:
#
# An OSM record was retained where the evidence indicated that
# it represented a genuinely separate physical store.
#
#
# ============================================================
# MANUALLY CONFIRMED DUPLICATES - REMOVE OSM
# ============================================================
#
# The following 20 OSM records were judged to duplicate stores
# already represented in GEOLYTIX:
#
# OSM-node-10587211657
#   Morrisons Daily, Exmouth
#
# OSM-node-10587211665
#   Morrisons Daily, Exmouth
#
# OSM-node-12923053147
#   Heron Foods, Bedminster
#
# OSM-node-14132060498
#   M&S, London Bridge / Shard
#
# OSM-node-1938101529
#   Tesco / Rowner Express
#
# OSM-node-425442524
#   Sainsbury's, Pentonville Road
#
# OSM-node-4866277724
#   Asda, Wolverton
#
# OSM-node-4944511321
#   Aldi, Chichester
#
# OSM-node-5760381482
#   M&S, London Bridge / Shard
#
# OSM-node-610453006
#   Lidl, Shepherd's Bush
#
# OSM-way-1380072962
#   Morrisons Daily, Andover
#
# OSM-way-223332358
#   Co-op, Newport Pagnell
#
# OSM-way-240323961
#   Morrisons, Hastings
#
# OSM-way-291700163
#   Sainsbury's, Bristol Hippodrome
#
# OSM-way-377488601
#   M&S, Liverpool Street
#
# OSM-way-377595859
#   M&S, Liverpool Street West Mall
#
# OSM-way-416601711
#   M&S, King's Cross
#
# OSM-way-451971783
#   Budgens, Thanet
#
# OSM-way-855193700
#   Co-op, Upminster Road
#
# OSM-way-954251425
#   Little Waitrose / Shell Blendon
#
#
# ============================================================
# MANUALLY CONFIRMED SEPARATE STORES - KEEP
# ============================================================
#
# The following four OSM records were deliberately retained:
#
# OSM-node-26659113
#   Sainsbury's Fetter Lane
#
#   The nearby GEOLYTIX record represented a different
#   Sainsbury's store.
#
#
# OSM-node-647011555
#   M&S St Pancras
#
#   Manual map inspection showed multiple genuine M&S outlets
#   inside St Pancras. The close OSM and GEOLYTIX points could
#   therefore represent separate stores.
#
#
# OSM-node-8176629229
#   Co-op Royal Albert Wharf
#
#   The nearby GEOLYTIX Co-op represented a different physical
#   outlet.
#
#
# OSM-way-1395332597
#   Morrisons Daily / PFS, Aldershot
#
#   This appears to represent the convenience / petrol filling
#   station operation rather than simply duplicating the nearby
#   Morrisons supermarket.
#
#
# ============================================================
# DENSE-LOCATION EXAMPLE: LONDON BRIDGE
# ============================================================
#
# London Bridge contained several M&S outlets within a very
# small area.
#
# Manual map inspection identified at least two separate stores:
#
#   Shard M&S Simply Food
#   approx. 51.504766, -0.086191
#
#   Marks & Spencer Food
#   approx. 51.504381, -0.085043
#
# The two ambiguous OSM records:
#
#   OSM-node-14132060498
#   OSM-node-5760381482
#
# were judged to represent the Shard store already represented
# in GEOLYTIX and were therefore removed.
#
# The two separate GEOLYTIX M&S records were retained.
#
#
# ============================================================
# DENSE-LOCATION EXAMPLE: ST PANCRAS
# ============================================================
#
# St Pancras also contains multiple genuine M&S Simply Food
# outlets within the same station.
#
# Visual inspection showed that the OSM point and nearby
# GEOLYTIX records were consistent with separate real stores.
#
# OSM-node-647011555 was therefore retained.
#
# This illustrates why a simple same-fascia + distance rule
# would risk incorrectly deleting genuine competitors.
#
#
# ============================================================
# IMPLEMENTATION
# ============================================================
#
# These decisions are not applied by manually editing the final
# rival dataset.
#
# Script 08 contains the manually confirmed REMOVE IDs and
# applies them automatically whenever the rival dataset is
# rebuilt.
#
# Script 08 therefore remains reproducible, while this file
# records the reasoning behind those judgement-based decisions.
# ============================================================