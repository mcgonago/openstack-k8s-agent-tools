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
    OpenStack K8s Agent Tools Server &mdash; Phase 1 &mdash; {{ now }}
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
    return _render(DASHBOARD_TEMPLATE,
                   title='Dashboard',
                   active_page='dashboard',
                   operators=operators,
                   total_controllers=total_controllers,
                   total_crds=total_crds)


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


# --- API endpoints -------------------------------------------------------
@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'phase': 1,
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


# --- Main ----------------------------------------------------------------
if __name__ == '__main__':
    config.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    config.USERS_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host='0.0.0.0', port=config.PORT, debug=True)
