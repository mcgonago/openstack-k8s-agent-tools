#!/usr/bin/env python3

"""
Go Code Style Analyzer for openstack-k8s-operators Operators
Analyzes and suggests improvements based on openstack-k8s-operators conventions
"""

import json
import re
import sys
import os


class GoStyleAnalyzer:
    def __init__(self):
        self.issues = []
        self.suggestions = []
        self.modernizations = []

    def analyze_file(self, file_path):
        """Analyze Go file for style issues"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}", file=sys.stderr)
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        analysis = {
            'file': file_path,
            'issues': [],
            'suggestions': [],
            'modernizations': [],
            'stats': {
                'lines': len(content.split('\n')),
                'functions': 0,
                'types': 0
            }
        }

        self.analyze_content(content, analysis)
        return analysis

    def analyze_content(self, content, analysis):
        """Main content analysis"""
        lines = content.split('\n')

        for index, line in enumerate(lines):
            line_num = index + 1

            # Check for various style issues
            self.check_slice_declaration(line, line_num, analysis)
            self.check_map_declaration(line, line_num, analysis)
            self.check_string_concatenation(line, line_num, analysis)
            self.check_error_handling(line, line_num, analysis)
            self.check_logging(line, line_num, analysis)
            self.check_naming(line, line_num, analysis)
            self.check_imports(line, line_num, analysis)
            self.check_controller_patterns(line, line_num, analysis)

        # Overall file analysis
        self.analyze_file_structure(content, analysis)

    def check_slice_declaration(self, line, line_num, analysis):
        """Check for old-style slice declarations"""
        # Pattern: var items []Type = []Type{}
        old_slice_pattern = re.compile(r'var\s+\w+\s+\[\]\w+\s*=\s*\[\]\w+\{\}')
        if old_slice_pattern.search(line):
            suggestion = re.sub(r'\s*=\s*\[\]\w+\{\}', '', line)
            analysis['modernizations'].append({
                'line': line_num,
                'type': 'slice_declaration',
                'current': line.strip(),
                'suggestion': suggestion,
                'description': 'Use zero-value initialization for slices'
            })

    def check_map_declaration(self, line, line_num, analysis):
        """Check for old-style map declarations"""
        # Pattern: var m map[K]V = make(map[K]V)
        old_map_pattern = re.compile(r'var\s+\w+\s+map\[[^\]]+\]\w+\s*=\s*make\(map\[[^\]]+\]\w+\)')
        if old_map_pattern.search(line):
            suggestion = re.sub(
                r'var\s+(\w+)\s+(map\[[^\]]+\]\w+)\s*=\s*make\(\2\)',
                r'var \1 = make(\2)',
                line
            )
            analysis['modernizations'].append({
                'line': line_num,
                'type': 'map_declaration',
                'current': line.strip(),
                'suggestion': suggestion,
                'description': 'Use short variable declaration for maps'
            })

    def check_string_concatenation(self, line, line_num, analysis):
        """Check for inefficient string concatenation"""
        # Look for string concatenation in loops
        if '+=' in line and '"' in line:
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'string_concatenation',
                'current': line.strip(),
                'description': 'Consider using strings.Builder for efficient string concatenation',
                'severity': 'medium'
            })

    def check_error_handling(self, line, line_num, analysis):
        """Check error handling patterns"""
        # Look for naked error returns
        if 'return' in line and 'err' in line and 'fmt.Errorf' not in line:
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'error_handling',
                'current': line.strip(),
                'description': 'Consider wrapping errors with context using fmt.Errorf',
                'severity': 'medium'
            })

        # Check for proper controller-runtime error patterns
        if 'errors.IsNotFound' in line and 'ctrl.Result{}' not in line:
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'controller_error_pattern',
                'current': line.strip(),
                'description': 'Use ctrl.Result{} for NotFound errors in reconcilers',
                'severity': 'low'
            })

    def check_logging(self, line, line_num, analysis):
        """Check logging patterns"""
        # Look for fmt.Printf/Println instead of proper logging
        if re.search(r'fmt\.(Printf|Println|Print)\(', line):
            analysis['issues'].append({
                'line': line_num,
                'type': 'logging',
                'current': line.strip(),
                'description': 'Use structured logging (ctrl.LoggerFrom(ctx)) instead of fmt.Print',
                'severity': 'medium'
            })

        # Check for proper logger context
        if '.Info(' in line and 'WithValues' not in line:
            has_context = 'log := ctrl.LoggerFrom(ctx)' in line
            if not has_context:
                analysis['suggestions'].append({
                    'line': line_num,
                    'type': 'logging_context',
                    'current': line.strip(),
                    'description': 'Consider adding context values to logger',
                    'severity': 'low'
                })

    def check_naming(self, line, line_num, analysis):
        """Check naming conventions"""
        # Check for exported functions/types without documentation
        if re.match(r'^func\s+[A-Z]\w*', line) or re.match(r'^type\s+[A-Z]\w*\s+struct', line):
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'documentation',
                'current': line.strip(),
                'description': 'Exported functions and types should have documentation comments',
                'severity': 'low'
            })

        # Check receiver naming
        receiver_pattern = re.compile(r'func\s*\(\s*(\w+)\s+\*?(\w+)\s*\)')
        match = receiver_pattern.search(line)
        if match:
            receiver_name = match.group(1)
            type_name = match.group(2)
            expected_name = type_name[0].lower()

            if receiver_name != expected_name and len(receiver_name) > 2:
                analysis['suggestions'].append({
                    'line': line_num,
                    'type': 'receiver_naming',
                    'current': line.strip(),
                    'description': f"Consider using '{expected_name}' instead of '{receiver_name}' for receiver",
                    'severity': 'low'
                })

    def check_imports(self, line, line_num, analysis):
        """Check import organization"""
        if line.strip().startswith('import '):
            # This would need more sophisticated logic to check import grouping
            # For now, just suggest running goimports
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'imports',
                'description': 'Run goimports to organize imports properly',
                'severity': 'low'
            })

    def check_controller_patterns(self, line, line_num, analysis):
        """Check controller-runtime specific patterns"""
        # Check for proper context usage in Reconcile method signature
        reconcile_signature = re.search(r'func\s*\(\w+\s+\*?\w+\)\s+Reconcile\s*\(', line)
        if reconcile_signature and 'ctx context.Context' not in line:
            analysis['issues'].append({
                'line': line_num,
                'type': 'controller_context',
                'current': line.strip(),
                'description': 'Reconcile functions should accept context.Context as first parameter',
                'severity': 'high'
            })

        # Check for finalizer patterns
        if 'finalizer' in line and 'controllerutil' not in line:
            analysis['suggestions'].append({
                'line': line_num,
                'type': 'finalizer_pattern',
                'current': line.strip(),
                'description': 'Use controllerutil.AddFinalizer/RemoveFinalizer for proper finalizer handling',
                'severity': 'medium'
            })

    def analyze_file_structure(self, content, analysis):
        """Analyze overall file structure"""
        # Count functions and types
        analysis['stats']['functions'] = len(re.findall(r'func\s+', content))
        analysis['stats']['types'] = len(re.findall(r'type\s+\w+\s+struct', content))

        # Check for missing package documentation
        if not re.search(r'^// Package \w+', content, re.MULTILINE):
            analysis['suggestions'].append({
                'line': 1,
                'type': 'package_documentation',
                'description': 'Consider adding package documentation',
                'severity': 'low'
            })

        # Check for proper imports grouping
        imports_match = re.search(r'import\s*\(\s*([\s\S]*?)\s*\)', content)
        if imports_match:
            import_lines = [line for line in imports_match.group(1).split('\n') if line.strip()]
            if len(import_lines) > 3:
                analysis['suggestions'].append({
                    'line': 0,
                    'type': 'import_grouping',
                    'description': 'Consider grouping imports: standard, third-party, local',
                    'severity': 'low'
                })

    def generate_report(self, analysis):
        """Generate style report"""
        if not analysis:
            return ''

        report = f"Style Analysis Report for {os.path.basename(analysis['file'])}\n"
        report += '=' * 50 + '\n\n'

        # Statistics
        report += f"Statistics:\n"
        report += f"  Lines: {analysis['stats']['lines']}\n"
        report += f"  Functions: {analysis['stats']['functions']}\n"
        report += f"  Types: {analysis['stats']['types']}\n\n"

        # Critical issues
        critical_issues = [i for i in analysis['issues'] if i.get('severity') == 'high']
        if critical_issues:
            report += f"Critical Issues ({len(critical_issues)}):\n"
            for issue in critical_issues:
                report += f"  Line {issue['line']}: {issue['description']}\n"
                report += f"    Current: {issue['current']}\n\n"

        # Modernization opportunities
        if analysis['modernizations']:
            report += f"Modernization Opportunities ({len(analysis['modernizations'])}):\n"
            for mod in analysis['modernizations']:
                report += f"  Line {mod['line']}: {mod['description']}\n"
                report += f"    Current:  {mod['current']}\n"
                report += f"    Improved: {mod['suggestion']}\n\n"

        # General suggestions
        suggestions = [s for s in analysis['suggestions'] if s.get('severity') != 'high']
        if suggestions:
            report += f"Suggestions ({len(suggestions)}):\n"
            for suggestion in suggestions[:10]:
                report += f"  Line {suggestion['line']}: {suggestion['description']}\n"
            if len(suggestions) > 10:
                report += f"  ... and {len(suggestions) - 10} more suggestions\n"

        return report

    @staticmethod
    def run_cli():
        """CLI interface"""
        args = sys.argv[1:]

        if '--help' in args or '-h' in args:
            print('Usage: style-analyzer.py [options] <file.go>')
            print('Options:')
            print('  --json           Output in JSON format')
            print('  --modernize      Focus on modernization suggestions')
            print('  --critical       Show only critical issues')
            print('  --help           Show this help')
            return

        file_arg = None
        for arg in args:
            if not arg.startswith('--'):
                file_arg = arg
                break

        if not file_arg:
            print('Please provide a Go file to analyze', file=sys.stderr)
            sys.exit(1)

        analyzer = GoStyleAnalyzer()
        analysis = analyzer.analyze_file(file_arg)

        if not analysis:
            sys.exit(1)

        if '--json' in args:
            print(json.dumps(analysis, indent=2))
        elif '--critical' in args:
            critical = [i for i in analysis['issues'] if i.get('severity') == 'high']
            print(f"Critical issues: {len(critical)}")
            for issue in critical:
                print(f"Line {issue['line']}: {issue['description']}")
        elif '--modernize' in args:
            print(f"Modernization opportunities: {len(analysis['modernizations'])}")
            for mod in analysis['modernizations']:
                print(f"Line {mod['line']}: {mod['description']}")
                print(f"  Before: {mod['current']}")
                print(f"  After:  {mod['suggestion']}")
        else:
            print(analyzer.generate_report(analysis))


if __name__ == "__main__":
    GoStyleAnalyzer.run_cli()
