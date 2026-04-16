#!/usr/bin/env python3
"""Interactive admin user creation for first deploy."""
import os
import sys
import yaml
import getpass
from pathlib import Path
from datetime import date
from werkzeug.security import generate_password_hash


def main():
    print("K8s Agent Tools Server -- Admin User Setup")
    print("=" * 42)
    print()

    data_root = os.environ.get('K8S_AGENT_TOOLS_DATA_ROOT',
                                str(Path(__file__).parent / 'data'))
    data_path = Path(data_root)
    users_file = data_path / 'users.yaml'
    users_dir = data_path / 'users'

    data_path.mkdir(parents=True, exist_ok=True)
    users_dir.mkdir(parents=True, exist_ok=True)

    if users_file.exists():
        with open(users_file) as f:
            users = yaml.safe_load(f) or {}
        print(f"Existing users: {', '.join(users.keys())}")
        print()
    else:
        users = {}

    username = input("Username [admin]: ").strip() or 'admin'
    if username in users:
        confirm = input(f"User '{username}' exists. Overwrite? [y/N]: ").strip()
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    full_name = input("Full Name [Admin]: ").strip() or 'Admin'
    email = input("Email [admin@redhat.com]: ").strip() or 'admin@redhat.com'

    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        confirm_pw = getpass.getpass("Confirm: ")
        if password != confirm_pw:
            print("Passwords do not match.")
            continue
        break

    users[username] = {
        'password_hash': generate_password_hash(password),
        'full_name': full_name,
        'email': email,
        'is_admin': True,
        'is_active': True,
        'created': date.today().isoformat(),
    }

    with open(users_file, 'w') as f:
        yaml.dump(users, f, default_flow_style=False)

    user_dir = users_dir / username
    user_dir.mkdir(parents=True, exist_ok=True)
    profile_file = user_dir / 'profile.yaml'
    if not profile_file.exists():
        profile = {
            'operators': {
                'repos': ['glance-operator', 'nova-operator',
                          'heat-operator', 'horizon-operator'],
                'gopath': '/home/ospng/go',
                'plans_dir': '~/.openstack-k8s-agents-plans',
            },
            'integrations': {
                'jira_projects': ['OSPRH', 'OSPCIX'],
                'github_org': 'openstack-k8s-operators',
            },
            'preferences': {
                'auto_refresh': True,
                'refresh_interval': 300,
                'theme': 'dark',
            },
        }
        with open(profile_file, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False)

    print()
    print(f"Created admin user '{username}' in {users_file}")
    print(f"Profile: {profile_file}")
    print()
    print("You can now start the server and log in.")


if __name__ == '__main__':
    main()
