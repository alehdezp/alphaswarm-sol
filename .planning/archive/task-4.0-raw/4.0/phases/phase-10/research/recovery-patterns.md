# Recovery Patterns for VKG

**Status:** Complete
**Created:** 2026-01-08
**Purpose:** Document error recovery patterns and best practices for BSKG implementation

---

## 1. Circuit Breaker Pattern

### When to Use
- Repeated failures to same external service
- Rate limiting scenarios
- Provider outages

### Implementation

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, TypeVar, Optional

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, stop trying
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for protecting against repeated failures."""

    failure_threshold: int = 5          # Failures before opening
    reset_timeout: int = 60             # Seconds before half-open
    half_open_max_calls: int = 3        # Test calls in half-open state

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for timeout transition."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if datetime.now() - self._last_failure_time > timedelta(seconds=self.reset_timeout):
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit open, retry after {self.reset_timeout}s")

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN or \
           self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass
```

### BSKG Application

```python
# LLM provider with circuit breaker
class LLMProviderWithBreaker:
    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider
        self._breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60,
        )

    def complete(self, prompt: str) -> str:
        return self._breaker.call(
            lambda: self._provider.complete(prompt)
        )
```

---

## 2. Retry with Exponential Backoff

### When to Use
- Transient failures (network blips, temporary unavailability)
- Rate limits with retry-after header
- Timeouts

### Implementation

```python
import time
import random
from functools import wraps
from typing import Callable, TypeVar, Tuple, Type

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Exceptions that trigger retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate delay
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter (0.5-1.5x delay)
                    if jitter:
                        delay *= 0.5 + random.random()

                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


# Usage
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError),
)
def call_llm_api(prompt: str) -> str:
    ...
```

### BSKG Application

```python
# LLM API calls with backoff
RETRYABLE_HTTP_CODES = (429, 500, 502, 503, 504)

class RobustLLMClient:
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        retryable_exceptions=(RateLimitError, ServiceUnavailableError),
    )
    def complete(self, prompt: str) -> str:
        response = self._make_request(prompt)
        if response.status_code in RETRYABLE_HTTP_CODES:
            raise RateLimitError(f"Status {response.status_code}")
        return response.json()
```

---

## 3. Safe State Writes (Atomic Operations)

### When to Use
- Any file write that must not corrupt
- Graph JSON saves
- Configuration updates

### Implementation

```python
import os
import json
import tempfile
from pathlib import Path
from typing import Any, Union
from contextlib import contextmanager


def safe_write(path: Union[str, Path], data: Union[str, bytes]) -> None:
    """
    Write data atomically using temp file + rename pattern.

    This ensures that if the write fails midway, the original
    file remains intact.
    """
    path = Path(path)

    # Write to temp file in same directory (for same-filesystem rename)
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )

    try:
        with os.fdopen(fd, 'wb' if isinstance(data, bytes) else 'w') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())  # Ensure data hits disk

        # Atomic rename (on POSIX)
        os.rename(temp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def safe_json_write(path: Union[str, Path], data: Any) -> None:
    """Write JSON atomically."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    safe_write(path, json_str)


@contextmanager
def safe_file_update(path: Path):
    """
    Context manager for safe file updates.

    Usage:
        with safe_file_update(config_path) as content:
            content['new_key'] = 'value'
        # File is written atomically on exit
    """
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    else:
        data = {}

    yield data

    safe_json_write(path, data)
```

### BSKG Application

```python
# Graph persistence with safe writes
class KnowledgeGraphPersistence:
    def save(self, graph: KnowledgeGraph, path: Path) -> None:
        """Save graph with atomic write."""
        data = graph.to_dict()
        safe_json_write(path, data)

    def save_with_backup(self, graph: KnowledgeGraph, path: Path) -> None:
        """Save graph with backup of previous version."""
        if path.exists():
            backup_path = path.with_suffix('.json.bak')
            safe_write(backup_path, path.read_bytes())

        self.save(graph, path)
```

---

## 4. Graceful Degradation Pattern

### When to Use
- Optional features fail
- External dependencies unavailable
- Resource constraints

### Implementation

```python
from dataclasses import dataclass
from typing import List, Set, Callable, Dict, Any
from enum import IntEnum, auto


class CapabilityLevel(IntEnum):
    """Capability levels for degradation."""
    FULL = auto()           # All features available
    STANDARD = auto()       # Core + some enhancements
    CORE = auto()           # Core features only
    MINIMAL = auto()        # Absolute minimum


@dataclass
class Capability:
    """A BSKG capability that can be degraded."""
    name: str
    level: CapabilityLevel
    available: bool
    reason: str = ""


class DegradationManager:
    """Manages graceful degradation of capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._degradation_handlers: Dict[str, Callable[[], None]] = {}

    def register_capability(
        self,
        name: str,
        level: CapabilityLevel,
        check_fn: Callable[[], bool],
    ) -> None:
        """Register a capability with availability check."""
        available = check_fn()
        self._capabilities[name] = Capability(
            name=name,
            level=level,
            available=available,
            reason="" if available else "Check failed",
        )

    def get_current_level(self) -> CapabilityLevel:
        """Get current capability level based on availability."""
        if all(c.available for c in self._capabilities.values()):
            return CapabilityLevel.FULL

        # Find highest level with all capabilities available
        for level in CapabilityLevel:
            level_caps = [
                c for c in self._capabilities.values()
                if c.level <= level
            ]
            if all(c.available for c in level_caps):
                return level

        return CapabilityLevel.MINIMAL

    def get_unavailable(self) -> List[Capability]:
        """Get list of unavailable capabilities."""
        return [c for c in self._capabilities.values() if not c.available]

    def format_degradation_message(self) -> str:
        """Format user-friendly degradation message."""
        unavailable = self.get_unavailable()
        if not unavailable:
            return "All capabilities available."

        level = self.get_current_level()
        lines = [f"Operating at {level.name} level."]
        lines.append("Unavailable features:")
        for cap in unavailable:
            lines.append(f"  - {cap.name}: {cap.reason}")

        return "\n".join(lines)
```

### BSKG Application

```python
# Degradation tree for VKG
DEGRADATION_TREE = """
Full Capability
    |
    +-- LLM fails --> Tier A only (pattern matching, graph queries)
    |                 Impact: No false positive filtering, no NL queries
    |
    +-- External tools fail --> BSKG patterns only
    |                          Impact: Fewer findings, no Aderyn/Medusa
    |
    +-- Slither fails --> CRITICAL: Cannot continue
                         Action: Fix Slither, cannot degrade further
"""

# Capability registration
degradation_manager = DegradationManager()

degradation_manager.register_capability(
    "tier_b_analysis",
    CapabilityLevel.STANDARD,
    check_fn=lambda: bool(os.environ.get("ANTHROPIC_API_KEY")),
)

degradation_manager.register_capability(
    "aderyn_analysis",
    CapabilityLevel.STANDARD,
    check_fn=lambda: shutil.which("aderyn") is not None,
)

degradation_manager.register_capability(
    "slither_analysis",
    CapabilityLevel.CORE,  # Core - cannot degrade
    check_fn=lambda: shutil.which("slither") is not None,
)
```

---

## 5. User Communication Pattern

### Error Message Template

```
[SEVERITY] Short description

  Context: What was happening
  Cause: Why it failed (if known)
  Next: What user can do
  Help: Where to get more info
```

### Implementation

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class ErrorSeverity(Enum):
    FATAL = "FATAL"      # Cannot continue
    ERROR = "ERROR"      # Operation failed
    WARNING = "WARNING"  # Degraded but continuing
    INFO = "INFO"        # Informational


@dataclass
class UserFriendlyError:
    """User-friendly error with recovery guidance."""
    severity: ErrorSeverity
    title: str
    context: str
    cause: Optional[str] = None
    next_steps: Optional[List[str]] = None
    help_command: Optional[str] = None

    def format(self) -> str:
        lines = [f"[{self.severity.value}] {self.title}", ""]
        lines.append(f"  Context: {self.context}")

        if self.cause:
            lines.append(f"  Cause: {self.cause}")

        if self.next_steps:
            lines.append("  Next steps:")
            for step in self.next_steps:
                lines.append(f"    - {step}")

        if self.help_command:
            lines.append(f"  Help: {self.help_command}")

        return "\n".join(lines)


# Factory functions for common errors
def slither_version_error(required: str, available: Optional[str]) -> UserFriendlyError:
    return UserFriendlyError(
        severity=ErrorSeverity.ERROR,
        title="Solidity version mismatch",
        context=f"Analyzing contracts requiring Solidity {required}",
        cause=f"Installed solc version: {available or 'none'}",
        next_steps=[
            f"Run: solc-select install {required}",
            f"Run: solc-select use {required}",
        ],
        help_command="vkg doctor --verbose",
    )


def llm_rate_limit_error(retry_after: int) -> UserFriendlyError:
    return UserFriendlyError(
        severity=ErrorSeverity.WARNING,
        title="LLM API rate limited",
        context="Making Tier B analysis request",
        cause="Too many requests to LLM provider",
        next_steps=[
            f"Wait {retry_after} seconds and retry",
            "Use --tier-a-only to skip LLM analysis",
            "Check your API quota",
        ],
        help_command="vkg doctor --check-llm",
    )


def disk_full_error(required_mb: int, available_mb: int) -> UserFriendlyError:
    return UserFriendlyError(
        severity=ErrorSeverity.FATAL,
        title="Insufficient disk space",
        context="Writing analysis results",
        cause=f"Need {required_mb}MB, only {available_mb}MB available",
        next_steps=[
            "Free up disk space",
            "Run: vkg cache clear",
            "Move .vkg directory to larger disk",
        ],
        help_command="vkg doctor --disk",
    )
```

---

## Decision Tree

```
Failure Detected
    │
    ├── Is it transient? (network, timeout, rate limit)
    │       │
    │       ├── Yes: Retry with backoff (max 3 attempts)
    │       │       └── Still failing? Continue to degradation check
    │       │
    │       └── No: Continue to core check
    │
    ├── Is core functionality? (Slither, Python)
    │       │
    │       ├── Yes: FATAL - fail with clear error, suggest fix
    │       │
    │       └── No: Continue to degradation check
    │
    ├── Can we degrade gracefully?
    │       │
    │       ├── Yes: Continue with reduced capability
    │       │       └── Log warning with missing features
    │       │
    │       └── No: Fail gracefully with recovery command
    │
    └── Is state corrupted?
            │
            ├── Yes:
            │       ├── Backup exists? Restore from backup
            │       └── No backup? Offer 'vkg repair' or 'vkg reset --confirm'
            │
            └── No: Report error, continue if possible
```

---

## Pattern Selection Guide

| Failure Type | Primary Pattern | Secondary Pattern |
|-------------|-----------------|-------------------|
| Network transient | Retry with Backoff | Circuit Breaker |
| Rate limiting | Circuit Breaker | Graceful Degradation |
| External tool missing | Graceful Degradation | - |
| File corruption | Safe State Writes | User Communication |
| Resource exhaustion | Graceful Degradation | User Communication |
| Configuration error | User Communication | - |

---

*Recovery Patterns | Version 1.0 | 2026-01-08*
