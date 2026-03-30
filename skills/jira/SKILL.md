---
name: jira
description: Jira integration for openstack-k8s-operators workflows. Reads tickets, validates hierarchy (epic/story/task), posts outcome comments, and suggests story/task creation. Used by /feature and /task-executor as a shared reference.
user-invocable: true
allowed-tools: ["Bash", "Read", "Write", "Grep"]
context: fork
---

Jira integration skill for openstack-k8s-operators development workflows.

When invoked directly (`/jira OSPRH-2345`), inspect the ticket and report its type, hierarchy, and linked issues. When used as a reference by other skills, follow the rules below.

## Ticket Inspection

When given a ticket ID:

1. Fetch the ticket via Atlassian MCP
2. Report: type (epic/story/task/bug), summary, status, priority
3. Show hierarchy: parent epic (if any), linked stories, sub-tasks
4. Flag any hierarchy issues (see Hierarchy Rules below)

## Hierarchy Rules

openstack-k8s-operators Jira follows this structure:

```
Epic (OSPRH-1000)
  represents a large feature or initiative
  |
  +-- Story (OSPRH-2345)
  |     represents a single deliverable unit of work
  |     maps to one PR (or a small set of related PRs)
  |     |
  |     +-- Task (OSPRH-2346)   optional, from plan breakdown
  |     +-- Task (OSPRH-2347)
  |
  +-- Story (OSPRH-2350)
```

### Key Rules

1. **Comments go on the Story, never on the Epic.** The story is the unit of work that maps to a PR. The epic is the container — it doesn't need implementation details.

2. **If the ticket is an Epic with no linked Story**, the user should create a story first. Do NOT post outcome comments directly on epics.

3. **If the ticket is a Story**, it should be linked to an Epic (warn if orphaned, but proceed).

4. **Tasks are optional.** Each task in the plan breakdown *can* become a Jira task under the story, but only if the user explicitly requests it.

5. **Bugs follow story rules.** A bug is treated like a story for hierarchy purposes — it should be linked to an epic and receives outcome comments.

## Operations

### Read Ticket

Fetch and normalize a Jira ticket into a structured summary:

```
Ticket: OSPRH-2345
Type: Story
Status: In Progress
Priority: Major
Summary: Add topology support to HeatAPI
Epic: OSPRH-1000 (Heat operator enhancements)
Sub-tasks: none
```

If the Atlassian MCP is not available, report the error and suggest the user provide the ticket details manually.

### Validate Hierarchy

Before any write operation, check the hierarchy:

```
Hierarchy check for OSPRH-2345:
  Type: Story
  Parent epic: OSPRH-1000 (Heat operator enhancements)
  Status: OK — story is linked to an epic
```

Or:

```
Hierarchy check for OSPRH-1000:
  Type: Epic
  Linked stories: none
  Status: WARNING — this is an epic with no stories.
    A story should be created under this epic before
    posting implementation outcomes.
```

When the ticket is an epic with no stories, suggest creating one:

```
This ticket is an Epic. To track implementation work, create a Story under it:

  Project: OSPRH
  Type: Story
  Summary: <suggested based on plan context>
  Epic Link: OSPRH-1000
  Description: <suggested based on plan context>

Create this story in Jira, then re-run with the story ID.
```

Do NOT create the story automatically — provide the fields and let the user create it.

### Post Outcome Comment

When `/task-executor` completes implementation and the user approves posting to Jira:

1. **Validate hierarchy** — ensure the target is a story or bug, not an epic
2. **Compose the comment:**

```
Implementation completed for OSPRH-2345.

Commit: abc1234
Branch: feature/topology-support

Summary:
- Added TopologyRef field to HeatAPISpec and HeatEngineSpec
- Reconciler propagates topology constraints to pod specs
- EnvTest coverage for topology reconciliation path

Files changed:
- api/v1beta1/heatapi_types.go
- controllers/heatapi_controller.go
- test/functional/heatapi_controller_test.go

Plan: ~/.local/share/openstack-k8s-agent-tools/plans/heat-operator/2026-03-25-OSPRH-2345-plan.md
```

3. **Present to the user for approval** before posting
4. Post via Atlassian MCP if approved
5. If MCP is not available, provide the comment text for manual pasting

### Suggest Task Creation

When the user wants to export plan tasks to Jira:

1. **Validate hierarchy** — tasks go under a story, not an epic
2. For each task group in the plan, present the suggested Jira tasks:

```
Suggested Jira tasks under OSPRH-2345:

Group 1: API Changes
  - Task: Add TopologyRef to HeatAPISpec and HeatEngineSpec
  - Task: Run make manifests generate
  - Task: Add webhook defaulting for topology fields

Group 2: Controller Logic
  - Task: Reconcile topology constraints into pod specs
  - Task: Add RBAC markers for Topology CR

Create these in Jira? (group by group)
```

3. Do NOT create tasks automatically — present the fields and let the user decide per group

## Integration with Other Skills

### /feature uses this skill to:
- Read and normalize Jira tickets (input routing)
- Validate hierarchy before planning
- Warn if an epic needs a story created first

### /task-executor uses this skill to:
- Post outcome comments after implementation
- Suggest task creation from plan breakdown

### /jira standalone:
- Inspect any ticket: `/jira OSPRH-2345`
- Check hierarchy: `/jira OSPRH-1000 --hierarchy`
