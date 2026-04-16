import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


def get_plans_root():
    env = os.environ.get('K8S_AGENT_TOOLS_PLANS_ROOT')
    if env:
        return Path(env).expanduser()
    return Path.home() / '.openstack-k8s-agents-plans'


def _mtime_iso(path):
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).isoformat(timespec='seconds')
    except OSError:
        return ''


def _time_ago(iso_str):
    if not iso_str:
        return '--'
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    delta = datetime.now() - dt
    if delta < timedelta(minutes=1):
        return 'just now'
    if delta < timedelta(hours=1):
        m = int(delta.total_seconds() / 60)
        return f'{m}m ago'
    if delta < timedelta(days=1):
        h = int(delta.total_seconds() / 3600)
        return f'{h}h ago'
    d = delta.days
    if d == 1:
        return 'yesterday'
    return f'{d}d ago'


def _read_state(operator_dir):
    state_file = operator_dir / 'state.json'
    if not state_file.exists():
        return {'active_tasks': [], 'completed_plans': [], 'worktrees': {}}
    try:
        with open(state_file) as f:
            data = json.load(f)
        data.setdefault('active_tasks', [])
        data.setdefault('completed_plans', [])
        data.setdefault('worktrees', {})
        return data
    except (json.JSONDecodeError, OSError):
        return {'active_tasks': [], 'completed_plans': [], 'worktrees': {}}


def _count_checkboxes(text):
    done = len(re.findall(r'- \[x\]', text, re.IGNORECASE))
    pending = len(re.findall(r'- \[ \]', text))
    total = done + pending
    pct = int((done / total) * 100) if total else 0
    return done, total, pct


def _plan_title(text):
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            title = line.lstrip('# ').strip()
            title = re.sub(r'^Feature Plan:\s*', '', title)
            return title
    return ''


def _plan_status(filename, state):
    active_files = {t.get('plan', '') for t in state.get('active_tasks', [])}
    completed_files = {c.get('plan', '')
                       for c in state.get('completed_plans', [])}
    if filename in active_files:
        return 'active'
    if filename in completed_files:
        return 'done'
    return 'pending'


def scan_plans(root=None):
    """Return list of operator summary dicts, sorted by last activity."""
    if root is None:
        root = get_plans_root()
    root = Path(root)
    if not root.exists():
        return []

    operators = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        plans = list(entry.glob('*-plan.md'))
        if not plans and not (entry / 'MEMORY.md').exists():
            continue

        state = _read_state(entry)
        tasks_done = 0
        tasks_total = 0
        last_mtime = ''

        for p in plans:
            try:
                text = p.read_text()
            except OSError:
                continue
            d, t, _ = _count_checkboxes(text)
            tasks_done += d
            tasks_total += t
            mt = _mtime_iso(p)
            if mt > last_mtime:
                last_mtime = mt

        mem_mt = _mtime_iso(entry / 'MEMORY.md') if (entry / 'MEMORY.md').exists() else ''
        if mem_mt > last_mtime:
            last_mtime = mem_mt

        pct = int((tasks_done / tasks_total) * 100) if tasks_total else 0
        operators.append({
            'name': entry.name,
            'plan_count': len(plans),
            'active_tasks': len(state.get('active_tasks', [])),
            'completed_plans': len(state.get('completed_plans', [])),
            'tasks_done': tasks_done,
            'tasks_total': tasks_total,
            'progress_percent': pct,
            'last_activity': last_mtime,
            'last_activity_ago': _time_ago(last_mtime),
        })

    operators.sort(key=lambda o: o['last_activity'], reverse=True)
    return operators


def get_operator_plans(root, operator):
    """Return list of plan summaries for one operator."""
    root = Path(root)
    op_dir = root / operator
    if not op_dir.exists():
        return []

    state = _read_state(op_dir)
    plans = []
    for p in sorted(op_dir.glob('*-plan.md')):
        try:
            text = p.read_text()
        except OSError:
            continue
        d, t, pct = _count_checkboxes(text)
        title = _plan_title(text)
        plans.append({
            'filename': p.name,
            'slug': p.stem,
            'title': title or p.stem,
            'tasks_done': d,
            'tasks_total': t,
            'progress_percent': pct,
            'status': _plan_status(p.name, state),
            'last_modified': _mtime_iso(p),
            'last_modified_ago': _time_ago(_mtime_iso(p)),
        })
    plans.sort(key=lambda x: x['last_modified'], reverse=True)
    return plans


def parse_plan_tasks(plan_path):
    """Parse a plan file into groups of tasks with progress stats."""
    plan_path = Path(plan_path)
    try:
        text = plan_path.read_text()
    except OSError:
        return None

    title = _plan_title(text)
    done_count, total_count, pct = _count_checkboxes(text)

    strategy = ''
    strat_match = re.search(
        r'##\s*Approved Strategy\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if strat_match:
        strategy = strat_match.group(1).strip()[:500]

    outcome = ''
    out_match = re.search(r'##\s*Outcome\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if out_match:
        outcome = out_match.group(1).strip()[:500]

    groups = []
    current_group = {'name': 'Tasks', 'tasks': []}
    for line in text.split('\n'):
        group_match = re.match(r'^###\s+(Group\s+\d+.*)', line)
        if group_match:
            if current_group['tasks']:
                groups.append(current_group)
            current_group = {'name': group_match.group(1).strip(), 'tasks': []}
            continue
        task_match = re.match(
            r'^- \[([ xX])\]\s+\*\*(.+?)\*\*', line)
        if task_match:
            current_group['tasks'].append({
                'name': task_match.group(2).strip(),
                'done': task_match.group(1).lower() == 'x',
            })
            continue
        dep_match = re.match(r'^\s+Dependencies?:\s*(.*)', line)
        if dep_match and current_group['tasks']:
            current_group['tasks'][-1]['dependencies'] = dep_match.group(1).strip()

    if current_group['tasks']:
        groups.append(current_group)

    return {
        'title': title,
        'strategy': strategy,
        'outcome': outcome,
        'groups': groups,
        'tasks_done': done_count,
        'tasks_total': total_count,
        'progress_percent': pct,
        'raw_body': text,
    }


def read_memory(root, operator):
    """Read MEMORY.md for an operator. Returns dict with content + metadata."""
    mem_path = Path(root) / operator / 'MEMORY.md'
    if not mem_path.exists():
        return {'exists': False, 'content': '', 'last_modified': '',
                'line_count': 0}
    try:
        content = mem_path.read_text()
    except OSError:
        return {'exists': False, 'content': '', 'last_modified': '',
                'line_count': 0}
    return {
        'exists': True,
        'content': content,
        'last_modified': _mtime_iso(mem_path),
        'last_modified_ago': _time_ago(_mtime_iso(mem_path)),
        'line_count': content.count('\n') + 1,
    }


def read_state_json(root, operator):
    """Read state.json for an operator."""
    state = _read_state(Path(root) / operator)
    state_file = Path(root) / operator / 'state.json'
    return {
        'exists': state_file.exists(),
        'active_tasks': state.get('active_tasks', []),
        'completed_plans': state.get('completed_plans', []),
        'worktrees': state.get('worktrees', {}),
        'raw': state,
    }


def compute_aggregate_progress(root=None):
    """Total tasks done / total across all plans."""
    if root is None:
        root = get_plans_root()
    operators = scan_plans(root)
    done = sum(o['tasks_done'] for o in operators)
    total = sum(o['tasks_total'] for o in operators)
    pct = int((done / total) * 100) if total else 0
    return {'done': done, 'total': total, 'percent': pct}


def get_last_activity(root=None):
    """Most recent file change across all plans."""
    if root is None:
        root = get_plans_root()
    operators = scan_plans(root)
    if not operators:
        return ''
    return operators[0]['last_activity']


def get_last_activity_ago(root=None):
    return _time_ago(get_last_activity(root))


# ---------------------------------------------------------------------------
# Demo data seeding
# ---------------------------------------------------------------------------

_DEMO_PLAN_NOVA_ACTIVE = """\
# Feature Plan: OSPRH-2345 — Add monitoring dashboard

## Input Source
Jira ticket OSPRH-2345: "Add Prometheus metrics and Grafana dashboard for Nova operator"

## Approved Strategy
Strategy B: Leverage the existing lib-common MetricsService helper to expose
reconciler-level metrics. Add PrometheusRule CRD for alerting. Grafana
dashboard JSON shipped as ConfigMap.

## Task Breakdown

### Group 1: API Foundation
- [x] **Task 1.1: Add MonitoringSpec to NovaSpec CRD**
  Dependencies: none
- [x] **Task 1.2: Run controller-gen to regenerate CRDs**
  Dependencies: Task 1.1
- [x] **Task 1.3: Add MonitoringSpec unit tests**
  Dependencies: Task 1.1

### Group 2: Reconciler Integration
- [x] **Task 2.1: Wire MetricsService into NovaReconciler**
  Dependencies: Task 1.2
- [x] **Task 2.2: Add reconciler metrics (reconcile_duration, errors_total)**
  Dependencies: Task 2.1
- [x] **Task 2.3: Add reconciler metrics unit tests**
  Dependencies: Task 2.2

### Group 3: PrometheusRule + Dashboard
- [ ] **Task 3.1: Create PrometheusRule CRD for Nova alerts**
  Dependencies: Task 2.2
- [ ] **Task 3.2: Create Grafana dashboard JSON ConfigMap**
  Dependencies: Task 2.2
- [ ] **Task 3.3: Add monitoring e2e test**
  Dependencies: Task 3.1, Task 3.2
- [ ] **Task 3.4: Update documentation**
  Dependencies: Task 3.3

## Outcome
(in progress)
"""

_DEMO_PLAN_NOVA_DONE = """\
# Feature Plan: OSPRH-1111 — Fix CRD validation webhook

## Approved Strategy
Strategy A: Add admission webhook for CRD validation with proper error messages.

## Task Breakdown

### Group 1: Webhook Setup
- [x] **Task 1.1: Add webhook handler scaffold**
  Dependencies: none
- [x] **Task 1.2: Implement validation logic**
  Dependencies: Task 1.1

### Group 2: Testing
- [x] **Task 2.1: Add unit tests for validation**
  Dependencies: Task 1.2
- [x] **Task 2.2: Add e2e test for webhook rejection**
  Dependencies: Task 2.1

## Outcome
Webhook deployed and tested. All CRD submissions now validated with clear error messages.
Merged in PR #847.
"""

_DEMO_MEMORY_NOVA = """\
## Active Work

- OSPRH-2345: Adding monitoring dashboard for Nova operator
  Strategy: Using lib-common MetricsService (Strategy B)
  Status: Group 2 complete, starting Group 3 (PrometheusRule + Dashboard)

## Completed Work

- OSPRH-1111: Fixed CRD validation webhook (PR #847 merged)

## Discovered Patterns

- lib-common has MetricsService helper at pkg/metrics/service.go
- All operators share test fixtures from openstack-operator/tests/functional/base
- PrometheusRule CRDs should go in config/prometheus/ not config/crd/bases/

## Key Decisions

- Use PrometheusRule CRD instead of ServiceMonitor for alerting
- Grafana dashboard shipped as ConfigMap (not operator-managed resource)
- Metrics namespace: openstack_nova_ prefix for all custom metrics

## Conventions

- Test files named *_test.go in same package
- Mock clients use fake.NewClientBuilder() from controller-runtime
- Feature branches named feature/OSPRH-NNNN
"""

_DEMO_STATE_NOVA = {
    "active_tasks": [
        {
            "plan": "2026-04-11-OSPRH-2345-plan.md",
            "task": "Task 3.1: Create PrometheusRule CRD for Nova alerts",
            "worktree": ".worktrees/OSPRH-2345",
            "started": "2026-04-15T14:30:00",
            "session_id": "demo-session-001"
        }
    ],
    "completed_plans": [
        {
            "plan": "2026-04-08-OSPRH-1111-plan.md",
            "completed_at": "2026-04-09T16:45:00"
        }
    ],
    "worktrees": {
        "OSPRH-2345": {
            "path": ".worktrees/OSPRH-2345",
            "branch": "feature/OSPRH-2345",
            "created": "2026-04-11T14:30:00"
        }
    }
}

_DEMO_PLAN_HORIZON = """\
# Feature Plan: OSPRH-1234 — Add RBAC policy override support

## Approved Strategy
Strategy A: Add PolicyOverride field to HorizonSpec allowing custom policy.yaml injection.

## Task Breakdown

### Group 1: API Changes
- [x] **Task 1.1: Add PolicyOverride to HorizonSpec**
  Dependencies: none
- [x] **Task 1.2: Regenerate CRDs**
  Dependencies: Task 1.1

### Group 2: Reconciler + Tests
- [ ] **Task 2.1: Mount policy.yaml from ConfigMap in reconciler**
  Dependencies: Task 1.2
- [ ] **Task 2.2: Add functional test for policy override**
  Dependencies: Task 2.1

## Outcome
(pending — paused for OSPRH-2345 priority work)
"""

_DEMO_MEMORY_HORIZON = """\
## Active Work

- OSPRH-1234: RBAC policy override for Horizon operator (paused)

## Discovered Patterns

- Horizon uses Apache as frontend proxy; policy.yaml must be volume-mounted
- ConfigMap data key must be "policy.yaml" (hardcoded in entrypoint.sh)

## Key Decisions

- Mount policy.yaml as subPath to avoid overwriting other config files
"""

_DEMO_STATE_HORIZON = {
    "active_tasks": [],
    "completed_plans": [],
    "worktrees": {}
}


def seed_demo_data(root=None):
    """Create sample operator directories with realistic plan data."""
    if root is None:
        root = get_plans_root()
    root = Path(root)

    nova = root / 'nova-operator'
    nova.mkdir(parents=True, exist_ok=True)
    (nova / '2026-04-11-OSPRH-2345-plan.md').write_text(_DEMO_PLAN_NOVA_ACTIVE)
    (nova / '2026-04-08-OSPRH-1111-plan.md').write_text(_DEMO_PLAN_NOVA_DONE)
    (nova / 'MEMORY.md').write_text(_DEMO_MEMORY_NOVA)
    with open(nova / 'state.json', 'w') as f:
        json.dump(_DEMO_STATE_NOVA, f, indent=2)

    horizon = root / 'horizon-operator'
    horizon.mkdir(parents=True, exist_ok=True)
    (horizon / '2026-04-10-OSPRH-1234-plan.md').write_text(_DEMO_PLAN_HORIZON)
    (horizon / 'MEMORY.md').write_text(_DEMO_MEMORY_HORIZON)
    with open(horizon / 'state.json', 'w') as f:
        json.dump(_DEMO_STATE_HORIZON, f, indent=2)
