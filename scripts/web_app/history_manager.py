import json
import yaml
from datetime import datetime, date, timedelta
from pathlib import Path

from . import config


def snapshot_today(user='system'):
    today = date.today().isoformat()
    snapshot = {
        'date': today,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'generated_by': user,
        'executions': _count_executions(today),
        'analyses': _count_analyses(today),
        'integrations': _integration_status(),
        'users': _count_users(),
    }

    config.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = config.HISTORY_DIR / f'{today}.yaml'
    with open(path, 'w') as f:
        yaml.dump(snapshot, f, default_flow_style=False)
    return snapshot


def _count_executions(date_str):
    exec_dir = config.EXECUTIONS_DIR
    if not exec_dir.exists():
        return {'total': 0, 'completed': 0, 'failed': 0,
                'running': 0, 'by_skill': {}}
    total = completed = failed = running = 0
    by_skill = {}
    for d in exec_dir.iterdir():
        meta_file = d / 'meta.yaml'
        if not d.is_dir() or not meta_file.exists():
            continue
        try:
            with open(meta_file) as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            continue
        created = meta.get('created_at', '')
        if not created.startswith(date_str):
            continue
        total += 1
        status = meta.get('status', '')
        if status == 'completed':
            completed += 1
        elif status == 'failed':
            failed += 1
        elif status == 'running':
            running += 1
        skill = meta.get('skill', 'unknown')
        by_skill[skill] = by_skill.get(skill, 0) + 1
    return {'total': total, 'completed': completed, 'failed': failed,
            'running': running, 'by_skill': by_skill}


def _count_analyses(date_str):
    analyses_root = config.ANALYSES_DIR
    if not analyses_root.exists():
        return {'total': 0, 'by_type': {}, 'findings': {}}
    total = 0
    by_type = {}
    errors = warnings = info = 0
    for atype_dir in analyses_root.iterdir():
        if not atype_dir.is_dir():
            continue
        atype = atype_dir.name
        count = 0
        for f in atype_dir.iterdir():
            if f.suffix != '.yaml':
                continue
            try:
                with open(f) as fh:
                    meta = yaml.safe_load(fh) or {}
            except Exception:
                continue
            if not meta.get('created_at', '').startswith(date_str):
                continue
            count += 1
            summary = meta.get('summary', {})
            errors += summary.get('errors', 0)
            warnings += summary.get('warnings', 0)
            info += summary.get('info', 0)
        if count > 0:
            by_type[atype] = count
            total += count
    return {'total': total, 'by_type': by_type,
            'findings': {'errors': errors, 'warnings': warnings, 'info': info}}


def _integration_status():
    result = {}
    for name in ('jira', 'github', 'gerrit'):
        cache_file = config.CACHE_DIR / f'{name}_data.json'
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                result[name] = {
                    'status': 'live' if data else 'empty',
                    'count': len(data) if isinstance(data, list) else 0,
                }
            except Exception:
                result[name] = {'status': 'error', 'count': 0}
        else:
            result[name] = {'status': 'demo', 'count': 0}
    return result


def _count_users():
    if not config.USERS_FILE.exists():
        return {'total': 0, 'active': 0}
    try:
        with open(config.USERS_FILE) as f:
            users = yaml.safe_load(f) or {}
    except Exception:
        return {'total': 0, 'active': 0}
    total = len(users)
    active = sum(1 for u in users.values()
                 if u.get('is_active', True))
    return {'total': total, 'active': active}


def list_snapshots(limit=30):
    if not config.HISTORY_DIR.exists():
        return []
    items = []
    for f in config.HISTORY_DIR.iterdir():
        if f.suffix == '.yaml':
            try:
                with open(f) as fh:
                    snap = yaml.safe_load(fh)
                if snap:
                    items.append(snap)
            except Exception:
                pass
    items.sort(key=lambda x: x.get('date', ''), reverse=True)
    return items[:limit]


def get_snapshot(date_str):
    path = config.HISTORY_DIR / f'{date_str}.yaml'
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def compute_trends(days=7):
    snapshots = list_snapshots(limit=days + 1)
    if not snapshots:
        return _empty_trends()

    today = snapshots[0]
    yesterday = snapshots[1] if len(snapshots) > 1 else {}

    t_exec = today.get('executions', {}).get('total', 0)
    y_exec = yesterday.get('executions', {}).get('total', 0)
    t_anal = today.get('analyses', {}).get('total', 0)
    y_anal = yesterday.get('analyses', {}).get('total', 0)

    t_pass = _pass_rate(today)
    y_pass = _pass_rate(yesterday)

    daily_execs = []
    daily_analyses = []
    daily_labels = []
    for snap in reversed(snapshots[:days]):
        daily_labels.append(snap.get('date', '?')[-5:])
        daily_execs.append(snap.get('executions', {}).get('total', 0))
        daily_analyses.append(snap.get('analyses', {}).get('total', 0))

    return {
        'exec_delta': t_exec - y_exec,
        'exec_arrow': _arrow(t_exec - y_exec),
        'analysis_delta': t_anal - y_anal,
        'analysis_arrow': _arrow(t_anal - y_anal),
        'pass_rate_delta': round(t_pass - y_pass, 1),
        'pass_rate_arrow': _arrow(t_pass - y_pass),
        'today_execs': t_exec,
        'today_analyses': t_anal,
        'today_pass_rate': round(t_pass, 1),
        'daily_execs': daily_execs,
        'daily_analyses': daily_analyses,
        'daily_labels': daily_labels,
        'has_data': True,
    }


def _pass_rate(snapshot):
    execs = snapshot.get('executions', {})
    total = execs.get('total', 0)
    if total == 0:
        return 0.0
    completed = execs.get('completed', 0)
    return (completed / total) * 100


def _arrow(delta):
    if delta > 0:
        return 'up'
    elif delta < 0:
        return 'down'
    return 'flat'


def _empty_trends():
    return {
        'exec_delta': 0, 'exec_arrow': 'flat',
        'analysis_delta': 0, 'analysis_arrow': 'flat',
        'pass_rate_delta': 0.0, 'pass_rate_arrow': 'flat',
        'today_execs': 0, 'today_analyses': 0, 'today_pass_rate': 0.0,
        'daily_execs': [], 'daily_analyses': [],
        'daily_labels': [], 'has_data': False,
    }


DEMO_SNAPSHOTS = [
    {'executions': {'total': 6, 'completed': 5, 'failed': 1, 'running': 0,
                    'by_skill': {'test-operator': 3, 'debug-operator': 2, 'code-style': 1}},
     'analyses': {'total': 3, 'by_type': {'log': 1, 'code-flow': 1, 'style': 1},
                  'findings': {'errors': 2, 'warnings': 5, 'info': 4}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 8, 'completed': 7, 'failed': 1, 'running': 0,
                    'by_skill': {'test-operator': 4, 'explain-flow': 2, 'debug-operator': 2}},
     'analyses': {'total': 4, 'by_type': {'log': 2, 'code-flow': 1, 'style': 1},
                  'findings': {'errors': 3, 'warnings': 8, 'info': 5}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 5, 'completed': 5, 'failed': 0, 'running': 0,
                    'by_skill': {'test-operator': 2, 'code-style': 2, 'explain-flow': 1}},
     'analyses': {'total': 2, 'by_type': {'log': 1, 'style': 1},
                  'findings': {'errors': 1, 'warnings': 3, 'info': 2}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 10, 'completed': 8, 'failed': 2, 'running': 0,
                    'by_skill': {'test-operator': 5, 'debug-operator': 3, 'code-style': 2}},
     'analyses': {'total': 5, 'by_type': {'log': 2, 'code-flow': 2, 'style': 1},
                  'findings': {'errors': 5, 'warnings': 12, 'info': 8}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 7, 'completed': 6, 'failed': 1, 'running': 0,
                    'by_skill': {'test-operator': 3, 'explain-flow': 2, 'debug-operator': 1, 'code-style': 1}},
     'analyses': {'total': 3, 'by_type': {'log': 1, 'code-flow': 1, 'style': 1},
                  'findings': {'errors': 2, 'warnings': 6, 'info': 4}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 4, 'completed': 4, 'failed': 0, 'running': 0,
                    'by_skill': {'test-operator': 2, 'debug-operator': 1, 'explain-flow': 1}},
     'analyses': {'total': 2, 'by_type': {'log': 1, 'code-flow': 1},
                  'findings': {'errors': 1, 'warnings': 3, 'info': 2}},
     'users': {'total': 2, 'active': 2}},

    {'executions': {'total': 9, 'completed': 8, 'failed': 1, 'running': 0,
                    'by_skill': {'test-operator': 4, 'debug-operator': 2, 'code-style': 2, 'explain-flow': 1}},
     'analyses': {'total': 4, 'by_type': {'log': 2, 'code-flow': 1, 'style': 1},
                  'findings': {'errors': 3, 'warnings': 7, 'info': 5}},
     'users': {'total': 2, 'active': 2}},
]


def seed_demo_history(user='system'):
    config.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    seeded = []
    for i, demo in enumerate(DEMO_SNAPSHOTS):
        d = today - timedelta(days=6 - i)
        snap = {
            'date': d.isoformat(),
            'generated_at': datetime.combine(
                d, datetime.min.time().replace(hour=17, minute=30)
            ).isoformat(timespec='seconds'),
            'generated_by': user,
            'integrations': {
                'jira': {'status': 'demo', 'count': 15},
                'github': {'status': 'demo', 'count': 8},
                'gerrit': {'status': 'demo', 'count': 12},
            },
        }
        snap.update(demo)
        path = config.HISTORY_DIR / f'{d.isoformat()}.yaml'
        with open(path, 'w') as f:
            yaml.dump(snap, f, default_flow_style=False)
        seeded.append(d.isoformat())
    return seeded
