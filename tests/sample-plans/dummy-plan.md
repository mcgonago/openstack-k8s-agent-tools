# Dummy Plan: Add Widget Support

> Test plan for validating memory, state tracking, worktree, and dependency resolution.

plan-version: 1

## Context Summary

**Source:** TEST-001 (test)
**Type:** Story
**Priority:** Major

### Problem Statement

The test-operator needs widget support for validation testing.

### Requirements

1. Add a WidgetSpec field to the API types
2. Reconcile widgets in the controller
3. Add EnvTest coverage

## Impact Analysis

**Affected controllers:** TestController
**Affected API types:** TestSpec

**lib-common:** No existing helpers needed.
**Prior art:** None.

## Planning Checklist

| Principle | Assessment |
|-----------|-----------|
| API Changes | Yes |
| lib-common Reuse | No |
| Code Style | Yes |
| EnvTest Tests | Yes |
| RBAC | No |

## Implementation Strategies

### Strategy A: Direct implementation (SELECTED)

Add WidgetSpec field and reconcile directly.

## Task Breakdown

### Group 1: API Changes

- [ ] **Task 1.1: Add WidgetSpec field**
  - **Files:** api/v1beta1/test_types.go
  - **Acceptance:** File contains WidgetSpec struct

- [ ] **Task 1.2: Run make manifests**
  - **Files:** config/crd/
  - **Depends on:** Task 1.1
  - **Acceptance:** make manifests runs cleanly

### Group 2: Controller Logic

- [ ] **Task 2.1: Reconcile widgets**
  - **Files:** controllers/test_controller.go
  - **Depends on:** Task 1.1, Task 1.2
  - **Acceptance:** Controller handles WidgetSpec

### Group 3: Testing

- [ ] **Task 3.1: Add EnvTest for widgets**
  - **Files:** test/functional/test_controller_test.go
  - **Depends on:** Task 2.1
  - **External dep:** lib-common PR #999
  - **Acceptance:** Tests pass
