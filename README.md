# openstack-k8s-operators Operator Tools

A comprehensive Claude Code plugin for openstack-k8s-operators operators development and troubleshooting.

## Features

🔍 **Debugging Skills**
- Systematic operator debugging workflows
- Log analysis and pattern recognition  
- Resource health monitoring
- Event timeline analysis

🎯 **Code Analysis**
- Flow diagram generation
- Controller logic explanation
- State transition mapping
- Error path tracing

📋 **Planning Tools**
- Feature planning with architectural guidance
- Task breakdown and prioritization
- Best practice alignment
- Implementation roadmaps

## Installation

### Claude Code
```bash
git clone <repository>
cd openstack-k8s-agent-tools
./scripts/install.sh
```

Then in Claude Code:
```
/plugin enable openstack-k8s-agent-tools
```

### OpenCode
```bash
./scripts/install.sh --opencode
```

## Documentation

- **[Getting Started](docs/GETTING-STARTED.md)** - Quick reference for all skills
- **[User Guide](docs/README.md)** - Installation and usage
- **[Development Guide](docs/DEVELOPMENT.md)** - Extending the plugin
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines

## Quick Usage

### Skills

- `/debug-operator` - Development workflow + testing
- `/test-operator quick` - Fast validation
- `/code-style` - Style enforcement
- `/analyze-logs` - Log analysis
- `/explain-flow` - Code flow
- `/plan-feature` - Feature planning

## Examples

```bash
# Debug operator in development
/debug-operator

# Quick validation
/test-operator quick

# Analyze controller flow
/explain-flow

# Pre-PR full check
/test-operator full
```

## Requirements

- Go toolchain (required for operator development)
- make (required)
- kubectl (optional, for runtime debugging)

## License

MIT - See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add skills following existing patterns
4. Test with real openstack-k8s-operators deployments
5. Submit pull request

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.