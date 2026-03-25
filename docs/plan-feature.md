# /plan-feature — Feature Planning Guide

Plan features and bug fixes for openstack-k8s-operators operators with Jira integration, cross-repo analysis, and structured implementation strategies.

## Quickstart

```bash
# From a Jira ticket (requires Atlassian MCP configured)
/plan-feature OSPRH-2345

# From a local spec file
/plan-feature docs/my-feature-spec.md

# Interactive — the skill asks what you have
/plan-feature
```

## What It Does

1. **Reads the input** — fetches a Jira ticket via Atlassian MCP, or reads a local markdown spec file
2. **Analyzes the codebase** — reads your operator's controllers, API types, webhooks, and tests
3. **Cross-references** — checks lib-common for existing helpers, peer operators for prior art, dev-docs for conventions
4. **Runs a planning checklist** — assesses 11 principles (API changes, lib-common reuse, webhooks, conditions, EnvTest, kuttl, RBAC, code style, etc.)
5. **Proposes 2-3 strategies** — with trade-offs, risks, and a recommendation
6. **Produces a task breakdown** — grouped by functional area (API, controller, testing, docs)
7. **Writes a plan file** — to `docs/plans/YYYY-MM-DD-<ticket>-plan.md` for `/task-executor` to execute

## Prerequisites

- **Atlassian MCP** (optional): configure in Claude Code settings for Jira integration. Without it, use spec files or paste content directly.
- **GitHub CLI** (optional): `gh` for browsing lib-common and peer operators when local checkouts aren't available.

## Use Case: Adding Topology Support to an Operator

You're working on `heat-operator` and need to add topology/affinity support (Jira: `OSPRH-4567`).

### Step 1: Invoke the skill

```bash
cd ~/go/src/github.com/openstack-k8s-operators/heat-operator
/plan-feature OSPRH-4567
```

### Step 2: The skill fetches and normalizes the ticket

```
## Context Summary

**Source:** OSPRH-4567 (Jira)
**Type:** Story
**Priority:** Major

### Problem Statement
Heat operator does not support topology spread constraints or pod affinity.
Deployers need control over pod placement for HA configurations.

### Requirements
1. Add topology/affinity fields to HeatAPI and HeatEngine specs
2. Follow the lib-common topology CR pattern
3. Propagate topology constraints to generated pods

### Acceptance Criteria
- [ ] HeatAPI and HeatEngine specs accept topology overrides
- [ ] Pods are scheduled respecting topology constraints
- [ ] EnvTest coverage for topology reconciliation
```

### Step 3: Cross-repo analysis

The skill checks your local checkouts (or GitHub) and reports:

```
## Impact Analysis

**Affected controllers:** HeatAPI, HeatEngine
**Affected API types:** HeatAPISpec, HeatEngineSpec

**lib-common:** common/affinity and common/topology modules already provide
TopologySpreadConstraints helpers — use these, do not reimplement.

**Prior art:** nova-operator and cinder-operator both implemented topology
support. nova-operator's approach (PR #423) is the closest match.

**dev-docs:** No specific topology convention doc, but the topology CR
pattern is established in lib-common.
```

### Step 4: Planning checklist

| Principle | Assessment |
|-----------|-----------|
| API Changes | **Yes** — add `TopologyRef` field to HeatAPISpec and HeatEngineSpec |
| lib-common Reuse | **Yes** — use `common/topology` module |
| Code Duplication | **Yes** — nova-operator has the same pattern, follow it |
| Webhook Changes | **Yes** — add defaulting for topology fields |
| Status Conditions | **No** — no new conditions needed |
| EnvTest Tests | **Yes** — test topology propagation to pods |
| Kuttl Tests | **N/A** — EnvTest is sufficient |
| RBAC | **Yes** — need watch on Topology CR |

### Step 5: Implementation strategies

The skill proposes approaches (e.g., "follow nova-operator exactly" vs "simplified version without TopologyRef") with trade-offs. You pick one.

### Step 6: Task breakdown

```
## Group 1: API Changes
- [ ] Task 1.1: Add TopologyRef to HeatAPISpec and HeatEngineSpec
- [ ] Task 1.2: Run make manifests generate
- [ ] Task 1.3: Add webhook defaulting for topology fields

## Group 2: Controller Logic
- [ ] Task 2.1: Reconcile topology constraints into pod specs
- [ ] Task 2.2: Add RBAC markers for Topology CR

## Group 3: Testing
- [ ] Task 3.1: Add EnvTest cases for topology propagation
```

### Step 7: Execute the plan

```bash
/task-executor docs/plans/2026-03-25-OSPRH-4567-plan.md
```

The task-executor picks up the plan file, shows progress, and executes tasks one by one with checkpointing. You can quit and resume anytime.

## Related Skills

- **`/task-executor`** — executes plans produced by `/plan-feature`
- **`/code-review`** — reviews code against the same conventions the planner checks
- **`/debug-operator`** — useful when the ticket is a bug and you need runtime analysis first
- **`/test-operator`** — run tests during or after plan execution

## Reference

- [Design spec](specs/2026-03-25-plan-feature-enhancement-design.md)
- [agents/plan-feature/AGENT.md](../agents/plan-feature/AGENT.md) — full planning methodology
- [agents/task-executor/AGENT.md](../agents/task-executor/AGENT.md) — execution principles
