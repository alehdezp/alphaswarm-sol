#!/usr/bin/env python3
"""
Verify Product Workflow - Strict Agentic Audit.

This script executes the critical path validation defined in PHASE_7.3_CRITICAL_AUDIT.md.
It acts as the *developer console* that triggers the Agentic Controller.
"""

import subprocess
import sys
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ProductVerify")

def main():
    logger.info("=== STARTING PHASE 7.3 CRITICAL PRODUCT AUDIT ===")
    
    # 1. Verify Environment
    logger.info("Step 1: Verifying Environment Tools...")
    tools = ["claude", "uv", "solc", "alphaswarm"]
    for tool in tools:
        if not shutil.which(tool):
            logger.error(f"CRITICAL: '{tool}' not found in PATH. Product cannot ship without it.")
            sys.exit(1)
            
    # 2. Run Economic Context Test via Agent Skill
    logger.info("Step 2: Triggering Strict Agentic Audit (FlashLoanArb)...")
    contract_path = Path("tests/contracts/economic/FlashLoanArb.sol")
    
    if not contract_path.exists():
        logger.error(f"Contract {contract_path} missing.")
        sys.exit(1)
        
    # The command instructs the Controller Agent (Claude) to perform the audit using the skill.
    # The prompt MUST be explicit about the expectations.
    prompt = (
        f"Please run the /vrs-strict-audit skill on {contract_path}. "
        "Create a blind test environment, spawn a subject agent, "
        "monitor its progress, and verify it detects the economic vulnerability "
        "(Flash Loan Arbitrage) and creates the correct artifacts (Graph, Beads). "
        "If the agent gets stuck or encounters errors, use your auto-fix capabilities. "
        "Report PASS only if the economic reasoning is sound."
    )
    
    cmd = ["claude", "-p", prompt]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        # We use check=True to fail if claude exits with non-zero
        subprocess.run(cmd, check=True)
        logger.info("=== PRODUCT VERIFICATION PASSED ===")
        
    except subprocess.CalledProcessError as e:
        logger.error("=== PRODUCT VERIFICATION FAILED ===")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()