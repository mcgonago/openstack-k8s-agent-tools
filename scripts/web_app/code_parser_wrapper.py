import json
import subprocess
import uuid
import yaml
from datetime import datetime
from pathlib import Path

from . import config


def analyze_code_flow(directory_path, user='anonymous'):
    analysis_id = str(uuid.uuid4())
    target = Path(directory_path).expanduser()

    if not target.exists():
        return {'id': analysis_id, 'error': f'Path not found: {target}',
                'result': {}, 'summary': {}, 'target': str(target)}

    plugin_root = Path(config.PLUGIN_PATH)
    cmd = ['python3', 'lib/code-parser.py', str(target)]

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

    summary = _build_summary(result)
    _save_analysis(analysis_id, 'code-flow', str(target), user, summary)
    return {'id': analysis_id, 'summary': summary, 'result': result,
            'target': str(target)}


def _build_summary(result):
    if isinstance(result, dict) and not result.get('error') and not result.get('parse_error'):
        reconcilers = result.get('reconcilers', [])
        total_flows = sum(len(r.get('flows', [])) for r in reconcilers)
        total_steps = sum(
            len(f.get('steps', []))
            for r in reconcilers for f in r.get('flows', [])
        )
        total_errors = sum(
            len(f.get('errorHandling', []))
            for r in reconcilers for f in r.get('flows', [])
        )
        return {
            'controllers': len(result.get('controllers', [])),
            'reconcilers': len(reconcilers),
            'flows': total_flows,
            'steps': total_steps,
            'error_patterns': total_errors,
            'crds': len(result.get('crds', [])),
            'webhooks': len(result.get('webhooks', [])),
            'has_main': result.get('main') is not None,
        }
    return {'controllers': 0, 'reconcilers': 0, 'flows': 0,
            'steps': 0, 'error_patterns': 0, 'crds': 0,
            'webhooks': 0, 'has_main': False}


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


def list_analyses(limit=20):
    analyses_dir = config.ANALYSES_DIR / 'code-flow'
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
