"""
Tests for Pattern Taxonomy Mapping (Task 3.16)

Tests the mapping of VKG patterns to standard vulnerability taxonomies:
- SWC (Smart Contract Weakness Classification)
- CWE (Common Weakness Enumeration)
- OWASP Smart Contract Top 10
- DASP (legacy)
"""

import unittest

from alphaswarm_sol.findings.taxonomy import (
    TaxonomyMapping,
    get_taxonomy,
    get_swc,
    get_cwe,
    get_owasp_sc,
    get_dasp,
    enrich_finding_with_taxonomy,
    TAXONOMY_REGISTRY,
    SWC_REFERENCE,
    OWASP_SC_REFERENCE,
    DASP_REFERENCE,
)


class TestTaxonomyMapping(unittest.TestCase):
    """Tests for TaxonomyMapping dataclass."""

    def test_empty_mapping(self):
        """Test empty taxonomy mapping."""
        mapping = TaxonomyMapping()
        self.assertEqual(mapping.swc, [])
        self.assertEqual(mapping.cwe, [])
        self.assertEqual(mapping.owasp_sc, [])
        self.assertEqual(mapping.dasp, [])

    def test_full_mapping(self):
        """Test full taxonomy mapping."""
        mapping = TaxonomyMapping(
            swc=["SWC-107"],
            cwe=["CWE-841"],
            owasp_sc=["SC05"],
            dasp=["DASP-1"],
        )
        self.assertEqual(mapping.swc, ["SWC-107"])
        self.assertEqual(mapping.cwe, ["CWE-841"])
        self.assertEqual(mapping.owasp_sc, ["SC05"])
        self.assertEqual(mapping.dasp, ["DASP-1"])

    def test_primary_swc(self):
        """Test primary SWC extraction."""
        mapping = TaxonomyMapping(swc=["SWC-107", "SWC-114"])
        self.assertEqual(mapping.primary_swc(), "SWC-107")

    def test_primary_swc_empty(self):
        """Test primary SWC when empty."""
        mapping = TaxonomyMapping()
        self.assertEqual(mapping.primary_swc(), "")

    def test_primary_cwe(self):
        """Test primary CWE extraction."""
        mapping = TaxonomyMapping(cwe=["CWE-841", "CWE-284"])
        self.assertEqual(mapping.primary_cwe(), "CWE-841")

    def test_primary_cwe_empty(self):
        """Test primary CWE when empty."""
        mapping = TaxonomyMapping()
        self.assertEqual(mapping.primary_cwe(), "")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        mapping = TaxonomyMapping(
            swc=["SWC-107"],
            cwe=["CWE-841"],
            owasp_sc=["SC05"],
            dasp=["DASP-1"],
        )
        d = mapping.to_dict()
        self.assertEqual(d["swc"], ["SWC-107"])
        self.assertEqual(d["cwe"], ["CWE-841"])
        self.assertEqual(d["owasp_sc"], ["SC05"])
        self.assertEqual(d["dasp"], ["DASP-1"])

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {
            "swc": ["SWC-105"],
            "cwe": ["CWE-284"],
            "owasp_sc": ["SC01"],
            "dasp": ["DASP-2"],
        }
        mapping = TaxonomyMapping.from_dict(d)
        self.assertEqual(mapping.swc, ["SWC-105"])
        self.assertEqual(mapping.cwe, ["CWE-284"])
        self.assertEqual(mapping.owasp_sc, ["SC01"])
        self.assertEqual(mapping.dasp, ["DASP-2"])

    def test_round_trip(self):
        """Test serialization round trip."""
        original = TaxonomyMapping(
            swc=["SWC-112"],
            cwe=["CWE-829"],
            owasp_sc=["SC06"],
            dasp=["DASP-6"],
        )
        d = original.to_dict()
        restored = TaxonomyMapping.from_dict(d)
        self.assertEqual(original.swc, restored.swc)
        self.assertEqual(original.cwe, restored.cwe)
        self.assertEqual(original.owasp_sc, restored.owasp_sc)
        self.assertEqual(original.dasp, restored.dasp)


class TestTaxonomyRegistry(unittest.TestCase):
    """Tests for the taxonomy registry."""

    def test_registry_not_empty(self):
        """Test registry has entries."""
        self.assertGreater(len(TAXONOMY_REGISTRY), 50)

    def test_reentrancy_patterns_mapped(self):
        """Test reentrancy patterns are mapped."""
        patterns = ["reentrancy", "reentrancy-basic", "vm-001", "state-write-after-call"]
        for pattern in patterns:
            self.assertIn(pattern, TAXONOMY_REGISTRY, f"Missing: {pattern}")
            mapping = TAXONOMY_REGISTRY[pattern]
            self.assertIn("SWC-107", mapping.swc, f"SWC-107 missing for {pattern}")
            self.assertIn("SC05", mapping.owasp_sc, f"SC05 missing for {pattern}")

    def test_access_control_patterns_mapped(self):
        """Test access control patterns are mapped."""
        patterns = ["auth", "auth-001", "weak-access-control"]
        for pattern in patterns:
            self.assertIn(pattern, TAXONOMY_REGISTRY, f"Missing: {pattern}")
            mapping = TAXONOMY_REGISTRY[pattern]
            self.assertIn("SWC-105", mapping.swc, f"SWC-105 missing for {pattern}")
            self.assertIn("SC01", mapping.owasp_sc, f"SC01 missing for {pattern}")

    def test_delegatecall_patterns_mapped(self):
        """Test delegatecall patterns are mapped."""
        patterns = ["delegatecall", "delegatecall-public", "delegatecall-no-gate"]
        for pattern in patterns:
            self.assertIn(pattern, TAXONOMY_REGISTRY, f"Missing: {pattern}")
            mapping = TAXONOMY_REGISTRY[pattern]
            self.assertIn("SWC-112", mapping.swc, f"SWC-112 missing for {pattern}")

    def test_oracle_patterns_mapped(self):
        """Test oracle patterns are mapped."""
        patterns = ["oracle", "oracle-manipulation", "oracle-003-missing-staleness-check"]
        for pattern in patterns:
            self.assertIn(pattern, TAXONOMY_REGISTRY, f"Missing: {pattern}")
            mapping = TAXONOMY_REGISTRY[pattern]
            self.assertIn("SC02", mapping.owasp_sc, f"SC02 missing for {pattern}")

    def test_dos_patterns_mapped(self):
        """Test DoS patterns are mapped."""
        patterns = ["dos", "dos-unbounded-mass-operation", "dos-transfer-in-loop"]
        for pattern in patterns:
            self.assertIn(pattern, TAXONOMY_REGISTRY, f"Missing: {pattern}")
            mapping = TAXONOMY_REGISTRY[pattern]
            self.assertIn("SC10", mapping.owasp_sc, f"SC10 missing for {pattern}")

    def test_all_mappings_have_swc(self):
        """Test all mappings have at least one SWC code."""
        for pattern_id, mapping in TAXONOMY_REGISTRY.items():
            self.assertGreater(
                len(mapping.swc), 0,
                f"Pattern {pattern_id} missing SWC mapping"
            )

    def test_all_mappings_have_cwe(self):
        """Test all mappings have at least one CWE code."""
        for pattern_id, mapping in TAXONOMY_REGISTRY.items():
            self.assertGreater(
                len(mapping.cwe), 0,
                f"Pattern {pattern_id} missing CWE mapping"
            )

    def test_all_mappings_have_owasp(self):
        """Test all mappings have at least one OWASP code."""
        for pattern_id, mapping in TAXONOMY_REGISTRY.items():
            self.assertGreater(
                len(mapping.owasp_sc), 0,
                f"Pattern {pattern_id} missing OWASP mapping"
            )


class TestGetTaxonomy(unittest.TestCase):
    """Tests for get_taxonomy lookup function."""

    def test_exact_match(self):
        """Test exact pattern ID match."""
        mapping = get_taxonomy("reentrancy-basic")
        self.assertIn("SWC-107", mapping.swc)

    def test_prefix_fallback(self):
        """Test prefix-based fallback."""
        # "auth-999" should fall back to "auth" prefix
        mapping = get_taxonomy("auth-999")
        self.assertIn("SWC-105", mapping.swc)

    def test_keyword_fallback(self):
        """Test keyword-based fallback."""
        # Pattern containing "reentrancy" should match
        mapping = get_taxonomy("custom-reentrancy-pattern")
        self.assertIn("SWC-107", mapping.swc)

    def test_no_match_returns_empty(self):
        """Test unknown patterns return empty mapping."""
        mapping = get_taxonomy("completely-unknown-pattern-xyz")
        self.assertEqual(mapping.swc, [])
        self.assertEqual(mapping.cwe, [])

    def test_case_insensitive_keywords(self):
        """Test keyword matching is case insensitive."""
        mapping = get_taxonomy("REENTRANCY_CHECK")
        self.assertIn("SWC-107", mapping.swc)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience lookup functions."""

    def test_get_swc(self):
        """Test get_swc function."""
        swc = get_swc("reentrancy")
        self.assertEqual(swc, "SWC-107")

    def test_get_swc_unknown(self):
        """Test get_swc for unknown pattern."""
        swc = get_swc("unknown-pattern")
        self.assertEqual(swc, "")

    def test_get_cwe(self):
        """Test get_cwe function."""
        cwe = get_cwe("reentrancy")
        self.assertEqual(cwe, "CWE-841")

    def test_get_cwe_unknown(self):
        """Test get_cwe for unknown pattern."""
        cwe = get_cwe("unknown-pattern")
        self.assertEqual(cwe, "")

    def test_get_owasp_sc(self):
        """Test get_owasp_sc function."""
        codes = get_owasp_sc("reentrancy")
        self.assertIn("SC05", codes)

    def test_get_dasp(self):
        """Test get_dasp function."""
        codes = get_dasp("reentrancy")
        self.assertIn("DASP-1", codes)


class TestEnrichFinding(unittest.TestCase):
    """Tests for enrich_finding_with_taxonomy function."""

    def test_enrich_finding(self):
        """Test finding enrichment."""
        finding = {
            "id": "VKG-001",
            "pattern_id": "reentrancy-basic",
            "description": "Reentrancy vulnerability",
        }
        enriched = enrich_finding_with_taxonomy(finding)
        self.assertEqual(enriched["swc"], "SWC-107")
        self.assertEqual(enriched["cwe"], "CWE-841")
        self.assertIn("taxonomy", enriched)
        self.assertIn("swc", enriched["taxonomy"])

    def test_enrich_unknown_pattern(self):
        """Test finding enrichment with unknown pattern."""
        finding = {
            "id": "VKG-002",
            "pattern_id": "unknown-pattern",
            "description": "Unknown vulnerability",
        }
        enriched = enrich_finding_with_taxonomy(finding)
        self.assertEqual(enriched["swc"], "")
        self.assertEqual(enriched["cwe"], "")

    def test_enrich_preserves_fields(self):
        """Test enrichment preserves existing fields."""
        finding = {
            "id": "VKG-003",
            "pattern_id": "auth-001",
            "severity": "critical",
            "contract": "Vault.sol",
        }
        enriched = enrich_finding_with_taxonomy(finding)
        self.assertEqual(enriched["id"], "VKG-003")
        self.assertEqual(enriched["severity"], "critical")
        self.assertEqual(enriched["contract"], "Vault.sol")
        self.assertEqual(enriched["swc"], "SWC-105")


class TestReferenceData(unittest.TestCase):
    """Tests for reference data dictionaries."""

    def test_swc_reference_complete(self):
        """Test SWC reference has common codes."""
        common_codes = [
            "SWC-100", "SWC-101", "SWC-104", "SWC-105",
            "SWC-107", "SWC-112", "SWC-114", "SWC-128",
        ]
        for code in common_codes:
            self.assertIn(code, SWC_REFERENCE, f"Missing: {code}")

    def test_owasp_reference_complete(self):
        """Test OWASP reference has all 10 codes."""
        for i in range(1, 11):
            code = f"SC{i:02d}"
            self.assertIn(code, OWASP_SC_REFERENCE, f"Missing: {code}")

    def test_dasp_reference_complete(self):
        """Test DASP reference has all 10 codes."""
        for i in range(1, 11):
            code = f"DASP-{i}"
            self.assertIn(code, DASP_REFERENCE, f"Missing: {code}")


class TestSpecificPatternMappings(unittest.TestCase):
    """Tests for specific pattern mappings."""

    def test_tx_origin_mapping(self):
        """Test tx.origin patterns."""
        mapping = get_taxonomy("tx-origin-auth")
        self.assertIn("SWC-115", mapping.swc)
        self.assertIn("CWE-477", mapping.cwe)

    def test_proxy_mapping(self):
        """Test proxy patterns."""
        mapping = get_taxonomy("proxy-uninitialized-implementation")
        self.assertIn("SWC-109", mapping.swc)
        self.assertIn("CWE-665", mapping.cwe)

    def test_mev_mapping(self):
        """Test MEV patterns."""
        mapping = get_taxonomy("mev-risk-high")
        self.assertIn("SWC-114", mapping.swc)
        self.assertIn("SC07", mapping.owasp_sc)

    def test_crypto_mapping(self):
        """Test crypto patterns."""
        mapping = get_taxonomy("crypto-signature-malleability")
        self.assertIn("SWC-117", mapping.swc)
        self.assertIn("CWE-347", mapping.cwe)

    def test_multisig_mapping(self):
        """Test multisig patterns."""
        mapping = get_taxonomy("multisig-001-execution-without-nonce")
        self.assertIn("SWC-121", mapping.swc)
        self.assertIn("CWE-294", mapping.cwe)

    def test_token_mapping(self):
        """Test token patterns."""
        mapping = get_taxonomy("token-001-unhandled-fee-on-transfer")
        self.assertIn("CWE-682", mapping.cwe)
        self.assertIn("SC03", mapping.owasp_sc)

    def test_governance_mapping(self):
        """Test governance patterns."""
        mapping = get_taxonomy("governance-vote-without-snapshot")
        self.assertIn("SWC-114", mapping.swc)
        self.assertIn("SC07", mapping.owasp_sc)


if __name__ == "__main__":
    unittest.main()
