import json
import os
import time

import requests

from . import config

GERRIT_URL = 'https://review.opendev.org'
GERRIT_QUERY = os.environ.get(
    'GERRIT_QUERY',
    'project:openstack/ status:open'
)

CACHE_FILE = config.CACHE_DIR / 'gerrit_cache.json'
CACHE_TTL = int(os.environ.get('K8S_AGENT_TOOLS_CACHE_TTL', '600'))


def _read_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        cached_at = data.get('_cached_at', 0)
        if time.time() - cached_at < CACHE_TTL:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _write_cache(data):
    data['_cached_at'] = time.time()
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _fetch_reviews(query=None, max_results=25):
    q = query or GERRIT_QUERY
    url = f'{GERRIT_URL}/changes/'
    params = {'q': q, 'n': max_results, 'o': ['LABELS', 'CURRENT_REVISION']}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        text = resp.text
        if text.startswith(")]}'"):
            text = text[4:].lstrip('\n')
        raw_list = json.loads(text)
        reviews = [_normalize_review(r) for r in raw_list]
        return {'reviews': reviews, '_demo': False}
    except Exception as e:
        return {'reviews': [], '_demo': False, '_error': str(e)}


def _normalize_review(raw):
    labels = raw.get('labels', {})
    code_review = labels.get('Code-Review', {})
    approved = code_review.get('approved', {})
    rejected = code_review.get('rejected', {})
    recommended = code_review.get('recommended', {})
    disliked = code_review.get('disliked', {})

    votes = {
        '+2': 1 if approved else 0,
        '+1': 1 if recommended else 0,
        '-1': 1 if disliked else 0,
        '-2': 1 if rejected else 0,
    }

    owner = raw.get('owner', {})
    return {
        'number': raw.get('_number', 0),
        'subject': raw.get('subject', ''),
        'status': raw.get('status', 'NEW'),
        'owner': owner.get('name', owner.get('username', f'user-{owner.get("_account_id", "?")}')),
        'updated': raw.get('updated', ''),
        'url': f'{GERRIT_URL}/c/{raw.get("project", "")}/+/{raw.get("_number", "")}',
        'project': raw.get('project', ''),
        'votes': votes,
    }


def get_reviews(query=None):
    cached = _read_cache()
    if cached:
        return cached
    try:
        data = _fetch_reviews(query or GERRIT_QUERY)
    except Exception:
        data = get_demo_data()
    _write_cache(data)
    return data


def get_counts(data):
    reviews = data.get('reviews', [])
    statuses = [r.get('status', '').upper() for r in reviews]
    return {
        'total': len(reviews),
        'open': sum(1 for s in statuses if s == 'NEW'),
        'merged': sum(1 for s in statuses if s == 'MERGED'),
        'wip': sum(1 for s in statuses if s == 'WIP'),
        'plus_two': sum(1 for r in reviews if r.get('votes', {}).get('+2', 0) > 0),
        'minus_one': sum(1 for r in reviews if r.get('votes', {}).get('-1', 0) > 0),
    }


def get_status():
    cached = _read_cache()
    if cached and cached.get('_error'):
        return 'error'
    return 'connected'


DEMO_REVIEWS = [
    {'number': 978234, 'subject': 'Nova: Fix reconciler requeue interval',
     'status': 'NEW', 'owner': 'dev-1',
     'updated': '2026-04-16T10:00:00',
     'url': 'https://review.opendev.org/c/openstack/nova-operator/+/978234',
     'project': 'openstack/nova-operator',
     'votes': {'+2': 1, '+1': 1, '-1': 0, '-2': 0}},
    {'number': 978190, 'subject': 'Keystone: Add endpoint readiness gate',
     'status': 'NEW', 'owner': 'dev-2',
     'updated': '2026-04-15T16:30:00',
     'url': 'https://review.opendev.org/c/openstack/keystone-operator/+/978190',
     'project': 'openstack/keystone-operator',
     'votes': {'+2': 0, '+1': 2, '-1': 0, '-2': 0}},
    {'number': 977998, 'subject': 'Glance: Update CRD for multi-store',
     'status': 'MERGED', 'owner': 'dev-3',
     'updated': '2026-04-15T14:00:00',
     'url': 'https://review.opendev.org/c/openstack/glance-operator/+/977998',
     'project': 'openstack/glance-operator',
     'votes': {'+2': 2, '+1': 0, '-1': 0, '-2': 0}},
    {'number': 977850, 'subject': 'Cinder: Fix volume backup controller',
     'status': 'NEW', 'owner': 'dev-1',
     'updated': '2026-04-14T11:00:00',
     'url': 'https://review.opendev.org/c/openstack/cinder-operator/+/977850',
     'project': 'openstack/cinder-operator',
     'votes': {'+2': 0, '+1': 0, '-1': 1, '-2': 0}},
    {'number': 977700, 'subject': 'Neutron: Webhook validation for subnet CRD',
     'status': 'NEW', 'owner': 'dev-2',
     'updated': '2026-04-14T09:00:00',
     'url': 'https://review.opendev.org/c/openstack/neutron-operator/+/977700',
     'project': 'openstack/neutron-operator',
     'votes': {'+2': 1, '+1': 1, '-1': 0, '-2': 0}},
    {'number': 977600, 'subject': 'Manila: Add share type reconciler',
     'status': 'WIP', 'owner': 'dev-3',
     'updated': '2026-04-13T17:00:00',
     'url': 'https://review.opendev.org/c/openstack/manila-operator/+/977600',
     'project': 'openstack/manila-operator',
     'votes': {'+2': 0, '+1': 0, '-1': 0, '-2': 0}},
]


def get_demo_data():
    return {'reviews': list(DEMO_REVIEWS), '_demo': True}
