#!/bin/bash
# Import SmartBugs curated dataset as test fixtures
#
# Source: https://github.com/smartbugs/smartbugs-curated
#
# This script:
# 1. Clones the SmartBugs curated repository
# 2. Copies contracts organized by vulnerability type
# 3. Creates ground-truth.yaml files from the dataset labels

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures/smartbugs"

echo "SmartBugs Import Script"
echo "======================"
echo "Fixtures directory: $FIXTURES_DIR"
echo ""

mkdir -p "$FIXTURES_DIR"

# Clone SmartBugs curated if not present
if [ ! -d "$FIXTURES_DIR/repo" ]; then
    echo "[1/4] Cloning SmartBugs curated repository..."
    git clone --depth 1 https://github.com/smartbugs/smartbugs-curated "$FIXTURES_DIR/repo"
else
    echo "[1/4] Repository already cloned, updating..."
    cd "$FIXTURES_DIR/repo" && git pull && cd -
fi

# Vulnerability types to import
VULN_TYPES=(
    "reentrancy"
    "access_control"
    "arithmetic"
    "unchecked_low_level_calls"
    "denial_of_service"
    "front_running"
    "time_manipulation"
)

echo ""
echo "[2/4] Creating vulnerability type directories..."

for vuln_type in "${VULN_TYPES[@]}"; do
    mkdir -p "$FIXTURES_DIR/$vuln_type/src"
done

echo ""
echo "[3/4] Copying contracts by vulnerability type..."

for vuln_type in "${VULN_TYPES[@]}"; do
    src_dir="$FIXTURES_DIR/repo/dataset/$vuln_type"
    dst_dir="$FIXTURES_DIR/$vuln_type/src"

    if [ -d "$src_dir" ]; then
        count=0
        for contract in "$src_dir"/*.sol; do
            if [ -f "$contract" ]; then
                cp "$contract" "$dst_dir/"
                ((count++)) || true
            fi
        done
        echo "  $vuln_type: $count contracts"
    else
        echo "  $vuln_type: directory not found in dataset"
    fi
done

echo ""
echo "[4/4] Creating ground truth files..."

# Create a Python script to generate ground truth from SmartBugs labels
python3 << 'PYTHON_SCRIPT'
import os
import json
import yaml
from pathlib import Path

fixtures_dir = os.environ.get('FIXTURES_DIR', 'tests/fixtures/smartbugs')
repo_dir = os.path.join(fixtures_dir, 'repo')

vuln_types = [
    'reentrancy',
    'access_control',
    'arithmetic',
    'unchecked_low_level_calls',
    'denial_of_service',
    'front_running',
    'time_manipulation',
]

for vuln_type in vuln_types:
    type_dir = os.path.join(fixtures_dir, vuln_type)
    src_dir = os.path.join(type_dir, 'src')

    if not os.path.exists(src_dir):
        continue

    contracts = []
    for sol_file in Path(src_dir).glob('*.sol'):
        contracts.append({
            'file': f'src/{sol_file.name}',
            'vulnerability_type': vuln_type,
            'source': 'smartbugs-curated',
            'notes': 'See SmartBugs paper for detailed labels'
        })

    if contracts:
        ground_truth = {
            'source': 'smartbugs-curated',
            'source_url': 'https://github.com/smartbugs/smartbugs-curated',
            'vulnerability_type': vuln_type,
            'contracts': contracts,
            'validation_notes': f'''
Ground truth labels from SmartBugs curated dataset.
Each contract in this directory is known to contain {vuln_type} vulnerabilities.
Specific line numbers and detailed labels are available in the SmartBugs repository.
'''.strip()
        }

        gt_path = os.path.join(type_dir, 'ground-truth.yaml')
        with open(gt_path, 'w') as f:
            yaml.dump(ground_truth, f, default_flow_style=False, sort_keys=False)

        print(f'  Created {vuln_type}/ground-truth.yaml ({len(contracts)} contracts)')

PYTHON_SCRIPT

echo ""
echo "SmartBugs fixtures imported successfully!"
echo ""
echo "Structure:"
find "$FIXTURES_DIR" -maxdepth 2 -type d | head -20
echo ""
echo "To use these fixtures in tests:"
echo "  from tests.fixtures.smartbugs import load_smartbugs_contracts"
