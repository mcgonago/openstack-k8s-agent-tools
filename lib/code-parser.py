#!/usr/bin/env python3

"""
Code Flow Parser for openstack-k8s-operators Operators
Analyzes Go operator code to extract flow patterns
"""

import json
import re
import sys
import os


class OperatorFlowParser:
    def __init__(self):
        self.controllers = []
        self.reconcile_functions = []
        self.custom_resources = []
        self.webhooks = []

    def parse_operator_directory(self, dir_path):
        """Parse operator directory structure"""
        try:
            result = {
                'controllers': self.find_controllers(dir_path),
                'reconcilers': self.find_reconcilers(dir_path),
                'crds': self.find_crds(dir_path),
                'webhooks': self.find_webhooks(dir_path),
                'main': self.find_main_function(dir_path)
            }

            print(json.dumps(result, indent=2))
            return result
        except Exception as e:
            print(f'Error parsing operator: {e}', file=sys.stderr)
            return None

    def find_controllers(self, dir_path):
        """Find controller files"""
        controllers = []
        controller_pattern = re.compile(r'controller|reconciler', re.IGNORECASE)

        try:
            for file_path in self.walk_directory(dir_path):
                if file_path.endswith('.go') and controller_pattern.search(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        controller = self.parse_controller_file(file_path, content)
                        if controller:
                            controllers.append(controller)
                    except Exception as e:
                        print(f'Error reading {file_path}: {e}', file=sys.stderr)
        except Exception as e:
            print(f'Error finding controllers: {e}', file=sys.stderr)

        return controllers

    def parse_controller_file(self, file_path, content):
        """Parse individual controller file"""
        reconcile_pattern = re.compile(
            r'func\s+\(.*?\)\s+Reconcile\s*\([^)]*\)\s+\([^)]*\)',
            re.DOTALL
        )
        setup_pattern = re.compile(
            r'func\s+\([^)]+\)\s+SetupWithManager\s*\([^)]*\)',
            re.DOTALL
        )

        reconcile_functions = []
        setup_functions = []

        # Find Reconcile functions
        for match in reconcile_pattern.finditer(content):
            reconcile_functions.append({
                'signature': match.group(0),
                'line': self.get_line_number(content, match.start())
            })

        # Find SetupWithManager functions
        for match in setup_pattern.finditer(content):
            setup_functions.append({
                'signature': match.group(0),
                'line': self.get_line_number(content, match.start())
            })

        if reconcile_functions or setup_functions:
            return {
                'file': os.path.relpath(file_path, os.getcwd()),
                'reconcile': reconcile_functions,
                'setup': setup_functions,
                'imports': self.extract_imports(content),
                'structs': self.extract_structs(content)
            }

        return None

    def find_reconcilers(self, dir_path):
        """Find reconciler functions and their flow"""
        reconcilers = []

        try:
            for file_path in self.walk_directory(dir_path):
                if file_path.endswith('.go'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        flows = self.parse_reconcile_flow(file_path, content)
                        if flows:
                            reconcilers.append({
                                'file': os.path.relpath(file_path, os.getcwd()),
                                'flows': flows
                            })
                    except Exception as e:
                        print(f'Error reading {file_path}: {e}', file=sys.stderr)
        except Exception as e:
            print(f'Error finding reconcilers: {e}', file=sys.stderr)

        return reconcilers

    def parse_reconcile_flow(self, file_path, content):
        """Parse reconcile function flow"""
        flows = []
        signature_pattern = re.compile(
            r'func\s+\([^)]+\)\s+Reconcile\s*\([^)]*\)\s+\([^)]*\)\s*{',
            re.DOTALL
        )

        for match in signature_pattern.finditer(content):
            body_start = match.end()
            body = self.extract_function_body(content, body_start)
            flow = {
                'function': match.group(0).rstrip().rstrip('{').strip() + ' {...}',
                'line': self.get_line_number(content, match.start()),
                'steps': self.extract_flow_steps(body),
                'errorHandling': self.extract_error_handling(body),
                'returns': self.extract_returns(body)
            }
            flows.append(flow)

        return flows

    def extract_function_body(self, content, start_index):
        """Extract function body using brace counting"""
        depth = 1
        i = start_index
        while i < len(content) and depth > 0:
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
            i += 1
        return content[start_index:i - 1]

    def extract_flow_steps(self, body):
        """Extract flow steps from reconcile function"""
        steps = []

        # Common patterns in reconcile functions
        patterns = [
            (re.compile(r'\.\s*Get\s*\(ctx\b[^)]*\)'), 'resource_fetch'),
            (re.compile(r'\.\s*Create\s*\(ctx\b[^)]*\)'), 'resource_create'),
            (re.compile(r'\.\s*Update\s*\(ctx\b[^)]*\)'), 'resource_update'),
            (re.compile(r'\.\s*Delete\s*\(ctx\b[^)]*\)'), 'resource_delete'),
            (re.compile(r'\.\s*Patch\s*\(ctx\b[^)]*\)'), 'resource_patch'),
            (re.compile(r'\.Set\s*\(condition\.\w+'), 'condition_set'),
            (re.compile(r'ctrl\.Result\{[^}]*\}'), 'result_return'),
            (re.compile(r'controllerutil\.\w+Finalizer'), 'finalizer'),
            (re.compile(r'helper\.GetConfigMapAndHashWithName'), 'config_map'),
            (re.compile(r'condition\.CreateList'), 'condition_init')
        ]

        for pattern, step_type in patterns:
            for match in pattern.finditer(body):
                steps.append({
                    'type': step_type,
                    'code': match.group(0),
                    'line': self.get_line_number(body, match.start())
                })

        return sorted(steps, key=lambda x: x['line'])

    def extract_error_handling(self, body):
        """Extract error handling patterns"""
        error_patterns = []
        patterns = [
            re.compile(r'if\s+err\s*!=\s*nil\s*{[^}]*}'),
            re.compile(r'return\s+[^,]*,\s*err'),
            re.compile(r'ctrl\.Result\{.*\},\s*err')
        ]

        for pattern in patterns:
            for match in pattern.finditer(body):
                error_patterns.append({
                    'code': match.group(0),
                    'line': self.get_line_number(body, match.start())
                })

        return error_patterns

    def extract_returns(self, body):
        """Extract return statements"""
        returns = []
        return_pattern = re.compile(r'return\s+([^;]+)')

        for match in return_pattern.finditer(body):
            returns.append({
                'code': match.group(0),
                'value': match.group(1).strip(),
                'line': self.get_line_number(body, match.start())
            })

        return returns

    def find_crds(self, dir_path):
        """Find CRD definitions"""
        crds = []

        try:
            for file_path in self.walk_directory(dir_path):
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if 'kind: CustomResourceDefinition' in content:
                            crds.append({
                                'file': os.path.relpath(file_path, os.getcwd()),
                                'content': self.extract_crd_info(content)
                            })
                    except Exception as e:
                        print(f'Error reading {file_path}: {e}', file=sys.stderr)
        except Exception as e:
            print(f'Error finding CRDs: {e}', file=sys.stderr)

        return crds

    def extract_crd_info(self, content):
        """Extract CRD information"""
        name_match = re.search(r'name:\s+([^\n]+)', content)
        group_match = re.search(r'group:\s+([^\n]+)', content)
        kind_match = re.search(r'kind:\s+([^\n]+)', content)

        return {
            'name': name_match.group(1).strip() if name_match else None,
            'group': group_match.group(1).strip() if group_match else None,
            'kind': kind_match.group(1).strip() if kind_match else None
        }

    def find_webhooks(self, dir_path):
        """Find webhook configurations"""
        webhooks = []

        try:
            for file_path in self.walk_directory(dir_path):
                if file_path.endswith('.go'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        webhook = self.parse_webhook_file(file_path, content)
                        if webhook:
                            webhooks.append(webhook)
                    except Exception as e:
                        print(f'Error reading {file_path}: {e}', file=sys.stderr)
        except Exception as e:
            print(f'Error finding webhooks: {e}', file=sys.stderr)

        return webhooks

    def parse_webhook_file(self, file_path, content):
        """Parse webhook file"""
        webhook_patterns = [
            re.compile(r'func\s+\([^)]+\)\s+ValidateCreate\s*\([^)]*\)'),
            re.compile(r'func\s+\([^)]+\)\s+ValidateUpdate\s*\([^)]*\)'),
            re.compile(r'func\s+\([^)]+\)\s+ValidateDelete\s*\([^)]*\)'),
            re.compile(r'func\s+\([^)]+\)\s+Default\s*\([^)]*\)')
        ]

        webhooks = []

        for pattern in webhook_patterns:
            for match in pattern.finditer(content):
                webhooks.append({
                    'function': match.group(0),
                    'line': self.get_line_number(content, match.start())
                })

        if webhooks:
            return {
                'file': os.path.relpath(file_path, os.getcwd()),
                'webhooks': webhooks
            }

        return None

    def find_main_function(self, dir_path):
        """Find main function"""
        try:
            candidates = [
                os.path.join(dir_path, 'main.go'),
                os.path.join(dir_path, 'cmd', 'main.go')
            ]
            for main_path in candidates:
                if os.path.exists(main_path):
                    with open(main_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return self.parse_main_function(content)
        except Exception as e:
            print(f'Error finding main function: {e}', file=sys.stderr)

        return None

    def parse_main_function(self, content):
        """Parse main function"""
        setup_pattern = re.compile(r'mgr\.Add\([^)]+\)')
        controller_pattern = re.compile(r'\.SetupWithManager\([^)]+\)')

        setup = []

        for match in setup_pattern.finditer(content):
            setup.append({
                'code': match.group(0),
                'line': self.get_line_number(content, match.start())
            })

        for match in controller_pattern.finditer(content):
            setup.append({
                'code': match.group(0),
                'line': self.get_line_number(content, match.start())
            })

        return {
            'setup': sorted(setup, key=lambda x: x['line']),
            'imports': self.extract_imports(content)
        }

    # Utility functions
    def walk_directory(self, dir_path):
        """Walk directory and yield file paths, skipping .git, vendor, and dot-directories"""
        if not os.path.exists(dir_path):
            return

        for root, dirs, files in os.walk(dir_path):
            # Skip .git, vendor, and dot-directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'vendor']

            for file in files:
                yield os.path.join(root, file)

    def extract_imports(self, content):
        """Extract imports from Go file"""
        import_pattern = re.compile(r'import\s*\(\s*([^)]*)\s*\)', re.DOTALL)
        match = import_pattern.search(content)
        if match:
            imports = [line.strip() for line in match.group(1).split('\n')]
            return [imp for imp in imports if imp]
        return []

    def extract_structs(self, content):
        """Extract struct definitions"""
        struct_pattern = re.compile(r'type\s+(\w+)\s+struct\s*{([^}]*)}')
        structs = []

        for match in struct_pattern.finditer(content):
            structs.append({
                'name': match.group(1),
                'fields': match.group(2).strip(),
                'line': self.get_line_number(content, match.start())
            })

        return structs

    def get_line_number(self, content, index):
        """Get line number from string index"""
        return content[:index].count('\n') + 1


# CLI interface
if __name__ == "__main__":
    args = sys.argv[1:]
    dir_path = args[0] if args and not args[0].startswith('-') else os.getcwd()

    if '--help' in args or '-h' in args:
        print('Usage: code-parser.py [directory]')
        print('  directory: Path to operator code (default: current directory)')
        sys.exit(0)

    parser = OperatorFlowParser()
    parser.parse_operator_directory(dir_path)
