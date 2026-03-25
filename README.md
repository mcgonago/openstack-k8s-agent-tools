# openstack-k8s-operators Operator Tools

Claude Code plugin for [openstack-k8s-operators](https://github.com/openstack-k8s-operators/) development — debugging, testing, code review, feature planning, and plan execution.

## Installation

### Claude Code (recommended)

Install via the plugin marketplace:

```bash
/plugin install openstack-k8s-agent-tools
```

Or clone and install manually:

```bash
git clone https://github.com/openstack-k8s-operators/operator-tools.git
cd operator-tools
./scripts/install.sh --claude-code
```

### OpenCode

```bash
./scripts/install.sh --opencode
```

### Check dependencies

```bash
./scripts/install.sh --check
```

## Dependencies

| Dependency | Required | Purpose |
|-----------|----------|---------|
| Go toolchain | Yes | Operator development, tests, linting |
| make | Yes | Build system (make test, make manifests, etc.) |
| gh (GitHub CLI) | Optional | Cross-repo analysis in `/plan-feature` when local checkouts aren't available |
| Atlassian MCP | Optional | Jira ticket reading in `/plan-feature` — configure in Claude Code settings |
| golangci-lint | Optional | Enhanced linting in `/test-operator` |
| gosec, govulncheck | Optional | Security scanning in `/test-operator security` |

## Skills

| Skill | Purpose |
|-------|---------|
| `/debug-operator` | Development workflow + runtime debugging |
| `/test-operator` | Testing & QA — quick, standard, full, security, coverage |
| `/code-style` | Go code style enforcement (gopls modernize, conventions) |
| `/analyze-logs` | Log pattern recognition (25+ patterns) |
| `/explain-flow` | Code flow analysis for controllers |
| `/plan-feature` | Feature/bug planning with Jira, cross-repo analysis, structured strategies |
| `/code-review` | Code review against openstack-k8s-operators conventions |
| `/task-executor` | Execute plans task-by-task with checkpointing and resume |

## Quickstart

### Plan and implement a feature from a Jira ticket

```bash
cd ~/go/src/github.com/openstack-k8s-operators/heat-operator

# Plan from Jira (requires Atlassian MCP)
/plan-feature OSPRH-4567

# Or plan from a local spec file
/plan-feature docs/my-feature-spec.md
```

The skill fetches the ticket, analyzes your codebase and cross-references lib-common and peer operators, runs an 11-principle planning checklist, proposes implementation strategies, and produces a task breakdown. Then execute it:

```bash
/task-executor docs/plans/2026-03-25-OSPRH-4567-plan.md
```

See [docs/plan-feature.md](docs/plan-feature.md) for a full walkthrough.

### Development loop

```bash
# Fast feedback while coding
/test-operator quick

# Run focused tests
/test-operator focus "Checks the Topology"

# Check code style
/code-style
```

### Pre-PR validation

```bash
# Full test suite + linting + security
/test-operator full

# Review your changes
/code-review
```

### Debugging a deployed operator

```bash
# Systematic debugging workflow
/debug-operator nova-operator openstack

# Analyze collected logs
kubectl logs deployment/nova-operator -n openstack > nova.log
/analyze-logs nova.log
```

## Workflows

### Feature Development

```
/plan-feature OSPRH-2345
    │
    ├── Fetches Jira ticket (or reads spec file)
    ├── Analyzes codebase + lib-common + peer operators + dev-docs
    ├── Runs planning checklist (API, webhooks, conditions, tests, RBAC, ...)
    ├── Proposes 2-3 strategies → you pick one
    └── Writes plan to docs/plans/

/task-executor docs/plans/...-plan.md
    │
    ├── Executes tasks sequentially with checkpointing
    ├── Test-first for new reconciliation paths
    ├── Pauses at group boundaries for review
    └── Resume anytime — progress saved to plan file

/test-operator full → /code-review → submit PR
```

### Bug Fix

```
/analyze-logs operator-error.log    → identify patterns
/debug-operator                     → systematic diagnosis
/plan-feature OSPRH-6789            → plan the fix (includes root cause + regression test)
/task-executor docs/plans/...-plan.md → implement
/test-operator full                 → validate
```

### Daily Development

```
/test-operator quick                → fast feedback (~10s)
/test-operator focus "pattern"      → iterate on specific tests
/code-style                         → check conventions
/test-operator standard             → pre-commit validation
/code-review                        → self-review before PR
```

## Documentation

- **[Getting Started](docs/GETTING-STARTED.md)** — quick reference for all skills
- **[Plan Feature Guide](docs/plan-feature.md)** — detailed walkthrough with use case
- **[Development Guide](docs/DEVELOPMENT.md)** — extending the plugin with new skills
- **[CLAUDE.md](CLAUDE.md)** — project conventions and skill reference

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add skills following existing patterns (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md))
4. Test with real openstack-k8s-operators operators
5. Submit a pull request

## License

MIT — see [LICENSE](LICENSE).
