from pathlib import Path
import os

BASE = Path(__file__).parent
_data_root = os.environ.get('K8S_AGENT_TOOLS_DATA_ROOT')
DATA_ROOT = Path(_data_root) if _data_root else BASE.parent / 'data'

USERS_FILE = DATA_ROOT / 'users.yaml'
USERS_DIR = DATA_ROOT / 'users'
CONFIG_FILE = DATA_ROOT / 'config.yaml'
CACHE_DIR = DATA_ROOT / 'cache'

PORT = int(os.environ.get('K8S_AGENT_TOOLS_PORT', '5005'))

PLUGIN_PATH = os.environ.get(
    'K8S_AGENT_TOOLS_PLUGIN_PATH',
    str(Path.home() / 'Work/mymcp/workspace/iproject/projects'
        '/openstack_k8s_agent_tools/repo/openstack-k8s-agent-tools')
)

PLANS_ROOT = os.environ.get(
    'K8S_AGENT_TOOLS_PLANS_ROOT',
    str(Path.home() / '.openstack-k8s-agents-plans')
)

EXECUTIONS_DIR = DATA_ROOT / 'executions'
MAX_CONCURRENT_EXECUTIONS = int(os.environ.get(
    'K8S_AGENT_TOOLS_MAX_WORKERS', '3'))
EXECUTION_TIMEOUT = int(os.environ.get(
    'K8S_AGENT_TOOLS_EXEC_TIMEOUT', '300'))

JIRA_URL = os.environ.get('JIRA_URL', 'https://issues.redhat.com')
JIRA_TOKEN = os.environ.get('JIRA_TOKEN', '')
JIRA_PROJECT = os.environ.get('JIRA_PROJECT', 'OSPRH')

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPOS_STR = os.environ.get('GITHUB_REPOS', '')

GERRIT_URL = 'https://review.opendev.org'
GERRIT_QUERY = os.environ.get('GERRIT_QUERY', 'project:openstack/ status:open')

INTEGRATION_CACHE_TTL = int(os.environ.get(
    'K8S_AGENT_TOOLS_CACHE_TTL', '600'))

ANALYSES_DIR = DATA_ROOT / 'analyses'
HISTORY_DIR = DATA_ROOT / 'history'
REPORTS_DIR = DATA_ROOT / 'reports'
