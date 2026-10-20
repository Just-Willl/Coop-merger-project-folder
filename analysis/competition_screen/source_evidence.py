"""Conservative identity evidence, distinct from competitive presence evidence."""
import re
from urllib.parse import urlsplit, unquote

OFFICIAL_DOMAINS = {
    'tesco': ('tesco.com',), 'waitrose': ('waitrose.com',),
    'sainsburys': ('sainsburys.co.uk',), 'asda': ('asda.com',),
    'morrisons': ('morrisons.com',), 'aldi': ('aldi.co.uk',), 'lidl': ('lidl.co.uk',),
    'marksandspencer': ('marksandspencer.com',), 'budgens': ('budgens.co.uk',),
    'spar': ('spar.co.uk',), 'londis': ('londis.co.uk',), 'nisa': ('nisalocally.co.uk',),
    'costcutter': ('costcutter.co.uk',), 'onestop': ('onestop.co.uk',),
}


def normalize_identity_text(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def normalize_store_url(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    parsed = urlsplit(raw if '://' in raw else 'https://' + raw)
    path = unquote(parsed.path).rstrip('/').lower()
    # A homepage or generic locator is not a store identifier.
    if not path or path in {'/stores', '/store-locator', '/find-a-store', '/store-finder'}:
        return ''
    segments = path.strip('/').split('/')
    locator_segments = {'stores', 'store', 'shops', 'branches', 'locations', 'store-locator',
                        'find-a-store', 'store-finder', 'our-stores', 'local-stores', 'storefinder'}
    if not any(segment in locator_segments for segment in segments[:-1]):
        return ''
    return parsed.netloc.lower().removeprefix('www.') + path


def corroborates_store_url(a, b):
    ua, ub = normalize_store_url(a.get('website', '')), normalize_store_url(b.get('website', ''))
    if ua and ua == ub and any(ua.split('/')[0] == d or ua.split('/')[0].endswith('.' + d)
                              for d in OFFICIAL_DOMAINS.get(normalize_identity_text(a.get('fascia', '')), ())):
        return True
    for url, other in [(ua, b), (ub, a)]:
        if not url:
            continue
        domain, _, path = url.partition('/')
        fascia = normalize_identity_text(other.get('fascia', ''))
        # Only a brand's own domain can corroborate a location/name/address.
        if not any(domain == d or domain.endswith('.' + d) for d in OFFICIAL_DOMAINS.get(fascia, ())):
            continue
        address = normalize_identity_text(other.get('address', ''))
        if len(address) >= 8 and address in normalize_identity_text(path):
            return True
        name = normalize_identity_text(other.get('name', ''))
        locality = name.removeprefix(fascia)
        if name.startswith(fascia) and len(locality) >= 6 and locality in normalize_identity_text(path):
            return True
    return False

