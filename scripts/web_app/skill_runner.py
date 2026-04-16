import subprocess
import uuid
import yaml
from datetime import datetime
from pathlib import Path

from . import config

SKILL_SCRIPTS = {
    'debug-operator': {
        'cmd': ['bash', 'lib/dev-workflow.sh'],
        'arg_name': 'operator_path',
        'description': 'Debug Go operator code with diagnostics',
    },
    'test-operator': {
        'cmd': ['bash', 'lib/test-workflow.sh'],
        'arg_name': 'operator_path',
        'description': 'Run operator test suites',
    },
    'code-style': {
        'cmd': ['python3', 'lib/style-analyzer.py'],
        'arg_name': 'operator_path',
        'description': 'Analyze Go code style and conventions',
    },
    'analyze-logs': {
        'cmd': ['python3', 'lib/log-analyzer.py'],
        'arg_name': 'log_path',
        'description': 'Analyze operator pod logs for patterns',
    },
    'explain-flow': {
        'cmd': ['python3', 'lib/code-parser.py'],
        'arg_name': 'file_path',
        'description': 'Parse and explain Go code flow',
    },
}

AI_SKILLS = ['feature', 'task-executor', 'code-review',
             'backport-review', 'jira']


def get_executable_skills():
    return [
        {'name': name, 'description': info['description'],
         'arg_name': info['arg_name'], 'executable': True}
        for name, info in SKILL_SCRIPTS.items()
    ]


def get_executable_skill_names():
    return set(SKILL_SCRIPTS.keys())


def _write_meta(exec_dir, meta):
    with open(exec_dir / 'meta.yaml', 'w') as f:
        yaml.dump(meta, f, default_flow_style=False)


def _read_meta(exec_dir):
    meta_file = exec_dir / 'meta.yaml'
    if not meta_file.exists():
        return {}
    with open(meta_file) as f:
        return yaml.safe_load(f) or {}


def _compute_duration(meta):
    if not meta.get('started_at'):
        return '--'
    try:
        started = datetime.fromisoformat(meta['started_at'])
    except (ValueError, TypeError):
        return '--'
    if not meta.get('finished_at'):
        delta = datetime.now() - started
        return f'{int(delta.total_seconds())}s...'
    try:
        finished = datetime.fromisoformat(meta['finished_at'])
    except (ValueError, TypeError):
        return '--'
    secs = int((finished - started).total_seconds())
    if secs < 60:
        return f'{secs}s'
    return f'{secs // 60}m {secs % 60}s'


def run_skill(skill, target_path, user, extra_args=None):
    if skill not in SKILL_SCRIPTS:
        raise ValueError(f'Skill {skill} is not executable')

    target = Path(target_path).expanduser()
    if not target.exists():
        raise FileNotFoundError(f'Path does not exist: {target}')

    exec_id = str(uuid.uuid4())
    exec_dir = config.EXECUTIONS_DIR / exec_id
    exec_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        'id': exec_id,
        'skill': skill,
        'target_path': str(target),
        'args': extra_args or {},
        'status': 'queued',
        'user': user,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'started_at': '',
        'finished_at': '',
        'exit_code': None,
        'error': '',
    }
    _write_meta(exec_dir, meta)

    script_info = SKILL_SCRIPTS[skill]
    cmd = script_info['cmd'] + [str(target)]

    from .job_queue import queue
    queue.submit(exec_id, _execute_subprocess, exec_id, cmd)

    return exec_id


def _execute_subprocess(exec_id, cmd):
    exec_dir = config.EXECUTIONS_DIR / exec_id
    meta = _read_meta(exec_dir)
    meta['status'] = 'running'
    meta['started_at'] = datetime.now().isoformat(timespec='seconds')
    _write_meta(exec_dir, meta)

    log_path = exec_dir / 'output.log'
    plugin_root = Path(config.PLUGIN_PATH)
    timeout = getattr(config, 'EXECUTION_TIMEOUT', 300)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(plugin_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        max_log_bytes = 1_000_000
        written = 0
        truncated = False
        with open(log_path, 'w') as log_file:
            log_file.write(f'$ {" ".join(cmd)}\n')
            written += len(cmd.__str__())
            for line in proc.stdout:
                if not truncated and written < max_log_bytes:
                    log_file.write(line)
                    log_file.flush()
                    written += len(line)
                elif not truncated:
                    log_file.write('\n[LOG TRUNCATED -- exceeded 1MB]\n')
                    log_file.flush()
                    truncated = True

        proc.wait(timeout=timeout)
        exit_code = proc.returncode

        meta['status'] = 'completed' if exit_code == 0 else 'failed'
        meta['exit_code'] = exit_code

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        meta['status'] = 'failed'
        meta['error'] = f'Execution timed out ({timeout}s)'
        meta['exit_code'] = -1
        with open(log_path, 'a') as log_file:
            log_file.write(f'\n[TIMEOUT -- killed after {timeout}s]\n')

    except Exception as e:
        meta['status'] = 'failed'
        meta['error'] = str(e)
        meta['exit_code'] = -1
        with open(log_path, 'a') as log_file:
            log_file.write(f'\n[ERROR: {e}]\n')

    meta['finished_at'] = datetime.now().isoformat(timespec='seconds')
    _write_meta(exec_dir, meta)


def get_execution(exec_id):
    exec_dir = config.EXECUTIONS_DIR / exec_id
    if not exec_dir.exists():
        return None
    meta = _read_meta(exec_dir)
    meta['duration'] = _compute_duration(meta)
    meta['short_id'] = meta.get('id', exec_id)[:8]
    meta['target_name'] = Path(meta.get('target_path', '')).name
    return meta


def list_executions(limit=50, offset=0):
    exec_root = config.EXECUTIONS_DIR
    if not exec_root.exists():
        return []
    execs = []
    for d in exec_root.iterdir():
        if d.is_dir() and (d / 'meta.yaml').exists():
            meta = _read_meta(d)
            meta['duration'] = _compute_duration(meta)
            meta['short_id'] = meta.get('id', d.name)[:8]
            meta['target_name'] = Path(meta.get('target_path', '')).name
            execs.append(meta)
    execs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return execs[offset:offset + limit]


def get_execution_log(exec_id):
    log_path = config.EXECUTIONS_DIR / exec_id / 'output.log'
    if not log_path.exists():
        return ''
    return log_path.read_text()


def cancel_execution(exec_id):
    from .job_queue import queue
    cancelled = queue.cancel(exec_id)
    if cancelled:
        exec_dir = config.EXECUTIONS_DIR / exec_id
        meta = _read_meta(exec_dir)
        meta['status'] = 'cancelled'
        meta['finished_at'] = datetime.now().isoformat(timespec='seconds')
        _write_meta(exec_dir, meta)
    return cancelled


def get_total_executions():
    exec_root = config.EXECUTIONS_DIR
    if not exec_root.exists():
        return 0
    return sum(1 for d in exec_root.iterdir()
               if d.is_dir() and (d / 'meta.yaml').exists())
