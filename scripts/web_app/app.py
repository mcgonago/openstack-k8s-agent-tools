import os
import yaml
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import (Flask, render_template_string, request, redirect,
                   url_for, flash, session, jsonify, abort)
from werkzeug.security import generate_password_hash, check_password_hash

from . import config
from .skill_catalog import get_skill_catalog, get_skill_detail
from .operator_scanner import scan_operators
from .plan_monitor import (scan_plans, get_operator_plans, parse_plan_tasks,
                           read_memory, read_state_json,
                           compute_aggregate_progress, get_last_activity_ago,
                           seed_demo_data, get_plans_root)

app = Flask(__name__)
app.secret_key = os.environ.get('K8S_AGENT_TOOLS_SECRET',
                                secrets.token_hex(32))

# ---------------------------------------------------------------------------
# CSS theme — dark with orange/amber accent
# ---------------------------------------------------------------------------
CSS_THEME = """
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --accent: #f0883e;
    --accent-light: #f5a623;
    --accent-dim: #d18616;
    --success: #3fb950;
    --danger: #f85149;
    --warning: #d29922;
    --border: #30363d;
    --link: #f0883e;
    --header-bg: #010409;
    --card-bg: #161b22;
    --input-bg: #0d1117;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
}

a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

/* --- HEADER / NAV -------------------------------------------------------- */
.site-header {
    background: var(--header-bg);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex;
    align-items: center;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
}
.site-header .brand {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    margin-right: 32px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.site-header nav { display: flex; align-items: center; gap: 6px; flex: 1; }
.site-header nav a,
.site-header nav .dropdown > button {
    padding: 6px 14px;
    border-radius: 6px;
    color: var(--text-secondary);
    font-size: 14px;
    font-weight: 500;
    transition: all 0.15s;
    background: none;
    border: none;
    cursor: pointer;
    font-family: inherit;
}
.site-header nav a:hover,
.site-header nav .dropdown > button:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    text-decoration: none;
}
.site-header nav a.active {
    background: var(--bg-tertiary);
    color: var(--accent);
}

.dropdown { position: relative; }
.dropdown-menu {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 0;
    min-width: 220px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    z-index: 200;
}
.dropdown:hover .dropdown-menu,
.dropdown:focus-within .dropdown-menu { display: block; }
.dropdown-menu a {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    font-size: 14px;
    color: var(--text-primary);
}
.dropdown-menu a:hover {
    background: var(--bg-tertiary);
    text-decoration: none;
}
.dropdown-menu .dd-hint {
    font-size: 11px;
    color: var(--text-secondary);
}
.dropdown-menu hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 4px 0;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
}
.header-right .user-badge {
    font-size: 13px;
    color: var(--text-secondary);
    padding: 4px 12px;
    background: var(--bg-tertiary);
    border-radius: 20px;
}
.btn {
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.15s;
}
.btn:hover { background: var(--bg-secondary); border-color: var(--accent); }
.btn-primary {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
}
.btn-primary:hover { background: var(--accent-light); }
.btn-sm { padding: 4px 10px; font-size: 12px; }

/* --- MAIN CONTENT -------------------------------------------------------- */
.container { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }

/* Cards */
.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 16px;
}
.card h3 { color: var(--accent); margin-bottom: 8px; }
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
}

/* Stats row */
.stats-row {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    flex: 1;
    min-width: 180px;
    text-align: center;
}
.stat-card .stat-value {
    font-size: 36px;
    font-weight: 700;
    color: var(--accent);
    display: block;
}
.stat-card .stat-label {
    font-size: 13px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
th, td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid var(--border);
}
th {
    font-weight: 600;
    color: var(--text-secondary);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
tr:hover td { background: var(--bg-tertiary); }

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.badge-ok { background: #0d3820; color: var(--success); }
.badge-warn { background: #3b2e0a; color: var(--warning); }
.badge-err { background: #3d1214; color: var(--danger); }
.badge-accent { background: #3d2008; color: var(--accent); }

/* Forms */
.form-group { margin-bottom: 16px; }
.form-group label {
    display: block;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-secondary);
}
.form-group input[type="text"],
.form-group input[type="password"] {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--input-bg);
    color: var(--text-primary);
    font-size: 14px;
}
.form-group input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(240,136,62,0.2);
}

/* Flash messages */
.flash {
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 16px;
    font-size: 14px;
}
.flash-error { background: #3d1214; color: var(--danger); border: 1px solid #9e2a2b; }
.flash-success { background: #0d3820; color: var(--success); border: 1px solid #1a7f37; }

/* Splash page */
.splash {
    text-align: center;
    padding: 80px 24px;
}
.splash h1 {
    font-size: 48px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 16px;
}
.splash .tagline {
    font-size: 20px;
    color: var(--text-secondary);
    margin-bottom: 40px;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
}
.splash .cta-row {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
}

/* Skill detail */
.skill-body {
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    max-height: 500px;
    overflow-y: auto;
}

/* Footer */
.site-footer {
    text-align: center;
    padding: 24px;
    font-size: 12px;
    color: var(--text-secondary);
    border-top: 1px solid var(--border);
    margin-top: 48px;
}

/* Pulse */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.pulse { animation: pulse 2s infinite; }

/* Phase 2: Progress bars */
.progress-bar {
    background: var(--bg-tertiary);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
    flex: 1;
}
.progress-fill {
    background: var(--accent);
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}
.progress-100 .progress-fill {
    background: var(--success);
}
.progress-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.progress-pct {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    min-width: 42px;
    text-align: right;
}

/* Phase 2: Plan status badges */
.badge-active {
    background: #3d2008;
    color: var(--accent);
    animation: pulse 2s infinite;
}
.badge-done {
    background: #0d3820;
    color: var(--success);
}
.badge-pending {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
}

/* Phase 2: Task checklist */
.task-list { list-style: none; padding: 0; }
.task-item {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 14px;
}
.task-icon-done { color: var(--success); }
.task-icon-pending { color: var(--text-secondary); }
.task-deps {
    font-size: 12px;
    color: var(--text-secondary);
    margin-left: 28px;
    padding-bottom: 4px;
}

/* Phase 2: Plan cards */
.plan-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
}
.plan-row:last-child { border-bottom: none; }
.plan-title { flex: 1; font-weight: 600; }
.plan-meta {
    font-size: 12px;
    color: var(--text-secondary);
}

/* Phase 2: Memory viewer */
.memory-body {
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 20px;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
    font-family: monospace;
}
"""

# ---------------------------------------------------------------------------
# Shared HTML header
# ---------------------------------------------------------------------------
HEADER_HTML = """
<header class="site-header">
    <a href="/" class="brand">&#x2699; K8s Agent Tools</a>
    <nav>
        <a href="/" class="{{ 'active' if active_page == 'splash' else '' }}">Home</a>
        <a href="/dashboard" class="{{ 'active' if active_page == 'dashboard' else '' }}">Dashboard</a>
        <a href="/skills" class="{{ 'active' if active_page == 'skills' else '' }}">Skills</a>
        <a href="/plans" class="{{ 'active' if active_page == 'plans' else '' }}">Plans</a>

        <div class="dropdown">
            <button>Ecosystem &#9662;</button>
            <div class="dropdown-menu">
                <a href="https://omcgonag.pages.redhat.com/mymcp/">
                    &#x1f4e6; mymcp <span class="dd-hint">MCP agents</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/iproject/">
                    &#x1f4cb; iproject <span class="dd-hint">Project mgmt</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/ireview/">
                    &#x1f50d; ireview <span class="dd-hint">Review tracker</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/isecure/">
                    &#x1f6e1; isecure <span class="dd-hint">Security</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/isdlc/">
                    &#x1f504; isdlc <span class="dd-hint">Agentic SDLC</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/ilearn/">
                    &#x1f393; ilearn <span class="dd-hint">Learning</span>
                </a>
                <a href="https://omcgonag.pages.redhat.com/ilecture/">
                    &#x1f3a4; ilecture <span class="dd-hint">Talks</span>
                </a>
                <hr>
                <a href="https://omcgonag.pages.redhat.com/ipong/">
                    &#x1f3d3; ipong <span class="dd-hint">Fun</span>
                </a>
            </div>
        </div>

        <div class="dropdown">
            <button>Servers &#9662;</button>
            <div class="dropdown-menu">
                <a href="http://10.0.151.101:8081/dashboard">
                    &#x1f4ca; status-report <span class="dd-hint">:8081</span>
                </a>
                <a href="http://10.0.151.101:8082/dashboard">
                    &#x1f4e6; mymcp <span class="dd-hint">:8082</span>
                </a>
                <a href="http://10.0.151.101:8083/dashboard">
                    &#x1f393; ilearn <span class="dd-hint">:8083</span>
                </a>
                <a href="http://10.0.151.101:8086/dashboard">
                    &#x1f504; isdlc <span class="dd-hint">:8086</span>
                </a>
                <a href="http://10.0.151.101:5005/dashboard" class="active-server">
                    &#x2699; k8s-agent-tools <span class="dd-hint">:5005</span>
                </a>
                <hr>
                <a href="http://10.0.151.101:8084/dashboard">
                    &#x1f3d3; ipong <span class="dd-hint">:8084</span>
                </a>
            </div>
        </div>
    </nav>

    <div class="header-right">
        {% if session.get('user') %}
            <span class="user-badge">&#x1f464; {{ session['user'] }}
                {% if session.get('role') == 'admin' %} (admin){% endif %}
            </span>
            <a href="/logout" class="btn btn-sm">Logout</a>
        {% else %}
            <a href="/login" class="btn btn-sm">Login</a>
            <a href="/register" class="btn btn-sm btn-primary">Register</a>
        {% endif %}
    </div>
</header>
"""

# ---------------------------------------------------------------------------
# Base template
# ---------------------------------------------------------------------------
BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - K8s Agent Tools</title>
    <style>""" + CSS_THEME + """</style>
</head>
<body>
""" + HEADER_HTML + """
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div class="container" style="padding-bottom:0">
{% for category, message in messages %}
    <div class="flash flash-{{ category }}">{{ message }}</div>
{% endfor %}
</div>
{% endif %}
{% endwith %}
{{ content | safe }}
<footer class="site-footer">
    OpenStack K8s Agent Tools Server &mdash; Phase 2 &mdash; {{ now }}
</footer>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Utility: load / save users
# ---------------------------------------------------------------------------

def _load_users():
    if not config.USERS_FILE.exists():
        return {}
    with open(config.USERS_FILE) as f:
        return yaml.safe_load(f) or {}


def _save_users(users):
    config.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.USERS_FILE, 'w') as f:
        yaml.dump(users, f, default_flow_style=False)


def _load_config():
    if not config.CONFIG_FILE.exists():
        return {'operator_repos': []}
    with open(config.CONFIG_FILE) as f:
        return yaml.safe_load(f) or {'operator_repos': []}


def _save_config(cfg):
    config.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.CONFIG_FILE, 'w') as f:
        yaml.dump(cfg, f, default_flow_style=False)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.path))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def _render(template_str, **kwargs):
    kwargs.setdefault('active_page', '')
    kwargs['now'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = render_template_string(template_str, **kwargs)
    return render_template_string(
        BASE_TEMPLATE,
        title=kwargs.get('title', 'K8s Agent Tools'),
        content=content,
        active_page=kwargs['active_page'],
        now=kwargs['now'],
    )


# ===================================================================
# ROUTES
# ===================================================================

# --- Splash page -------------------------------------------------------
SPLASH_TEMPLATE = """
<div class="splash">
    <h1>&#x2699; K8s Agent Tools</h1>
    <p class="tagline">
        Monitor, orchestrate, and manage OpenStack K8s operator agent skills
        from a single dashboard.
    </p>
    <div class="cta-row">
        <a href="/dashboard" class="btn btn-primary" style="padding:12px 32px; font-size:16px;">
            Open Dashboard
        </a>
        <a href="/skills" class="btn" style="padding:12px 32px; font-size:16px;">
            Browse Skills
        </a>
        <a href="/register" class="btn" style="padding:12px 32px; font-size:16px;">
            Get Started
        </a>
    </div>
</div>

<div class="container">
    <div class="card-grid">
        <div class="card">
            <h3>&#x1f4ca; Operator Dashboard</h3>
            <p>Scan local operator repos, inspect controllers,
               CRDs, and branches at a glance.</p>
        </div>
        <div class="card">
            <h3>&#x1f9e9; Skill Catalog</h3>
            <p>Browse all {{ skill_count }} skills with descriptions,
               allowed tools, and linked agents.</p>
        </div>
        <div class="card">
            <h3>&#x1f512; Multi-User</h3>
            <p>Register, log in, and manage per-user configurations
               and operator repo lists.</p>
        </div>
    </div>
</div>
"""


@app.route('/')
def splash():
    catalog = get_skill_catalog(config.PLUGIN_PATH)
    return _render(SPLASH_TEMPLATE,
                   title='Home',
                   active_page='splash',
                   skill_count=catalog['total_skills'])


# --- Registration -------------------------------------------------------
REGISTER_TEMPLATE = """
<div class="container" style="max-width:440px">
    <div class="card">
        <h3>Create Account</h3>
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <div class="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirm" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%">
                Register
            </button>
        </form>
        <p style="text-align:center; margin-top:12px; font-size:13px; color:var(--text-secondary)">
            Already have an account? <a href="/login">Log in</a>
        </p>
    </div>
</div>
"""


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        users = _load_users()
        if username in users:
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        users[username] = {
            'password_hash': generate_password_hash(password),
            'role': 'user',
            'created': datetime.now().isoformat(),
        }
        _save_users(users)
        user_dir = config.USERS_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)
        profile = {'display_name': username, 'operator_repos': []}
        with open(user_dir / 'profile.yaml', 'w') as f:
            yaml.dump(profile, f, default_flow_style=False)
        session['user'] = username
        session['role'] = 'user'
        flash('Account created! Welcome.', 'success')
        return redirect(url_for('dashboard'))
    return _render(REGISTER_TEMPLATE, title='Register', active_page='')


# --- Login --------------------------------------------------------------
LOGIN_TEMPLATE = """
<div class="container" style="max-width:440px">
    <div class="card">
        <h3>Log In</h3>
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%">
                Log In
            </button>
        </form>
        <p style="text-align:center; margin-top:12px; font-size:13px; color:var(--text-secondary)">
            Need an account? <a href="/register">Register</a>
        </p>
    </div>
</div>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        users = _load_users()
        user = users.get(username)
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials.', 'error')
            return redirect(url_for('login'))
        session['user'] = username
        session['role'] = user.get('role', 'user')
        flash(f'Welcome back, {username}!', 'success')
        return redirect(request.args.get('next', url_for('dashboard')))
    return _render(LOGIN_TEMPLATE, title='Login', active_page='')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'success')
    return redirect(url_for('splash'))


# --- Dashboard ----------------------------------------------------------
DASHBOARD_TEMPLATE = """
<div class="container">
    <h2 style="margin-bottom:24px">&#x1f4ca; Operator Dashboard</h2>

    <div class="stats-row">
        <div class="stat-card">
            <span class="stat-value">{{ operators | length }}</span>
            <span class="stat-label">Repos Scanned</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ operators | selectattr('status', 'eq', 'ok') | list | length }}</span>
            <span class="stat-label">Found</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ total_controllers }}</span>
            <span class="stat-label">Controllers</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ total_crds }}</span>
            <span class="stat-label">CRDs</span>
        </div>
        <div class="stat-card">
            <span class="stat-value {{ 'pulse' if plan_active > 0 else '' }}">{{ plan_active }}</span>
            <span class="stat-label">Active Plans</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ plan_done }}/{{ plan_total }}</span>
            <span class="stat-label">Tasks Done</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" style="font-size:20px">{{ plan_last_activity }}</span>
            <span class="stat-label">Last Activity</span>
        </div>
    </div>

    {% if operators %}
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Operator</th>
                    <th>Status</th>
                    <th>Branch</th>
                    <th>Controllers</th>
                    <th>CRDs</th>
                    <th>go.mod</th>
                    <th>Makefile</th>
                    <th>Last Commit</th>
                </tr>
            </thead>
            <tbody>
            {% for op in operators %}
                <tr>
                    <td><strong>{{ op.name }}</strong></td>
                    <td>
                        {% if op.status == 'ok' %}
                            <span class="badge badge-ok">OK</span>
                        {% else %}
                            <span class="badge badge-err">Not Found</span>
                        {% endif %}
                    </td>
                    <td>{{ op.branch or '-' }}</td>
                    <td>{{ op.controllers }}</td>
                    <td>{{ op.crds }}</td>
                    <td>{{ '&#10003;' if op.has_gomod else '-' }}</td>
                    <td>{{ '&#10003;' if op.has_makefile else '-' }}</td>
                    <td>{{ op.last_commit or '-' }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="card" style="text-align:center; padding:48px">
        <p style="color:var(--text-secondary); margin-bottom:16px">
            No operator repos configured yet.
        </p>
        <a href="/config" class="btn btn-primary">Configure Repos</a>
    </div>
    {% endif %}
</div>
"""


@app.route('/dashboard')
def dashboard():
    cfg = _load_config()
    repos = cfg.get('operator_repos', [])
    if session.get('user'):
        profile_file = config.USERS_DIR / session['user'] / 'profile.yaml'
        if profile_file.exists():
            with open(profile_file) as f:
                profile = yaml.safe_load(f) or {}
            user_repos = profile.get('operator_repos', [])
            if user_repos:
                repos = list(set(repos + user_repos))
    operators = scan_operators(repos)
    total_controllers = sum(o['controllers'] for o in operators)
    total_crds = sum(o['crds'] for o in operators)

    plans_root = get_plans_root()
    plan_operators = scan_plans(plans_root)
    plan_active = sum(o['active_tasks'] for o in plan_operators)
    agg = compute_aggregate_progress(plans_root)
    plan_last = get_last_activity_ago(plans_root)

    return _render(DASHBOARD_TEMPLATE,
                   title='Dashboard',
                   active_page='dashboard',
                   operators=operators,
                   total_controllers=total_controllers,
                   total_crds=total_crds,
                   plan_active=plan_active,
                   plan_done=agg['done'],
                   plan_total=agg['total'],
                   plan_last_activity=plan_last)


# --- Skills catalog -----------------------------------------------------
SKILLS_TEMPLATE = """
<div class="container">
    <h2 style="margin-bottom:24px">&#x1f9e9; Skill Catalog</h2>

    <div class="stats-row">
        <div class="stat-card">
            <span class="stat-value">{{ catalog.total_skills }}</span>
            <span class="stat-label">Skills</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ catalog.total_agents }}</span>
            <span class="stat-label">Agents</span>
        </div>
    </div>

    {% if catalog.agents %}
    <div class="card" style="margin-bottom:24px">
        <h3 style="margin-bottom:16px">Agents</h3>
        <table>
            <thead>
                <tr><th>Agent</th><th>Model</th><th>Preloaded Skills</th><th>Description</th></tr>
            </thead>
            <tbody>
            {% for a in catalog.agents %}
                <tr>
                    <td><strong>{{ a.name }}</strong></td>
                    <td><span class="badge badge-accent">{{ a.model }}</span></td>
                    <td>{{ a.preloads | join(', ') if a.preloads else '-' }}</td>
                    <td>{{ a.description }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="card-grid">
    {% for s in catalog.skills %}
        <div class="card">
            <h3>
                <a href="/skills/{{ s.name }}">{{ s.name }}</a>
                {% if s.has_agent %}
                    <span class="badge badge-accent" style="margin-left:8px">has agent</span>
                {% endif %}
            </h3>
            <p style="color:var(--text-secondary); font-size:14px; margin-bottom:8px">
                {{ s.description }}
            </p>
            {% if s.allowed_tools %}
            <p style="font-size:12px; color:var(--text-secondary)">
                Tools: {{ s.allowed_tools | join(', ') | truncate(80) }}
            </p>
            {% endif %}
            {% if s.summary %}
            <p style="font-size:13px; margin-top:8px">{{ s.summary | truncate(200) }}</p>
            {% endif %}
        </div>
    {% endfor %}
    </div>

    {% if not catalog.skills %}
    <div class="card" style="text-align:center; padding:48px">
        <p style="color:var(--text-secondary)">
            No skills found. Make sure the plugin path is configured
            and contains skills/ directory.
        </p>
        <p style="font-size:13px; color:var(--text-secondary); margin-top:8px">
            Plugin path: {{ plugin_path }}
        </p>
    </div>
    {% endif %}
</div>
"""


@app.route('/skills')
def skills():
    catalog = get_skill_catalog(config.PLUGIN_PATH)
    return _render(SKILLS_TEMPLATE,
                   title='Skills',
                   active_page='skills',
                   catalog=catalog,
                   plugin_path=config.PLUGIN_PATH)


# --- Skill detail -------------------------------------------------------
SKILL_DETAIL_TEMPLATE = """
<div class="container" style="max-width:900px">
    <p style="margin-bottom:16px">
        <a href="/skills">&larr; Back to Skill Catalog</a>
    </p>
    <div class="card">
        <h2>{{ skill.name }}</h2>
        <p style="color:var(--text-secondary); margin-bottom:16px">{{ skill.description }}</p>

        <table style="max-width:500px; margin-bottom:16px">
            <tr><th>Context</th><td>{{ skill.context }}</td></tr>
            {% if skill.argument_hint %}
            <tr><th>Argument hint</th><td>{{ skill.argument_hint }}</td></tr>
            {% endif %}
            <tr><th>Allowed tools</th><td>{{ skill.allowed_tools | join(', ') or 'none' }}</td></tr>
        </table>

        {% if skill.agent %}
        <div style="background:var(--bg-tertiary); border-radius:6px; padding:16px; margin-bottom:16px">
            <h3>Linked Agent: {{ skill.agent.name }}</h3>
            <p style="font-size:14px; color:var(--text-secondary)">
                Model: <span class="badge badge-accent">{{ skill.agent.model }}</span>
                &nbsp; Preloads: {{ skill.agent.preloads | join(', ') or 'none' }}
            </p>
        </div>
        {% endif %}

        <h3 style="margin-top:16px; margin-bottom:8px">SKILL.md Content</h3>
        <div class="skill-body">{{ skill.body }}</div>
    </div>
</div>
"""


@app.route('/skills/<name>')
def skill_detail(name):
    skill = get_skill_detail(config.PLUGIN_PATH, name)
    if not skill:
        abort(404)
    return _render(SKILL_DETAIL_TEMPLATE,
                   title=f'Skill: {name}',
                   active_page='skills',
                   skill=skill)


# --- Config page --------------------------------------------------------
CONFIG_TEMPLATE = """
<div class="container" style="max-width:700px">
    <div class="card">
        <h3>&#x2699; Configuration</h3>

        <form method="POST" action="/config">
            <div class="form-group">
                <label>Plugin Path</label>
                <input type="text" name="plugin_path" value="{{ plugin_path }}" disabled
                       style="opacity:0.6"
                       title="Set via K8S_AGENT_TOOLS_PLUGIN_PATH env var">
                <p style="font-size:12px; color:var(--text-secondary); margin-top:4px">
                    Set via <code>K8S_AGENT_TOOLS_PLUGIN_PATH</code> env var.
                </p>
            </div>

            <div class="form-group">
                <label>Operator Repo Paths (one per line)</label>
                <textarea name="repos" rows="8"
                    style="width:100%; padding:8px 12px; border:1px solid var(--border);
                           border-radius:6px; background:var(--input-bg); color:var(--text-primary);
                           font-size:14px; font-family:monospace; resize:vertical">{{ repos_text }}</textarea>
            </div>

            <button type="submit" class="btn btn-primary">Save</button>
        </form>
    </div>
</div>
"""


@app.route('/config', methods=['GET', 'POST'])
@login_required
def config_page():
    if request.method == 'POST':
        repos_text = request.form.get('repos', '')
        repos = [r.strip() for r in repos_text.strip().split('\n') if r.strip()]
        if session.get('role') == 'admin':
            cfg = _load_config()
            cfg['operator_repos'] = repos
            _save_config(cfg)
        else:
            user_dir = config.USERS_DIR / session['user']
            user_dir.mkdir(parents=True, exist_ok=True)
            profile_file = user_dir / 'profile.yaml'
            profile = {}
            if profile_file.exists():
                with open(profile_file) as f:
                    profile = yaml.safe_load(f) or {}
            profile['operator_repos'] = repos
            with open(profile_file, 'w') as f:
                yaml.dump(profile, f, default_flow_style=False)
        flash('Configuration saved.', 'success')
        return redirect(url_for('config_page'))

    cfg = _load_config()
    repos = cfg.get('operator_repos', [])
    if session.get('role') != 'admin':
        profile_file = config.USERS_DIR / session['user'] / 'profile.yaml'
        if profile_file.exists():
            with open(profile_file) as f:
                profile = yaml.safe_load(f) or {}
            repos = profile.get('operator_repos', repos)
    repos_text = '\n'.join(repos)
    return _render(CONFIG_TEMPLATE,
                   title='Config',
                   active_page='config',
                   plugin_path=config.PLUGIN_PATH,
                   repos_text=repos_text)


# --- Admin panel --------------------------------------------------------
ADMIN_TEMPLATE = """
<div class="container" style="max-width:800px">
    <div class="card">
        <h3>&#x1f6e1; Admin Panel</h3>
        <table>
            <thead>
                <tr><th>Username</th><th>Role</th><th>Created</th></tr>
            </thead>
            <tbody>
            {% for uname, udata in users.items() %}
                <tr>
                    <td>{{ uname }}</td>
                    <td><span class="badge {{ 'badge-accent' if udata.role == 'admin' else 'badge-ok' }}">
                        {{ udata.role }}
                    </span></td>
                    <td>{{ udata.get('created', '-') }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""


@app.route('/admin')
@admin_required
def admin_panel():
    users = _load_users()
    return _render(ADMIN_TEMPLATE,
                   title='Admin',
                   active_page='admin',
                   users=users)


# --- Plans list (Phase 2) ------------------------------------------------
PLANS_TEMPLATE = """
<div class="container">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px">
        <h2>&#x1f4cb; Plans</h2>
        {% if not plan_operators %}
        <form method="POST" action="/plans/seed-demo">
            <button type="submit" class="btn btn-primary">Seed Demo Data</button>
        </form>
        {% endif %}
    </div>

    {% if plan_operators %}
    <div class="stats-row">
        <div class="stat-card">
            <span class="stat-value {{ 'pulse' if total_active > 0 else '' }}">{{ total_active }}</span>
            <span class="stat-label">Active Plans</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ agg.done }}/{{ agg.total }}</span>
            <span class="stat-label">Tasks Done</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" style="font-size:20px">{{ last_activity_ago }}</span>
            <span class="stat-label">Last Activity</span>
        </div>
    </div>

    {% for op in plan_operators %}
    <div class="card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px">
            <h3><a href="/plans/{{ op.name }}">{{ op.name }}</a></h3>
            <span class="plan-meta">
                {{ op.plan_count }} plan{{ 's' if op.plan_count != 1 else '' }}
                | {{ op.active_tasks }} active
                | {{ op.tasks_done }}/{{ op.tasks_total }} tasks done
            </span>
        </div>
        {% for p in op.plans %}
        <div class="plan-row">
            <a href="/plans/{{ op.name }}/{{ p.slug }}" class="plan-title">{{ p.title or p.slug }}</a>
            <span class="badge badge-{{ p.status }}">{{ p.status }}</span>
            <div class="progress-row" style="min-width:200px">
                <div class="progress-bar {{ 'progress-100' if p.progress_percent == 100 else '' }}">
                    <div class="progress-fill" style="width:{{ p.progress_percent }}%"></div>
                </div>
                <span class="progress-pct">{{ p.progress_percent }}%</span>
            </div>
            <span class="plan-meta">{{ p.last_modified_ago }}</span>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    {% else %}
    <div class="card" style="text-align:center; padding:48px">
        <p style="color:var(--text-secondary); font-size:16px; margin-bottom:12px">
            No plans found
        </p>
        <p style="color:var(--text-secondary); font-size:14px; margin-bottom:24px">
            Plans are created when you run <code>/feature</code> or
            <code>/task-executor</code> through the openstack-k8s-agent-tools plugin.
        </p>
        <form method="POST" action="/plans/seed-demo">
            <button type="submit" class="btn btn-primary" style="padding:10px 24px">
                Seed Demo Data
            </button>
        </form>
    </div>
    {% endif %}
</div>
"""


@app.route('/plans')
@login_required
def plans_list():
    plans_root = get_plans_root()
    plan_operators = scan_plans(plans_root)
    for op in plan_operators:
        op['plans'] = get_operator_plans(plans_root, op['name'])
    total_active = sum(o['active_tasks'] for o in plan_operators)
    agg = compute_aggregate_progress(plans_root)
    last_ago = get_last_activity_ago(plans_root)
    return _render(PLANS_TEMPLATE,
                   title='Plans',
                   active_page='plans',
                   plan_operators=plan_operators,
                   total_active=total_active,
                   agg=agg,
                   last_activity_ago=last_ago)


@app.route('/plans/seed-demo', methods=['POST'])
@login_required
def plans_seed():
    seed_demo_data()
    flash('Demo data seeded!', 'success')
    return redirect(url_for('plans_list'))


# --- Plans per operator (Phase 2) ---------------------------------------
PLANS_OPERATOR_TEMPLATE = """
<div class="container">
    <p style="margin-bottom:16px">
        <a href="/plans">&larr; Back to Plans</a>
    </p>
    <h2 style="margin-bottom:24px">{{ operator }}</h2>

    <div class="stats-row">
        <div class="stat-card">
            <span class="stat-value">{{ plans | length }}</span>
            <span class="stat-label">Plans</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ state_info.active_tasks | length }}</span>
            <span class="stat-label">Active Tasks</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ state_info.completed_plans | length }}</span>
            <span class="stat-label">Completed</span>
        </div>
    </div>

    <div class="card">
        <h3 style="margin-bottom:12px">Plans</h3>
        {% for p in plans %}
        <div class="plan-row">
            <a href="/plans/{{ operator }}/{{ p.slug }}" class="plan-title">{{ p.title or p.slug }}</a>
            <span class="badge badge-{{ p.status }}">{{ p.status }}</span>
            <div class="progress-row" style="min-width:200px">
                <div class="progress-bar {{ 'progress-100' if p.progress_percent == 100 else '' }}">
                    <div class="progress-fill" style="width:{{ p.progress_percent }}%"></div>
                </div>
                <span class="progress-pct">{{ p.progress_percent }}%</span>
            </div>
            <span class="plan-meta">{{ p.last_modified_ago }}</span>
        </div>
        {% endfor %}
    </div>

    {% if memory_info.exists %}
    <div class="card">
        <h3>MEMORY.md</h3>
        <p style="font-size:12px; color:var(--text-secondary); margin-bottom:8px">
            {{ memory_info.line_count }} lines | Last modified: {{ memory_info.last_modified_ago }}
        </p>
        <a href="/plans/{{ operator }}/memory" class="btn btn-sm">View MEMORY.md</a>
    </div>
    {% endif %}

    {% if state_info.active_tasks %}
    <div class="card">
        <h3>Active Tasks (state.json)</h3>
        <table>
            <thead>
                <tr><th>Plan</th><th>Task</th><th>Worktree</th><th>Started</th></tr>
            </thead>
            <tbody>
            {% for t in state_info.active_tasks %}
                <tr>
                    <td>{{ t.plan }}</td>
                    <td>{{ t.task }}</td>
                    <td><code>{{ t.worktree }}</code></td>
                    <td>{{ t.started }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</div>
"""


@app.route('/plans/<operator>')
@login_required
def plans_operator(operator):
    plans_root = get_plans_root()
    plans = get_operator_plans(plans_root, operator)
    if not plans:
        flash(f'No plans found for {operator}.', 'error')
        return redirect(url_for('plans_list'))
    memory_info = read_memory(plans_root, operator)
    state_info = read_state_json(plans_root, operator)
    return _render(PLANS_OPERATOR_TEMPLATE,
                   title=f'Plans: {operator}',
                   active_page='plans',
                   operator=operator,
                   plans=plans,
                   memory_info=memory_info,
                   state_info=state_info)


# --- Plan detail (Phase 2) -----------------------------------------------
PLAN_DETAIL_TEMPLATE = """
<div class="container" style="max-width:900px">
    <p style="margin-bottom:16px">
        <a href="/plans/{{ operator }}">&larr; Back to {{ operator }}</a>
    </p>

    <div style="display:flex; align-items:center; gap:12px; margin-bottom:24px">
        <h2>{{ plan_data.title or slug }}</h2>
        <span class="badge badge-{{ status }}">{{ status }}</span>
    </div>

    <div class="stats-row">
        <div class="stat-card">
            <span class="stat-value">{{ plan_data.tasks_total }}</span>
            <span class="stat-label">Total Tasks</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ plan_data.tasks_done }}</span>
            <span class="stat-label">Done</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{{ plan_data.progress_percent }}%</span>
            <span class="stat-label">Progress</span>
        </div>
    </div>

    <div class="progress-row" style="margin-bottom:24px">
        <div class="progress-bar {{ 'progress-100' if plan_data.progress_percent == 100 else '' }}" style="height:12px">
            <div class="progress-fill" style="width:{{ plan_data.progress_percent }}%; height:12px"></div>
        </div>
        <span class="progress-pct">{{ plan_data.progress_percent }}%</span>
    </div>

    {% if plan_data.strategy %}
    <div class="card">
        <h3>Approved Strategy</h3>
        <p style="font-size:14px; margin-top:8px">{{ plan_data.strategy }}</p>
    </div>
    {% endif %}

    {% for group in plan_data.groups %}
    <div class="card">
        <h3>{{ group.name }}</h3>
        <ul class="task-list">
        {% for task in group.tasks %}
            <li class="task-item">
                {% if task.done %}
                    <span class="task-icon-done">&#x2705;</span>
                {% else %}
                    <span class="task-icon-pending">&#x2B1C;</span>
                {% endif %}
                <span>{{ task.name }}</span>
            </li>
            {% if task.dependencies is defined and task.dependencies %}
            <li class="task-deps">Dependencies: {{ task.dependencies }}</li>
            {% endif %}
        {% endfor %}
        </ul>
    </div>
    {% endfor %}

    {% if plan_data.outcome %}
    <div class="card">
        <h3>Outcome</h3>
        <p style="font-size:14px; margin-top:8px">{{ plan_data.outcome }}</p>
    </div>
    {% endif %}

    {% if state_info.active_tasks %}
    <div class="card">
        <h3>state.json — Active Work</h3>
        <table>
            <thead>
                <tr><th>Task</th><th>Worktree</th><th>Session</th><th>Started</th></tr>
            </thead>
            <tbody>
            {% for t in state_info.active_tasks %}
                <tr>
                    <td>{{ t.task }}</td>
                    <td><code>{{ t.worktree }}</code></td>
                    <td><code>{{ t.session_id }}</code></td>
                    <td>{{ t.started }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div style="margin-top:16px">
        <a href="/plans/{{ operator }}/{{ slug }}/memory" class="btn">View MEMORY.md</a>
    </div>
</div>
"""


@app.route('/plans/<operator>/<slug>')
@login_required
def plan_detail(operator, slug):
    plans_root = get_plans_root()
    plan_file = Path(plans_root) / operator / f'{slug}.md'
    plan_data = parse_plan_tasks(plan_file)
    if not plan_data:
        flash(f'Plan not found: {slug}', 'error')
        return redirect(url_for('plans_operator', operator=operator))
    state_info = read_state_json(plans_root, operator)
    from .plan_monitor import _plan_status, _read_state
    state_raw = _read_state(Path(plans_root) / operator)
    status = _plan_status(f'{slug}.md', state_raw)
    return _render(PLAN_DETAIL_TEMPLATE,
                   title=f'Plan: {slug}',
                   active_page='plans',
                   operator=operator,
                   slug=slug,
                   plan_data=plan_data,
                   state_info=state_info,
                   status=status)


# --- MEMORY.md viewer (Phase 2) ------------------------------------------
MEMORY_TEMPLATE = """
<div class="container" style="max-width:900px">
    <p style="margin-bottom:16px">
        <a href="/plans/{{ operator }}">&larr; Back to {{ operator }}</a>
    </p>
    <div class="card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px">
            <h2>MEMORY.md &mdash; {{ operator }}</h2>
            <span class="plan-meta">
                {{ memory_info.line_count }} lines |
                Last modified: {{ memory_info.last_modified_ago }}
            </span>
        </div>
        {% if memory_info.exists %}
        <div class="memory-body">{{ memory_info.content }}</div>
        {% else %}
        <p style="color:var(--text-secondary); text-align:center; padding:24px">
            No MEMORY.md found for {{ operator }}.
        </p>
        {% endif %}
    </div>
</div>
"""


@app.route('/plans/<operator>/<slug>/memory')
@login_required
def plan_memory(operator, slug):
    plans_root = get_plans_root()
    memory_info = read_memory(plans_root, operator)
    return _render(MEMORY_TEMPLATE,
                   title=f'MEMORY.md: {operator}',
                   active_page='plans',
                   operator=operator,
                   slug=slug,
                   memory_info=memory_info)


# Also allow direct memory access per operator
@app.route('/plans/<operator>/memory')
@login_required
def operator_memory(operator):
    plans_root = get_plans_root()
    memory_info = read_memory(plans_root, operator)
    return _render(MEMORY_TEMPLATE,
                   title=f'MEMORY.md: {operator}',
                   active_page='plans',
                   operator=operator,
                   slug='',
                   memory_info=memory_info)


# --- API endpoints -------------------------------------------------------
@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'phase': 2,
                    'server': 'k8s-agent-tools',
                    'timestamp': datetime.now().isoformat()})


@app.route('/api/skills')
def api_skills():
    return jsonify(get_skill_catalog(config.PLUGIN_PATH))


@app.route('/api/operators')
def api_operators():
    cfg = _load_config()
    repos = cfg.get('operator_repos', [])
    return jsonify(scan_operators(repos))


@app.route('/api/plans')
@login_required
def api_plans():
    plans_root = get_plans_root()
    return jsonify(scan_plans(plans_root))


@app.route('/api/plans/<operator>/<slug>/state')
@login_required
def api_plan_state(operator, slug):
    plans_root = get_plans_root()
    state = read_state_json(plans_root, operator)
    return jsonify(state)


# --- Main ----------------------------------------------------------------
if __name__ == '__main__':
    config.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    config.USERS_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host='0.0.0.0', port=config.PORT, debug=True)
