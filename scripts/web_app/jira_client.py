import json
import os
import time

import requests

from . import config

JIRA_URL = os.environ.get('JIRA_URL', 'https://issues.redhat.com')
JIRA_TOKEN = os.environ.get('JIRA_TOKEN', '')
JIRA_PROJECT = os.environ.get('JIRA_PROJECT', 'OSPRH')

CACHE_FILE = config.CACHE_DIR / 'jira_cache.json'
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
    return bool(JIRA_TOKEN)


def _fetch_issues(project=None, max_results=50):
    proj = project or JIRA_PROJECT
    jql = f'project={proj} ORDER BY updated DESC'
    url = f'{JIRA_URL}/rest/api/3/search'
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Accept': 'application/json',
    }
    params = {'jql': jql, 'maxResults': max_results,
              'fields': 'summary,status,priority,assignee,updated,labels'}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        issues = [_normalize_issue(i) for i in raw.get('issues', [])]
        return {'issues': issues, '_demo': False}
    except Exception as e:
        return {'issues': [], '_demo': False, '_error': str(e)}


def _normalize_issue(raw):
    fields = raw.get('fields', {})
    assignee = fields.get('assignee') or {}
    priority = fields.get('priority') or {}
    status = fields.get('status') or {}
    return {
        'key': raw.get('key', ''),
        'summary': fields.get('summary', ''),
        'status': status.get('name', 'Unknown'),
        'priority': priority.get('name', 'Medium'),
        'assignee': assignee.get('displayName', 'unassigned'),
        'updated': fields.get('updated', ''),
        'url': f'{JIRA_URL}/browse/{raw.get("key", "")}',
        'labels': fields.get('labels', []),
    }


def get_issues(project=None):
    cached = _read_cache()
    if cached:
        return cached
    if _is_configured():
        data = _fetch_issues(project or JIRA_PROJECT)
    else:
        data = get_demo_data()
    _write_cache(data)
    return data


def get_counts(data):
    issues = data.get('issues', [])
    total = len(issues)
    statuses = [i.get('status', '').lower() for i in issues]
    return {
        'total': total,
        'open': sum(1 for s in statuses if s in ('open', 'to do', 'new', 'backlog')),
        'in_progress': sum(1 for s in statuses if s in ('in progress', 'in review')),
        'done': sum(1 for s in statuses if s in ('done', 'closed', 'resolved')),
        'blocked': sum(1 for s in statuses if s in ('blocked', 'impediment')),
    }


def get_status():
    if _is_configured():
        cached = _read_cache()
        if cached and cached.get('_error'):
            return 'error'
        return 'connected'
    return 'demo'


DEMO_ISSUES = [
    {'key': 'DEMO-001', 'summary': 'Nova operator reconciler timeout on large deployments',
     'status': 'In Progress', 'priority': 'High',
     'assignee': 'developer-1', 'updated': '2026-04-16T10:30:00',
     'url': '#', 'labels': ['nova-operator']},
    {'key': 'DEMO-002', 'summary': 'Add Keystone endpoint health check to operator',
     'status': 'Open', 'priority': 'Medium',
     'assignee': 'developer-2', 'updated': '2026-04-16T09:15:00',
     'url': '#', 'labels': ['keystone-operator']},
    {'key': 'DEMO-003', 'summary': 'Glance operator CRD schema validation failing',
     'status': 'Blocked', 'priority': 'Critical',
     'assignee': 'developer-1', 'updated': '2026-04-15T16:00:00',
     'url': '#', 'labels': ['glance-operator']},
    {'key': 'DEMO-004', 'summary': 'Update Cinder operator Go dependencies',
     'status': 'Done', 'priority': 'Low',
     'assignee': 'developer-3', 'updated': '2026-04-15T14:30:00',
     'url': '#', 'labels': ['cinder-operator']},
    {'key': 'DEMO-005', 'summary': 'Implement Neutron operator webhook validation',
     'status': 'In Progress', 'priority': 'High',
     'assignee': 'developer-2', 'updated': '2026-04-16T11:00:00',
     'url': '#', 'labels': ['neutron-operator']},
    {'key': 'DEMO-006', 'summary': 'Fix Manila operator finalizer race condition',
     'status': 'Open', 'priority': 'Medium',
     'assignee': 'unassigned', 'updated': '2026-04-14T08:00:00',
     'url': '#', 'labels': ['manila-operator']},
    {'key': 'DEMO-007', 'summary': 'Placement operator: add TLS support',
     'status': 'In Progress', 'priority': 'Medium',
     'assignee': 'developer-3', 'updated': '2026-04-16T12:00:00',
     'url': '#', 'labels': ['placement-operator']},
    {'key': 'DEMO-008', 'summary': 'Heat operator stack reconciliation improvements',
     'status': 'Open', 'priority': 'Low',
     'assignee': 'unassigned', 'updated': '2026-04-13T17:00:00',
     'url': '#', 'labels': ['heat-operator']},
]


def get_demo_data():
    return {'issues': list(DEMO_ISSUES), '_demo': True}
