#!/bin/bash

# openstack-k8s-operators Operator Testing and Quality Assurance Workflow
# Comprehensive testing, linting, and security scanning

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Track results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if we're in an operator directory
check_operator_directory() {
    if [ ! -f "Makefile" ] || [ ! -f "go.mod" ]; then
        error "Not in an operator directory (Makefile and go.mod not found)"
        return 1
    fi

    local operator_name=$(basename "$(pwd)")
    info "Detected operator: $operator_name"
    return 0
}

# Run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local required="${3:-true}"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "\n${BLUE}[$TESTS_RUN] Running: $test_name${NC}"
    echo "Command: $test_command"

    if eval "$test_command"; then
        success "$test_name passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        if [ "$required" = "true" ]; then
            error "$test_name failed (REQUIRED)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        else
            warn "$test_name failed (optional)"
            return 0
        fi
    fi
}

# Quick tests (fast feedback)
run_quick_tests() {
    echo -e "${BLUE}Running Quick Tests${NC}"
    echo "==================================="

    check_operator_directory || return 1

    run_test "Code Formatting" "make fmt"
    run_test "Static Analysis" "make vet"
    run_test "Go Mod Tidy" "make tidy"

    # Check for uncommitted changes
    if ! git diff --quiet go.mod go.sum; then
        warn "go.mod or go.sum has uncommitted changes after tidy"
    fi

    info "Quick tests completed: $TESTS_PASSED/$TESTS_RUN passed"
}

# Standard tests (pre-commit)
run_standard_tests() {
    echo -e "${BLUE}Running Standard Tests${NC}"
    echo "===================================="

    check_operator_directory || return 1

    run_test "Code Formatting Check" "make gofmt" false
    run_test "Enhanced Static Analysis" "make govet"
    run_test "Standard Linting" "make golangci" false
    run_test "Dependency Check" "make tidy"
    run_test "Unit Tests" "make test"

    info "Standard tests completed: $TESTS_PASSED/$TESTS_RUN passed"
}

# Full tests (pre-PR)
run_full_tests() {
    echo -e "${BLUE}Running Full Test Suite${NC}"
    echo "====================================="

    check_operator_directory || return 1

    # Code generation and validation
    run_test "Generate Manifests" "make manifests"
    run_test "Generate Code" "make generate"

    # Check for generated file changes
    if ! git diff --quiet api/ config/ 2>/dev/null; then
        warn "Generated files have uncommitted changes"
        echo "Changed files:"
        git diff --name-only api/ config/ 2>/dev/null
    fi

    # Comprehensive linting
    run_test "Full Linting" "make golangci-lint" false
    run_test "Operator Linting" "make operator-lint" false
    run_test "Go Lint" "make golint" false

    # Testing
    run_test "Full Test Suite" "make test"
    run_test "CRD Schema Check" "make crd-schema-check" false

    info "Full tests completed: $TESTS_PASSED/$TESTS_RUN passed"
}

# Security scanning
run_security_scan() {
    echo -e "${BLUE}Running Security Scan${NC}"
    echo "================================"

    check_operator_directory || return 1

    # Check for gosec
    if command -v gosec &> /dev/null; then
        run_test "Security Scanning (gosec)" "gosec ./..." false
    else
        warn "gosec not installed. Install with: go install github.com/securego/gosec/v2/cmd/gosec@latest"
    fi

    # Check for govulncheck
    if command -v govulncheck &> /dev/null; then
        run_test "Vulnerability Check" "govulncheck ./..." false
    else
        warn "govulncheck not installed. Install with: go install golang.org/x/vuln/cmd/govulncheck@latest"
    fi

    # Check for staticcheck
    if command -v staticcheck &> /dev/null; then
        run_test "Static Check" "staticcheck ./..." false
    else
        warn "staticcheck not installed. Install with: go install honnef.co/go/tools/cmd/staticcheck@latest"
    fi

    info "Security scan completed: $TESTS_PASSED/$TESTS_RUN passed"
}

# Test coverage analysis
run_coverage_analysis() {
    echo -e "${BLUE}Running Coverage Analysis${NC}"
    echo "===================================="

    check_operator_directory || return 1

    info "Generating coverage report..."
    if make test GINKGO_ARGS="--cover --coverprofile=coverage.out" 2>/dev/null; then
        success "Coverage report generated: coverage.out"

        if [ -f "coverage.out" ]; then
            info "Coverage summary:"
            go tool cover -func=coverage.out | tail -1

            # Parse coverage percentage
            local coverage=$(go tool cover -func=coverage.out | tail -1 | awk '{print $3}' | sed 's/%//')
            if (( $(echo "$coverage >= 80" | bc -l) )); then
                success "Coverage is above 80%: ${coverage}%"
            elif (( $(echo "$coverage >= 60" | bc -l) )); then
                warn "Coverage is moderate: ${coverage}% (target: 80%)"
            else
                error "Coverage is low: ${coverage}% (target: 80%)"
            fi

            info "View detailed coverage: go tool cover -html=coverage.out"
        fi
    else
        error "Failed to generate coverage report"
    fi
}

# Focused test execution
run_focused_test() {
    local pattern="$1"

    if [ -z "$pattern" ]; then
        error "Usage: run_focused_test '<test pattern>'"
        echo "Example: run_focused_test 'initializes the status fields'"
        return 1
    fi

    check_operator_directory || return 1

    echo -e "${BLUE}Running Focused Test${NC}"
    echo "Pattern: $pattern"
    echo "================================"

    run_test "Focused Test: $pattern" "make test GINKGO_ARGS=\"--focus '$pattern' -v\""
}

# Lint only mode
run_lint_only() {
    echo -e "${BLUE}Running Lint Checks Only${NC}"
    echo "======================================"

    check_operator_directory || return 1

    run_test "Code Formatting" "make fmt"
    run_test "Format Check" "make gofmt" false
    run_test "Static Analysis" "make vet"
    run_test "Standard Linting" "make golangci" false
    run_test "Full Linting" "make golangci-lint" false
    run_test "Operator Linting" "make operator-lint" false

    info "Lint checks completed: $TESTS_PASSED/$TESTS_RUN passed"
}

# Fix common issues
run_auto_fix() {
    echo -e "${BLUE}Running Auto-Fix${NC}"
    echo "==============================="

    check_operator_directory || return 1

    info "Applying automatic fixes..."

    # Format code
    echo "Running go fmt..."
    make fmt

    # Fix imports
    if command -v goimports &> /dev/null; then
        echo "Running goimports..."
        find . -name "*.go" -not -path "./vendor/*" -exec goimports -w {} \;
    fi

    # Tidy dependencies
    echo "Running go mod tidy..."
    make tidy

    # Run golangci-lint with --fix
    echo "Running golangci-lint --fix..."
    if [ -f "$(pwd)/bin/golangci-lint" ]; then
        $(pwd)/bin/golangci-lint run --fix
    elif command -v golangci-lint &> /dev/null; then
        golangci-lint run --fix
    else
        warn "golangci-lint not found, skipping"
    fi

    # Show changes
    if ! git diff --quiet; then
        info "Changes made:"
        git diff --stat
    else
        success "No changes needed"
    fi
}

# Install recommended tools
install_tools() {
    echo -e "${BLUE}Installing Recommended Tools${NC}"
    echo "======================================="

    local tools=(
        "github.com/securego/gosec/v2/cmd/gosec@latest"
        "golang.org/x/vuln/cmd/govulncheck@latest"
        "honnef.co/go/tools/cmd/staticcheck@latest"
        "golang.org/x/tools/cmd/goimports@latest"
        "github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
    )

    for tool in "${tools[@]}"; do
        info "Installing $tool..."
        go install "$tool"
    done

    success "Tools installed successfully"
}

# Show test summary
show_summary() {
    echo
    echo -e "${BLUE}Test Summary${NC}"
    echo "==============="
    echo -e "Total tests:  ${TESTS_RUN}"
    echo -e "Passed:       ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed:       ${RED}${TESTS_FAILED}${NC}"

    if [ $TESTS_RUN -gt 0 ]; then
        local success_rate=$(( TESTS_PASSED * 100 / TESTS_RUN ))
        echo -e "Success rate: ${success_rate}%"
    fi

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}Some tests failed${NC}"
        return 1
    fi
}

# Help menu
show_help() {
    echo -e "${BLUE}openstack-k8s-operators Operator Testing Workflow${NC}"
    echo "====================================="
    echo
    echo "Available commands:"
    echo "  quick             - Quick tests (fmt + vet + tidy)"
    echo "  standard          - Standard tests (quick + lint + test)"
    echo "  full              - Full test suite (all checks)"
    echo "  security          - Security scanning (gosec + govulncheck)"
    echo "  coverage          - Test coverage analysis"
    echo "  focus '<pattern>' - Run focused tests"
    echo "  lint              - Lint checks only"
    echo "  fix               - Auto-fix common issues"
    echo "  install-tools     - Install recommended tools"
    echo
    echo "Examples:"
    echo "  ./test-workflow.sh quick"
    echo "  ./test-workflow.sh focus 'Glance controller'"
    echo "  ./test-workflow.sh full"
}

# Main command dispatcher
main() {
    case "${1:-help}" in
        "quick")
            run_quick_tests
            show_summary
            ;;
        "standard")
            run_standard_tests
            show_summary
            ;;
        "full")
            run_full_tests
            show_summary
            ;;
        "security")
            run_security_scan
            show_summary
            ;;
        "coverage")
            run_coverage_analysis
            ;;
        "focus")
            run_focused_test "$2"
            show_summary
            ;;
        "lint")
            run_lint_only
            show_summary
            ;;
        "fix")
            run_auto_fix
            ;;
        "install-tools")
            install_tools
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Execute main if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
