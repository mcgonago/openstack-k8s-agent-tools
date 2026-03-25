#!/bin/bash

# openstack-k8s-operators Operator Tools Plugin Test Suite
# Validates plugin functionality and components

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test functions
run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN] $test_name${NC}"

    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}  ✅ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}  ❌ FAILED${NC}"
        echo -e "${YELLOW}     Command: $test_command${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# File existence tests
test_file_exists() {
    local file="$1"
    local description="$2"

    run_test "$description" "[ -f '$file' ]"
}

test_executable() {
    local file="$1"
    local description="$2"

    run_test "$description" "[ -x '$file' ]"
}

# JSON validation tests
test_json_valid() {
    local file="$1"
    local description="$2"

    run_test "$description" "jq . '$file' >/dev/null 2>&1"
}

# Node.js script tests
test_node_script() {
    local script="$1"
    local description="$2"

    run_test "$description" "node '$script' --help >/dev/null 2>&1"
}

# Main test suite
run_plugin_tests() {
    echo -e "${BLUE}🧪 openstack-k8s-operators Operator Tools Plugin Test Suite${NC}"
    echo "=========================================="
    echo

    # Test plugin structure
    echo -e "${YELLOW}📂 Testing Plugin Structure${NC}"
    test_file_exists ".claude-plugin/plugin.json" "Plugin metadata exists"
    test_json_valid ".claude-plugin/plugin.json" "Plugin metadata is valid JSON"

    # Discover and test skills
    echo -e "\n${YELLOW}🎯 Testing Skills${NC}"
    for skill_dir in skills/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        test_file_exists "${skill_dir}SKILL.md" "Skill '$skill_name' has SKILL.md"

        # Validate frontmatter has required fields
        if [ -f "${skill_dir}SKILL.md" ]; then
            frontmatter=$(sed -n '2,/^---$/p' "${skill_dir}SKILL.md" | head -n -1)
            for field in name description user-invocable; do
                if echo "$frontmatter" | grep -q "^${field}:"; then
                    run_test "Skill '$skill_name' has '$field' field" "true"
                else
                    run_test "Skill '$skill_name' has '$field' field" "false"
                fi
            done

            # If skill references an agent, check it exists
            if grep -q "agents/${skill_name}/AGENT.md" "${skill_dir}SKILL.md"; then
                test_file_exists "agents/${skill_name}/AGENT.md" "Skill '$skill_name' has matching AGENT.md"
            fi
        fi
    done

    # Discover and test agents
    echo -e "\n${YELLOW}🤖 Testing Agents${NC}"
    for agent_dir in agents/*/; do
        [ -d "$agent_dir" ] || continue
        agent_name=$(basename "$agent_dir")
        test_file_exists "${agent_dir}AGENT.md" "Agent '$agent_name' has AGENT.md"

        # Check agent has meaningful content (>10 lines)
        if [ -f "${agent_dir}AGENT.md" ]; then
            lines=$(wc -l < "${agent_dir}AGENT.md")
            run_test "Agent '$agent_name' has content (${lines} lines)" "[ $lines -gt 10 ]"
        fi
    done

    # Discover and test lib helpers
    echo -e "\n${YELLOW}📦 Testing Lib${NC}"
    for f in lib/*.sh; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        test_file_exists "$f" "Lib '$name' exists"
        test_executable "$f" "Lib '$name' is executable"
    done
    for f in lib/*.js; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        test_file_exists "$f" "Lib '$name' exists"
    done
    for f in lib/*.json; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        test_file_exists "$f" "Lib '$name' exists"
        test_json_valid "$f" "Lib '$name' is valid JSON"
    done

    # Discover and test scripts
    echo -e "\n${YELLOW}📜 Testing Scripts${NC}"
    for f in scripts/*.sh; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        test_file_exists "$f" "Script '$name' exists"
        test_executable "$f" "Script '$name' is executable"
    done

    # Test documentation
    echo -e "\n${YELLOW}📚 Testing Documentation${NC}"
    test_file_exists "README.md" "README exists"
    test_file_exists "CLAUDE.md" "Claude development guide exists"
    test_file_exists "LICENSE" "License exists"
    test_file_exists "package.json" "Package.json exists"
    test_json_valid "package.json" "Package.json is valid JSON"
}

# Functional tests
run_functional_tests() {
    echo -e "\n${YELLOW}⚙️  Testing Functionality${NC}"

    # Test script help
    run_test "Install script help" "./scripts/install.sh --help >/dev/null 2>&1"

    # Test lib tools
    run_test "Log analyzer patterns" "node lib/log-analyzer.js --patterns >/dev/null 2>&1"
    run_test "Code parser help" "node lib/code-parser.js --help >/dev/null 2>&1"
    run_test "Dev workflow help" "./lib/dev-workflow.sh help >/dev/null 2>&1"
    run_test "Test workflow help" "./lib/test-workflow.sh help >/dev/null 2>&1"
}

# Plugin validation tests
run_plugin_validation() {
    echo -e "\n${YELLOW}✅ Testing Plugin Validation${NC}"

    # Check plugin.json structure
    if [ -f ".claude-plugin/plugin.json" ]; then
        local has_name=$(jq '.name' .claude-plugin/plugin.json 2>/dev/null)
        local has_version=$(jq '.version' .claude-plugin/plugin.json 2>/dev/null)
        local has_skills=$(jq '.skills' .claude-plugin/plugin.json 2>/dev/null)

        run_test "Plugin has name field" "[ '$has_name' != 'null' ]"
        run_test "Plugin has version field" "[ '$has_version' != 'null' ]"
        run_test "Plugin has skills field" "[ '$has_skills' != 'null' ]"
    fi

    # Check skill references
    if command -v jq >/dev/null 2>&1; then
        local skills=$(jq -r '.skills | keys[]' .claude-plugin/plugin.json 2>/dev/null)
        for skill in $skills; do
            local skill_file=$(jq -r ".skills[\"$skill\"]" .claude-plugin/plugin.json 2>/dev/null)
            run_test "Skill '$skill' file exists" "[ -f '$skill_file' ]"
        done
    fi
}

# Performance tests
run_performance_tests() {
    echo -e "\n${YELLOW}⚡ Testing Performance${NC}"

    # Test script execution time
    local start_time=$(date +%s.%N)
    ./lib/dev-workflow.sh help >/dev/null 2>&1
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "1")

    run_test "Dev workflow runs quickly (<2s)" "[ $(echo '$duration < 2' | bc -l 2>/dev/null || echo 0) -eq 1 ]"

    # Test log analyzer with small input
    echo "test error message" | timeout 5s node lib/log-analyzer.js - >/dev/null 2>&1
    local exit_code=$?
    run_test "Log analyzer handles input quickly" "[ $exit_code -eq 0 ]"
}

# Security tests
run_security_tests() {
    echo -e "\n${YELLOW}🔒 Testing Security${NC}"

    # Check for hardcoded secrets
    run_test "No hardcoded passwords" "! grep -r -i 'password.*=' . --include='*.js' --include='*.sh' --include='*.md'"
    run_test "No hardcoded tokens" "! grep -r -i 'token.*=' . --include='*.js' --include='*.sh' --include='*.md'"
    run_test "No hardcoded API keys" "! grep -r -i 'apikey.*=' . --include='*.js' --include='*.sh' --include='*.md'"

    # Check file permissions
    run_test "Scripts have safe permissions" "find scripts/ -name '*.sh' -exec test '{}' -perm /o+w \\; -print | wc -l | grep -q '^0$'"
}

# Integration tests
run_integration_tests() {
    echo -e "\n${YELLOW}🔗 Testing Integration${NC}"

    # Test install script check mode
    run_test "Install script check mode" "./scripts/install.sh --check >/dev/null 2>&1"

    # Test plugin installation
    if [ -d "$HOME/.claude/plugins" ]; then
        run_test "Plugin can be installed" "./scripts/install.sh --claude-code >/dev/null 2>&1"
    fi
}

# Summary report
show_summary() {
    echo
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo "==============="
    echo -e "Total tests:  ${TESTS_RUN}"
    echo -e "Passed:       ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed:       ${RED}${TESTS_FAILED}${NC}"
    echo -e "Success rate: $(( TESTS_PASSED * 100 / TESTS_RUN ))%"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed. Please review and fix issues.${NC}"
        exit 1
    fi
}

# Main execution
main() {
    local test_type="${1:-all}"

    case "$test_type" in
        "structure")
            run_plugin_tests
            ;;
        "functional")
            run_functional_tests
            ;;
        "validation")
            run_plugin_validation
            ;;
        "performance")
            run_performance_tests
            ;;
        "security")
            run_security_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "all")
            run_plugin_tests
            run_functional_tests
            run_plugin_validation
            run_performance_tests
            run_security_tests
            run_integration_tests
            ;;
        "help")
            echo "Usage: $0 [test-type]"
            echo "Test types: structure, functional, validation, performance, security, integration, all"
            exit 0
            ;;
        *)
            echo "Unknown test type: $test_type"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac

    show_summary
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
