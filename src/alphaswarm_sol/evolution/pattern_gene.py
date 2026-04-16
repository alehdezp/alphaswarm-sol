"""
Pattern Gene - Mutable component of a pattern for genetic evolution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random
import copy


@dataclass
class PatternGene:
    """A mutable component of a pattern."""

    property: str           # Property name (e.g., "visibility", "has_access_gate")
    operator: str           # Comparison operator (e.g., "==", "in", ">=")
    value: Any              # Value to compare against
    weight: float = 1.0     # Mutation probability weight
    is_required: bool = True  # If False, can be removed by mutation

    def copy(self) -> "PatternGene":
        """Create a deep copy of this gene."""
        return PatternGene(
            property=self.property,
            operator=self.operator,
            value=copy.deepcopy(self.value),
            weight=self.weight,
            is_required=self.is_required,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to pattern condition dict."""
        return {
            "property": self.property,
            "op": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PatternGene":
        """Create from pattern condition dict."""
        return cls(
            property=d.get("property", ""),
            operator=d.get("op", "=="),
            value=d.get("value"),
            is_required=d.get("required", True),
        )


@dataclass
class EvolvablePattern:
    """Pattern that can mutate and crossover for genetic evolution."""

    pattern_id: str
    name: str
    severity: str = "medium"
    genes: List[PatternGene] = field(default_factory=list)
    none_genes: List[PatternGene] = field(default_factory=list)  # Exclusion conditions

    # Evolution tracking
    generation: int = 0
    fitness: float = 0.0
    parent_ids: List[str] = field(default_factory=list)

    # Performance metrics
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    def copy(self) -> "EvolvablePattern":
        """Create a deep copy of this pattern."""
        return EvolvablePattern(
            pattern_id=self.pattern_id,
            name=self.name,
            severity=self.severity,
            genes=[g.copy() for g in self.genes],
            none_genes=[g.copy() for g in self.none_genes],
            generation=self.generation,
            fitness=self.fitness,
            parent_ids=self.parent_ids.copy(),
        )

    def mutate(self, mutation_rate: float = 0.1) -> "EvolvablePattern":
        """Create a mutated copy of this pattern."""
        mutant = self.copy()
        mutant.pattern_id = f"{self.pattern_id}_m{random.randint(1000, 9999)}"
        mutant.generation = self.generation + 1
        mutant.parent_ids = [self.pattern_id]
        mutant.fitness = 0.0  # Reset fitness

        # Mutate genes
        for gene in mutant.genes:
            if random.random() < mutation_rate * gene.weight:
                mutant._mutate_gene(gene)

        # Mutate none_genes
        for gene in mutant.none_genes:
            if random.random() < mutation_rate * gene.weight:
                mutant._mutate_gene(gene)

        # Possibly add or remove genes
        if random.random() < mutation_rate / 2:
            mutant._structural_mutation()

        return mutant

    def _mutate_gene(self, gene: PatternGene) -> None:
        """Mutate a single gene in place."""
        mutation_type = random.choice(["operator", "value", "threshold"])

        if mutation_type == "operator":
            # Flip operator
            operator_pairs = {
                "==": "!=",
                "!=": "==",
                ">=": "<",
                "<": ">=",
                "<=": ">",
                ">": "<=",
                "in": "not_in",
                "not_in": "in",
            }
            if gene.operator in operator_pairs:
                gene.operator = operator_pairs[gene.operator]

        elif mutation_type == "value":
            # Modify value
            if isinstance(gene.value, bool):
                gene.value = not gene.value
            elif isinstance(gene.value, (int, float)):
                gene.value = gene.value * random.uniform(0.5, 2.0)
            elif isinstance(gene.value, list):
                # Add or remove list element
                if gene.value and random.random() < 0.5:
                    gene.value.pop(random.randrange(len(gene.value)))

        elif mutation_type == "threshold":
            # Adjust weight
            gene.weight *= random.uniform(0.8, 1.2)
            gene.weight = max(0.1, min(2.0, gene.weight))

    def _structural_mutation(self) -> None:
        """Add or remove a gene."""
        if random.random() < 0.5 and len(self.genes) > 1:
            # Remove a non-required gene
            removable = [g for g in self.genes if not g.is_required]
            if removable:
                self.genes.remove(random.choice(removable))
        else:
            # Move a gene from genes to none_genes or vice versa
            if self.genes and random.random() < 0.3:
                gene = random.choice(self.genes)
                if not gene.is_required:
                    self.genes.remove(gene)
                    self.none_genes.append(gene)

    def crossover(self, other: "EvolvablePattern") -> "EvolvablePattern":
        """Create offspring by combining genes from two parents."""
        child = EvolvablePattern(
            pattern_id=f"{self.pattern_id}_x_{other.pattern_id[:8]}",
            name=f"{self.name} (hybrid)",
            severity=random.choice([self.severity, other.severity]),
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[self.pattern_id, other.pattern_id],
        )

        # Combine genes - take from each parent
        all_genes = {}
        for gene in self.genes + other.genes:
            if gene.property not in all_genes:
                all_genes[gene.property] = gene.copy()
            elif random.random() < 0.5:
                all_genes[gene.property] = gene.copy()

        child.genes = list(all_genes.values())

        # Combine none_genes
        all_none_genes = {}
        for gene in self.none_genes + other.none_genes:
            if gene.property not in all_none_genes:
                all_none_genes[gene.property] = gene.copy()
            elif random.random() < 0.5:
                all_none_genes[gene.property] = gene.copy()

        child.none_genes = list(all_none_genes.values())

        return child

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate precision, recall, F1 from confusion matrix."""
        tp = self.true_positives
        fp = self.false_positives
        fn = self.false_negatives
        tn = self.true_negatives

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": accuracy,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
        }

    def to_yaml(self) -> Dict[str, Any]:
        """Convert to YAML pattern format."""
        conditions = [gene.to_dict() for gene in self.genes]
        none_conditions = [gene.to_dict() for gene in self.none_genes]

        match = {"tier_a": {"all": conditions}}
        if none_conditions:
            match["tier_a"]["none"] = none_conditions

        return {
            "id": self.pattern_id,
            "name": self.name,
            "severity": self.severity,
            "match": match,
            "metadata": {
                "generation": self.generation,
                "fitness": self.fitness,
                "parent_ids": self.parent_ids,
                "metrics": self.calculate_metrics(),
            },
        }

    @classmethod
    def from_yaml(cls, yaml_dict: Dict[str, Any]) -> "EvolvablePattern":
        """Create from YAML pattern dict."""
        pattern = cls(
            pattern_id=yaml_dict.get("id", "unknown"),
            name=yaml_dict.get("name", "Unknown Pattern"),
            severity=yaml_dict.get("severity", "medium"),
        )

        match = yaml_dict.get("match", {})
        tier_a = match.get("tier_a", {})

        # Parse all conditions
        for cond in tier_a.get("all", []):
            if "property" in cond:
                pattern.genes.append(PatternGene.from_dict(cond))

        # Parse none conditions
        for cond in tier_a.get("none", []):
            if "property" in cond:
                pattern.none_genes.append(PatternGene.from_dict(cond))

        # Parse metadata if present
        metadata = yaml_dict.get("metadata", {})
        pattern.generation = metadata.get("generation", 0)
        pattern.fitness = metadata.get("fitness", 0.0)
        pattern.parent_ids = metadata.get("parent_ids", [])

        return pattern

    def __str__(self) -> str:
        return f"EvolvablePattern({self.pattern_id}, gen={self.generation}, fitness={self.fitness:.3f})"

    def __repr__(self) -> str:
        return self.__str__()
