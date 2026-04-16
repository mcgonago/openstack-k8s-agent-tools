import json
import os
import time

import requests

from . import config

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPOS_STR = os.environ.get('GITHUB_REPOS', '')
GITHUB_API = 'https://api.github.com'

CACHE_FILE = config.CACHE_DIR / 'github_cache.json'
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


def _is_configured():
    return bool(GITHUB_TOKEN)


def _headers():
    h = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        h['Authorization'] = f'token {GITHUB_TOKEN}'
    return h


def _get_repos():
    if GITHUB_REPOS_STR:
        return [r.strip() for r in GITHUB_REPOS_STR.split(',') if '/' in r.strip()]
    return []


def _fetch_prs(owner, repo, state='open', max_results=25):
    url = f'{GITHUB_API}/repos/{owner}/{repo}/pulls'
    params = {'state': state, 'per_page': max_results, 'sort': 'updated', 'direction': 'desc'}
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        return [_normalize_pr(pr, repo) for pr in resp.json()]
    except Exception:
        return []


def _fetch_commits(owner, repo, since_days=7):
    from datetime import datetime, timedelta
    since = (datetime.now() - timedelta(days=since_days)).isoformat() + 'Z'
    url = f'{GITHUB_API}/repos/{owner}/{repo}/commits'
    params = {'since': since, 'per_page': 25}
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        return [_normalize_commit(c, repo) for c in resp.json()]
    except Exception:
        return []


def _normalize_pr(raw, repo_name):
    return {
        'number': raw.get('number', 0),
        'title': raw.get('title', ''),
        'state': raw.get('state', 'open'),
        'author': (raw.get('user') or {}).get('login', 'unknown'),
        'repo': repo_name,
        'created': raw.get('created_at', ''),
        'updated': raw.get('updated_at', ''),
        'url': raw.get('html_url', '#'),
        'draft': raw.get('draft', False),
        'reviews': len(raw.get('requested_reviewers', [])),
    }


def _normalize_commit(raw, repo_name):
    commit = raw.get('commit', {})
    author = commit.get('author', {})
    return {
        'sha': raw.get('sha', '')[:8],
        'message': commit.get('message', '').split('\n')[0],
        'author': author.get('name', 'unknown'),
        'date': author.get('date', ''),
        'repo': repo_name,
        'url': raw.get('html_url', '#'),
    }


def get_prs():
    cached = _read_cache()
    if cached:
        return cached
    repos = _get_repos()
    if repos:
        data = {'prs': [], 'commits': [], '_demo': False}
        for repo_full in repos:
            owner, name = repo_full.split('/', 1)
            data['prs'].extend(_fetch_prs(owner, name))
            data['commits'].extend(_fetch_commits(owner, name))
        data['prs'].sort(key=lambda x: x.get('updated', ''), reverse=True)
        data['commits'].sort(key=lambda x: x.get('date', ''), reverse=True)
    else:
        data = get_demo_data()
    _write_cache(data)
    return data


def get_counts(data):
    prs = data.get('prs', [])
    commits = data.get('commits', [])
    return {
        'open_prs': sum(1 for p in prs if p.get('state') == 'open'),
        'merged_week': sum(1 for p in prs if p.get('state') in ('merged', 'closed')),
        'total_commits': len(commits),
        'repos': len(set(p.get('repo', '') for p in prs)),
    }


def get_status():
    if _is_configured():
        return 'connected'
    repos = _get_repos()
    if repos:
        return 'connected'
    return 'demo'


DEMO_PRS = [
    {'number': 89, 'title': 'Fix nova reconciler timeout handling',
     'state': 'open', 'author': 'developer-1', 'repo': 'nova-operator',
     'created': '2026-04-15T10:00:00', 'updated': '2026-04-16T09:30:00',
     'url': '#', 'draft': False, 'reviews': 1},
    {'number': 45, 'title': 'Add keystone endpoint health probe',
     'state': 'open', 'author': 'developer-2', 'repo': 'keystone-operator',
     'created': '2026-04-14T14:00:00', 'updated': '2026-04-16T08:00:00',
     'url': '#', 'draft': False, 'reviews': 2},
    {'number': 88, 'title': 'Update Go dependencies to 1.22',
     'state': 'merged', 'author': 'developer-3', 'repo': 'nova-operator',
     'created': '2026-04-12T09:00:00', 'updated': '2026-04-14T16:00:00',
     'url': '#', 'draft': False, 'reviews': 3},
    {'number': 23, 'title': 'Fix CRD schema for GlanceAPI',
     'state': 'open', 'author': 'developer-1', 'repo': 'glance-operator',
     'created': '2026-04-16T07:00:00', 'updated': '2026-04-16T11:00:00',
     'url': '#', 'draft': True, 'reviews': 0},
    {'number': 12, 'title': 'Implement webhook for NeutronAPI validation',
     'state': 'open', 'author': 'developer-2', 'repo': 'neutron-operator',
     'created': '2026-04-15T15:00:00', 'updated': '2026-04-16T10:00:00',
     'url': '#', 'draft': False, 'reviews': 1},
]

DEMO_COMMITS = [
    {'sha': 'a1b2c3d4', 'message': 'Fix reconciler timeout on large Nova deployments',
     'author': 'developer-1', 'date': '2026-04-16T09:30:00',
     'repo': 'nova-operator', 'url': '#'},
    {'sha': 'e5f6g7h8', 'message': 'Add unit tests for keystone health probe',
     'author': 'developer-2', 'date': '2026-04-16T08:15:00',
     'repo': 'keystone-operator', 'url': '#'},
    {'sha': 'i9j0k1l2', 'message': 'Update glance-operator CRD validation',
     'author': 'developer-1', 'date': '2026-04-15T17:00:00',
     'repo': 'glance-operator', 'url': '#'},
    {'sha': 'm3n4o5p6', 'message': 'Refactor cinder volume backup controller',
     'author': 'developer-3', 'date': '2026-04-15T15:30:00',
     'repo': 'cinder-operator', 'url': '#'},
    {'sha': 'q7r8s9t0', 'message': 'Add neutron webhook admission controller',
     'author': 'developer-2', 'date': '2026-04-15T14:00:00',
     'repo': 'neutron-operator', 'url': '#'},
    {'sha': 'u1v2w3x4', 'message': 'Fix placement API endpoint discovery',
     'author': 'developer-3', 'date': '2026-04-15T11:00:00',
     'repo': 'placement-operator', 'url': '#'},
    {'sha': 'y5z6a7b8', 'message': 'Add manila share type reconciler test',
     'author': 'developer-1', 'date': '2026-04-14T16:30:00',
     'repo': 'manila-operator', 'url': '#'},
    {'sha': 'c9d0e1f2', 'message': 'Heat stack owner reference fix',
     'author': 'developer-2', 'date': '2026-04-14T10:00:00',
     'repo': 'heat-operator', 'url': '#'},
]


def get_demo_data():
    return {'prs': list(DEMO_PRS), 'commits': list(DEMO_COMMITS), '_demo': True}
