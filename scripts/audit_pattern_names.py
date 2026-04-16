#!/usr/bin/env python3
"""
Pattern Name Dependency Audit Script

Scans all VKG patterns and identifies those that rely on function/variable
naming conventions rather than semantic properties, which may fail when
code uses non-standard names.

Part of Phase 0: Foundation & Baseline
"""

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml


# Name dependency indicators
NAME_INDICATORS = [
    (r'property:\s*label', 'label property check'),
    (r'op:\s*regex', 'regex operator'),
]

# Hardcoded name patterns commonly used in security patterns
HARDCODED_NAME_PATTERNS = [
    # Access control
    r'owner|admin|authority|controller|manager|supervisor',
    # Value movement
    r'withdraw|transfer|deposit|redeem|claim|stake|unstake',
    r'mint|burn|swap|send|receive',
    # Privileged operations
    r'set[A-Z]|update[A-Z]|configure|change|modify',
    r'pause|unpause|halt|freeze|unfreeze',
    r'upgrade|migrate|initialize|reinit',
    r'grant|revoke|add[A-Z]|remove[A-Z]',
    # Emergency/rescue
    r'emergency|rescue|recover|force|sweep|drain',
    # Financial terms
    r'fee|slippage|liquidation|collateral|interest|rate',
    r'treasury|vault|pool|reserve',
    # Governance
    r'vote|proposal|quorum|timelock|execute|submit|confirm',
    # DeFi specific
    r'oracle|price|feed|bridge|relayer|router',
    r'whitelist|blacklist|allowlist|denylist',
    # Balance/token
    r'balance|allowance|approve|token',
]

# Modifier names that indicate name-based detection
NAME_BASED_MODIFIERS = [
    'nonReentrant', 'onlyOwner', 'onlyAdmin', 'onlyRole',
    'whenNotPaused', 'whenPaused', 'initializer', 'reinitializer',
]


@dataclass
class PatternDependency:
    """Represents a name dependency found in a pattern."""
    type: str  # 'label_regex', 'modifier_name', 'hardcoded_name'
    detail: str  # The specific pattern or name
    location: str  # Where in the pattern file


@dataclass
class PatternAuditResult:
    """Result of auditing a single pattern."""
    id: str
    file_path: str
    name: str
    has_name_dependency: bool
    dependencies: List[PatternDependency] = field(default_factory=list)
    severity: str = 'unknown'
    lens: List[str] = field(default_factory=list)


def find_hardcoded_names(text: str) -> List[str]:
    """Find hardcoded name patterns in text."""
    found = []
    for pattern in HARDCODED_NAME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    return found


def find_modifier_names(data: Dict[str, Any]) -> List[str]:
    """Find checks for specific modifier names."""
    found = []

    def search_conditions(obj):
        if isinstance(obj, dict):
            # Check for modifier-based conditions
            if obj.get('property') == 'modifiers':
                values = obj.get('value', [])
                if isinstance(values, list):
                    for v in values:
                        if v in NAME_BASED_MODIFIERS:
                            found.append(v)
                elif isinstance(values, str) and values in NAME_BASED_MODIFIERS:
                    found.append(values)
            # Recurse
            for v in obj.values():
                search_conditions(v)
        elif isinstance(obj, list):
            for item in obj:
                search_conditions(item)

    search_conditions(data)
    return found


def find_label_regex(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Find conditions that use regex on label property."""
    found = []

    def search_conditions(obj, path='root'):
        if isinstance(obj, dict):
            # Check for label + regex condition
            prop = obj.get('property', '')
            op = obj.get('op', '')
            value = obj.get('value', '')

            if prop == 'label' and op == 'regex':
                found.append({
                    'path': path,
                    'value': value
                })

            # Recurse
            for k, v in obj.items():
                search_conditions(v, f'{path}.{k}')
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_conditions(item, f'{path}[{i}]')

    search_conditions(data)
    return found


def audit_pattern(file_path: Path) -> List[PatternAuditResult]:
    """Audit a pattern file for name dependencies."""
    results = []
    text = file_path.read_text()

    try:
        # Handle multiple documents in a file
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return results

    for data in docs:
        if data is None:
            continue

        # Handle both single patterns and pattern lists
        patterns = data if isinstance(data, list) else [data]

        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue

            pattern_id = pattern.get('id', file_path.stem)
            pattern_name = pattern.get('name', 'Unknown')
            severity = pattern.get('severity', 'unknown')
            lens = pattern.get('lens', [])

            dependencies = []

            # Check for label regex patterns
            label_regexes = find_label_regex(pattern)
            for lr in label_regexes:
                dependencies.append(PatternDependency(
                    type='label_regex',
                    detail=lr['value'],
                    location=lr['path']
                ))

            # Check for modifier name dependencies
            modifier_names = find_modifier_names(pattern)
            for mod in modifier_names:
                dependencies.append(PatternDependency(
                    type='modifier_name',
                    detail=mod,
                    location='match.modifiers'
                ))

            # Check for hardcoded names in regex values
            match_section = yaml.dump(pattern.get('match', {}))
            hardcoded = find_hardcoded_names(match_section)
            for hc in hardcoded:
                # Only add if this appears in a regex context
                if re.search(rf'regex.*{hc}|{hc}.*regex', match_section, re.IGNORECASE | re.DOTALL):
                    dependencies.append(PatternDependency(
                        type='hardcoded_name',
                        detail=hc,
                        location='match section regex'
                    ))

            results.append(PatternAuditResult(
                id=pattern_id,
                file_path=str(file_path),
                name=pattern_name,
                has_name_dependency=len(dependencies) > 0,
                dependencies=dependencies,
                severity=severity,
                lens=lens if isinstance(lens, list) else [lens]
            ))

    return results


def audit_all_patterns(patterns_dir: Path) -> List[PatternAuditResult]:
    """Audit all patterns in a directory."""
    results = []

    for yaml_file in patterns_dir.rglob('*.yaml'):
        # Skip template files
        if 'template' in yaml_file.name.lower():
            continue
        results.extend(audit_pattern(yaml_file))

    return results


def generate_report(results: List[PatternAuditResult]) -> Dict[str, Any]:
    """Generate a summary report from audit results."""
    total = len(results)
    name_dependent = [r for r in results if r.has_name_dependency]
    name_independent = [r for r in results if not r.has_name_dependency]

    # Categorize by dependency type
    by_type = {
        'label_regex': [],
        'modifier_name': [],
        'hardcoded_name': []
    }
    for r in name_dependent:
        for dep in r.dependencies:
            by_type[dep.type].append(r.id)

    # Categorize by lens
    by_lens = {}
    for r in results:
        for lens in r.lens:
            if lens not in by_lens:
                by_lens[lens] = {'total': 0, 'name_dependent': 0}
            by_lens[lens]['total'] += 1
            if r.has_name_dependency:
                by_lens[lens]['name_dependent'] += 1

    # Categorize by severity
    by_severity = {}
    for r in results:
        sev = r.severity
        if sev not in by_severity:
            by_severity[sev] = {'total': 0, 'name_dependent': 0}
        by_severity[sev]['total'] += 1
        if r.has_name_dependency:
            by_severity[sev]['name_dependent'] += 1

    return {
        'summary': {
            'total_patterns': total,
            'name_dependent_patterns': len(name_dependent),
            'name_independent_patterns': len(name_independent),
            'name_dependency_percentage': round(len(name_dependent) / total * 100, 1) if total > 0 else 0,
        },
        'by_dependency_type': {
            'label_regex': len(set(by_type['label_regex'])),
            'modifier_name': len(set(by_type['modifier_name'])),
            'hardcoded_name': len(set(by_type['hardcoded_name'])),
        },
        'by_lens': by_lens,
        'by_severity': by_severity,
        'name_dependent_patterns': [
            {
                'id': r.id,
                'name': r.name,
                'severity': r.severity,
                'lens': r.lens,
                'dependencies': [
                    {'type': d.type, 'detail': d.detail}
                    for d in r.dependencies
                ]
            }
            for r in name_dependent
        ],
        'name_independent_patterns': [
            {
                'id': r.id,
                'name': r.name,
                'severity': r.severity,
                'lens': r.lens
            }
            for r in name_independent
        ]
    }


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """Generate a markdown report."""
    lines = [
        "# VKG Pattern Name Dependency Baseline Audit",
        "",
        "## Summary",
        "",
        f"- **Total Patterns**: {report['summary']['total_patterns']}",
        f"- **Name-Dependent Patterns**: {report['summary']['name_dependent_patterns']}",
        f"- **Name-Independent Patterns**: {report['summary']['name_independent_patterns']}",
        f"- **Name Dependency Rate**: {report['summary']['name_dependency_percentage']}%",
        "",
        "## Dependency Types",
        "",
        "| Type | Count |",
        "|------|-------|",
        f"| Label Regex | {report['by_dependency_type']['label_regex']} |",
        f"| Modifier Name | {report['by_dependency_type']['modifier_name']} |",
        f"| Hardcoded Name | {report['by_dependency_type']['hardcoded_name']} |",
        "",
        "## By Lens",
        "",
        "| Lens | Total | Name-Dependent | Rate |",
        "|------|-------|----------------|------|",
    ]

    for lens, data in sorted(report['by_lens'].items()):
        rate = round(data['name_dependent'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        lines.append(f"| {lens} | {data['total']} | {data['name_dependent']} | {rate}% |")

    lines.extend([
        "",
        "## By Severity",
        "",
        "| Severity | Total | Name-Dependent | Rate |",
        "|----------|-------|----------------|------|",
    ])

    for sev in ['critical', 'high', 'medium', 'low', 'info', 'unknown']:
        if sev in report['by_severity']:
            data = report['by_severity'][sev]
            rate = round(data['name_dependent'] / data['total'] * 100, 1) if data['total'] > 0 else 0
            lines.append(f"| {sev} | {data['total']} | {data['name_dependent']} | {rate}% |")

    lines.extend([
        "",
        "## Name-Dependent Patterns (Detail)",
        "",
    ])

    for p in report['name_dependent_patterns']:
        lines.append(f"### {p['id']}")
        lines.append(f"- **Name**: {p['name']}")
        lines.append(f"- **Severity**: {p['severity']}")
        lines.append(f"- **Lens**: {', '.join(p['lens'])}")
        lines.append("- **Dependencies**:")
        for dep in p['dependencies']:
            lines.append(f"  - `{dep['type']}`: `{dep['detail']}`")
        lines.append("")

    lines.extend([
        "",
        "## Name-Independent Patterns",
        "",
        "These patterns use semantic properties and should work regardless of naming conventions:",
        "",
    ])

    for p in report['name_independent_patterns'][:20]:  # Limit to first 20
        lines.append(f"- **{p['id']}**: {p['name']} ({p['severity']})")

    if len(report['name_independent_patterns']) > 20:
        lines.append(f"- ... and {len(report['name_independent_patterns']) - 20} more")

    lines.extend([
        "",
        "---",
        "",
        "*Generated by audit_pattern_names.py*"
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Audit VKG patterns for name dependencies')
    parser.add_argument('--patterns-dir', type=Path,
                        default=Path(__file__).parent.parent / 'patterns',
                        help='Directory containing pattern YAML files')
    parser.add_argument('--output-json', type=Path,
                        help='Output JSON report file')
    parser.add_argument('--output-md', type=Path,
                        help='Output markdown report file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    print(f"Auditing patterns in {args.patterns_dir}...")
    results = audit_all_patterns(args.patterns_dir)

    report = generate_report(results)

    # Print summary
    print(f"\nTotal patterns: {report['summary']['total_patterns']}")
    print(f"Name-dependent: {report['summary']['name_dependent_patterns']} ({report['summary']['name_dependency_percentage']}%)")
    print(f"Name-independent: {report['summary']['name_independent_patterns']}")

    if args.verbose:
        print("\nName-dependent patterns:")
        for p in report['name_dependent_patterns']:
            deps = ', '.join(f"{d['type']}" for d in p['dependencies'])
            print(f"  - {p['id']}: {deps}")

    # Output JSON
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report written to {args.output_json}")

    # Output Markdown
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        md_report = generate_markdown_report(report)
        with open(args.output_md, 'w') as f:
            f.write(md_report)
        print(f"Markdown report written to {args.output_md}")

    return report


if __name__ == '__main__':
    main()
