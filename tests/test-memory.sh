#!/bin/bash

# Test memory, state tracking, worktree isolation, and dependency resolution.
# Simulates the task-executor workflow against a dummy plan.
#
# Usage: bash tests/test-memory.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
TOTAL=0

pass() { PASS=$((PASS + 1)); TOTAL=$((TOTAL + 1)); echo -e "  ${GREEN}PASS${NC} $1"; }
fail() { FAIL=$((FAIL + 1)); TOTAL=$((TOTAL + 1)); echo -e "  ${RED}FAIL${NC} $1"; }

# Setup: create a temp directory simulating the plans directory
TMPDIR=$(mktemp -d)
PLANS_DIR="$TMPDIR/test-operator"
OPERATOR_REPO="$TMPDIR/operator-repo"
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$PLANS_DIR"
mkdir -p "$OPERATOR_REPO"

# Initialize a git repo in the operator repo (needed for worktree tests)
cd "$OPERATOR_REPO"
git init -q
git config --local core.hooksPath /dev/null
git config --local commit.gpgsign false
echo "test" > README.md
git add . && git commit -q --no-verify -m "init"
cd "$SCRIPT_DIR"

PLAN_FILE="$PLANS_DIR/2026-04-11-TEST-001-plan.md"
MEMORY_FILE="$PLANS_DIR/MEMORY.md"
STATE_FILE="$PLANS_DIR/state.json"

# Copy the dummy plan
cp "$SCRIPT_DIR/tests/sample-plans/dummy-plan.md" "$PLAN_FILE"

echo -e "${BLUE}Testing memory, state, worktree, and dependency resolution${NC}"
echo "=========================================="

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 1: MEMORY.md lifecycle${NC}"
# -----------------------------------------------

# Test: create MEMORY.md
cat > "$MEMORY_FILE" << 'EOF'
# test-operator Memory

## Active Work
- TEST-001: Add widget support (plan complete, not started)

## Discoveries
- No existing widget helpers in lib-common

## Decisions
- [2026-04-11] TEST-001: Direct implementation (Strategy A)

## Blockers
- (none currently)
EOF

if [ -f "$MEMORY_FILE" ]; then
    pass "MEMORY.md created"
else
    fail "MEMORY.md not created"
fi

# Test: line count under 200
lines=$(wc -l < "$MEMORY_FILE")
if [ "$lines" -lt 200 ]; then
    pass "MEMORY.md under 200 lines ($lines lines)"
else
    fail "MEMORY.md over 200 lines ($lines lines)"
fi

# Test: contains required sections
for section in "Active Work" "Discoveries" "Decisions" "Blockers"; do
    if grep -q "## $section" "$MEMORY_FILE"; then
        pass "MEMORY.md has '$section' section"
    else
        fail "MEMORY.md missing '$section' section"
    fi
done

# Test: update MEMORY.md with a new discovery
echo "- Widget reconciliation needs special error handling" >> "$MEMORY_FILE"
if grep -q "Widget reconciliation" "$MEMORY_FILE"; then
    pass "MEMORY.md updated with new discovery"
else
    fail "MEMORY.md update failed"
fi

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 2: state.json lifecycle${NC}"
# -----------------------------------------------

# Test: create state.json
cat > "$STATE_FILE" << 'EOF'
{
  "active_tasks": [],
  "completed": [],
  "discoveries": []
}
EOF

if [ -f "$STATE_FILE" ] && python3 -c "import json; json.load(open('$STATE_FILE'))" 2>/dev/null; then
    pass "state.json created and valid JSON"
else
    fail "state.json creation or validation failed"
fi

# Test: register a task
SESSION_ID="test-session-$(date +%s)"
python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
state['active_tasks'].append({
    'plan': '2026-04-11-TEST-001-plan.md',
    'task': '1.1',
    'worktree': '.worktrees/TEST-001',
    'branch': 'feature/TEST-001',
    'session': '$SESSION_ID',
    'started': '2026-04-11T10:30:00Z'
})
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
active_count=$(python3 -c "import json; print(len(json.load(open('$STATE_FILE'))['active_tasks']))")
if [ "$active_count" -eq 1 ]; then
    pass "state.json: task registered in active_tasks"
else
    fail "state.json: task not registered (count: $active_count)"
fi

# Test: session ID stored
stored_session=$(python3 -c "import json; print(json.load(open('$STATE_FILE'))['active_tasks'][0]['session'])")
if [ "$stored_session" = "$SESSION_ID" ]; then
    pass "state.json: session ID stored correctly"
else
    fail "state.json: session ID mismatch (got: $stored_session)"
fi

# Test: duplicate detection (same plan+task, different session)
DUPLICATE_SESSION="other-session-123"
python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    state = json.load(f)
for task in state['active_tasks']:
    if task['plan'] == '2026-04-11-TEST-001-plan.md' and task['task'] == '1.1':
        if task['session'] != '$DUPLICATE_SESSION':
            print('CONFLICT: task owned by session', task['session'])
            sys.exit(0)
sys.exit(1)
" && pass "state.json: duplicate detection works (different session)" \
  || fail "state.json: duplicate detection failed"

# Test: complete a task
python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
state['active_tasks'] = [t for t in state['active_tasks'] if t['task'] != '1.1']
state['completed'].append({
    'plan': '2026-04-11-TEST-001-plan.md',
    'completed': '2026-04-11T11:00:00Z',
    'commit': 'abc1234',
    'session': '$SESSION_ID'
})
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
active_count=$(python3 -c "import json; print(len(json.load(open('$STATE_FILE'))['active_tasks']))")
completed_count=$(python3 -c "import json; print(len(json.load(open('$STATE_FILE'))['completed']))")
if [ "$active_count" -eq 0 ] && [ "$completed_count" -eq 1 ]; then
    pass "state.json: task moved from active to completed"
else
    fail "state.json: task completion failed (active: $active_count, completed: $completed_count)"
fi

# Test: add discovery
python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
discovery = 'Widget reconciliation needs special error handling'
if discovery not in state['discoveries']:
    state['discoveries'].append(discovery)
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
disc_count=$(python3 -c "import json; print(len(json.load(open('$STATE_FILE'))['discoveries']))")
if [ "$disc_count" -eq 1 ]; then
    pass "state.json: discovery added"
else
    fail "state.json: discovery not added (count: $disc_count)"
fi

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 3: Worktree isolation${NC}"
# -----------------------------------------------

cd "$OPERATOR_REPO"

# Test: create worktree
WORKTREE_DIR=".worktrees/TEST-001"
BRANCH="feature/TEST-001"
git worktree add -b "$BRANCH" "$WORKTREE_DIR" -q 2>/dev/null
if [ -d "$WORKTREE_DIR" ]; then
    pass "Worktree created at $WORKTREE_DIR"
else
    fail "Worktree creation failed"
fi

# Test: worktree is on correct branch
worktree_branch=$(git -C "$WORKTREE_DIR" rev-parse --abbrev-ref HEAD)
if [ "$worktree_branch" = "$BRANCH" ]; then
    pass "Worktree is on branch $BRANCH"
else
    fail "Worktree on wrong branch (got: $worktree_branch)"
fi

# Test: changes in worktree don't affect main
echo "widget code" > "$WORKTREE_DIR/widget.go"
if [ ! -f "widget.go" ]; then
    pass "Worktree changes isolated from main"
else
    fail "Worktree changes leaked to main"
fi

# Test: cleanup worktree
git worktree remove "$WORKTREE_DIR" -f 2>/dev/null
git branch -D "$BRANCH" -q 2>/dev/null
if [ ! -d "$WORKTREE_DIR" ]; then
    pass "Worktree cleaned up"
else
    fail "Worktree cleanup failed"
fi

cd "$SCRIPT_DIR"

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 4: Dependency resolution${NC}"
# -----------------------------------------------

# Test: intra-plan dependency (Task 1.1 not done -> Task 2.1 blocked)
task_1_1_done=$(grep -c "\[x\].*Task 1.1" "$PLAN_FILE" || true)
if [ "$task_1_1_done" -eq 0 ]; then
    pass "Intra-plan: Task 1.1 not done -> Task 2.1 correctly blocked"
else
    fail "Intra-plan: Task 1.1 should not be done yet"
fi

# Test: mark Task 1.1 as done and verify dependency resolves
sed -i 's/- \[ \] \*\*Task 1.1/- [x] **Task 1.1/' "$PLAN_FILE"
task_1_1_done=$(grep -c "\[x\].*Task 1.1" "$PLAN_FILE" || true)
if [ "$task_1_1_done" -eq 1 ]; then
    pass "Intra-plan: Task 1.1 marked done"
else
    fail "Intra-plan: Failed to mark Task 1.1 done"
fi

# Test: Task 2.1 still blocked (depends on 1.1 AND 1.2)
task_1_2_done=$(grep -c "\[x\].*Task 1.2" "$PLAN_FILE" || true)
if [ "$task_1_2_done" -eq 0 ]; then
    pass "Intra-plan: Task 2.1 still blocked (Task 1.2 not done)"
else
    fail "Intra-plan: Task 1.2 should not be done yet"
fi

# Test: mark Task 1.2 as done -> Task 2.1 unblocked
sed -i 's/- \[ \] \*\*Task 1.2/- [x] **Task 1.2/' "$PLAN_FILE"
task_1_1_done=$(grep -c "\[x\].*Task 1.1" "$PLAN_FILE" || true)
task_1_2_done=$(grep -c "\[x\].*Task 1.2" "$PLAN_FILE" || true)
if [ "$task_1_1_done" -eq 1 ] && [ "$task_1_2_done" -eq 1 ]; then
    pass "Intra-plan: Task 2.1 unblocked (both deps done)"
else
    fail "Intra-plan: Task 2.1 should be unblocked"
fi

# Test: external dependency detection
if grep -q "External dep:" "$PLAN_FILE"; then
    pass "External dependency detected in plan (Task 3.1 -> lib-common PR #999)"
else
    fail "External dependency not found in plan"
fi

# Test: cross-plan dependency format
# Add a cross-plan dep line directly
echo '  - **Cross-plan dep:** TEST-002/Task 1.1' >> "$PLAN_FILE"
if grep -q "TEST-002/Task 1.1" "$PLAN_FILE"; then
    pass "Cross-plan dependency format supported"
else
    fail "Cross-plan dependency format not found"
fi

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 5: Plan file checkpointing${NC}"
# -----------------------------------------------

# Test: checkpoint (mark task done, verify file updated)
completed_count=$(grep -c "\[x\]" "$PLAN_FILE" || true)
total_count=$(grep -c "\[.\]" "$PLAN_FILE" || true)
if [ "$completed_count" -eq 2 ] && [ "$total_count" -ge 4 ]; then
    pass "Checkpointing: 2/4+ tasks marked done in plan file"
else
    fail "Checkpointing: unexpected state (completed: $completed_count, total: $total_count)"
fi

# Test: find next pending task
next_task=$(grep -m1 "\[ \]" "$PLAN_FILE" | sed 's/.*\*\*Task \([0-9.]*\):.*/\1/')
if [ -n "$next_task" ]; then
    pass "Next pending task found: Task $next_task"
else
    fail "No pending task found"
fi

# -----------------------------------------------
echo -e "\n${YELLOW}Phase 6: MEMORY.md pruning${NC}"
# -----------------------------------------------

# Test: generate a large MEMORY.md and verify pruning logic
large_memory="$PLANS_DIR/MEMORY-large.md"
{
    echo "# test-operator Memory"
    echo ""
    echo "## Active Work"
    for i in $(seq 1 50); do
        echo "- TEST-$i: Task $i (in progress)"
    done
    echo ""
    echo "## Discoveries"
    for i in $(seq 1 100); do
        echo "- Discovery $i: something learned"
    done
    echo ""
    echo "## Decisions"
    for i in $(seq 1 60); do
        echo "- [2026-01-01] Decision $i"
    done
} > "$large_memory"

large_lines=$(wc -l < "$large_memory")
if [ "$large_lines" -gt 200 ]; then
    pass "Large MEMORY.md generated ($large_lines lines, over 200 limit)"
else
    fail "Large MEMORY.md should be over 200 lines (got: $large_lines)"
fi

# Simulate pruning: keep last 5 active, 10 discoveries, 10 decisions
{
    echo "# test-operator Memory"
    echo ""
    echo "## Active Work"
    tail -5 <(grep "^- TEST-" "$large_memory")
    echo ""
    echo "## Discoveries"
    tail -10 <(grep "^- Discovery" "$large_memory")
    echo ""
    echo "## Decisions"
    tail -10 <(grep "^- \[" "$large_memory")
    echo ""
    echo "## Blockers"
    echo "- (none currently)"
} > "$PLANS_DIR/MEMORY-pruned.md"

pruned_lines=$(wc -l < "$PLANS_DIR/MEMORY-pruned.md")
if [ "$pruned_lines" -lt 200 ]; then
    pass "Pruned MEMORY.md is under 200 lines ($pruned_lines lines)"
else
    fail "Pruned MEMORY.md still over 200 lines ($pruned_lines lines)"
fi

# -----------------------------------------------
echo ""
echo "=========================================="
echo -e "${BLUE}Test Summary${NC}"
echo "=========================================="
echo -e "Total:   $TOTAL"
echo -e "Passed:  ${GREEN}$PASS${NC}"
echo -e "Failed:  ${RED}$FAIL${NC}"

if [ "$FAIL" -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed.${NC}"
    exit 1
fi
