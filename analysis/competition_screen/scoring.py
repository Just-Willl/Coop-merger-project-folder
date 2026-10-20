"""Pure scoring rules: inclusion, weights, fascia grouping and threshold.

Weights describe retailer categories, not market shares. Source reconciliation
must finish before scoring. Benchmark outcomes never enter these functions.
"""
import math


def rival_weight(rival, rules):
    """Return the reference weight and its auditable reason."""
    category, fascia = rival.retailer_type, rival.fascia
    if fascia in {'Cook', 'Costco'}:
        return 0.0, 'product_scope_exclusion'
    weights = {'major': rules['major_weight'], 'discounter': rules['discounter_weight'],
               'symbol': rules['reference']['symbol_weight'], 'independent': rules['independent_weight'],
               'party_franchise': rules['reference']['franchise_weight'], 'specialist': 0.0}
    if category not in weights:
        raise ValueError(f'Unrecognised retailer category: {category}')
    return float(weights[category]), category + '_reference_weight'


def fascia_group(rival):
    """Count recognised chains/symbols once; independent premises separately."""
    if rival.retailer_type == 'independent' or rival.fascia == 'Co-op unresolved society':
        return rival.premises_id
    return rival.fascia


def score_catchment(rivals, evidence, rules):
    """Return the sum of one maximum weight per group, plus observation lineage."""
    groups, contributions = {}, []
    for rival in rivals.itertuples():
        if evidence == 'core' and rival.is_suspect:
            continue
        weight, reason = rival_weight(rival, rules)
        key = fascia_group(rival)
        groups[key] = max(groups.get(key, 0.0), weight)
        contributions.append(dict(premises_id=rival.premises_id, source_ids=rival.source_ids,
            name=rival.name, postcode=rival.postcode, fascia=rival.fascia, group_key=key,
            observation_weight=weight, weight_reason=reason, is_suspect=rival.is_suspect))
    return round(sum(groups.values()), 8), contributions


def is_concern(score, eligible, other_party_count, rules):
    """A convenience screen flag requires eligibility, overlap and score ≤3."""
    return bool(eligible and other_party_count > 0 and not math.isnan(score)
                and score <= rules['rival_weight_threshold'])
