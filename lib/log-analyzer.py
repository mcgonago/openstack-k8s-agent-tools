#!/usr/bin/env python3

"""
Advanced Log Analyzer for openstack-k8s-operators Operators
Analyzes operator logs using pattern matching and metrics extraction
"""

import json
import re
import sys
import os


class OperatorLogAnalyzer:
    def __init__(self):
        self.patterns = self.load_patterns()
        self.metrics = []
        self.findings = []

    def load_patterns(self):
        """Load pattern definitions"""
        try:
            patterns_path = os.path.join(os.path.dirname(__file__), 'log-patterns.json')
            with open(patterns_path, 'r') as f:
                return json.load(f)
        except Exception as error:
            print(f'Error loading patterns: {error}', file=sys.stderr)
            return {
                'error_patterns': [],
                'warning_patterns': [],
                'success_patterns': []
            }

    def analyze_log_content(self, log_content, options=None):
        """Analyze log content"""
        if options is None:
            options = {}

        lines = log_content.split('\n')
        analysis = {
            'summary': {
                'total_lines': len(lines),
                'errors': 0,
                'warnings': 0,
                'successes': 0
            },
            'errors': [],
            'warnings': [],
            'performance': [],
            'openstack_issues': [],
            'timeline': [],
            'recommendations': []
        }

        for index, line in enumerate(lines):
            line_number = index + 1
            timestamp = self.extract_timestamp(line)

            # Check error patterns
            for pattern in self.patterns.get('error_patterns', []):
                if self.matches_pattern(line, pattern['pattern']):
                    analysis['errors'].append({
                        'line': line_number,
                        'timestamp': timestamp,
                        'content': line.strip(),
                        'pattern': pattern['name'],
                        'severity': pattern['severity'],
                        'category': pattern['category'],
                        'description': pattern['description'],
                        'suggestions': pattern['suggestions']
                    })
                    analysis['summary']['errors'] += 1

            # Check warning patterns
            for pattern in self.patterns.get('warning_patterns', []):
                if self.matches_pattern(line, pattern['pattern']):
                    analysis['warnings'].append({
                        'line': line_number,
                        'timestamp': timestamp,
                        'content': line.strip(),
                        'pattern': pattern['name'],
                        'severity': pattern['severity'],
                        'category': pattern['category'],
                        'description': pattern['description'],
                        'suggestions': pattern['suggestions']
                    })
                    analysis['summary']['warnings'] += 1

            # Check success patterns
            for pattern in self.patterns.get('success_patterns', []):
                if self.matches_pattern(line, pattern['pattern']):
                    analysis['summary']['successes'] += 1

            # Check performance patterns
            for pattern in self.patterns.get('performance_patterns', []):
                match = re.search(pattern['pattern'], line, re.IGNORECASE)
                if match:
                    # Get first two capture groups (value and unit)
                    value = match.group(1) if match.lastindex >= 1 else ''
                    unit = match.group(2) if match.lastindex >= 2 else ''
                    analysis['performance'].append({
                        'line': line_number,
                        'timestamp': timestamp,
                        'metric': pattern['metric'],
                        'value': value,
                        'unit': unit,
                        'content': line.strip()
                    })

            # Check OpenStack specific patterns
            for pattern in self.patterns.get('openstack_patterns', []):
                if self.matches_pattern(line, pattern['pattern']):
                    analysis['openstack_issues'].append({
                        'line': line_number,
                        'timestamp': timestamp,
                        'content': line.strip(),
                        'pattern': pattern['name'],
                        'severity': pattern['severity'],
                        'category': pattern['category'],
                        'description': pattern['description'],
                        'suggestions': pattern['suggestions']
                    })

        # Generate recommendations
        analysis['recommendations'] = self.generate_recommendations(analysis)

        # Generate timeline
        analysis['timeline'] = self.generate_timeline(analysis)

        return analysis

    def matches_pattern(self, line, pattern):
        """Check if line matches pattern"""
        try:
            return bool(re.search(pattern, line, re.IGNORECASE))
        except Exception as error:
            print(f'Invalid regex pattern: {pattern}', file=sys.stderr)
            return False

    def extract_timestamp(self, line):
        """Extract timestamp from log line"""
        # Common timestamp patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)',  # ISO format
            r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})',              # Simple format
            r'(\w{3} \d{1,2} \d{2}:\d{2}:\d{2})'                   # Syslog format
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return None

    def generate_recommendations(self, analysis):
        """Generate recommendations based on findings"""
        recommendations = []

        # High severity errors
        critical_errors = [e for e in analysis['errors'] if e['severity'] == 'critical']
        if critical_errors:
            recommendations.append({
                'priority': 'critical',
                'title': 'Critical Errors Detected',
                'description': f'Found {len(critical_errors)} critical errors that require immediate attention',
                'actions': [
                    'Stop operator if running',
                    'Review panic traces and stack dumps',
                    'Check for resource limits and constraints',
                    'Verify code logic and error handling'
                ]
            })

        # RBAC issues
        rbac_errors = [e for e in analysis['errors'] if e['category'] == 'permissions']
        if len(rbac_errors) > 3:
            recommendations.append({
                'priority': 'high',
                'title': 'RBAC Permission Issues',
                'description': f'Multiple permission errors detected ({len(rbac_errors)} instances)',
                'actions': [
                    'Review ClusterRole and RoleBinding configurations',
                    'Verify ServiceAccount has required permissions',
                    'Check namespace-specific permissions'
                ]
            })

        # Performance issues
        perf_issues = [
            p for p in analysis['performance']
            if (p['metric'] == 'duration' and float(p['value']) > 30) or
               (p['metric'] == 'queue_depth' and int(p['value']) > 100)
        ]
        if perf_issues:
            recommendations.append({
                'priority': 'medium',
                'title': 'Performance Concerns',
                'description': 'Slow reconciliation or large queue depths detected',
                'actions': [
                    'Profile reconciliation logic',
                    'Consider increasing worker count',
                    'Review external API call patterns',
                    'Implement caching where appropriate'
                ]
            })

        # OpenStack specific issues
        if analysis['openstack_issues']:
            recommendations.append({
                'priority': 'high',
                'title': 'OpenStack Service Issues',
                'description': f'Detected {len(analysis["openstack_issues"])} OpenStack service-related problems',
                'actions': [
                    'Check OpenStack service health',
                    'Verify service credentials and endpoints',
                    'Review network connectivity to OpenStack APIs'
                ]
            })

        return recommendations

    def generate_timeline(self, analysis):
        """Generate timeline of significant events"""
        events = []

        # Add all errors with timestamps
        for error in analysis['errors']:
            if error['timestamp']:
                events.append({
                    'timestamp': error['timestamp'],
                    'type': 'error',
                    'severity': error['severity'],
                    'event': error['pattern'],
                    'line': error['line']
                })

        # Add performance events
        for perf in analysis['performance']:
            if perf['timestamp'] and perf['metric'] == 'duration' and float(perf['value']) > 10:
                events.append({
                    'timestamp': perf['timestamp'],
                    'type': 'performance',
                    'severity': 'medium',
                    'event': f'Slow reconciliation ({perf["value"]}{perf["unit"]})',
                    'line': perf['line']
                })

        # Sort by timestamp (rough sorting, may need improvement for different formats)
        def sort_key(event):
            return (event['timestamp'] or '', event['line'])

        return sorted(events, key=sort_key)

    def format_results(self, analysis, options=None):
        """Format analysis results for display"""
        if options is None:
            options = {}

        format_type = options.get('format', 'text')
        verbose = options.get('verbose', False)

        if format_type == 'json':
            return json.dumps(analysis, indent=2)

        output = ''

        # Summary
        output += 'Log Analysis Summary\n'
        output += '=' * 25 + '\n'
        output += f'Total Lines: {analysis["summary"]["total_lines"]}\n'
        output += f'Errors: {analysis["summary"]["errors"]}\n'
        output += f'Warnings: {analysis["summary"]["warnings"]}\n'
        output += f'Successes: {analysis["summary"]["successes"]}\n\n'

        # Critical findings
        if analysis['errors']:
            output += 'Critical Issues\n'
            output += '-' * 20 + '\n'
            errors_to_show = analysis['errors'] if verbose else analysis['errors'][:5]
            for error in errors_to_show:
                output += f'[{error["severity"].upper()}] Line {error["line"]}: {error["pattern"]}\n'
                output += f'  {error["description"]}\n'
                if verbose:
                    output += f'  Content: {error["content"]}\n'
                    output += f'  Suggestions: {", ".join(error["suggestions"])}\n'
                output += '\n'

        # Recommendations
        if analysis['recommendations']:
            output += 'Recommendations\n'
            output += '-' * 20 + '\n'
            for rec in analysis['recommendations']:
                output += f'[{rec["priority"].upper()}] {rec["title"]}\n'
                output += f'  {rec["description"]}\n'
                output += f'  Actions: {"; ".join(rec["actions"])}\n\n'

        # Performance insights
        if analysis['performance']:
            output += 'Performance Metrics\n'
            output += '-' * 25 + '\n'
            duration_metrics = [p for p in analysis['performance'] if p['metric'] == 'duration']
            if duration_metrics:
                durations = [float(p['value']) for p in duration_metrics]
                avg_duration = sum(durations) / len(durations)
                output += f'Average reconciliation time: {avg_duration:.2f}s\n'
                output += f'Max reconciliation time: {max(durations)}s\n'

        return output

    @staticmethod
    def run_cli():
        """CLI interface"""
        args = sys.argv[1:]

        if '--help' in args or '-h' in args:
            print('Usage: log-analyzer.py [options] <log-file>')
            print('Options:')
            print('  --json           Output in JSON format')
            print('  --verbose        Show detailed information')
            print('  --patterns       Show available patterns')
            print('  --help           Show this help')
            return

        analyzer = OperatorLogAnalyzer()

        if '--patterns' in args:
            print('Available patterns:')
            print('Error patterns:', [p['name'] for p in analyzer.patterns.get('error_patterns', [])])
            print('Warning patterns:', [p['name'] for p in analyzer.patterns.get('warning_patterns', [])])
            print('Performance patterns:', [p['name'] for p in analyzer.patterns.get('performance_patterns', [])])
            return

        log_file = None
        for arg in args:
            if not arg.startswith('--'):
                log_file = arg
                break

        if not log_file:
            print('Please provide a log file to analyze (use - for stdin)', file=sys.stderr)
            sys.exit(1)

        format_options = {
            'format': 'json' if '--json' in args else 'text',
            'verbose': '--verbose' in args
        }

        try:
            if log_file == '-':
                log_content = sys.stdin.read()
            else:
                with open(log_file, 'r') as f:
                    log_content = f.read()

            analysis = analyzer.analyze_log_content(log_content)
            print(analyzer.format_results(analysis, format_options))
        except Exception as error:
            print(f'Error analyzing log file: {error}', file=sys.stderr)
            sys.exit(1)


# CLI execution
if __name__ == '__main__':
    OperatorLogAnalyzer.run_cli()
