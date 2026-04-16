"""Phase 19: Parallel Processing Support.

This module provides parallel processing functionality for
the VKG build pipeline.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult(Generic[T]):
    """Result of a batch operation.

    Attributes:
        results: List of results
        errors: List of (index, error) tuples
        total_time_ms: Total processing time
        items_per_second: Processing rate
    """
    results: List[T] = field(default_factory=list)
    errors: List[tuple[int, str]] = field(default_factory=list)
    total_time_ms: float = 0.0
    items_per_second: float = 0.0

    @property
    def success_count(self) -> int:
        return len(self.results)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        if total == 0:
            return 1.0
        return self.success_count / total


class ParallelProcessor(Generic[T, R]):
    """Processes items in parallel using thread pool.

    Provides safe parallel execution with error handling and
    result collection.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
    ):
        """Initialize processor.

        Args:
            max_workers: Maximum worker threads (default: CPU count)
            timeout_seconds: Timeout per item
        """
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

    def map(
        self,
        func: Callable[[T], R],
        items: List[T],
    ) -> BatchResult[R]:
        """Process items in parallel.

        Args:
            func: Function to apply to each item
            items: Items to process

        Returns:
            BatchResult with results and errors
        """
        import time
        start = time.perf_counter()

        result = BatchResult[R]()

        if not items:
            return result

        # Use ThreadPoolExecutor for I/O bound operations
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all tasks
            futures = {
                executor.submit(func, item): i
                for i, item in enumerate(items)
            }

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    res = future.result(timeout=self.timeout_seconds)
                    result.results.append(res)
                except Exception as e:
                    result.errors.append((idx, str(e)))

        # Calculate stats
        elapsed = (time.perf_counter() - start) * 1000
        result.total_time_ms = elapsed
        if elapsed > 0:
            result.items_per_second = len(items) / (elapsed / 1000)

        return result

    def map_with_index(
        self,
        func: Callable[[int, T], R],
        items: List[T],
    ) -> BatchResult[R]:
        """Process items in parallel with index.

        Args:
            func: Function taking (index, item) -> result
            items: Items to process

        Returns:
            BatchResult with results and errors
        """
        def indexed_func(item_with_idx: tuple[int, T]) -> R:
            idx, item = item_with_idx
            return func(idx, item)

        indexed_items = list(enumerate(items))

        # Use regular map with indexed wrapper
        import time
        start = time.perf_counter()

        result = BatchResult[R]()

        if not items:
            return result

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = {
                executor.submit(indexed_func, (i, item)): i
                for i, item in enumerate(items)
            }

            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    res = future.result(timeout=self.timeout_seconds)
                    result.results.append(res)
                except Exception as e:
                    result.errors.append((idx, str(e)))

        elapsed = (time.perf_counter() - start) * 1000
        result.total_time_ms = elapsed
        if elapsed > 0:
            result.items_per_second = len(items) / (elapsed / 1000)

        return result


class BatchProcessor(Generic[T, R]):
    """Processes items in batches for efficiency.

    Groups items into batches before processing to reduce
    overhead for small items.
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_workers: Optional[int] = None,
    ):
        """Initialize processor.

        Args:
            batch_size: Items per batch
            max_workers: Maximum worker threads
        """
        self.batch_size = batch_size
        self._parallel = ParallelProcessor[List[T], List[R]](
            max_workers=max_workers
        )

    def process(
        self,
        func: Callable[[T], R],
        items: List[T],
    ) -> BatchResult[R]:
        """Process items in batches.

        Args:
            func: Function to apply to each item
            items: Items to process

        Returns:
            BatchResult with results
        """
        if not items:
            return BatchResult[R]()

        # Create batches
        batches: List[List[T]] = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)

        # Process batches
        def process_batch(batch: List[T]) -> List[R]:
            return [func(item) for item in batch]

        batch_result = self._parallel.map(process_batch, batches)

        # Flatten results
        result = BatchResult[R]()
        result.total_time_ms = batch_result.total_time_ms

        for batch_results in batch_result.results:
            result.results.extend(batch_results)

        # Map batch errors back to items
        for batch_idx, error in batch_result.errors:
            # Approximate item index
            item_idx = batch_idx * self.batch_size
            result.errors.append((item_idx, error))

        if result.total_time_ms > 0:
            result.items_per_second = len(items) / (result.total_time_ms / 1000)

        return result


def parallel_detect(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
) -> List[R]:
    """Detect properties in parallel.

    Convenience function for parallel property detection.

    Args:
        func: Detection function
        items: Items to process
        max_workers: Maximum workers

    Returns:
        List of results (errors silently skipped)
    """
    processor = ParallelProcessor[T, R](max_workers=max_workers)
    result = processor.map(func, items)
    return result.results


class AsyncBatchCollector(Generic[T]):
    """Collects items for batch processing.

    Accumulates items until batch size is reached, then
    processes the batch.
    """

    def __init__(
        self,
        batch_size: int = 10,
        process_fn: Optional[Callable[[List[T]], Any]] = None,
    ):
        """Initialize collector.

        Args:
            batch_size: Items per batch
            process_fn: Function to process each batch
        """
        self.batch_size = batch_size
        self.process_fn = process_fn
        self._buffer: List[T] = []
        self._processed_count: int = 0

    def add(self, item: T) -> bool:
        """Add item to batch.

        Args:
            item: Item to add

        Returns:
            True if a batch was processed
        """
        self._buffer.append(item)

        if len(self._buffer) >= self.batch_size:
            self._flush()
            return True

        return False

    def _flush(self) -> None:
        """Process current batch."""
        if self._buffer and self.process_fn:
            self.process_fn(self._buffer)
            self._processed_count += len(self._buffer)
            self._buffer = []

    def finish(self) -> int:
        """Finish processing remaining items.

        Returns:
            Total items processed
        """
        if self._buffer:
            self._flush()
        return self._processed_count

    @property
    def pending_count(self) -> int:
        """Get count of pending items."""
        return len(self._buffer)


__all__ = [
    "BatchResult",
    "ParallelProcessor",
    "BatchProcessor",
    "parallel_detect",
    "AsyncBatchCollector",
]
