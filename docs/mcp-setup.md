# MCP Setup

Optional MCP server integrations for the plugin skills.

## Atlassian (Jira)

Required for `/feature` (Jira ticket planning) and `/jira` (ticket inspection). Uses [mcp-atlassian](https://github.com/sooperset/mcp-atlassian).

### Prerequisites

Install `uv`:

```bash
brew install uv    # macOS
pip install uv     # or via pip
```

### Jira Cloud

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://your-instance.atlassian.net",
        "JIRA_USERNAME": "you@example.com",
        "JIRA_API_TOKEN": "YOUR_JIRA_API_TOKEN",
        "JIRA_SSL_VERIFY": "true",
        "READ_ONLY_MODE": "true"
      }
    }
  }
}
```

Generate a Cloud API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

### Configuration

The JSON above goes in different locations depending on your platform:

| Platform | Global config | Project config |
|----------|--------------|----------------|
| Claude Code | `~/.claude/settings.json` | `.claude/settings.json` |
| OpenCode | `~/.config/opencode/opencode.json` | `opencode.json` |

**Claude Code CLI** — add via the CLI instead of editing JSON:

```bash
claude mcp add-json "mcp-atlassian" \
  '{"command":"uvx","args":["mcp-atlassian"],"env":{"JIRA_URL":"https://your-instance.atlassian.net","JIRA_USERNAME":"you@example.com","JIRA_API_TOKEN":"YOUR_TOKEN","JIRA_SSL_VERIFY":"true","READ_ONLY_MODE":"true"}}'
```

**OpenCode** — add the `mcpServers` block to your `opencode.json`:

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://your-instance.atlassian.net",
        "JIRA_USERNAME": "you@example.com",
        "JIRA_API_TOKEN": "YOUR_TOKEN",
        "JIRA_SSL_VERIFY": "true",
        "READ_ONLY_MODE": "true"
      }
    }
  }
}
```

Note: OpenCode requires the `"type": "stdio"` field in MCP server definitions.

### Read-Only Mode

Set `READ_ONLY_MODE` to `"true"` when you only need to read tickets (recommended for `/feature` planning). Set to `"false"` if you want `/jira` or `/task-executor` to post comments back to Jira.

Note: even with `READ_ONLY_MODE=false`, the plugin's global rules require human approval before posting any comment. See `~/.claude/CLAUDE.md`.

## Which Skills Need MCP

| Skill | MCP Required | What It Uses |
|-------|-------------|-------------|
| `/feature` | Optional | Reads Jira tickets for planning. Falls back to spec files without it. |
| `/jira` | Optional | Reads and inspects tickets. Can post comments if READ_ONLY_MODE=false. |
| `/task-executor` | Optional | Posts outcome comments to Jira after implementation. |
| `/code-review` | No | Uses `gh` CLI or WebFetch for PRs, not MCP. |
| All other skills | No | No MCP integration. |
