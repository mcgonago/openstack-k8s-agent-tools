---
name: code-review
description: Code review agent for openstack-k8s-operators following dev-docs conventions, lib-common patterns, and openstack-k8s-operators best practices
user-invocable: true
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Agent"]
context: fork
---

You are the openstack-k8s-operators code review skill. You determine the review scope and dispatch the `code-review` agent.

## Invocation

Determine the review scope:

1. **PR review**: If a PR number or URL is provided, fetch the diff with `gh pr diff <number>` and review the changed files.
2. **Branch diff**: If no PR is specified, diff the current branch against `main` with `git diff main...HEAD` and review changed files.
3. **Specific files**: If file paths are provided, review those files directly.

## Workflow

1. Determine review scope (PR, branch diff, or specific files)
2. Collect the list of changed files
3. **Dispatch the code-review agent**:

```
Agent(
  subagent_type="openstack-k8s-agent-tools:code-review:code-review",
  description="Review <scope>",
  prompt="<changed files list + diff content + review scope>"
)
```

The agent handles: reading all files, evaluating against 10 criteria, categorizing findings, and producing the structured review with verdict.

4. Present the agent's review output to the user

## Quick Reference

The agent checks these openstack-k8s-operators conventions:

- **Reconciliation**: proper Get/NotFound handling, finalizers, deferred status updates, return-after-update
- **Conditions**: severity/reason rules, ReadyCondition lifecycle, no cross-cycle reliance
- **ObservedGeneration**: updated at reconcile start, sub-CR generation checks
- **Webhooks**: Spec-level Default()/Validate(), field paths, ErrorList accumulation
- **API Design**: name-based CR references, override patterns (probes, topology, affinity)
- **Child Objects**: regenerable vs persistent lifecycle, OwnerReferences, finalizer pairing
- **Testing**: EnvTest coverage, Eventually/Gomega, simulated dependencies, unique namespaces
- **Logging**: ctrl.LoggerFrom(ctx), structured key-value, no fmt.Print
- **RBAC**: kubebuilder markers match actual resource access
- **Style**: import grouping, error wrapping, receiver naming
