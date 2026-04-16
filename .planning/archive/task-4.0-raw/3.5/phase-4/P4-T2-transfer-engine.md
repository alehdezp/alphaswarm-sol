# [P4-T2] Vulnerability Transfer Engine

**Phase**: 4 - Cross-Project Transfer
**Task ID**: P4-T2
**Status**: NOT_STARTED
**Priority**: MEDIUM
**Estimated Effort**: 3-4 days
**Actual Effort**: -

---

## Executive Summary

Transfer vulnerability knowledge from similar audited projects to new projects. If a similar project had vulnerability X, check if the new project has the same vulnerability.

**Research Basis**: CVE-Genie achieves 51% vulnerability reproduction rate through cross-project transfer.

---

## Dependencies

### Required Before Starting
- [ ] [P4-T1] Project Profiler
- [ ] [P0-T2] Adversarial Knowledge Graph

### Blocks These Tasks
- Phase 4 completion

---

## Objectives

1. Find similar projects in database
2. Transfer vulnerability patterns from similar projects
3. Validate transferred patterns apply
4. Report with similarity confidence

---

## Technical Design

```python
@dataclass
class TransferredFinding:
    """A finding transferred from a similar project."""
    source_project: str
    source_vulnerability: str
    target_function: str
    similarity: float
    validation_status: str  # "confirmed", "likely", "rejected"
    explanation: str


class VulnerabilityTransferEngine:
    """Transfers vulnerability knowledge across projects."""

    def __init__(self, project_db: Dict[str, ProjectProfile], adversarial_kg):
        self.project_db = project_db
        self.adversarial_kg = adversarial_kg

    def transfer(
        self,
        target_profile: ProjectProfile,
        target_kg: "KnowledgeGraph",
        k: int = 5,
    ) -> List[TransferredFinding]:
        """Find and transfer vulnerabilities from similar projects."""

        # Find similar projects
        similar = self._find_similar(target_profile, k)

        transferred = []
        for proj, similarity in similar:
            # Get known vulns from similar project
            for vuln_id in proj.known_vulns:
                pattern = self.adversarial_kg.patterns.get(vuln_id)
                if not pattern:
                    continue

                # Check if pattern applies to target
                matches = self._find_pattern_matches(target_kg, pattern)
                for match in matches:
                    transferred.append(TransferredFinding(
                        source_project=proj.project_id,
                        source_vulnerability=vuln_id,
                        target_function=match.function_id,
                        similarity=similarity * match.confidence,
                        validation_status=self._validate(match),
                        explanation=f"Similar to {vuln_id} from {proj.name}",
                    ))

        return transferred

    def _find_similar(
        self,
        target: ProjectProfile,
        k: int,
    ) -> List[tuple[ProjectProfile, float]]:
        """Find k most similar projects."""
        similarities = []

        for proj in self.project_db.values():
            sim = self._compute_similarity(target, proj)
            similarities.append((proj, sim))

        return sorted(similarities, key=lambda x: -x[1])[:k]

    def _compute_similarity(self, a: ProjectProfile, b: ProjectProfile) -> float:
        """Compute similarity between two projects."""
        score = 0.0

        # Same protocol type
        if a.protocol_type == b.protocol_type:
            score += 0.4

        # Shared primitives
        shared = set(a.primitives_used) & set(b.primitives_used)
        if a.primitives_used:
            score += 0.3 * len(shared) / len(a.primitives_used)

        # Similar architecture
        if a.is_upgradeable == b.is_upgradeable:
            score += 0.15
        if a.uses_oracles == b.uses_oracles:
            score += 0.15

        return score
```

---

## Success Criteria

- [ ] Similar project finding working
- [ ] Pattern transfer working
- [ ] Validation of transferred patterns
- [ ] Accuracy on known vulnerable projects

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
