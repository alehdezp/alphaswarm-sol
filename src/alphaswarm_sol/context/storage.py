"""Persistent storage for protocol context packs.

File-based storage for ProtocolContextPack objects using YAML format
for human readability (per 03-CONTEXT.md decision).

Storage structure:
    {base_path}/
        {protocol_name}/
            context.yaml       # Full context pack
            sections/          # Section-level cache for targeted retrieval
                roles.yaml
                assumptions.yaml
                invariants.yaml
                ...

Usage:
    from pathlib import Path
    from alphaswarm_sol.context.storage import ContextPackStorage
    from alphaswarm_sol.context.schema import ProtocolContextPack

    storage = ContextPackStorage(Path(".vrs/context"))

    # Save a pack
    pack = ProtocolContextPack(protocol_name="Aave", protocol_type="lending")
    storage.save(pack)

    # Load a pack
    loaded = storage.load("Aave")

    # Load specific section (for minimal context)
    roles = storage.load_section("Aave", "roles")

    # Update specific section
    storage.update_section("Aave", "assumptions", new_assumptions_data)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .schema import ProtocolContextPack


class ContextPackStorage:
    """File-based storage for protocol context packs.

    Stores context packs as YAML files for human readability (per 03-CONTEXT.md).
    Supports section-level retrieval for minimal context loading.

    Attributes:
        path: Base directory for storing context packs

    Example:
        storage = ContextPackStorage(Path(".vrs/context"))
        storage.save(pack, "my_protocol")
        loaded = storage.load("my_protocol")
    """

    def __init__(self, path: Path):
        """Initialize storage.

        Args:
            path: Directory path for storing context packs.
                  Will be created if it doesn't exist.
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _get_protocol_path(self, name: str) -> Path:
        """Get path for a protocol's context pack directory.

        Args:
            name: Protocol name

        Returns:
            Path to protocol directory
        """
        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self.path / safe_name

    def _get_context_file(self, name: str) -> Path:
        """Get path to main context.yaml file.

        Args:
            name: Protocol name

        Returns:
            Path to context.yaml
        """
        return self._get_protocol_path(name) / "context.yaml"

    def _get_sections_dir(self, name: str) -> Path:
        """Get path to sections directory.

        Args:
            name: Protocol name

        Returns:
            Path to sections directory
        """
        return self._get_protocol_path(name) / "sections"

    def save(self, pack: ProtocolContextPack, name: Optional[str] = None) -> Path:
        """Save context pack as YAML.

        Saves both the full context pack and individual sections
        for targeted retrieval.

        Args:
            pack: ProtocolContextPack to save
            name: Optional name override (defaults to pack.protocol_name)

        Returns:
            Path to saved context.yaml file
        """
        name = name or pack.protocol_name
        if not name:
            raise ValueError("Protocol name required (either in pack or as argument)")

        # Create protocol directory
        protocol_path = self._get_protocol_path(name)
        protocol_path.mkdir(parents=True, exist_ok=True)

        # Save full context
        context_file = self._get_context_file(name)
        data = pack.to_dict()

        with open(context_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Save individual sections for targeted retrieval
        self._save_sections(name, pack)

        return context_file

    def _save_sections(self, name: str, pack: ProtocolContextPack) -> None:
        """Save individual sections for targeted retrieval.

        Args:
            name: Protocol name
            pack: ProtocolContextPack to save sections from
        """
        sections_dir = self._get_sections_dir(name)
        sections_dir.mkdir(parents=True, exist_ok=True)

        # Section names that can be retrieved independently
        section_names = [
            "metadata",
            "roles",
            "economics",
            "assumptions",
            "invariants",
            "offchain_inputs",
            "security",
            "accepted_risks",
            "governance",
            "sources",
            "deployment",
            "notes",
        ]

        for section_name in section_names:
            section_data = pack.get_section(section_name)
            if section_data:
                section_file = sections_dir / f"{section_name}.yaml"
                with open(section_file, "w", encoding="utf-8") as f:
                    yaml.dump(
                        section_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
                    )

    def load(self, name: str) -> Optional[ProtocolContextPack]:
        """Load context pack from YAML.

        Args:
            name: Protocol name to load

        Returns:
            ProtocolContextPack if found, None otherwise
        """
        context_file = self._get_context_file(name)
        if not context_file.exists():
            return None

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            return ProtocolContextPack.from_dict(data)

        except (yaml.YAMLError, KeyError) as e:
            print(f"Warning: Error loading context pack {name}: {e}", file=sys.stderr)
            return None

    def load_section(self, name: str, section: str) -> Optional[Dict[str, Any]]:
        """Load specific section for targeted retrieval.

        Per 03-CONTEXT.md: designed for minimal context loading.

        Args:
            name: Protocol name
            section: Section name (metadata, roles, assumptions, etc.)

        Returns:
            Dict with section data, or None if not found
        """
        section_file = self._get_sections_dir(name) / f"{section}.yaml"

        if not section_file.exists():
            # Fall back to loading from full context
            pack = self.load(name)
            if pack:
                return pack.get_section(section)
            return None

        try:
            with open(section_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data

        except yaml.YAMLError as e:
            print(f"Warning: Error loading section {section} for {name}: {e}", file=sys.stderr)
            return None

    def exists(self, name: str) -> bool:
        """Check if context pack exists.

        Args:
            name: Protocol name

        Returns:
            True if context pack exists
        """
        return self._get_context_file(name).exists()

    def list_packs(self) -> List[str]:
        """List all stored context packs.

        Returns:
            List of protocol names
        """
        packs = []
        for path in sorted(self.path.iterdir()):
            if path.is_dir() and (path / "context.yaml").exists():
                packs.append(path.name)
        return packs

    def delete(self, name: str) -> bool:
        """Delete a context pack.

        Args:
            name: Protocol name to delete

        Returns:
            True if deleted, False if not found
        """
        protocol_path = self._get_protocol_path(name)
        if not protocol_path.exists():
            return False

        import shutil

        shutil.rmtree(protocol_path)
        return True

    def update_section(self, name: str, section: str, data: Dict[str, Any]) -> bool:
        """Update a specific section.

        Per 03-CONTEXT.md: bidirectional sync support.

        Args:
            name: Protocol name
            section: Section name to update
            data: New section data

        Returns:
            True if updated successfully, False if pack not found
        """
        # Load existing pack
        pack = self.load(name)
        if not pack:
            return False

        # Update the section in the pack
        pack_dict = pack.to_dict()

        # Map section names to pack fields
        section_to_fields = {
            "metadata": ["version", "schema_version", "protocol_name", "protocol_type", "generated_at", "auto_generated", "reviewed"],
            "roles": ["roles"],
            "economics": ["value_flows", "incentives", "tokenomics_summary"],
            "assumptions": ["assumptions"],
            "invariants": ["invariants"],
            "offchain_inputs": ["offchain_inputs"],
            "security": ["security_model", "critical_functions"],
            "accepted_risks": ["accepted_risks"],
            "governance": ["governance"],
            "sources": ["sources"],
            "deployment": ["deployment"],
            "notes": ["notes"],
        }

        fields = section_to_fields.get(section, [])
        for field in fields:
            if field in data:
                pack_dict[field] = data[field]

        # Reconstruct and save
        updated_pack = ProtocolContextPack.from_dict(pack_dict)
        self.save(updated_pack, name)

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all stored context packs.

        Returns:
            Dict with counts and pack names
        """
        packs = self.list_packs()
        summaries = []

        for pack_name in packs:
            pack = self.load(pack_name)
            if pack:
                summaries.append(
                    {
                        "name": pack_name,
                        "protocol_type": pack.protocol_type,
                        "roles": len(pack.roles),
                        "assumptions": len(pack.assumptions),
                        "invariants": len(pack.invariants),
                        "reviewed": pack.reviewed,
                    }
                )

        return {
            "total": len(packs),
            "packs": summaries,
        }

    def clear(self) -> int:
        """Clear all context packs from storage.

        Returns:
            Count of packs deleted
        """
        count = 0
        for pack_name in self.list_packs():
            if self.delete(pack_name):
                count += 1
        return count


# Export for module
__all__ = ["ContextPackStorage"]
