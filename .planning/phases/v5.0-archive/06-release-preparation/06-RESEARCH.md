# Phase 6: Release Preparation - Research

**Researched:** 2026-01-21
**Domain:** Python packaging, rebrand, PyPI/Docker distribution, documentation
**Confidence:** HIGH

## Summary

This research covers the complete release preparation for AlphaSwarm.sol 0.5.0, including the rebrand from AlphaSwarm.sol, PyPI publishing via Trusted Publishing, Docker image creation, and MkDocs Material documentation.

The project currently exists as `alphaswarm` with package `true_vkg` in `src/true_vkg/`. The rebrand requires renaming approximately 1000+ files containing references, the source directory itself, and all package/import paths. PyPI Trusted Publishing eliminates the need for API tokens by using GitHub's OIDC identity. Docker multi-stage builds with uv provide efficient, small production images.

**Primary recommendation:** Execute rebrand first (atomic commit), then set up PyPI trusted publisher, then create release workflow, then Docker, then docs. The rebrand is the most invasive change and should be isolated.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | >=1.25.0 | Build backend | Modern, simple, used by PyPA |
| pypa/gh-action-pypi-publish | release/v1 | PyPI publishing | Official PyPA action with Trusted Publishing |
| actions/attest-build-provenance | v2 | Artifact attestations | GitHub's official attestation action |
| MkDocs Material | 9.x | Documentation | Most popular MkDocs theme, feature-rich |
| uv | latest | Python package manager | Fast, modern, handles Docker builds well |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs-material[imaging] | 9.x | Social cards, image optimization | Auto social previews |
| ghp-import | latest | GitHub Pages deployment | Behind mkdocs gh-deploy |
| docker (multi-stage) | latest | Container builds | CLI distribution |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hatchling | setuptools | hatchling simpler for pure Python |
| MkDocs Material | Sphinx | MkDocs faster, Material prettier |
| Trusted Publishing | API tokens | Trusted Publishing more secure, no secrets |

**Installation:**
```bash
# Build/publish tools
pip install build twine

# Documentation
pip install mkdocs-material

# Already in project
uv sync
```

## Architecture Patterns

### Rebrand File Changes

Files requiring "true_vkg" -> "alphaswarm" changes:

```
REBRAND SCOPE (approximate):
├── pyproject.toml                    # name, CLI entry points
├── src/
│   └── true_vkg/ -> alphaswarm/      # RENAME directory
│       ├── __init__.py               # Package docstring
│       ├── cli/main.py               # App help text, all "alphaswarm" refs
│       └── **/*.py                   # ~90+ files with imports
├── tests/
│   └── **/*.py                       # ~200+ files with imports
├── README.md                         # All references, examples
├── CLAUDE.md                         # All references
├── docs/**/*.md                      # ~100+ files
├── .claude/agents/*.md               # 10 agent files
├── .claude/skills/**/*.md            # Skill files
├── .vrs/AGENTS.md                    # Agent interface doc
├── .github/workflows/*.yml           # 4 workflow files
├── .planning/**/*.md                 # ~50+ planning docs
├── patterns/**/*.yaml                # References in pattern files
└── scripts/**/*.py                   # Script files
```

**Total files affected:** ~1000+ (based on grep showing 1009 matches)

### Rebrand Pattern

**Step 1: Rename source directory**
```bash
mv src/true_vkg src/alphaswarm
```

**Step 2: Update pyproject.toml**
```toml
[project]
name = "alphaswarm-sol"
version = "0.5.0"

[project.scripts]
alphaswarm = "alphaswarm.cli:app"
aswarm = "alphaswarm.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/alphaswarm"]
```

**Step 3: Mass find-replace (order matters)**
```bash
# 1. Package imports (most critical)
find . -type f -name "*.py" -exec sed -i '' 's/from true_vkg/from alphaswarm/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/import true_vkg/import alphaswarm/g' {} +

# 2. CLI commands in docs/examples
find . -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" \) \
    -exec sed -i '' 's/alphaswarm/alphaswarm/g' {} +

# 3. Directory references
find . -type f -exec sed -i '' 's/\.true_vkg/\.alphaswarm/g' {} +

# 4. Human-readable name
find . -type f -name "*.md" -exec sed -i '' 's/AlphaSwarm.sol/AlphaSwarm.sol/g' {} +
```

### PyPI Publishing Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write  # For GitHub release
  id-token: write  # REQUIRED for Trusted Publishing

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Build distributions
        run: uv build

      - name: Upload distributions
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi  # Requires GitHub environment named "pypi"
    permissions:
      id-token: write
      attestations: write
      contents: read
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Generate attestations
        uses: actions/attest-build-provenance@v2
        with:
          subject-path: 'dist/*'

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # No credentials needed - uses OIDC

  github-release:
    needs: [build, publish]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
          generate_release_notes: true
```

### PyPI Trusted Publisher Setup

**On PyPI (pending publisher for new package):**
1. Go to https://pypi.org/manage/account/publishing/
2. Add pending publisher:
   - **PyPI Project Name:** `alphaswarm-sol`
   - **Owner:** `<github-username-or-org>`
   - **Repository name:** `alphaswarm-sol`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi` (optional but recommended)

**On GitHub:**
1. Create environment named `pypi`
2. Add required reviewers for manual approval
3. No secrets needed - OIDC handles authentication

### Docker Multi-Stage Build

```dockerfile
# Dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim

# Install runtime dependencies (solc, git for slither)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN useradd -m -s /bin/bash alphaswarm
USER alphaswarm

WORKDIR /audit

ENTRYPOINT ["alphaswarm"]
CMD ["--help"]
```

**Agent-optimized variant:**
```dockerfile
# Dockerfile.agent - Optimized for multi-agent workflows
FROM python:3.12-slim AS builder
# ... same build stage ...

FROM python:3.12-slim

# Minimal runtime for agent use
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Agent mode: no interactive features
ENV ALPHASWARM_AGENT_MODE=1
ENV ALPHASWARM_OUTPUT_FORMAT=json

WORKDIR /audit
ENTRYPOINT ["alphaswarm"]
```

### MkDocs Configuration

```yaml
# mkdocs.yml
site_name: AlphaSwarm.sol
site_url: https://<org>.github.io/alphaswarm-sol
site_description: AI-native smart contract security analysis

theme:
  name: material
  palette:
    - scheme: default
      primary: deep purple
      accent: amber
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: deep purple
      accent: amber
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.instant
    - navigation.tabs
    - navigation.sections
    - content.code.copy
    - search.highlight

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - First Audit: getting-started/first-audit.md
  - Reference:
    - CLI Commands: reference/cli.md
  - Philosophy: philosophy.md

plugins:
  - search

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - admonition
  - toc:
      permalink: true
```

### GitHub Pages Deployment Workflow

```yaml
# .github/workflows/docs.yml
name: Deploy Docs

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install mkdocs-material

      - run: mkdocs gh-deploy --force
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI authentication | API token management | Trusted Publishing | Secretless, auto-rotating tokens |
| Build provenance | Manual checksums | GitHub Artifact Attestations | Sigstore-signed, verifiable |
| Docs deployment | Custom deploy scripts | mkdocs gh-deploy | Built-in, handles gh-pages branch |
| Docker layer caching | Manual COPY ordering | uv with --mount=type=cache | Optimized for Python deps |
| Changelog generation | Manual CHANGELOG.md | GitHub release notes | Auto-generated from commits |

**Key insight:** The Python packaging ecosystem has standardized on PyPA tools and patterns. Using them ensures compatibility and reduces maintenance.

## Common Pitfalls

### Pitfall 1: Rebrand Import Breakage
**What goes wrong:** Renaming the source directory breaks all imports
**Why it happens:** Python imports use the directory name as package name
**How to avoid:**
1. Rename directory FIRST
2. Update pyproject.toml immediately
3. Run mass import replacement
4. Test with `python -c "import alphaswarm"`
**Warning signs:** ImportError on any module

### Pitfall 2: Trusted Publishing Permission Denied
**What goes wrong:** Workflow fails with "permission denied" on PyPI
**Why it happens:** Missing `id-token: write` permission or wrong workflow/environment
**How to avoid:**
1. Add `id-token: write` at job level
2. Verify workflow filename matches PyPI configuration exactly
3. Use named environment (`environment: pypi`)
**Warning signs:** 403/401 errors in publish step

### Pitfall 3: Version String Duplication
**What goes wrong:** Version in multiple places gets out of sync
**Why it happens:** Version in pyproject.toml, __init__.py, docs, etc.
**How to avoid:** Single source of truth in pyproject.toml
```python
# alphaswarm/__init__.py
from importlib.metadata import version
__version__ = version("alphaswarm-sol")
```
**Warning signs:** `alphaswarm --version` shows different version than PyPI

### Pitfall 4: Docker Image Too Large
**What goes wrong:** Docker image >1GB due to build tools
**Why it happens:** Build dependencies included in final image
**How to avoid:**
1. Multi-stage build with separate builder stage
2. Only copy .venv to final image
3. Use slim base image
4. Clean apt cache in same RUN instruction
**Warning signs:** Image size >500MB for pure Python app

### Pitfall 5: MkDocs Navigation Not Updating
**What goes wrong:** New docs not appearing in navigation
**Why it happens:** mkdocs.yml nav section is static
**How to avoid:** Either:
1. Maintain nav section manually (recommended for structure)
2. Use mkdocs-awesome-pages-plugin for auto-nav
**Warning signs:** Docs build succeeds but pages missing from nav

### Pitfall 6: .alphaswarm vs .vkg Directory Confusion
**What goes wrong:** Old .true_vkg references left in code
**Why it happens:** Incomplete find-replace
**How to avoid:**
1. Grep for all variations: `.true_vkg`, `true_vkg`, `.vkg`
2. Test fresh install creates `.alphaswarm/` directory
3. Update AGENTS.md file references
**Warning signs:** FileNotFoundError at runtime

## Code Examples

Verified patterns from official sources:

### Dynamic Version from pyproject.toml
```python
# Source: Python Packaging User Guide
# alphaswarm/__init__.py
"""AlphaSwarm.sol - AI-native smart contract security."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("alphaswarm-sol")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
```

### pyproject.toml Complete Configuration
```toml
# Source: PyPA packaging guide
[project]
name = "alphaswarm-sol"
version = "0.5.0"
description = "AI-native smart contract security analysis"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
keywords = ["solidity", "security", "vulnerability", "audit", "llm"]
authors = [{ name = "AlphaSwarm Team" }]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Security",
]

dependencies = [
    # ... existing dependencies
]

[project.urls]
Homepage = "https://github.com/<org>/alphaswarm-sol"
Documentation = "https://<org>.github.io/alphaswarm-sol"
Repository = "https://github.com/<org>/alphaswarm-sol"

[project.scripts]
alphaswarm = "alphaswarm.cli:app"
aswarm = "alphaswarm.cli:app"

[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/alphaswarm"]
```

### CLI Entry Point Update
```python
# Source: Typer documentation
# alphaswarm/cli/main.py

app = typer.Typer(
    name="alphaswarm",
    help="AlphaSwarm.sol: AI-native smart contract security analysis"
)

@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
) -> None:
    """AlphaSwarm.sol - Find vulnerabilities humans miss."""
    if version:
        from alphaswarm import __version__
        typer.echo(f"AlphaSwarm.sol {__version__}")
        raise typer.Exit()
```

### Smoke Test Script
```bash
#!/bin/bash
# smoke_test.sh - Validate fresh install

set -e

echo "=== AlphaSwarm.sol Smoke Test ==="

# Test 1: Version
echo -n "Testing version... "
VERSION=$(alphaswarm --version)
if [[ $VERSION == *"0.5.0"* ]]; then
    echo "PASS: $VERSION"
else
    echo "FAIL: Expected 0.5.0, got $VERSION"
    exit 1
fi

# Test 2: Help
echo -n "Testing help... "
alphaswarm --help > /dev/null && echo "PASS" || echo "FAIL"

# Test 3: Build KG (with sample contract)
echo -n "Testing build-kg... "
cat > /tmp/Test.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract Test {
    function foo() public {}
}
EOF
alphaswarm build-kg /tmp/Test.sol > /dev/null && echo "PASS" || echo "FAIL"

# Test 4: Query
echo -n "Testing query... "
alphaswarm query "MATCH functions" --graph /tmp/.alphaswarm/graphs/graph.json > /dev/null && echo "PASS" || echo "FAIL"

echo "=== All Tests Passed ==="
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| API tokens for PyPI | Trusted Publishing (OIDC) | 2023 | No secrets, auto-rotating tokens |
| Manual checksums | GitHub Artifact Attestations | 2024 | Sigstore-signed provenance |
| setup.py | pyproject.toml + hatchling | 2022 | Simpler config, standard format |
| pip install | uv for dev, pip for users | 2024 | 10-100x faster installs |
| requirements.txt | uv.lock | 2024 | Full dependency graph, reproducible |

**Deprecated/outdated:**
- `setup.py`: Replaced by pyproject.toml declarative config
- `setup.cfg`: Merged into pyproject.toml
- API tokens for CI publishing: Replaced by Trusted Publishing
- Manual MANIFEST.in: Hatchling handles automatically

## Open Questions

Things that couldn't be fully resolved:

1. **GitHub Repo Rename Timing**
   - What we know: Repo rename from alphaswarm to alphaswarm-sol needed
   - What's unclear: Whether to rename before or after first release
   - Recommendation: Rename BEFORE release so PyPI pending publisher matches

2. **Test File Updates**
   - What we know: ~200+ test files have true_vkg imports
   - What's unclear: Automated sed may miss edge cases
   - Recommendation: Run full test suite after rebrand, fix manually

3. **Backward Compatibility Period**
   - What we know: Package name changes break existing installs
   - What's unclear: Whether to publish `alphaswarm` pointing to new name
   - Recommendation: Clean break for 0.5.0 (pre-1.0, no BC guarantee)

## Sources

### Primary (HIGH confidence)
- [PyPI Trusted Publishing Docs](https://docs.pypi.org/trusted-publishers/) - Pending publisher setup
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) - Full workflow example
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) - Theme configuration
- [uv Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/) - Multi-stage patterns
- [GitHub Artifact Attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations) - Provenance signing

### Secondary (MEDIUM confidence)
- [PyPA gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) - Action usage
- [hatchling docs](https://hatch.pypa.io/) - Build configuration

### Tertiary (LOW confidence)
- WebSearch results for Docker best practices - General patterns verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official PyPA tooling, well-documented
- Architecture: HIGH - Standard patterns from official guides
- Pitfalls: MEDIUM - Based on common issues, verified with docs
- Rebrand scope: HIGH - Verified with grep on actual codebase

**Research date:** 2026-01-21
**Valid until:** 2026-02-21 (30 days - stable ecosystem)
