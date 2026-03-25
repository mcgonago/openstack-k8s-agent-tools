# openstack-k8s-operators Operator Tools - Developer Guide

Guide for extending and evolving the openstack-k8s-operators Operator Tools plugin.

## Project Structure

```
openstack-k8s-agent-tools/
├── .claude-plugin/          # Plugin metadata
│   └── plugin.json          # Name, version, description, keywords
├── .claude/                 # Auto-discovered by Claude Code
│   └── skills/              # Symlinked skills for project-local use
├── skills/                  # Skill definitions
│   ├── <skill-name>/
│   │   ├── SKILL.md         # Skill metadata and instructions
│   │   ├── <helper>.sh      # Shell helper scripts
│   │   └── <tool>.js        # Node.js tools (optional)
├── scripts/                 # Utility scripts
│   ├── install.sh           # Installation script
│   └── test-plugin.sh       # Test harness
└── docs/                    # Documentation
    ├── README.md            # User guide overview
    ├── GETTING-STARTED.md   # Quick reference
    └── DEVELOPMENT.md       # This file
```

## Creating Skills

Skills are the core extensibility mechanism. They provide reusable workflows and domain knowledge.

### Skill File Structure

Create a new directory in `skills/`:

```bash
mkdir -p skills/my-skill
cd skills/my-skill
```

### SKILL.md Format

Every skill requires a `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
description: Brief description of what this skill does
user-invocable: true
allowed-tools: ["Bash", "Read", "Grep", "Write", "TaskCreate"]
context: fork
---

# Skill Title

Comprehensive description and instructions for Claude to follow.

## When to Use

Explain when this skill should be invoked.

## Workflow

Detailed step-by-step workflow:

1. **Step 1**: Description
2. **Step 2**: Description
3. **Step 3**: Description

## Helper Scripts

Document any helper scripts included with the skill.

## Examples

Provide usage examples.

## Integration

How this skill integrates with other tools/skills.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier (kebab-case) |
| `description` | Yes | One-line summary for skill discovery |
| `user-invocable` | Yes | `true` if users can call with `/skill-name` |
| `allowed-tools` | Yes | Array of Claude Code tools the skill can use |
| `context` | Yes | `fork` for isolated context, `main` for shared |

### Common Tool Permissions

```yaml
# File operations
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep"]

# Shell execution
allowed-tools: ["Bash"]

# Task management
allowed-tools: ["TaskCreate", "TaskUpdate", "TaskList"]

# Git operations
allowed-tools: ["Bash", "Read"]  # Use bash for git commands

# All-in-one development
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "TaskCreate"]
```

### Helper Scripts

Skills can include helper scripts for complex operations:

```bash
#!/usr/bin/env bash
# skills/my-skill/helpers.sh

set -euo pipefail

# Function: check_environment
# Validates required environment variables and tools
check_environment() {
    if [[ -z "${KUBECONFIG:-}" ]]; then
        echo "❌ KUBECONFIG not set"
        return 1
    fi

    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl not found"
        return 1
    fi

    echo "✓ Environment validated"
}

# Function: run_workflow
# Main workflow implementation
run_workflow() {
    local mode="${1:-default}"

    echo "Running workflow in $mode mode..."

    # Implementation here

    echo "✓ Workflow complete"
}

# Allow sourcing or direct execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Called directly
    check_environment
    run_workflow "$@"
fi
```

Make scripts executable:

```bash
chmod +x skills/my-skill/helpers.sh
```

### Node.js Tools (Optional)

For complex analysis or data processing:

```javascript
#!/usr/bin/env node
// skills/my-skill/analyzer.js

const fs = require('fs');
const path = require('path');

function analyzeData(filePath) {
    const data = fs.readFileSync(filePath, 'utf8');

    // Analysis logic
    const results = {
        patterns: [],
        issues: [],
        suggestions: []
    };

    return results;
}

// CLI interface
if (require.main === module) {
    const filePath = process.argv[2];

    if (!filePath) {
        console.error('Usage: analyzer.js <file>');
        process.exit(1);
    }

    const results = analyzeData(filePath);
    console.log(JSON.stringify(results, null, 2));
}

module.exports = { analyzeData };
```

### Testing Skills

Create test cases in `tests/skills/`:

```bash
#!/usr/bin/env bash
# tests/skills/test-my-skill.sh

source skills/my-skill/helpers.sh

test_check_environment() {
    export KUBECONFIG="/tmp/test-kubeconfig"

    if check_environment; then
        echo "✓ Environment check passed"
    else
        echo "✗ Environment check failed"
        return 1
    fi
}

# Run tests
test_check_environment
```

### Skill Best Practices

1. **Clear Instructions**: Write for an AI assistant, be explicit
2. **Modular Helpers**: Break complex logic into reusable functions
3. **Error Handling**: Always validate inputs and environment
4. **Documentation**: Include examples and integration guidance
5. **Tool Permissions**: Request minimal necessary tools
6. **Context Mode**: Use `fork` for isolated work, `main` for shared state

## Creating Commands

Commands are quick utilities accessible via `/command-name`.

### Command Structure

```javascript
#!/usr/bin/env node
// commands/my-command.js

// Validate environment
if (!process.env.KUBECONFIG) {
    console.error('❌ KUBECONFIG environment variable required');
    console.error('Usage: export KUBECONFIG=/path/to/config');
    process.exit(1);
}

// Parse arguments
const args = process.argv.slice(2);
const [resource, namespace = 'default'] = args;

if (!resource) {
    console.error('Usage: my-command <resource> [namespace]');
    process.exit(1);
}

// Main logic
async function runCommand() {
    try {
        // Implementation
        console.log('✓ Command executed successfully');
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

runCommand();
```

### Command Best Practices

1. **Validate Environment**: Check required env vars and tools
2. **Clear Usage**: Print usage on missing arguments
3. **Error Handling**: Catch and report errors clearly
4. **Exit Codes**: Use proper exit codes (0 success, 1+ failure)
5. **Executable**: `chmod +x commands/my-command.js`
6. **Shebang**: Start with `#!/usr/bin/env node` or `#!/usr/bin/env bash`

## Creating Agents

Agents are specialized assistants with specific expertise and tool access.

### Agent Configuration

Create JSON configuration in `agents/`:

```json
{
  "name": "my-agent",
  "description": "Specialized agent for specific task domain",
  "instructions": "You are an expert in <domain>. When working:\n\n1. Start with <initial step>\n2. Analyze <specific aspects>\n3. Provide <specific output>\n4. Always be <characteristic>\n\nKey responsibilities:\n- Responsibility 1\n- Responsibility 2\n- Responsibility 3",
  "tools": [
    "Bash",
    "Read",
    "Grep",
    "Write"
  ],
  "skills": [
    "skill-1",
    "skill-2"
  ],
  "context": {
    "domain_knowledge": "Description of domain expertise",
    "approach": "Description of methodology"
  }
}
```

### Agent Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Agent identifier (kebab-case) |
| `description` | Yes | One-line summary |
| `instructions` | Yes | Detailed behavioral instructions |
| `tools` | Yes | Array of allowed tools |
| `skills` | No | Array of skills the agent can use |
| `context` | No | Additional context/knowledge |

### Agent Best Practices

1. **Specific Expertise**: Focus on a well-defined problem domain
2. **Clear Instructions**: Define methodology and approach
3. **Tool Access**: Grant minimal necessary tools
4. **Skill Integration**: Leverage existing skills
5. **Context**: Provide domain-specific knowledge

## Creating Hooks

Hooks automate behaviors in response to events (not yet implemented in this plugin).

### Hook Configuration Pattern

Hooks are configured in Claude Code's `settings.json`:

```json
{
  "hooks": {
    "before-commit": {
      "command": "./scripts/pre-commit-hook.sh",
      "description": "Run tests and linting before commit"
    },
    "after-task-complete": {
      "command": "./scripts/task-complete-hook.sh",
      "description": "Update task tracking"
    }
  }
}
```

### Hook Script Pattern

```bash
#!/usr/bin/env bash
# scripts/pre-commit-hook.sh

set -euo pipefail

echo "Running pre-commit checks..."

# Run quick tests
if ! ./lib/test-workflow.sh quick; then
    echo "❌ Pre-commit tests failed"
    exit 1
fi

echo "✓ Pre-commit checks passed"
exit 0
```

### Available Hook Events

| Event | When Triggered |
|-------|----------------|
| `before-commit` | Before git commit |
| `after-commit` | After git commit |
| `before-push` | Before git push |
| `after-push` | After git push |
| `task-complete` | When task marked complete |
| `session-start` | When Claude Code session starts |

## Plugin Metadata

Update `.claude-plugin/plugin.json` when adding features:

```json
{
  "name": "openstack-k8s-agent-tools",
  "version": "0.3.0",
  "description": "Development and troubleshooting tools for openstack-k8s-operators operators",
  "author": {
    "name": "openstack-k8s-operators Development Team",
    "email": "openstack-k8s-operators-dev@redhat.com"
  },
  "homepage": "https://github.com/openstack-k8s-operators/operator-tools",
  "repository": "https://github.com/openstack-k8s-operators/operator-tools",
  "license": "MIT",
  "keywords": [
    "openstack-k8s-operators",
    "operators",
    "debugging",
    "kubernetes",
    "openstack"
  ]
}
```

### Semantic Versioning

- **Major** (x.0.0): Breaking changes to skill interfaces
- **Minor** (0.x.0): New skills, commands, or agents
- **Patch** (0.0.x): Bug fixes and improvements

## Installation Script

Update `scripts/install.sh` when adding new features:

```bash
#!/usr/bin/env bash

install_for_claude_code() {
    local target_dir="$HOME/.claude/projects/$(basename "$PWD")"

    # Install skills
    mkdir -p "$target_dir/skills"
    cp -r skills/* "$target_dir/skills/"

    # Install commands (if adding command support)
    # mkdir -p "$target_dir/commands"
    # cp -r commands/* "$target_dir/commands/"

    # Install agents (if adding agent support)
    # mkdir -p "$target_dir/agents"
    # cp -r agents/* "$target_dir/agents/"

    echo "✓ Installed for Claude Code"
}
```

## Testing

### Manual Testing

```bash
# Test individual skill helper
./skills/my-skill/helpers.sh

# Test command directly
export KUBECONFIG=/path/to/config
node ./commands/my-command.js arg1 arg2

# Test in Claude Code
claude
/my-skill
/my-command arg1 arg2
```

### Automated Testing

Create test harness in `scripts/test-plugin.sh`:

```bash
#!/usr/bin/env bash

set -euo pipefail

echo "Testing openstack-k8s-operators Operator Tools Plugin"

# Test skill helpers
echo "Testing skill helpers..."
for skill in skills/*/helpers.sh; do
    if [[ -x "$skill" ]]; then
        echo "  Testing $(basename $(dirname $skill))..."
        bash -n "$skill" || exit 1
    fi
done

# Test commands
echo "Testing commands..."
for cmd in commands/*.js; do
    if [[ -x "$cmd" ]]; then
        echo "  Testing $(basename $cmd)..."
        node --check "$cmd" || exit 1
    fi
done

# Validate agent configs
echo "Validating agent configs..."
for agent in agents/*.json; do
    echo "  Validating $(basename $agent)..."
    jq empty "$agent" || exit 1
done

echo "✓ All tests passed"
```

## Documentation

Update documentation when adding features:

1. **GETTING-STARTED.md**: Add concise usage examples
2. **README.md**: Update features list
3. **CLAUDE.md**: Update available skills/commands
4. **This file**: Document new patterns

## Integration Patterns

### Skill Dependencies

Skills can reference other skills:

```markdown
## Integration

This skill works with:
- **debug-operator**: Use for runtime debugging
- **test-operator**: Validate changes before deploying
- **analyze-logs**: Parse output for patterns
```

### Command-Skill Integration

Commands can be simple wrappers for skills:

```javascript
// commands/quick-test.js
console.log('Run: /test-operator quick');
```

### Agent-Skill Composition

Agents orchestrate multiple skills:

```json
{
  "skills": [
    "debug-operator",
    "analyze-logs",
    "explain-flow"
  ],
  "instructions": "Use debug-operator for systematic analysis, then analyze-logs for patterns, then explain-flow for understanding."
}
```

## Contributing

1. **Fork**: Fork the repository
2. **Branch**: Create feature branch (`git checkout -b feature/my-feature`)
3. **Develop**: Follow patterns in this guide
4. **Test**: Run `./scripts/test-plugin.sh`
5. **Document**: Update relevant documentation
6. **PR**: Submit pull request with clear description

## Examples

### Example 1: Adding a New Skill

```bash
# Create skill directory
mkdir -p skills/validate-crd

# Create SKILL.md
cat > skills/validate-crd/SKILL.md << 'EOF'
---
name: validate-crd
description: Validate Custom Resource Definitions for openstack-k8s-operators operators
user-invocable: true
allowed-tools: ["Bash", "Read", "Grep"]
context: fork
---

# Validate CRD

Validates Custom Resource Definitions for correctness and completeness.

## Workflow

1. **Find CRDs**: Locate CRD files in config/crd/bases/
2. **Schema Validation**: Check OpenAPI schema validity
3. **Status Subresource**: Verify status subresource present
4. **Conditions**: Check for standard status conditions
5. **Validation Rules**: Verify validation rules

## Usage

/validate-crd
EOF

# Create helper script
cat > skills/validate-crd/validator.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

validate_crd() {
    local crd_file="$1"

    echo "Validating $crd_file..."

    # Check for status subresource
    if ! grep -q "status: {}" "$crd_file"; then
        echo "❌ Missing status subresource"
        return 1
    fi

    echo "✓ CRD valid"
}

for crd in config/crd/bases/*.yaml; do
    validate_crd "$crd"
done
EOF

chmod +x skills/validate-crd/validator.sh

# Update plugin.json version
# Update CHEATSHEET.md with usage
# Test the skill
```

### Example 2: Adding a New Command

```bash
# Create command
cat > commands/crd-status.js << 'EOF'
#!/usr/bin/env node

if (!process.env.KUBECONFIG) {
    console.error('❌ KUBECONFIG required');
    process.exit(1);
}

const { execSync } = require('child_process');

const crdName = process.argv[2];

if (!crdName) {
    console.error('Usage: crd-status <crd-name>');
    process.exit(1);
}

try {
    const output = execSync(`kubectl get crd ${crdName} -o yaml`, {
        encoding: 'utf8'
    });

    console.log('✓ CRD Status:\n');
    console.log(output);
} catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
}
EOF

chmod +x commands/crd-status.js

# Test
export KUBECONFIG=/path/to/config
node commands/crd-status.js glances.openstack.org
```

### Example 3: Adding a New Agent

```bash
# Create agent config
cat > agents/crd-expert.json << 'EOF'
{
  "name": "crd-expert",
  "description": "Expert in Custom Resource Definition design and validation",
  "instructions": "You are a CRD design expert. When helping with CRDs:\n\n1. Start with schema validation\n2. Check for proper status subresource\n3. Verify validation rules\n4. Ensure proper conditions\n5. Review webhook integration\n\nAlways follow Kubernetes API conventions.",
  "tools": ["Bash", "Read", "Grep", "Write"],
  "skills": ["validate-crd", "explain-flow"],
  "context": {
    "expertise": "Deep knowledge of Kubernetes API machinery and CRD best practices"
  }
}
EOF

# Update CLAUDE.md to document the new agent
```

## Reference

- [Claude Code Skills Documentation](https://docs.anthropic.com/claude-code/skills)
- [openstack-k8s-operators/dev-docs](https://github.com/openstack-k8s-operators/dev-docs)
- [Operator SDK Best Practices](https://sdk.operatorframework.io/docs/best-practices/)
- [Kubernetes Operator Patterns](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
