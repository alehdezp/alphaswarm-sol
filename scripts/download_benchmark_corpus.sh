#!/bin/bash
# VKG Benchmark Corpus Download Script
# Downloads all benchmark corpora for VKG testing

set -e

CORPUS_DIR="${1:-.vkg/benchmarks/corpora}"
STRIP_GIT="${STRIP_GIT:-0}"

strip_git_dir() {
    local target="$1"
    if [ "$STRIP_GIT" = "1" ] && [ -d "$target/.git" ]; then
        rm -rf "$target/.git"
    fi
}
echo "Downloading VKG benchmark corpora to: $CORPUS_DIR"

mkdir -p "$CORPUS_DIR"
cd "$CORPUS_DIR"

# -----------------------------------------------------------------------------
# 1. Damn Vulnerable DeFi v3
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Damn Vulnerable DeFi v3 ==="
if [ -d "damn-vulnerable-defi" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 --branch v3.0.0 \
        https://github.com/tinchoabbate/damn-vulnerable-defi.git
    echo "Downloaded: 13 challenges"
    strip_git_dir "damn-vulnerable-defi"
fi

# -----------------------------------------------------------------------------
# 2. DeFiHackLabs
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading DeFiHackLabs ==="
if [ -d "defihacklabs" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/SunWeb3Sec/DeFiHackLabs.git defihacklabs
    echo "Downloaded: 200+ real exploit PoCs"
    strip_git_dir "defihacklabs"
fi

# -----------------------------------------------------------------------------
# 3. SmartBugs (Academic Benchmark)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading SmartBugs Curated ==="
if [ -d "smartbugs" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/smartbugs/smartbugs-curated.git smartbugs
    echo "Downloaded: Standard academic benchmark"
    strip_git_dir "smartbugs"
fi

# -----------------------------------------------------------------------------
# 4. Ethernaut (OpenZeppelin CTF)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Ethernaut ==="
if [ -d "ethernaut" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/OpenZeppelin/ethernaut.git
    echo "Downloaded: 30+ CTF levels"
    strip_git_dir "ethernaut"
fi

# -----------------------------------------------------------------------------
# 5. Paradigm CTF (Advanced)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Paradigm CTF 2021 ==="
if [ -d "paradigm-ctf" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/paradigmxyz/paradigm-ctf-2021.git paradigm-ctf
    echo "Downloaded: Advanced CTF challenges"
    strip_git_dir "paradigm-ctf"
fi

# -----------------------------------------------------------------------------
# 6. Damn Vulnerable DeFi (Latest)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Damn Vulnerable DeFi (Latest) ==="
if [ -d "damn-vulnerable-defi-latest" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/theredguild/damn-vulnerable-defi.git \
        damn-vulnerable-defi-latest
    echo "Downloaded: Latest DVDeFi challenges"
    strip_git_dir "damn-vulnerable-defi-latest"
fi

# -----------------------------------------------------------------------------
# 7. Paradigm CTF 2022
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Paradigm CTF 2022 ==="
if [ -d "paradigm-ctf-2022" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/paradigmxyz/paradigm-ctf-2022.git paradigm-ctf-2022
    echo "Downloaded: 2022 CTF challenges"
    strip_git_dir "paradigm-ctf-2022"
fi

# -----------------------------------------------------------------------------
# 8. Paradigm CTF 2023
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Paradigm CTF 2023 ==="
if [ -d "paradigm-ctf-2023" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/paradigmxyz/paradigm-ctf-2023.git paradigm-ctf-2023
    echo "Downloaded: 2023 CTF challenges"
    strip_git_dir "paradigm-ctf-2023"
fi

# -----------------------------------------------------------------------------
# 9. Not So Smart Contracts (Classic Vuln Suite)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Not So Smart Contracts ==="
if [ -d "not-so-smart-contracts" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/crytic/not-so-smart-contracts.git
    echo "Downloaded: Classic vulnerability samples"
    strip_git_dir "not-so-smart-contracts"
fi

# -----------------------------------------------------------------------------
# 10. SWC Registry (PoC Examples)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading SWC Registry ==="
if [ -d "swc-registry" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/SmartContractSecurity/SWC-registry.git swc-registry
    echo "Downloaded: SWC PoC examples"
    strip_git_dir "swc-registry"
fi

# -----------------------------------------------------------------------------
# 11. Smart Contract Attack Vectors (PoC Library)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Smart Contract Attack Vectors ==="
if [ -d "smart-contract-attack-vectors" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/harendra-shakya/smart-contract-attack-vectors.git \
        smart-contract-attack-vectors
    echo "Downloaded: Attack vector examples"
    strip_git_dir "smart-contract-attack-vectors"
fi

# -----------------------------------------------------------------------------
# 12. CryptoVulhub (Exploit PoCs)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading CryptoVulhub ==="
if [ -d "cryptovulhub" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/Rivaill/CryptoVulhub.git cryptovulhub
    echo "Downloaded: Exploit PoCs"
    strip_git_dir "cryptovulhub"
fi

# -----------------------------------------------------------------------------
# 13. Smart Contract Vulnerabilities (Catalog + Examples)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Smart Contract Vulnerabilities ==="
if [ -d "smart-contract-vulnerabilities" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/kadenzipfel/smart-contract-vulnerabilities.git \
        smart-contract-vulnerabilities
    echo "Downloaded: Vulnerability catalog"
    strip_git_dir "smart-contract-vulnerabilities"
fi

# -----------------------------------------------------------------------------
# 14. ConsenSys Academy Bootcamp (Security Modules)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading ConsenSys Academy Bootcamp ==="
if [ -d "consensys-bootcamp" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/ConsenSys-Academy/Blockchain-Developer-Bootcamp.git \
        consensys-bootcamp
    echo "Downloaded: Security exercises"
    strip_git_dir "consensys-bootcamp"
fi

# -----------------------------------------------------------------------------
# 15. Taiko (Audit Reports + Code)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Taiko (taiko-mono) ==="
if [ -d "taiko-mono" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/taikoxyz/taiko-mono.git taiko-mono
    echo "Downloaded: Taiko protocol + audit reports"
    strip_git_dir "taiko-mono"
fi

# -----------------------------------------------------------------------------
# 16. Reserve Protocol (Audit Reports + Code)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Reserve Protocol ==="
if [ -d "reserve-protocol" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/reserve-protocol/protocol.git reserve-protocol
    echo "Downloaded: Reserve protocol + audits"
    strip_git_dir "reserve-protocol"
fi

# -----------------------------------------------------------------------------
# 17. Alchemix v2 (Audit Competition Targets)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Alchemix v2 (Foundry) ==="
if [ -d "alchemix-v2-foundry" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/alchemix-finance/v2-foundry.git alchemix-v2-foundry
    echo "Downloaded: Alchemix v2 contracts"
    strip_git_dir "alchemix-v2-foundry"
fi

# -----------------------------------------------------------------------------
# 18. Past Audit Competitions (Findings Index)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Past Audit Competitions (Immunefi) ==="
if [ -d "past-audit-competitions" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/immunefi-team/Past-Audit-Competitions.git \
        past-audit-competitions
    echo "Downloaded: Audit findings index"
    strip_git_dir "past-audit-competitions"
fi

# -----------------------------------------------------------------------------
# 19. Pashov Audits (Findings + PoC Tests)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Pashov Audits ==="
if [ -d "pashov-audits" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/pashov/audits.git pashov-audits
    echo "Downloaded: Audit reports + PoC tests"
    strip_git_dir "pashov-audits"
fi

# -----------------------------------------------------------------------------
# 20. MixBytes Audits (Findings Index)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading MixBytes Audits ==="
if [ -d "mixbytes-audits" ]; then
    echo "Already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/mixbytes/audits_public.git mixbytes-audits
    echo "Downloaded: Audit reports"
    strip_git_dir "mixbytes-audits"
fi

# -----------------------------------------------------------------------------
# 21. Code4rena 2025 Snapshots (Logic/Auth Targets)
# -----------------------------------------------------------------------------
echo ""
echo "=== Downloading Code4rena 2025 Snapshots ==="

if [ -d "c4-2025-04-virtuals" ]; then
    echo "Virtuals Protocol already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/code-423n4/2025-04-virtuals-protocol.git \
        c4-2025-04-virtuals
    echo "Downloaded: Virtuals Protocol (2025-04)"
    strip_git_dir "c4-2025-04-virtuals"
fi

if [ -d "c4-2025-05-blackhole" ]; then
    echo "Blackhole already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/code-423n4/2025-05-blackhole.git \
        c4-2025-05-blackhole
    echo "Downloaded: Blackhole (2025-05)"
    strip_git_dir "c4-2025-05-blackhole"
fi

if [ -d "c4-2025-06-panoptic" ]; then
    echo "Panoptic Hypovault already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/code-423n4/2025-06-panoptic.git \
        c4-2025-06-panoptic
    echo "Downloaded: Panoptic Hypovault (2025-06)"
    strip_git_dir "c4-2025-06-panoptic"
fi

if [ -d "c4-2025-10-sequence" ]; then
    echo "Sequence already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/code-423n4/2025-10-sequence.git \
        c4-2025-10-sequence
    echo "Downloaded: Sequence (2025-10)"
    strip_git_dir "c4-2025-10-sequence"
fi

if [ -d "c4-2025-10-hybra" ]; then
    echo "Hybra Finance already exists, skipping..."
else
    git clone --depth 1 \
        https://github.com/code-423n4/2025-10-hybra-finance.git \
        c4-2025-10-hybra
    echo "Downloaded: Hybra Finance (2025-10)"
    strip_git_dir "c4-2025-10-hybra"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=== Corpus Download Complete ==="
echo ""
echo "Downloaded corpora:"
ls -la "$CORPUS_DIR"
echo ""
echo "Total size:"
du -sh "$CORPUS_DIR"
echo ""
echo "Next steps:"
echo "  1. Create expected results: .vkg/benchmarks/expectations/"
echo "  2. Run benchmark: vkg benchmark run --suite all"
echo "  3. Set baseline: vkg benchmark set-baseline --version v4.0.0"
echo ""
echo "Optional: set STRIP_GIT=1 to remove .git history for offline runs."
