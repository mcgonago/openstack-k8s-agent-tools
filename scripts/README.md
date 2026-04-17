# OpenStack K8s Agent Tools — Web Server

A production web dashboard and API layer that wraps
[fmount/openstack-k8s-agent-tools](https://github.com/fmount/openstack-k8s-agent-tools)
— 10 AI-powered skills and 3 agents for OpenStack K8s operator development —
into a multi-user interactive server with real-time skill execution, plan
monitoring, analysis dashboards, team portal, history tracking, and reporting.

**Production URL:** `http://10.0.151.101:8087/`
**Local dev URL:** `http://localhost:5005/`

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Environment Variables](#environment-variables)
- [Feature Summary — 7 Phases](#feature-summary--7-phases)
- [Module Reference](#module-reference)
- [Production Deployment](#production-deployment)
- [Server Fleet — Cohosting](#server-fleet--cohosting)
- [Demo Mode](#demo-mode)
- [Design Documentation](#design-documentation)

---

## Overview

The openstack-k8s-agent-tools plugin is a Claude Code / OpenCode plugin that
provides AI-assisted development workflows for the
[openstack-k8s-operators](https://github.com/openstack-k8s-operators/) ecosystem.
This server does **not** replace the plugin — it wraps, monitors, and exposes its
capabilities through a web UI and REST API.

**What the plugin provides (10 skills):**

| Skill | Type | Description |
|---|---|---|
| debug-operator | CLI | Inspect running pods, logs, CRDs, RBAC |
| test-operator | CLI | Run tiered test suites (quick / standard / full) |
| code-style | CLI | Go modernization hints, gopls/golangci-lint guidance |
| analyze-logs | CLI | Pattern-based log classification (25+ regex patterns) |
| explain-flow | CLI | Parse controller/reconciler flows, generate diagrams |
| code-review | AI | Structured 11-criteria Go code review |
| backport-review | AI | Compare downstream GitLab MRs vs upstream Gerrit |
| feature | AI | Jira-aware multi-strategy planning with cross-repo analysis |
| task-executor | AI | Task-by-task execution with checkpointing |
| jira | AI | Read/write Jira tickets with hierarchy rules |

**What this server adds:**

- Multi-user authentication (registration, login, per-user profiles)
- Real-time skill execution from the browser with live log streaming
- Plan monitoring with progress bars, task checklists, MEMORY.md viewer
- Team portal aggregating Jira, GitHub, and Gerrit data
- Analysis dashboards for logs, code flow, and style
- History tracking with 7-day trends and on-demand reports
- Built-in demo mode with seed data and guided walk-through
- Production deployment via systemd + Apache + SELinux

---

## Architecture

```
+-----------------------------------------------------------+
|                        Browser                            |
+-----------------------------------------------------------+
          |                              |
          v                              v
+-------------------+          +-------------------+
| Apache httpd      |          | Flask Dev Server  |
| :8087 (prod)      |          | :5005 (local)     |
+-------------------+          +-------------------+
          |                              |
          v                              v
+-----------------------------------------------------------+
|                  Gunicorn / Flask App                      |
|                   (54 routes, ~6300 LOC)                   |
|-----------------------------------------------------------|
|  app.py           | Main Flask app, all routes + templates |
|  config.py        | Centralized env-var-driven config      |
|  skill_catalog.py | Discovers SKILL.md files from plugin   |
|  skill_runner.py  | Subprocess executor for CLI skills     |
|  job_queue.py     | ThreadPoolExecutor background workers  |
|  plan_monitor.py  | Scans ~/.openstack-k8s-agents-plans/   |
|  operator_scanner.py | Discovers operator repos on disk    |
|  jira_client.py   | Jira REST API + demo data fallback     |
|  github_client.py | GitHub REST API + demo data fallback   |
|  gerrit_client.py | Gerrit REST API + demo data fallback   |
|  history_manager.py | Daily snapshots, trends, demo seed   |
|  report_generator.py | Daily/weekly markdown report gen    |
|  log_analyzer_wrapper.py   | Wraps lib/log-analyzer.py    |
|  code_parser_wrapper.py    | Wraps lib/code-parser.py     |
|  style_analyzer_wrapper.py | Wraps lib/style-analyzer.py  |
+-----------------------------------------------------------+
          |                    |                    |
          v                    v                    v
+----------------+   +-----------------+   +-----------------+
| data/          |   | Plugin repo     |   | External APIs   |
| users.yaml     |   | skills/         |   | Jira (OSPRH)    |
| config.yaml    |   | agents/         |   | GitHub (k8s-op) |
| executions/    |   | lib/            |   | Gerrit (OpenDev)|
| analyses/      |   | tests/          |   +-----------------+
| history/       |   | SKILL.md files  |
| reports/       |   +-----------------+
| cache/         |
+----------------+
```

**Request flow:**

```
Browser --> Apache :8087 --> Gunicorn :5006 --> Flask app
                                                   |
              +------------------------------------+--------------------+
              |                  |                  |                    |
              v                  v                  v                    v
        Skill Runner       Plan Monitor       Integration         Analysis
        (subprocess)       (filesystem)       Clients (REST)      Wrappers
              |                  |                  |              (subprocess)
              v                  v                  v                    |
        data/executions/   ~/.openstack-       data/cache/              v
                           k8s-agents-plans/                    data/analyses/
```

---

## Directory Structure

```
scripts/
|-- README.md              <-- You are here
|-- local_dev.sh           <-- One-command local dev server
|-- deploy_to_runner.sh    <-- One-command production deploy
|-- create_admin.py        <-- Interactive admin user creation
|-- run.py                 <-- WSGI entry point for Gunicorn
|-- requirements.txt       <-- Python dependencies
|-- web_app/
|   |-- __init__.py
|   |-- app.py                     <-- Flask app (54 routes, templates, CSS)
|   |-- config.py                  <-- All env-var-driven configuration
|   |-- skill_catalog.py           <-- SKILL.md discovery and parsing
|   |-- skill_runner.py            <-- Subprocess execution engine
|   |-- job_queue.py               <-- Background worker pool
|   |-- plan_monitor.py            <-- Plan/task/MEMORY.md scanner
|   |-- operator_scanner.py        <-- Operator repo discovery
|   |-- jira_client.py             <-- Jira REST client + demo data
|   |-- github_client.py           <-- GitHub REST client + demo data
|   |-- gerrit_client.py           <-- Gerrit REST client + demo data
|   |-- history_manager.py         <-- Daily snapshots + trend computation
|   |-- report_generator.py        <-- Markdown report generation
|   |-- log_analyzer_wrapper.py    <-- Wraps plugin's lib/log-analyzer.py
|   |-- code_parser_wrapper.py     <-- Wraps plugin's lib/code-parser.py
|   |-- style_analyzer_wrapper.py  <-- Wraps plugin's lib/style-analyzer.py
|   +-- data/                      <-- Runtime data (git-ignored)
|       |-- users.yaml
|       |-- config.yaml
|       |-- users/
|       |-- executions/
|       |-- analyses/
|       |-- history/
|       |-- reports/
|       +-- cache/
|
systemd/                           <-- Production deploy configs
|-- k8s-agent-tools-server.service       <-- Gunicorn systemd unit
|-- k8s-agent-tools-server-apache.conf   <-- Apache reverse proxy
|-- k8s-agent-tools-server-backup.service <-- Daily backup oneshot
+-- k8s-agent-tools-server-backup.timer   <-- Daily backup timer (02:00)
```

---

## Quick Start (Local Development)

**Prerequisites:** Python 3.10+, the plugin repo cloned locally.

```bash
cd scripts/
./local_dev.sh
```

That single command:

1. Creates a Python virtualenv in `scripts/.venv/`
2. Installs dependencies from `requirements.txt`
3. Starts Flask in debug mode on `http://localhost:5005/`

On first launch, register an account at `/register`. To create an admin user
with full privileges, use the interactive script:

```bash
cd scripts/
.venv/bin/python create_admin.py
```

**Dependencies:**

| Package | Version | Purpose |
|---|---|---|
| flask | >= 3.0 | Web framework |
| gunicorn | >= 22.0 | Production WSGI server |
| pyyaml | >= 6.0 | YAML data persistence |
| requests | >= 2.31 | External API clients (Jira, GitHub) |
| werkzeug | >= 3.0 | Password hashing, request utilities |

---

## Environment Variables

All configuration is driven by environment variables with sensible defaults.
For local development, `local_dev.sh` sets the essentials automatically.

| Variable | Default | Description |
|---|---|---|
| `K8S_AGENT_TOOLS_DATA_ROOT` | `scripts/data/` | Root directory for all persistent data |
| `K8S_AGENT_TOOLS_PLUGIN_PATH` | Auto-detected | Path to the plugin repo root |
| `K8S_AGENT_TOOLS_PORT` | `5005` | Flask/Gunicorn listen port |
| `K8S_AGENT_TOOLS_SECRET` | Random (per restart) | Flask session encryption key |
| `K8S_AGENT_TOOLS_PLANS_ROOT` | `~/.openstack-k8s-agents-plans` | Agent plans directory |
| `K8S_AGENT_TOOLS_MAX_WORKERS` | `3` | Max concurrent skill executions |
| `K8S_AGENT_TOOLS_EXEC_TIMEOUT` | `300` (seconds) | Skill execution timeout |
| `K8S_AGENT_TOOLS_CACHE_TTL` | `600` (seconds) | Integration API cache lifetime |
| `JIRA_URL` | `https://issues.redhat.com` | Jira server URL |
| `JIRA_TOKEN` | (empty) | Jira Personal Access Token |
| `JIRA_PROJECT` | `OSPRH` | Default Jira project key |
| `GITHUB_TOKEN` | (empty) | GitHub Personal Access Token |
| `GITHUB_REPOS` | (empty) | Comma-separated `org/repo` list |
| `GERRIT_URL` | `https://review.opendev.org` | Gerrit server URL |
| `GERRIT_QUERY` | `project:openstack/ status:open` | Default Gerrit query |

**Important:** Set `K8S_AGENT_TOOLS_SECRET` to a stable value in production.
Without it, every server restart generates a new random key and invalidates all
user sessions.

---

## Feature Summary — 7 Phases

The server was built incrementally in 7 phases, each adding a layer of
capability. Every phase has a corresponding design doc, implementation spec,
and step-by-step guide.

### Phase 1 — Core Server + Operator Dashboard

- Dark-themed splash page with orange/amber gradient
- User registration and login with session management
- Dashboard with stat cards (operators, skills, agents, plans, executions)
- Skill catalog discovering all 10 SKILL.md files from the plugin
- Skill detail pages rendering full SKILL.md documentation
- Operator scanner detecting repos on disk
- Navigation with Ecosystem (GitLab Pages) and Servers dropdowns

### Phase 2 — Skill Status + Plan Monitoring

- Plan discovery from `~/.openstack-k8s-agents-plans/`
- Plan list with progress bars, status badges, grouped by operator
- Plan detail with task checklists and completion percentages
- MEMORY.md viewer showing the agent's persistent memory
- `state.json` dashboard for active task tracking
- "Seed Demo Data" for instant plan visualization

### Phase 3 — Skill Execution API

- Execute 5 CLI-based skills directly from the browser
- Background worker pool (`ThreadPoolExecutor`, configurable concurrency)
- Real-time log streaming via polling API endpoint
- Execution history with full logs, duration, exit codes
- Execution detail page with auto-refreshing log viewer
- Cancel running executions

### Phase 4 — Team Portal + External Integrations

- Jira integration: issue list, status badges, priority indicators
- GitHub integration: PR list, review status, commit history
- Gerrit/OpenDev integration: review list, vote indicators
- Operator health cross-referencing data from all three sources
- TTL-based caching for API responses (default 10 minutes)
- Demo-first design: realistic sample data when no API keys are configured

### Phase 5 — Analysis + Intelligence

- Log Analysis: paste or load demo logs, get parsed errors/warnings/info
- Code Flow: point at a directory, see reconciler flows with color-coded steps
- Style Analysis: point at a Go file, see style findings with severity
- All three wrap the plugin's existing CLI tools (`lib/log-analyzer.py`,
  `lib/code-parser.py`, `lib/style-analyzer.py`) via subprocess
- Analysis history with summary counts across all runs

### Phase 6 — History + Reporting

- Daily data snapshots capturing execution counts, analysis counts, pass rates
- 7-day trend bars on dashboard and history page
- Trend arrows (up/down/flat) comparing today vs. yesterday
- History detail page with per-day breakdown
- On-demand daily and weekly report generation (Markdown format)
- Report download as `.md` for sharing via Slack or email
- "Seed Demo History" populates 7 days of realistic activity data

### Phase 7 — Production Deployment

- One-command deploy: `./deploy_to_runner.sh`
- Gunicorn + Apache reverse proxy on `10.0.151.101`
- systemd service with auto-restart and SELinux configuration
- Daily backups at 02:00 with 30-day retention
- `--code-only` flag for fast iterative deploys (~8 seconds)
- Cohosted alongside 6 sibling servers on the same host

---

## Module Reference

| Module | Lines | Responsibility |
|---|---|---|
| `app.py` | ~3940 | Flask app, 54 routes, all HTML/CSS/JS templates |
| `config.py` | 48 | Centralized env-var-driven configuration |
| `skill_catalog.py` | ~100 | Discovers and parses SKILL.md files from plugin |
| `skill_runner.py` | ~120 | Subprocess executor, log capture, result persistence |
| `job_queue.py` | ~80 | ThreadPoolExecutor wrapper, execution lifecycle |
| `plan_monitor.py` | ~200 | Plan/task scanner, MEMORY.md reader, demo data seeder |
| `operator_scanner.py` | ~60 | Discovers operator repos on disk |
| `jira_client.py` | ~150 | Jira REST API client with TTL cache + demo fallback |
| `github_client.py` | ~150 | GitHub REST API client with TTL cache + demo fallback |
| `gerrit_client.py` | ~150 | Gerrit REST API client with TTL cache + demo fallback |
| `history_manager.py` | ~180 | Daily snapshots, trend computation, demo history seeder |
| `report_generator.py` | ~160 | Daily/weekly Markdown report generator |
| `log_analyzer_wrapper.py` | ~80 | Wraps `lib/log-analyzer.py`, parses JSON output |
| `code_parser_wrapper.py` | ~80 | Wraps `lib/code-parser.py`, parses JSON output |
| `style_analyzer_wrapper.py` | ~80 | Wraps `lib/style-analyzer.py`, parses JSON output |

**Total:** ~6300 lines of Python across 16 modules.

---

## Production Deployment

The server runs on `10.0.151.101` using the same proven deploy pattern as
[isdlc-server](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/isdlc/repo/isdlc/scripts/deploy_to_runner.sh),
[ilearn-server](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/ilearn_server/repo/ilearn_server/deploy_to_runner.sh),
and 4 other sibling servers.

### Deploy Commands

```bash
# Full 9-step deploy (first time or major changes, ~40 seconds)
./deploy_to_runner.sh

# Quick code sync + restart (iterative development, ~8 seconds)
./deploy_to_runner.sh --code-only

# Show help
./deploy_to_runner.sh --help
```

### What the Full Deploy Does (9 Steps)

```
+-------------+    +-------------+    +-------------+
| 1. Stop     | -> | 2. Create   | -> | 3. Sync     |
|    service  |    |    dirs     |    |    app code |
+-------------+    +-------------+    +-------------+
                                            |
+-------------+    +-------------+    +-----v-------+
| 6. Seed     | <- | 5. Setup    | <- | 4. Sync     |
|    data     |    |    venv     |    |    plugin   |
+-------------+    +-------------+    +-------------+
      |
+-----v-------+    +-------------+    +-------------+
| 7. Install  | -> | 8. SELinux  | -> | 9. Start    |
|    systemd  |    |    + backup |    |    + verify |
|    + Apache |    |    timer    |    |    health   |
+-------------+    +-------------+    +-------------+
```

### What `--code-only` Does

Runs only steps 1, 3, 4, 9 — stops the service, syncs code (web_app + plugin),
restarts, and verifies health. Skips venv rebuild, data seed, systemd configs,
and SELinux. Ideal for iterating on code changes.

### Production Stack

```
+-------------------------------------------------------+
|                   10.0.151.101                         |
|-------------------------------------------------------|
|  Apache httpd                                         |
|  :8087 -> ProxyPass -> 127.0.0.1:5006 (Gunicorn)     |
|-------------------------------------------------------|
|  systemd services:                                    |
|  - k8s-agent-tools-server.service  (Gunicorn, 2 wkrs)|
|  - k8s-agent-tools-server-backup.timer  (daily 02:00)|
|-------------------------------------------------------|
|  SELinux: enforcing, bin_t on venv/bin/, http_port_t  |
|  Backups: /home/ospng/k8s-agent-tools-server/backups/ |
|           30-day retention, tar.gz of data/           |
+-------------------------------------------------------+
```

### First Deploy — Admin User

After the first deploy, create the admin user on the server:

```bash
ssh -i ~/.ssh/id_rsa_omcgonag_runner ospng@10.0.151.101
cd /home/ospng/k8s-agent-tools-server
venv/bin/python3 app/create_admin.py
```

The script prompts for username, full name, email, and password interactively.

---

## Server Fleet — Cohosting

The k8s-agent-tools server is cohosted on `10.0.151.101` alongside 6 sibling
servers, all following the same architecture (Gunicorn + Apache + systemd):

| Server | Apache Port | Gunicorn Port | URL |
|---|---|---|---|
| iproject-server | 80 | 5001 | `http://10.0.151.101/` |
| ilearn-server | 8082 | 5002 | `http://10.0.151.101:8082/` |
| status-report-server | 8083 | 5003 | `http://10.0.151.101:8083/` |
| iticket-server | 8084 | 5004 | `http://10.0.151.101:8084/` |
| iupstream-server | 8085 | 5005 | `http://10.0.151.101:8085/` |
| isdlc-server | 8086 | 5004 | `http://10.0.151.101:8086/` |
| **k8s-agent-tools** | **8087** | **5006** | **`http://10.0.151.101:8087/`** |

All servers share the navigation Ecosystem and Servers dropdowns for
cross-server navigation.

---

## Demo Mode

The server is designed to be impressive without any API keys or live data.
Every feature has a "demo-first" fallback:

- **Seed Demo Data** buttons populate plans, team portal, and history
- **Pre-filled inputs** on Execute and Analysis pages point to working
  sample paths from the plugin's `tests/sample-operator/` directory
- **Demo Walk Through** page (`/demo`) provides a guided, numbered,
  step-by-step tour of every feature with a scroll-tracking progress bar
- **Reset Demo** button (`/demo` or `POST /api/demo/reset`) clears all
  runtime data back to first-deploy state while preserving user accounts

### Demo Walk Through

Click the glowing orange **DEMO** button in the navigation bar to access
the guided walk-through. The 9-step tour covers:

1. Splash page
2. Registration and login
3. Dashboard with trend indicators
4. Skill catalog and execution (with pre-filled paths)
5. Plan monitoring with demo data
6. Team portal with Jira/GitHub/Gerrit demo data
7. Analysis dashboards with auto-filled paths
8. History and reporting with 7-day demo data
9. Production deployment overview

All links on the demo page open in new tabs, keeping the walk-through as
a persistent "home base."

---

## Design Documentation

Each phase has a complete set of design, implementation, and step-by-step
documents:

### Reverse Engineering (Plugin Analysis)

- [Reverse-Engineered Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_REVERSE_ENGINEERED_DESIGN.md) — Full architecture analysis of the original plugin
- [Reverse-Engineered Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_REVERSE_ENGINEERED_IMPLEMENTATION.md) — Detailed code-level analysis

### Server Roadmap

- [Phase X Design (Comprehensive Roadmap)](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_X_DESIGN.md)
- [Phase X Implementation (Comprehensive Roadmap)](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_X_IMPLEMENTATION.md)

### Per-Phase Documentation

| Phase | Design | Implementation | Step-by-Step |
|---|---|---|---|
| 1 — Core + Dashboard | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_1_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_1_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_1_STEP_BY_STEP.md) |
| 2 — Plans + Monitoring | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_2_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_2_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_2_STEP_BY_STEP.md) |
| 3 — Skill Execution | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_3_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_3_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_3_STEP_BY_STEP.md) |
| 4 — Team Portal | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_4_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_4_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_4_STEP_BY_STEP.md) |
| 5 — Analysis | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_5_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_5_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_5_STEP_BY_STEP.md) |
| 6 — History + Reporting | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_6_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_6_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_6_STEP_BY_STEP.md) |
| 7 — Production Deploy | [Design](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_7_DESIGN.md) | [Implementation](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_7_IMPLEMENTATION.md) | [Step-by-Step](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_7_STEP_BY_STEP.md) |

### Additional Documentation

- [Demo Walk Through](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_DEMO_WALK_THROUGH.md) — Concise guide for demo presentations
- [Claude vs Cursor Analysis](https://gitlab.cee.redhat.com/omcgonag/iproject/-/blob/master/projects/openstack_k8s_agent_tools/docs/OPENSTACK_K8S_AGENT_TOOLS_SERVER_PHASE_X_CLAUDE_VS_CURSOR.md) — AI runtime comparison for the 5 AI-backed skills

---

## API Endpoints

The server exposes a REST API alongside the web UI. All endpoints require
authentication (session cookie).

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check (no auth required) |
| POST | `/api/execute/<skill>` | Trigger skill execution |
| GET | `/api/executions` | List all executions |
| GET | `/api/executions/<id>` | Execution detail |
| GET | `/api/executions/<id>/log` | Execution log (for polling) |
| GET | `/api/plans` | List all plans |
| GET | `/api/plans/<operator>/<slug>/state` | Plan state.json |
| GET | `/api/history` | History snapshots |
| POST | `/api/history/snapshot` | Capture today's snapshot |
| POST | `/api/history/seed-demo` | Seed 7 days of demo history |
| GET | `/api/reports` | List generated reports |
| GET | `/api/jira/<project>` | Jira issues for project |
| GET | `/api/github/prs` | GitHub pull requests |
| GET | `/api/gerrit/reviews` | Gerrit reviews |
| POST | `/api/demo/reset` | Reset all demo/runtime data |

---

## License

This server wraps [fmount/openstack-k8s-agent-tools](https://github.com/fmount/openstack-k8s-agent-tools).
See the upstream repository for plugin licensing.
