#!/bin/bash
# Pattern triage: move broken patterns to quarantine or archive
# All patterns here have ALL their tier_a conditions referencing non-existent builder properties.

set -e
cd /Volumes/ex_ssd/home/projects/python/vkg-solidity/true-vkg

QUARANTINE=vulndocs/.quarantine
ARCHIVE=vulndocs/.archive/deprecated

# ===========================================================================
# QUARANTINE: Properties are implementable via AST/Slither analysis
# These patterns are valid but need builder property implementation first.
# ===========================================================================

# --- abi decode / calldata ---
git mv vulndocs/logic/array-handling/patterns/abi-decode-without-length-check.yaml $QUARANTINE/
git mv vulndocs/logic/array-handling/patterns/calldata-slice-without-length-check.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-010.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-038.yaml $QUARANTINE/

# --- array handling ---
git mv vulndocs/logic/array-handling/patterns/array-length-mismatch.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-022.yaml $QUARANTINE/

# --- arithmetic (implementable precision/overflow detectors) ---
git mv vulndocs/arithmetic/general/patterns/arith-003.yaml $QUARANTINE/
git mv vulndocs/arithmetic/general/patterns/arith-004.yaml $QUARANTINE/
git mv vulndocs/arithmetic/general/patterns/arith-008.yaml $QUARANTINE/
git mv vulndocs/arithmetic/general/patterns/arith-014.yaml $QUARANTINE/
git mv vulndocs/arithmetic/general/patterns/arith-015.yaml $QUARANTINE/
git mv vulndocs/arithmetic/general/patterns/arith-016.yaml $QUARANTINE/

# --- delegatecall properties ---
git mv vulndocs/access-control/delegatecall/patterns/delegatecall-context-issue.yaml $QUARANTINE/
git mv vulndocs/access-control/delegatecall/patterns/delegatecall-storage-collision.yaml $QUARANTINE/

# --- opcode detection (uses_extcodesize, uses_extcodehash, uses_gasleft) ---
git mv vulndocs/access-control/general/patterns/auth-079.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-080.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-081.yaml $QUARANTINE/

# --- merkle proof ---
git mv vulndocs/access-control/external-call/patterns/ext-011.yaml $QUARANTINE/
git mv vulndocs/crypto/merkle/patterns/merkle-leaf-without-domain-separation.yaml $QUARANTINE/

# --- oracle update properties (implementable: detect oracle updater functions) ---
git mv vulndocs/access-control/external-call/patterns/ext-027.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-028.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-029.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-030.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-031.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-064.yaml $QUARANTINE/
git mv vulndocs/oracle/freshness/patterns/oracle-update-missing-deviation-check.yaml $QUARANTINE/
git mv vulndocs/oracle/freshness/patterns/oracle-update-missing-rate-limit.yaml $QUARANTINE/
git mv vulndocs/oracle/freshness/patterns/oracle-update-missing-sequence-check.yaml $QUARANTINE/
git mv vulndocs/oracle/freshness/patterns/oracle-update-missing-signature-check.yaml $QUARANTINE/

# --- address validation properties ---
git mv vulndocs/access-control/external-call/patterns/ext-018.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-019.yaml $QUARANTINE/

# --- amount division ---
git mv vulndocs/access-control/external-call/patterns/ext-059.yaml $QUARANTINE/

# --- read-only reentrancy surface (implementable: view functions reading mutable state) ---
git mv vulndocs/reentrancy/read-only/patterns/read-only-reentrancy.yaml $QUARANTINE/
git mv vulndocs/reentrancy/classic/patterns/value-movement-read-only-reentrancy.yaml $QUARANTINE/
git mv vulndocs/reentrancy/general/patterns/vm-004.yaml $QUARANTINE/

# --- cross-chain context (implementable: detect bridge patterns) ---
git mv vulndocs/access-control/external-call/patterns/ext-034.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-056.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-070.yaml $QUARANTINE/
git mv vulndocs/access-control/external-call/patterns/ext-074.yaml $QUARANTINE/

# --- logic patterns with implementable properties ---
git mv vulndocs/logic/general/patterns/logic-014.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-015.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-021.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-023.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-024.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-026.yaml $QUARANTINE/

# --- DOS patterns with implementable storage growth detection ---
git mv vulndocs/dos/general/patterns/live-025.yaml $QUARANTINE/
git mv vulndocs/dos/general/patterns/live-026.yaml $QUARANTINE/
git mv vulndocs/dos/general/patterns/live-037.yaml $QUARANTINE/

# --- access gate detail properties (implementable: inspect modifier internals) ---
git mv vulndocs/access-control/general/patterns/auth-095.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-101.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-102.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-105.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-106.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-018.yaml $QUARANTINE/
git mv vulndocs/access-control/general/patterns/auth-057.yaml $QUARANTINE/

# --- invariant detection ---
git mv vulndocs/logic/invariants/patterns/invariant-touch-without-check.yaml $QUARANTINE/
git mv vulndocs/logic/general/patterns/logic-010.yaml $QUARANTINE/

# ===========================================================================
# ARCHIVE: Properties require deep semantic analysis, LLM reasoning, or
# cross-contract analysis — not suitable for tier_a deterministic matching.
# These should be tier_b/tier_c patterns or handled by LLM agents.
# ===========================================================================

# --- governance (requires understanding voting/quorum semantics) ---
git mv vulndocs/access-control/general/patterns/auth-046.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-072.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-073.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-076.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-077.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-093.yaml $ARCHIVE/
git mv vulndocs/access-control/external-call/patterns/ext-045.yaml $ARCHIVE/
git mv vulndocs/governance/voting/patterns/governance-vote-without-snapshot.yaml $ARCHIVE/

# --- multisig (requires understanding multisig protocol semantics) ---
git mv vulndocs/access-control/general/patterns/auth-047.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-048.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-074.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-075.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-099.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-100.yaml $ARCHIVE/

# --- complex semantic (requires cross-function/cross-contract reasoning) ---
git mv vulndocs/access-control/general/patterns/auth-009.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-010.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-030.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-049.yaml $ARCHIVE/
git mv vulndocs/access-control/general/patterns/auth-050.yaml $ARCHIVE/

# --- logic patterns requiring deep semantic analysis ---
git mv vulndocs/logic/general/patterns/logic-001.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-002.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-004.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-007.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-011.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-012.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-013.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-017.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-019.yaml $ARCHIVE/
git mv vulndocs/logic/general/patterns/logic-020.yaml $ARCHIVE/

# --- arithmetic patterns requiring semantic financial context ---
git mv vulndocs/arithmetic/general/patterns/arith-005.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-006.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-007.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-010.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-017.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-018.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-019.yaml $ARCHIVE/
git mv vulndocs/arithmetic/general/patterns/arith-020.yaml $ARCHIVE/

# --- dos patterns with semantic fund-locking analysis ---
git mv vulndocs/dos/general/patterns/live-010.yaml $ARCHIVE/
git mv vulndocs/dos/general/patterns/live-036.yaml $ARCHIVE/

echo "Done. Moved patterns to quarantine and archive."
