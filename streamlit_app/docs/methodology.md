# Methodology

This independent model implements the published **convenience-store** decision-rule structure. It is not a CMA finding. Geography, source coverage, retailer identities and selected operational assumptions differ from the regulator's evidence.

## Workflow

1. **Prepared observations.** Load GEOLYTIX and archived OpenStreetMap records, the supplied merger-party estate and cached candidate catchments. Existing party identity matches and store-format proxies are explicit prepared inputs.
2. **Resolve shops.** Each GEOLYTIX record is an anchor. Compatible OSM observations attach directly to an unambiguous anchor. Multiple OSM records can describe one shop. Canonical name, location, postcode, fascia and size remain GEOLYTIX's. Identity disagreements are retained separately from competitive inclusion.
3. **Define rivals.** Remove acquired-party observations. Restore the inferred independent Southern Welcome franchise group as a rival constraint. Apply retailer categories and product-scope assumptions. Unresolved ownership or alternative OSM identities remain visible through the inclusive evidence treatment.
4. **Identify local observations.** Use spatial joins against the original one-mile and five-minute polygons. Display polygons are simplified only after scoring. A shop can appear in both methods, but scores are not summed across methods.
5. **Calculate weighted fascias.** Count each recognised chain/symbol group once per catchment and independent premises separately. Flag an eligible convenience centroid only when a corporate-proxy opposite-party store overlaps and at most three weighted rival fascias remain, excluding the parties.
6. **Compare outcomes.** Aggregate flags to store level using either eligible method. Join CMA Annex 1 only after scoring. Absence from Annex 1 does not prove a CMA clearance for every candidate.

## Reference weights

| Category | Reference weight | Status |
|---|---:|---|
| Named major grocery chains | 1.0 | Published CMA precedent |
| Aldi, Lidl, M&S | 0.8 | Published CMA precedent |
| Symbol groups | 0.8 | Reference choice; public precedent also uses 1.0 depending on centroid |
| Independent grocery premises | 0.5 | Published precedent; eligibility/classification still needs evidence |
| Inferred party-franchise rivals | 0.6 | Explicit unresolved franchise-weight assumption |
| Classified specialists, including Cook/Costco | 0 | Reference product-scope treatment; not all exclusions are settled transaction rules |

Unknown retailer names fall back to `Independent / unclassified`; this can misclassify specialists and unrecognised chains. A store's individual sales area does not scale the reference weight. There is no distance decay inside a catchment, turnover weighting, switching estimate, diversion ratio or price-effect calculation.

## Source matching and inclusion

The current source-priority rule is in `config/entity_resolution.json`. Compatible same-chain OSM observations can link within 30 metres; stronger branch-URL or address/postcode corroboration can support a direct link within 60 metres. Conflicting source postcodes are recorded rather than treated as a global matching veto. Two possible nearby GEOLYTIX anchors require a nearest-anchor gap of at least 5 metres; otherwise the OSM link is reviewed and both anchors remain present. No two GEOLYTIX anchors are combined and OSM chains cannot bridge to distant anchors. Distinct independent businesses are not merged merely because they are close.

Different OSM identities within 5 metres of a GEOLYTIX store remain uncertain alternatives. General proximity and duplicate-link uncertainty do not erase a GEOLYTIX competitor. This source precedence is an explicit assumption, not a guarantee that the primary dataset is correct or currently trading.

## Scope limits

- Store-size bands are proxies for CMA net sales area. Known supermarket proxies and unknown-size centroids are outside the reference convenience flag.
- Larger grocery shops can constrain convenience centroids; unknown OSM floor area does not automatically exclude a rival.
- The Southern franchise source-group proxy is not a verified legal ownership register.
- Archived OSM vintage/completeness is unknown. GEOLYTIX was downloaded in October 2026 according to the author; its exact release date was not established.
- Cached candidate selection, coordinate discrepancies and road-network assumptions may omit or move relevant overlaps. No cached catchment means not assessed.
- The separate supermarket framework, prospective entry, and full case-specific competitive assessment are not implemented.
- Core/inclusive scores are sensitivity treatments, not statistical confidence bounds.

## Sources for the economic framework

- [Co-operative Group / Southern decision](https://assets.publishing.service.gov.uk/media/6ac50e5135adbc27761df938/__Full_text_decision___.pdf), paragraphs 16–19, 36 and 64–71, footnote 93 and Annex 1.
- [Asda / Arthur](https://assets.publishing.service.gov.uk/media/643815e5773a8a000cab2c0f/A._Decision_on_relevant_merger_situation_and_substantial_lessening_of_competition.pdf), paragraphs 116–119 and footnotes 148/152.
- [Morrisons / McColl's](https://assets.publishing.service.gov.uk/media/633ffd21d3bf7f587561bb50/Morrisons_McColls_-_SLC_Decision__.pdf), paragraphs 46–50.
