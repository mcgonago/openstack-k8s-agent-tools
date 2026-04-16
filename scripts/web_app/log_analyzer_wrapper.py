import json
import subprocess
import tempfile
import uuid
import yaml
from datetime import datetime
from pathlib import Path

from . import config

DEMO_LOG = """\
2026-04-16T10:00:01.234Z INFO  controller/nova Starting reconciliation {"nova": "openstack/nova"}
2026-04-16T10:00:01.456Z INFO  controller/nova Fetching Nova resource {"nova": "openstack/nova"}
2026-04-16T10:00:02.100Z WARN  controller/nova Service not ready, requeuing {"service": "nova-api", "requeue": "30s"}
2026-04-16T10:00:02.500Z ERROR controller/nova Failed to create deployment {"error": "context deadline exceeded"}
2026-04-16T10:00:03.001Z INFO  controller/nova Reconciliation complete {"nova": "openstack/nova", "duration": "1.767s"}
2026-04-16T10:00:05.200Z WARN  controller/nova Requeue after backoff {"nova": "openstack/nova", "backoff": "30s"}
2026-04-16T10:00:10.100Z ERROR controller/nova Reconcile error {"nova": "openstack/nova", "error": "timeout waiting for condition"}
2026-04-16T10:00:10.500Z INFO  controller/nova Retrying reconciliation {"nova": "openstack/nova", "attempt": 2}
2026-04-16T10:00:11.300Z WARN  controller/nova Resource version conflict {"nova": "openstack/nova"}
2026-04-16T10:00:12.000Z INFO  controller/nova Successfully reconciled {"nova": "openstack/nova", "result": "ok"}
2026-04-16T10:00:15.000Z WARN  controller/keystone Endpoint not responding {"endpoint": "keystone-api", "timeout": "5s"}
2026-04-16T10:00:16.200Z ERROR controller/glance CRD validation failed {"crd": "GlanceAPI", "error": "spec.replicas must be positive"}
2026-04-16T10:00:17.500Z INFO  controller/cinder Volume backup controller started {"cinder": "openstack/cinder"}
2026-04-16T10:00:18.000Z WARN  controller/neutron Webhook admission timeout {"webhook": "validate-neutronapi", "duration": "8s"}
2026-04-16T10:00:19.100Z INFO  controller/nova Status update successful {"nova": "openstack/nova", "condition": "Ready=True"}
"""


def analyze_logs(log_text, user='anonymous'):
    analysis_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(log_text)
        temp_path = f.name

    plugin_root = Path(config.PLUGIN_PATH)
    cmd = ['python3', 'lib/log-analyzer.py', temp_path]

    try:
        proc = subprocess.run(
            cmd, cwd=str(plugin_root), capture_output=True,
            text=True, timeout=60
        )
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {'raw_output': proc.stdout, 'stderr': proc.stderr,
                      'parse_error': True}
    except subprocess.TimeoutExpired:
        result = {'error': 'Analysis timed out (60s)'}
    except Exception as e:
        result = {'error': str(e)}
    finally:
        Path(temp_path).unlink(missing_ok=True)

    summary = _build_summary(result, log_text)
    _save_analysis(analysis_id, 'log', '(pasted)', user, summary)
    return {'id': analysis_id, 'summary': summary, 'result': result,
            'lines': len(log_text.splitlines())}


def _build_summary(result, log_text=''):
    if isinstance(result, dict) and not result.get('error') and not result.get('parse_error'):
        findings = result.get('findings', [])
        return {
            'errors': sum(1 for f in findings if f.get('severity') == 'error'),
            'warnings': sum(1 for f in findings if f.get('severity') == 'warning'),
            'info': sum(1 for f in findings if f.get('severity') == 'info'),
            'total': len(findings),
            'metrics': result.get('metrics', {}),
        }
    lines = log_text.splitlines() if log_text else []
    errors = sum(1 for l in lines if 'ERROR' in l)
    warnings = sum(1 for l in lines if 'WARN' in l)
    infos = sum(1 for l in lines if 'INFO' in l)
    return {
        'errors': errors, 'warnings': warnings, 'info': infos,
        'total': errors + warnings + infos, 'metrics': {},
        'fallback': True,
    }


def _save_analysis(analysis_id, atype, target, user, summary):
    analyses_dir = config.ANALYSES_DIR / atype
    analyses_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'id': analysis_id,
        'type': atype,
        'target': target,
        'user': user,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'summary': summary,
    }
    with open(analyses_dir / f'{analysis_id}.yaml', 'w') as f:
        yaml.dump(meta, f, default_flow_style=False)


def get_demo_log():
    return DEMO_LOG


def list_analyses(limit=20):
    analyses_dir = config.ANALYSES_DIR / 'log'
    if not analyses_dir.exists():
        return []
    items = []
    for f in analyses_dir.iterdir():
        if f.suffix == '.yaml':
            try:
                with open(f) as fh:
                    items.append(yaml.safe_load(fh))
            except Exception:
                pass
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return items[:limit]
