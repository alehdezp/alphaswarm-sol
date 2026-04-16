---
phase: 02-builder-foundation-modularization
plan: 04
subsystem: builder-modularization
tags: [functions, helpers, extraction, refactor]
dependency-graph:
  requires: [02-02, 02-03]
  provides: [FunctionProcessor, helpers.py, FunctionProperties]
  affects: [02-05, 02-06, 02-07]
tech-stack:
  added: []
  patterns: [processor-pattern, dataclass-properties, delegation-pattern]
key-files:
  created:
    - src/true_vkg/kg/builder/functions.py
    - src/true_vkg/kg/builder/helpers.py
  modified:
    - src/true_vkg/kg/builder/__init__.py
decisions:
  - id: D02-04-001
    decision: "Use delegation pattern to legacy builder for transitional migration"
    rationale: "Allows incremental migration of complex property computation"
    impact: "FunctionProcessor can be used immediately while we migrate methods"
  - id: D02-04-002
    decision: "Create FunctionProperties dataclass with 225 fields"
    rationale: "Comprehensive type-safe representation of all computed properties"
    impact: "Better IDE support and documentation for function properties"
  - id: D02-04-003
    decision: "Extract 25+ helper functions to helpers.py"
    rationale: "Pure functions can be reused across modules without state"
    impact: "Cleaner code, easier testing, better separation of concerns"
metrics:
  duration: ~15m
  completed: 2026-01-20
---

# Phase 02 Plan 04: Extract Function Processing Summary

## One-Liner
Extracted function processing (~1400 LOC) into FunctionProcessor class with 225-field FunctionProperties dataclass and 25+ pure helper utilities.

## What Changed

### Task 1: Create helpers.py with Shared Utilities (551 LOC)
Created `src/true_vkg/kg/builder/helpers.py` with 25+ pure helper functions:

**Source Location Helpers:**
- `source_location(obj)` - Extract source location from Slither object
- `relpath(filename, project_root)` - Convert to relative path
- `evidence_from_location(file_path, line_start, line_end)` - Create Evidence list
- `get_source_lines(file_path, project_root, cache)` - Get source lines with caching
- `get_source_slice(...)` - Get source code slice

**Function/Node Helpers:**
- `function_label(fn)` - Get function label
- `is_access_gate(modifier_name)` - Check if modifier is access control
- `uses_var_name(variables, name)` - Check variable usage
- `strip_comments(text)` - Remove comments from source
- `node_expression(node)` - Get CFG node expression
- `callsite_data_expression(call)` - Get call data expression
- `callsite_destination(call)` - Get call destination
- `normalize_state_mutability(fn)` - Normalize mutability

**ID Generation:**
- `node_id_hash(kind, name, file_path, line_start)` - Generate node ID
- `edge_id_hash(edge_type, source, target)` - Generate edge ID

**Control Flow Helpers:**
- `is_user_controlled_destination(destination, parameter_names)`
- `is_user_controlled_expression(expression, parameter_names, allow_msg_value)`
- `is_hardcoded_gas(gas_value)`

**CFG Node Helpers:**
- `node_type_name(node)` - Get lowercase node type
- `is_loop_start(node)` - Check if loop start
- `is_loop_end(node)` - Check if loop end
- `node_has_external_call(node)` - Check for external call
- `node_has_delete(node)` - Check for delete operation

**Parameter Classification:**
- `classify_parameter_types(parameters)` - Classify parameters by type

### Task 2: Create functions.py with FunctionProcessor (1194 LOC)
Created `src/true_vkg/kg/builder/functions.py` with:

**FunctionProperties Dataclass (225 fields):**
Organized into 16 logical groups:
1. Basic Identity & Visibility (8 properties)
2. Access Control (18 properties)
3. State Operations (14 properties)
4. External Calls (20 properties)
5. User Input & Parameters (18 properties)
6. Context Variables (12 properties)
7. Token Operations (24 properties)
8. Oracle & Price (22 properties)
9. Deadline & Slippage (12 properties)
10. Loop Analysis (12 properties)
11. Arithmetic & Precision (28 properties)
12. Reentrancy (6 properties)
13. Function Classification (16 properties)
14. Flash Loan (8 properties)
15. Semantic Operations (4 properties)
16. Source Location (3 properties)

**FunctionProcessor Class:**
- `__init__(ctx: BuildContext)` - Initialize with build context
- `process_all(contract, contract_node)` - Process all functions for a contract
- `process(fn, contract, contract_node)` - Process single function
- `_compute_all_properties(...)` - Compute all 225+ properties

**Delegation Pattern:**
For the transitional period, FunctionProcessor delegates complex property
computation to the legacy builder. This allows:
- Immediate use of the new modular structure
- Incremental migration of methods without breaking changes
- Gradual test coverage improvement

### Task 3: Update Exports
Updated `src/true_vkg/kg/builder/__init__.py`:
- Export `FunctionProcessor`, `FunctionProperties`, `process_functions`
- Export `source_location`, `evidence_from_location`, `is_access_gate`
- Updated `__all__` with all new exports
- Updated module docstring

## Commits Made

| Commit | Message | Files |
|--------|---------|-------|
| 6718ec4 | feat(02-04): create helpers.py with shared builder utilities | helpers.py |
| 2992e43 | feat(02-04): extract function processing to functions.py | functions.py |
| 7f44c76 | feat(02-04): update exports for functions and helpers modules | __init__.py |

## Test Results

**Key Tests (61 passed):**
- test_operations.py - All semantic operations tests pass
- test_sequencing.py - All sequencing/ordering tests pass
- test_heuristics.py - All heuristic tests pass
- test_patterns.py - All pattern matching tests pass

**Known Pre-existing Failures (unrelated to this plan):**
- test_authority_lens.py::test_auth_005_edge_cases - Missing test contract function
- test_3.5/test_P0_T0_llm_abstraction.py::test_google_provider - Google API quota limit

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Ready for Plan 02-05 (Modifiers Extraction):**
- helpers.py provides shared utilities that can be used by modifiers.py
- FunctionProcessor demonstrates the processor pattern for extraction
- Delegation pattern allows continued migration

**Dependencies Satisfied:**
- BuildContext (02-01) - Used for DI
- Core orchestration (02-02) - Integration point
- ContractProcessor/StateVarProcessor (02-03) - Same pattern

## Key Insights

1. **Delegation Pattern Works**: The transitional delegation to legacy builder
   allows immediate use of the new structure while preserving all existing
   functionality.

2. **FunctionProperties is Comprehensive**: 225 fields capture all security
   properties computed during function analysis. This provides excellent
   type safety and IDE support.

3. **Helper Functions are Reusable**: The 25+ pure helper functions can be
   used by any module in the builder package without coupling.

4. **Test Coverage is Strong**: All 61 key tests pass, confirming the
   extraction preserves existing behavior.
