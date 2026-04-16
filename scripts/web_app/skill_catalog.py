import re
import yaml
from pathlib import Path


def _parse_frontmatter(content):
    """Extract YAML frontmatter between --- markers."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not match:
        return {}, content
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, match.group(2)


def _first_paragraph(body):
    """Extract first non-empty, non-heading paragraph from markdown body."""
    lines = []
    for line in body.strip().split('\n'):
        stripped = line.strip()
        if not stripped and lines:
            break
        if stripped and not stripped.startswith('#'):
            lines.append(stripped)
    return ' '.join(lines)[:300] if lines else ''


def get_skill_catalog(plugin_path):
    """Scan plugin skills/ and agents/ directories; return catalog dict."""
    skills_dir = Path(plugin_path) / 'skills'
    agents_dir = Path(plugin_path) / 'agents'
    skills = []
    agents = []
    agent_names = set()

    if agents_dir.exists():
        for agent_dir in sorted(agents_dir.iterdir()):
            agent_file = agent_dir / 'AGENT.md'
            if not agent_file.exists():
                continue
            meta, body = _parse_frontmatter(agent_file.read_text())
            name = meta.get('name', agent_dir.name)
            agent_names.add(name)
            agents.append({
                'name': name,
                'description': meta.get('description', ''),
                'model': meta.get('model', 'inherit'),
                'preloads': meta.get('skills', []),
                'summary': _first_paragraph(body),
            })

    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / 'SKILL.md'
            if not skill_file.exists():
                continue
            meta, body = _parse_frontmatter(skill_file.read_text())
            name = meta.get('name', skill_dir.name)
            tools = meta.get('allowed-tools', [])
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(',')]
            skills.append({
                'name': name,
                'description': meta.get('description', ''),
                'argument_hint': meta.get('argument-hint', ''),
                'allowed_tools': tools,
                'user_invocable': meta.get('user-invocable', True),
                'context': meta.get('context', 'fork'),
                'has_agent': name in agent_names,
                'summary': _first_paragraph(body),
            })

    return {
        'skills': skills,
        'agents': agents,
        'total_skills': len(skills),
        'total_agents': len(agents),
    }


def get_skill_detail(plugin_path, name):
    """Return full detail dict for one skill, including linked agent."""
    skill_file = Path(plugin_path) / 'skills' / name / 'SKILL.md'
    if not skill_file.exists():
        return None

    meta, body = _parse_frontmatter(skill_file.read_text())
    tools = meta.get('allowed-tools', [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(',')]

    agent = None
    agent_file = Path(plugin_path) / 'agents' / name / 'AGENT.md'
    if agent_file.exists():
        agent_meta, agent_body = _parse_frontmatter(agent_file.read_text())
        agent = {
            'name': agent_meta.get('name', name),
            'description': agent_meta.get('description', ''),
            'model': agent_meta.get('model', 'inherit'),
            'preloads': agent_meta.get('skills', []),
            'body_preview': agent_body[:800],
        }

    return {
        'name': meta.get('name', name),
        'description': meta.get('description', ''),
        'argument_hint': meta.get('argument-hint', ''),
        'allowed_tools': tools,
        'context': meta.get('context', 'fork'),
        'body': body,
        'agent': agent,
    }
