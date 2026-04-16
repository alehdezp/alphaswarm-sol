# Research: vulndocs Namespace Collision (Task 2)

**Finding: COLLISION — use `_vulndocs_data`**

## Analysis

The `alphaswarm_sol.vulndocs` Python subpackage exists at `src/alphaswarm_sol/vulndocs/` and contains:
- `__init__.py` (150 lines, exports 40+ symbols)
- 20+ Python modules (schema.py, discovery.py, validation.py, etc.)
- 10+ subdirectories (agents/, ingestion/, pipeline/, etc.)

The vulndocs YAML data lives at the project root `vulndocs/` and contains:
- 19 category directories (access-control, reentrancy, oracle, etc.)
- 680+ pattern YAML files
- `index.yaml`

## Collision Test

If we force-include `vulndocs/` → `alphaswarm_sol/vulndocs/` in the wheel:
- Hatch's force-include would attempt to merge the YAML data files INTO the Python subpackage directory
- This creates a directory containing BOTH Python modules AND YAML data files
- `importlib.resources.files("alphaswarm_sol").joinpath("vulndocs")` would return a `Traversable` pointing to the MERGED directory
- Python `import alphaswarm_sol.vulndocs` would still work (the `__init__.py` is preserved)
- BUT: `.iterdir()` would return both `.py` files AND category directories, causing confusion
- Category discovery code would need to filter out Python files

**This is a namespace collision.** The data and code share the same directory path in the installed wheel.

## Decision

Use `_vulndocs_data` as the bundled data path:
- `pyproject.toml` force-include: `"vulndocs" = "alphaswarm_sol/_vulndocs_data"`
- `vulndocs_read_path()` uses: `importlib.resources.files("alphaswarm_sol").joinpath("_vulndocs_data")`
- Clean separation: Python code at `alphaswarm_sol/vulndocs/`, data at `alphaswarm_sol/_vulndocs_data/`
- No filtering needed, no confusion, no merge conflicts

## Evidence

```
# Python subpackage
$ ls src/alphaswarm_sol/vulndocs/
__init__.py  schema.py  discovery.py  validation.py  ingestion/  agents/  ...

# YAML data
$ ls vulndocs/
access-control/  reentrancy/  oracle/  token/  ...  index.yaml
```

These occupy different namespaces currently. Force-including into the same path would merge them.
