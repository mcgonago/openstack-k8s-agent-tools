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
