"""Tests for JSONL bead storage."""

import pytest
from pathlib import Path

from alphaswarm_sol.beads.jsonl_storage import BeadJSONLStorage, BeadEntry


class TestBeadJSONLStorage:
    """Tests for BeadJSONLStorage."""

    def test_create_bead_returns_id(self, tmp_path: Path):
        """Create bead returns valid ID."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        bead_id = storage.create(title="Test bead", severity="high")
        assert bead_id.startswith("bd-")
        assert len(bead_id) == 11  # bd- + 8 chars

    def test_bead_persists_across_reload(self, tmp_path: Path):
        """Bead persists after storage reload."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        bead_id = storage.create(title="Test bead")

        # Reload storage from disk
        storage2 = BeadJSONLStorage(tmp_path / ".beads")
        bead = storage2.get(bead_id)
        assert bead is not None
        assert bead.title == "Test bead"

    def test_update_bead_changes_status(self, tmp_path: Path):
        """Update bead changes status."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        bead_id = storage.create(title="Test bead")

        storage.update(bead_id, status="in_progress")
        bead = storage.get(bead_id)
        assert bead.status == "in_progress"

    def test_list_filters_by_status(self, tmp_path: Path):
        """List beads filters by status."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        storage.create(title="Open bead")
        id2 = storage.create(title="Complete bead")
        storage.update(id2, status="complete")

        open_beads = storage.list(status="open")
        assert len(open_beads) == 1
        assert open_beads[0].title == "Open bead"

    def test_get_ready_excludes_blocked(self, tmp_path: Path):
        """get_ready excludes blocked beads."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        id1 = storage.create(title="Blocker")
        id2 = storage.create(title="Blocked")
        storage.update(id2, blocked_by=id1)

        ready = storage.get_ready()
        assert len(ready) == 1
        assert ready[0].id == id1

    def test_get_ready_includes_unblocked(self, tmp_path: Path):
        """get_ready includes beads when blocker is complete."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        id1 = storage.create(title="Blocker")
        id2 = storage.create(title="Blocked")
        storage.update(id2, blocked_by=id1)
        storage.update(id1, status="complete")

        ready = storage.get_ready()
        assert len(ready) == 1
        assert ready[0].id == id2

    def test_update_nonexistent_raises(self, tmp_path: Path):
        """Update nonexistent bead raises ValueError."""
        storage = BeadJSONLStorage(tmp_path / ".beads")
        with pytest.raises(ValueError, match="not found"):
            storage.update("bd-notreal", status="complete")
