"""Phase 19: Performance Optimization Tests.

Tests for profiling, caching, incremental builds, and parallel processing.
"""

import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

from alphaswarm_sol.performance.profiler import (
    BuildPhase,
    TimingEntry,
    ProfileResult,
    BuildProfiler,
    timed,
    profile_build,
)
from alphaswarm_sol.performance.cache import (
    CacheEntry,
    CacheStore,
    GraphCache,
    cache_result,
)
from alphaswarm_sol.performance.incremental import (
    FileState,
    ChangeSet,
    ChangeDetector,
    IncrementalBuildResult,
    IncrementalBuilder,
    detect_changes,
)
from alphaswarm_sol.performance.parallel import (
    BatchResult,
    ParallelProcessor,
    BatchProcessor,
    parallel_detect,
    AsyncBatchCollector,
)


class TestBuildPhase(unittest.TestCase):
    """Tests for BuildPhase enum."""

    def test_phases_defined(self):
        """All build phases are defined."""
        self.assertEqual(BuildPhase.SLITHER_PARSE.value, "slither_parse")
        self.assertEqual(BuildPhase.NODE_CREATION.value, "node_creation")
        self.assertEqual(BuildPhase.PROPERTY_DETECTION.value, "property_detection")


class TestTimingEntry(unittest.TestCase):
    """Tests for TimingEntry dataclass."""

    def test_entry_creation(self):
        """TimingEntry can be created with all fields."""
        entry = TimingEntry(
            name="test_op",
            phase=BuildPhase.NODE_CREATION,
            start_time=1000.0,
            end_time=1050.0,
            duration_ms=50.0,
            count=10,
            metadata={"key": "value"},
        )

        self.assertEqual(entry.name, "test_op")
        self.assertEqual(entry.phase, BuildPhase.NODE_CREATION)
        self.assertEqual(entry.duration_ms, 50.0)

    def test_to_dict(self):
        """TimingEntry serializes correctly."""
        entry = TimingEntry(
            name="test",
            phase=BuildPhase.SEMANTIC_OPS,
            duration_ms=25.5,
        )

        d = entry.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["phase"], "semantic_ops")
        self.assertEqual(d["duration_ms"], 25.5)


class TestProfileResult(unittest.TestCase):
    """Tests for ProfileResult dataclass."""

    def test_result_creation(self):
        """ProfileResult can be created."""
        result = ProfileResult(
            total_time_ms=100.0,
            phase_times={"node_creation": 50.0, "edge_creation": 30.0},
            bottlenecks=["slow phase"],
            recommendations=["optimize it"],
        )

        self.assertEqual(result.total_time_ms, 100.0)
        self.assertEqual(result.slowest_phase, "node_creation")

    def test_to_dict(self):
        """ProfileResult serializes correctly."""
        result = ProfileResult(
            total_time_ms=100.0,
            phase_times={"test": 50.0},
        )

        d = result.to_dict()
        self.assertEqual(d["total_time_ms"], 100.0)

    def test_to_report(self):
        """ProfileResult generates report."""
        result = ProfileResult(
            total_time_ms=100.0,
            phase_times={"test": 50.0},
            bottlenecks=["slow phase"],
            recommendations=["optimize"],
        )

        report = result.to_report()
        self.assertIn("Build Profile Report", report)
        self.assertIn("Total Time", report)
        self.assertIn("Bottlenecks", report)


class TestBuildProfiler(unittest.TestCase):
    """Tests for BuildProfiler class."""

    def test_profile_build(self):
        """Profiler tracks build timing."""
        profiler = BuildProfiler()
        profiler.start_build()

        profiler.start_phase("test_op", BuildPhase.NODE_CREATION, count=5)
        time.sleep(0.01)  # 10ms
        profiler.end_phase("test_op")

        result = profiler.get_result()
        self.assertGreater(result.total_time_ms, 0)
        self.assertIn("node_creation", result.phase_times)

    def test_record_timing(self):
        """Profiler records timing directly."""
        profiler = BuildProfiler()
        profiler.start_build()

        profiler.record(
            name="direct_op",
            phase=BuildPhase.SEMANTIC_OPS,
            duration_ms=25.0,
            count=10,
        )

        result = profiler.get_result()
        self.assertEqual(len(result.timings), 1)
        self.assertEqual(result.timings[0].duration_ms, 25.0)

    def test_identifies_bottlenecks(self):
        """Profiler identifies bottlenecks."""
        profiler = BuildProfiler()
        profiler.start_build()

        # Record a slow operation
        profiler.record(
            name="slow_op",
            phase=BuildPhase.PROPERTY_DETECTION,
            duration_ms=1000.0,  # 1 second
        )

        result = profiler.get_result()
        self.assertGreater(len(result.bottlenecks), 0)

    def test_generates_recommendations(self):
        """Profiler generates recommendations."""
        profiler = BuildProfiler()
        profiler.start_build()

        profiler.record(
            name="slow_slither",
            phase=BuildPhase.SLITHER_PARSE,
            duration_ms=10000.0,  # 10 seconds
        )

        result = profiler.get_result()
        self.assertGreater(len(result.recommendations), 0)


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self):
        """CacheEntry can be created."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "value"},
            size_bytes=100,
        )

        self.assertEqual(entry.key, "test_key")
        self.assertFalse(entry.is_expired)

    def test_expiry(self):
        """CacheEntry expires correctly."""
        entry = CacheEntry(
            key="test",
            value="data",
            expires_at=time.time() - 1,  # Already expired
        )

        self.assertTrue(entry.is_expired)


class TestCacheStore(unittest.TestCase):
    """Tests for CacheStore class."""

    def test_set_and_get(self):
        """CacheStore stores and retrieves values."""
        cache: CacheStore[str] = CacheStore(max_entries=10)

        cache.set("key1", "value1")
        result = cache.get("key1")

        self.assertEqual(result, "value1")

    def test_miss(self):
        """CacheStore returns None for missing keys."""
        cache: CacheStore[str] = CacheStore()

        result = cache.get("missing")
        self.assertIsNone(result)

    def test_eviction_by_count(self):
        """CacheStore evicts when max_entries exceeded."""
        cache: CacheStore[int] = CacheStore(max_entries=2)

        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)

        # key1 should be evicted (LRU)
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), 2)
        self.assertEqual(cache.get("key3"), 3)

    def test_ttl_expiry(self):
        """CacheStore respects TTL."""
        cache: CacheStore[str] = CacheStore()

        cache.set("key1", "value1", ttl_seconds=0.01)  # 10ms
        time.sleep(0.02)  # Wait for expiry

        result = cache.get("key1")
        self.assertIsNone(result)

    def test_hit_rate(self):
        """CacheStore tracks hit rate."""
        cache: CacheStore[str] = CacheStore()

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        self.assertEqual(cache.hit_rate, 2/3)

    def test_delete(self):
        """CacheStore deletes entries."""
        cache: CacheStore[str] = CacheStore()

        cache.set("key1", "value1")
        deleted = cache.delete("key1")

        self.assertTrue(deleted)
        self.assertIsNone(cache.get("key1"))

    def test_clear(self):
        """CacheStore clears all entries."""
        cache: CacheStore[str] = CacheStore()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        self.assertEqual(cache.size, 0)


class TestGraphCache(unittest.TestCase):
    """Tests for GraphCache class."""

    def test_get_contract_hash(self):
        """GraphCache generates consistent hashes."""
        cache = GraphCache()

        hash1 = cache.get_contract_hash("contract code")
        hash2 = cache.get_contract_hash("contract code")
        hash3 = cache.get_contract_hash("different code")

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

    def test_set_and_get_graph(self):
        """GraphCache stores and retrieves graphs."""
        cache = GraphCache()

        graph_data = {"nodes": [], "edges": []}
        cache.set_graph("hash123", graph_data)

        result = cache.get_graph("hash123")
        self.assertEqual(result, graph_data)

    def test_invalidate(self):
        """GraphCache invalidates entries."""
        cache = GraphCache()

        cache.set_graph("hash123", {"data": "value"})
        cache.invalidate("hash123")

        result = cache.get_graph("hash123")
        self.assertIsNone(result)


class TestChangeDetector(unittest.TestCase):
    """Tests for ChangeDetector class."""

    def test_detect_added_files(self):
        """ChangeDetector detects added files."""
        detector = ChangeDetector()

        # Empty baseline
        detector.set_baseline({})

        # Current has one file
        current = {
            "/path/file.sol": FileState(
                path="/path/file.sol",
                hash="abc123",
                mtime=1000.0,
                size=100,
            )
        }

        changeset = detector.detect_changes(current)

        self.assertEqual(len(changeset.added), 1)
        self.assertEqual(len(changeset.modified), 0)
        self.assertEqual(len(changeset.deleted), 0)

    def test_detect_modified_files(self):
        """ChangeDetector detects modified files."""
        detector = ChangeDetector()

        baseline = {
            "/path/file.sol": FileState(
                path="/path/file.sol",
                hash="abc123",
                mtime=1000.0,
                size=100,
            )
        }
        detector.set_baseline(baseline)

        current = {
            "/path/file.sol": FileState(
                path="/path/file.sol",
                hash="def456",  # Different hash
                mtime=2000.0,
                size=150,
            )
        }

        changeset = detector.detect_changes(current)

        self.assertEqual(len(changeset.modified), 1)
        self.assertEqual(len(changeset.added), 0)
        self.assertEqual(len(changeset.unchanged), 0)

    def test_detect_deleted_files(self):
        """ChangeDetector detects deleted files."""
        detector = ChangeDetector()

        baseline = {
            "/path/file.sol": FileState(
                path="/path/file.sol",
                hash="abc123",
                mtime=1000.0,
                size=100,
            )
        }
        detector.set_baseline(baseline)

        current = {}  # File deleted

        changeset = detector.detect_changes(current)

        self.assertEqual(len(changeset.deleted), 1)

    def test_detect_unchanged_files(self):
        """ChangeDetector detects unchanged files."""
        detector = ChangeDetector()

        file_state = FileState(
            path="/path/file.sol",
            hash="abc123",
            mtime=1000.0,
            size=100,
        )
        baseline = {"/path/file.sol": file_state}
        detector.set_baseline(baseline)

        changeset = detector.detect_changes(baseline)

        self.assertEqual(len(changeset.unchanged), 1)
        self.assertFalse(changeset.has_changes)


class TestChangeSet(unittest.TestCase):
    """Tests for ChangeSet dataclass."""

    def test_has_changes(self):
        """ChangeSet.has_changes works correctly."""
        changeset = ChangeSet()
        self.assertFalse(changeset.has_changes)

        changeset.added.append("file.sol")
        self.assertTrue(changeset.has_changes)

    def test_changed_files(self):
        """ChangeSet.changed_files combines added and modified."""
        changeset = ChangeSet(
            added=["new.sol"],
            modified=["changed.sol"],
            unchanged=["same.sol"],
        )

        self.assertEqual(len(changeset.changed_files), 2)
        self.assertIn("new.sol", changeset.changed_files)
        self.assertIn("changed.sol", changeset.changed_files)


class TestIncrementalBuilder(unittest.TestCase):
    """Tests for IncrementalBuilder class."""

    def test_plan_build_no_baseline(self):
        """IncrementalBuilder does full rebuild without baseline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.sol"
            test_file.write_text("contract Test {}")

            builder = IncrementalBuilder()
            changeset, result = builder.plan_build(Path(tmpdir))

            self.assertTrue(result.full_rebuild)
            self.assertEqual(len(result.files_processed), 1)

    def test_should_rebuild_file(self):
        """IncrementalBuilder correctly determines rebuild need."""
        builder = IncrementalBuilder()

        changeset = ChangeSet(
            added=["new.sol"],
            modified=["changed.sol"],
            unchanged=["same.sol"],
        )

        self.assertTrue(builder.should_rebuild_file("new.sol", changeset))
        self.assertTrue(builder.should_rebuild_file("changed.sol", changeset))
        self.assertFalse(builder.should_rebuild_file("same.sol", changeset))


class TestBatchResult(unittest.TestCase):
    """Tests for BatchResult dataclass."""

    def test_result_creation(self):
        """BatchResult can be created."""
        result: BatchResult[int] = BatchResult(
            results=[1, 2, 3],
            errors=[(4, "error")],
            total_time_ms=100.0,
        )

        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.success_rate, 0.75)


class TestParallelProcessor(unittest.TestCase):
    """Tests for ParallelProcessor class."""

    def test_map(self):
        """ParallelProcessor.map processes items."""
        processor: ParallelProcessor[int, int] = ParallelProcessor()

        def double(x: int) -> int:
            return x * 2

        result = processor.map(double, [1, 2, 3, 4, 5])

        self.assertEqual(result.success_count, 5)
        self.assertEqual(sorted(result.results), [2, 4, 6, 8, 10])

    def test_handles_errors(self):
        """ParallelProcessor handles errors gracefully."""
        processor: ParallelProcessor[int, int] = ParallelProcessor()

        def maybe_fail(x: int) -> int:
            if x == 3:
                raise ValueError("test error")
            return x * 2

        result = processor.map(maybe_fail, [1, 2, 3, 4])

        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.error_count, 1)

    def test_empty_input(self):
        """ParallelProcessor handles empty input."""
        processor: ParallelProcessor[int, int] = ParallelProcessor()

        result = processor.map(lambda x: x, [])

        self.assertEqual(result.success_count, 0)


class TestBatchProcessor(unittest.TestCase):
    """Tests for BatchProcessor class."""

    def test_process_batches(self):
        """BatchProcessor processes items in batches."""
        processor: BatchProcessor[int, int] = BatchProcessor(batch_size=3)

        result = processor.process(lambda x: x * 2, [1, 2, 3, 4, 5, 6, 7])

        self.assertEqual(result.success_count, 7)
        self.assertEqual(sorted(result.results), [2, 4, 6, 8, 10, 12, 14])


class TestParallelDetect(unittest.TestCase):
    """Tests for parallel_detect function."""

    def test_parallel_detect(self):
        """parallel_detect processes items."""
        items = [1, 2, 3, 4, 5]

        results = parallel_detect(lambda x: x * 2, items)

        self.assertEqual(sorted(results), [2, 4, 6, 8, 10])


class TestAsyncBatchCollector(unittest.TestCase):
    """Tests for AsyncBatchCollector class."""

    def test_collects_batches(self):
        """AsyncBatchCollector collects items into batches."""
        processed_batches: List[List[int]] = []

        collector: AsyncBatchCollector[int] = AsyncBatchCollector(
            batch_size=3,
            process_fn=lambda batch: processed_batches.append(batch),
        )

        for i in range(7):
            collector.add(i)

        collector.finish()

        # Should have processed 3 batches: [0,1,2], [3,4,5], [6]
        self.assertEqual(len(processed_batches), 3)
        self.assertEqual(processed_batches[0], [0, 1, 2])
        self.assertEqual(processed_batches[1], [3, 4, 5])
        self.assertEqual(processed_batches[2], [6])

    def test_pending_count(self):
        """AsyncBatchCollector tracks pending items."""
        collector: AsyncBatchCollector[int] = AsyncBatchCollector(batch_size=5)

        collector.add(1)
        collector.add(2)

        self.assertEqual(collector.pending_count, 2)


class TestCacheResultDecorator(unittest.TestCase):
    """Tests for cache_result decorator."""

    def test_caches_results(self):
        """cache_result decorator caches function results."""
        cache: CacheStore[int] = CacheStore()
        call_count = 0

        @cache_result(cache)
        def expensive_fn(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - computes
        result1 = expensive_fn(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)

        # Second call - cached
        result2 = expensive_fn(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1)  # Not called again


if __name__ == "__main__":
    unittest.main()
