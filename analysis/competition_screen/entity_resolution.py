"""GEOLYTIX-anchored entity resolution, separate from competitor inclusion.

Many OSM observations can support one primary premise. No automatic operation
joins two GEOLYTIX anchors, or chains OSM points to reach a distant anchor.
"""
import hashlib
import re
from .source_evidence import normalize_identity_text, corroborates_store_url


def identities_compatible(a, b):
    # Unresolved society/ownership is handled separately, never inferred by brand.
    if a.fascia == b.fascia and a.retailer_type != 'independent':
        return a.fascia != 'Co-op unresolved society'
    if a.retailer_type == b.retailer_type == 'independent':
        name = normalize_identity_text(a['name'])
        return (len(name) >= 8 and name == normalize_identity_text(b['name'])
                and name not in {'conveniencestore', 'supermarket', 'grocerystore', 'cornershop'})
    return False


def resolve_entities(sources, decisions, policy):
    s = sources.copy()
    s['primary_source_id'] = s.source_id
    s['identity_review_reason'] = ''
    pairs = []
    records = {i: r for i, r in s.iterrows()}
    by_id = {r.source_id: i for i, r in records.items()}
    parent = {i: i for i in records}

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i

    def key(a, b):
        return tuple(sorted((records[a].source_id, records[b].source_id)))

    def note(i, reason):
        old = s.at[i, 'identity_review_reason'].split(';')
        s.at[i, 'identity_review_reason'] = ';'.join(sorted(set(filter(None, [*old, reason]))))

    def suspect(i, reason):
        s.at[i, 'is_suspect'] = True
        s.at[i, 'suspect_reason'] = ';'.join(sorted(set(filter(None, [*s.at[i, 'suspect_reason'].split(';'), reason]))))

    def join(i, j):
        left, right = find(i), find(j)
        if left == right:
            return
        members = [k for k in records if find(k) in {left, right}]
        if any(decisions.get(key(a,b)) == 'distinct_premises' for a in members for b in members if a < b):
            raise ValueError('Identity union contradicts an explicit distinct-premises decision')
        primaries = [k for k in members if records[k].source == policy['primary_source']]
        if len(primaries) > 1:
            raise ValueError('Cannot merge two primary-source stores automatically or through a transitive link')
        chosen = primaries[0] if primaries else min(members, key=lambda k: records[k].source_id)
        for k in members:
            parent[k] = chosen

    # Binding manual decisions are applied before automatic candidates.
    for ids, decision in decisions.items():
        if not all(x in by_id for x in ids):
            raise ValueError(f'Manual decision refers to absent source IDs: {ids}')
        if decision == 'same_premises':
            join(*(by_id[x] for x in ids))

    radius = policy['corroborated_link_radius_m']
    for i, a in records.items():
        for pos in s.sindex.query(a.geometry.buffer(radius), predicate='intersects'):
            j = s.index[pos]
            if i >= j:
                continue
            b = records[j]
            distance = float(a.geometry.distance(b.geometry))
            if distance > radius:
                continue
            same_fascia = a.fascia == b.fascia and a.retailer_type != 'independent'
            url = corroborates_store_url(a, b)
            same_postcode = bool(normalize_identity_text(a.postcode) and normalize_identity_text(a.postcode) == normalize_identity_text(b.postcode))
            address = normalize_identity_text(a.get('address', ''))
            same_address = len(address) >= 8 and address == normalize_identity_text(b.get('address', ''))
            cross = a.source != b.source
            # Retain existing tight observation matching for unresolved Co-op sites;
            # this does not resolve the society's legal ownership.
            coop = (cross and a.fascia == b.fascia == 'Co-op unresolved society' and distance <= 15
                    and (same_postcode or normalize_identity_text(a['name']) == normalize_identity_text(b['name'])))
            eligible = (cross and identities_compatible(a,b) and
                        (distance <= policy['same_chain_link_radius_m'] or url or (same_address and same_postcode))) or coop
            p = dict(left_id=a.source_id, right_id=b.source_id, i=i, j=j, distance_m=distance,
                     same_fascia=same_fascia, same_postcode=same_postcode,
                     postcode_conflict=bool(normalize_identity_text(a.postcode) and normalize_identity_text(b.postcode) and not same_postcode),
                     store_url_corroboration=url, auto_candidate=eligible,
                     match_rule='primary_same_chain_spatial' if eligible else '', treatment='review_only')
            if url and eligible:
                p['match_rule'] = 'primary_store_url_corroboration'
            if coop:
                p['match_rule'] = 'tight_coop_observation_match_ownership_unresolved'
            pairs.append(p)

    # Resolve each OSM observation against anchors, not reciprocal pair counts:
    # a node AND a way may both describe one real GEOLYTIX store.
    for i, a in records.items():
        if a.source != 'OSM' or find(i) != i:
            continue
        options = []
        for p in pairs:
            if i not in (p['i'], p['j']) or not p['auto_candidate']:
                continue
            j = p['j'] if p['i'] == i else p['i']
            if records[j].source != policy['primary_source'] or decisions.get(key(i,j)) == 'distinct_premises':
                continue
            options.append((p['distance_m'], j, p))
        options.sort(key=lambda x: (x[0], records[x[1]].source_id))
        if not options:
            continue
        if len(options) > 1 and options[1][0] - options[0][0] < policy['nearest_primary_margin_m']:
            suspect(i, 'ambiguous_primary_link_osm_only')
            note(i, 'multiple_plausible_primary_stores_no_merge')
            for _, j, p in options:
                note(j, 'osm_identity_ambiguity_primary_presence_retained')
                p['treatment'] = 'ambiguous_anchor_osm_review_primary_retained'
            continue
        _, j, p = options[0]
        join(i,j)
        p['treatment'] = 'linked_to_primary'
        if p['postcode_conflict']:
            note(i, 'source_postcode_disagreement_retained')
            note(j, 'source_postcode_disagreement_retained')

    # Conservative OSM-only node/way deduplication; no same-source proximity-only
    # merge of independent businesses, and no path that joins separate anchors.
    for p in pairs:
        i,j = p['i'],p['j']
        if decisions.get(key(i,j)) == 'distinct_premises':
            p['treatment'] = 'manual_distinct'
            continue
        if find(i) == find(j):
            if p['treatment'] == 'review_only':
                p['treatment'] = 'same_resolved_premise'
            continue
        a,b = records[i],records[j]
        if a.source == b.source == 'OSM' and p['distance_m'] <= policy['osm_duplicate_radius_m']:
            if identities_compatible(a,b) and normalize_identity_text(a['name']) == normalize_identity_text(b['name']):
                # Never attach an unmatched observation via another OSM record.
                if all(records[find(k)].source == 'OSM' for k in (i,j)):
                    join(i,j)
                    p['treatment'] = 'osm_only_exact_identity'
                    continue
        if p['distance_m'] > policy['same_chain_link_radius_m']:
            continue
        for k in [i,j]:
            note(k, 'nearby_observation_review_not_absence_evidence')
        if a.source != b.source and a.fascia != b.fascia and p['distance_m'] <= policy['different_brand_review_radius_m']:
            # Possible rebrand/co-location: GEOLYTIX controls the reference,
            # while the competing OSM identity remains visible in sensitivity.
            osm = i if a.source == 'OSM' else j
            if records[osm].source == 'OSM' and records[find(osm)].source == 'OSM':
                suspect(osm, 'osm_alternative_identity_near_primary')
                p['treatment'] = 'osm_alternative_review_primary_retained'
    for i in records:
        anchor = find(i)
        s.at[i,'premises_id'] = 'SITE-' + records[anchor].source_id
        s.at[i,'primary_source_id'] = records[anchor].source_id
        s.at[i,'source_conflict_id'] = hashlib.sha256(s.at[i,'identity_review_reason'].encode()).hexdigest()[:12] if s.at[i,'identity_review_reason'] else ''
    return s, pairs
