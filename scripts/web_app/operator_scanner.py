import os
import subprocess
from pathlib import Path


def scan_operators(repos_config):
    """Scan configured operator repo paths and return status list."""
    results = []
    for repo in repos_config:
        path = Path(repo).expanduser()
        if not path.exists():
            results.append({
                'name': path.name, 'path': str(path),
                'status': 'not_found',
                'has_gomod': False, 'has_makefile': False,
                'controllers': 0, 'crds': 0,
                'branch': '', 'last_commit': '',
            })
            continue

        has_gomod = (path / 'go.mod').exists()
        has_makefile = (path / 'Makefile').exists()

        controllers = 0
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs
                       if d not in ('.git', 'vendor', '.worktrees',
                                    'node_modules')]
            for f in files:
                if f.endswith('_controller.go') or \
                   f.endswith('_reconciler.go'):
                    controllers += 1

        crd_count = 0
        crd_base = path / 'config' / 'crd' / 'bases'
        if crd_base.exists():
            crd_count = len(list(crd_base.glob('*.yaml')))

        branch = ''
        last_commit = ''
        try:
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=str(path), stderr=subprocess.DEVNULL
            ).decode().strip()
            last_commit = subprocess.check_output(
                ['git', 'log', '-1', '--format=%ci'],
                cwd=str(path), stderr=subprocess.DEVNULL
            ).decode().strip()[:10]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        results.append({
            'name': path.name,
            'path': str(path),
            'status': 'ok',
            'has_gomod': has_gomod,
            'has_makefile': has_makefile,
            'controllers': controllers,
            'crds': crd_count,
            'branch': branch,
            'last_commit': last_commit,
        })

    return results
