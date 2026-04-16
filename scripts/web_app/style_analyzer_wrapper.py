import json
import subprocess
import uuid
import yaml
from datetime import datetime
from pathlib import Path

from . import config


def analyze_style(file_path, user='anonymous'):
    analysis_id = str(uuid.uuid4())
    target = Path(file_path).expanduser()

    if not target.exists():
        return {'id': analysis_id, 'error': f'Path not found: {target}',
                'result': {}, 'summary': {}, 'target': str(target)}

    plugin_root = Path(config.PLUGIN_PATH)
    cmd = ['python3', 'lib/style-analyzer.py', str(target)]

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
    _save_analysis(analysis_id, 'style', str(target), user, summary)
    return {'id': analysis_id, 'summary': summary, 'result': result,
            'target': str(target)}


def _build_summary(result):
    if isinstance(result, dict) and not result.get('error') and not result.get('parse_error'):
        issues = result.get('issues', [])
        suggestions = result.get('suggestions', [])
        modernizations = result.get('modernizations', [])
        return {
            'issues': len(issues),
            'warnings': sum(1 for i in issues if i.get('severity') in ('warn', 'warning')),
            'info': sum(1 for i in issues if i.get('severity') == 'info'),
            'suggestions': len(suggestions),
            'modernizations': len(modernizations),
            'score': result.get('score', result.get('overall_score', None)),
        }
    return {'issues': 0, 'warnings': 0, 'info': 0,
            'suggestions': 0, 'modernizations': 0, 'score': None}


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
    analyses_dir = config.ANALYSES_DIR / 'style'
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
