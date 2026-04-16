"""
Contract Monitor

Monitors blockchain for contract events (deployments, upgrades, high-value changes).
Provides real-time contract lifecycle tracking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Set
from enum import Enum
from datetime import datetime
import asyncio
import logging
import hashlib

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of contract events."""
    DEPLOYMENT = "deployment"           # New contract deployed
    UPGRADE = "upgrade"                 # Proxy implementation changed
    OWNERSHIP_CHANGE = "ownership_change"  # Owner/admin changed
    HIGH_VALUE_TX = "high_value_tx"     # Large value transaction
    SUSPICIOUS_CALL = "suspicious_call"  # Unusual function call pattern
    PAUSE = "pause"                     # Contract paused
    UNPAUSE = "unpause"                 # Contract unpaused
    SELF_DESTRUCT = "self_destruct"     # Contract self-destructed


@dataclass
class ContractEvent:
    """
    An event related to a monitored contract.
    """
    event_type: EventType
    contract_address: str
    block_number: int
    tx_hash: str
    timestamp: datetime

    # Event-specific data
    data: Dict[str, Any] = field(default_factory=dict)

    # Analysis flags
    requires_audit: bool = False
    priority: str = "normal"            # normal, high, critical

    def __post_init__(self):
        self._set_priority()

    def _set_priority(self):
        """Set priority based on event type."""
        critical_events = {EventType.UPGRADE, EventType.OWNERSHIP_CHANGE, EventType.SELF_DESTRUCT}
        high_events = {EventType.DEPLOYMENT, EventType.HIGH_VALUE_TX}

        if self.event_type in critical_events:
            self.priority = "critical"
            self.requires_audit = True
        elif self.event_type in high_events:
            self.priority = "high"
            self.requires_audit = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "contract_address": self.contract_address,
            "block_number": self.block_number,
            "tx_hash": self.tx_hash,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "requires_audit": self.requires_audit,
            "data": self.data,
        }


@dataclass
class MonitorConfig:
    """Configuration for contract monitoring."""
    # Monitoring targets
    watch_addresses: List[str] = field(default_factory=list)
    watch_patterns: List[str] = field(default_factory=list)  # Regex for addresses

    # Event filters
    event_types: Set[EventType] = field(default_factory=lambda: set(EventType))
    min_value_threshold: float = 0.0     # Minimum value for HIGH_VALUE_TX (ETH)

    # Timing
    poll_interval_seconds: float = 12.0  # Block time
    max_blocks_per_poll: int = 100       # Max blocks to process per poll

    # Proxy detection
    detect_proxy_upgrades: bool = True
    proxy_implementation_slots: List[str] = field(default_factory=lambda: [
        "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",  # EIP-1967
        "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",  # OpenZeppelin
    ])


class ContractMonitor:
    """
    Monitors blockchain for contract events.

    Works with simulated or real blockchain data.
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.events: List[ContractEvent] = []
        self.event_handlers: Dict[EventType, List[Callable]] = {e: [] for e in EventType}
        self._running = False

        # State tracking
        self._last_block: int = 0
        self._implementation_cache: Dict[str, str] = {}  # proxy -> impl
        self._owner_cache: Dict[str, str] = {}           # contract -> owner

    def add_handler(self, event_type: EventType, handler: Callable[[ContractEvent], None]):
        """Add event handler for specific event type."""
        self.event_handlers[event_type].append(handler)

    def remove_handler(self, event_type: EventType, handler: Callable):
        """Remove event handler."""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)

    def watch_address(self, address: str):
        """Add address to watch list."""
        if address not in self.config.watch_addresses:
            self.config.watch_addresses.append(address)

    def unwatch_address(self, address: str):
        """Remove address from watch list."""
        if address in self.config.watch_addresses:
            self.config.watch_addresses.remove(address)

    async def start(self):
        """Start monitoring (async)."""
        self._running = True
        logger.info("Contract monitor started")

        while self._running:
            try:
                await self._poll_blocks()
            except Exception as e:
                logger.error(f"Error polling blocks: {e}")

            await asyncio.sleep(self.config.poll_interval_seconds)

    def stop(self):
        """Stop monitoring."""
        self._running = False
        logger.info("Contract monitor stopped")

    async def _poll_blocks(self):
        """Poll for new blocks and process events."""
        # This would connect to actual blockchain in production
        # Here we simulate for testing
        pass

    def process_block(self, block_data: Dict[str, Any]) -> List[ContractEvent]:
        """
        Process a block and extract events.

        Args:
            block_data: Block data with transactions

        Returns:
            List of detected events
        """
        events = []
        block_number = block_data.get("number", 0)
        timestamp = datetime.fromisoformat(
            block_data.get("timestamp", datetime.now().isoformat())
        )

        for tx in block_data.get("transactions", []):
            tx_events = self._process_transaction(tx, block_number, timestamp)
            events.extend(tx_events)

        # Handle events
        for event in events:
            self._handle_event(event)
            self.events.append(event)

        self._last_block = block_number
        return events

    def _process_transaction(
        self,
        tx: Dict[str, Any],
        block_number: int,
        timestamp: datetime
    ) -> List[ContractEvent]:
        """Process a single transaction for events."""
        events = []
        tx_hash = tx.get("hash", "")
        from_addr = tx.get("from", "")
        to_addr = tx.get("to")
        value = float(tx.get("value", 0))
        input_data = tx.get("input", "")

        # Contract deployment (to=None)
        if to_addr is None:
            contract_address = tx.get("contractAddress", "")
            if contract_address:
                events.append(ContractEvent(
                    event_type=EventType.DEPLOYMENT,
                    contract_address=contract_address,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={
                        "deployer": from_addr,
                        "code_hash": hashlib.sha256(input_data.encode()).hexdigest()[:16],
                    }
                ))

        # Check watched addresses
        if to_addr and to_addr in self.config.watch_addresses:
            # High value transaction
            if value >= self.config.min_value_threshold and value > 0:
                events.append(ContractEvent(
                    event_type=EventType.HIGH_VALUE_TX,
                    contract_address=to_addr,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={
                        "value": value,
                        "from": from_addr,
                        "function": input_data[:10] if input_data else None,
                    }
                ))

            # Check for upgrade signature
            if self._is_upgrade_call(input_data):
                events.append(ContractEvent(
                    event_type=EventType.UPGRADE,
                    contract_address=to_addr,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={
                        "caller": from_addr,
                        "new_implementation": self._extract_implementation(input_data),
                    }
                ))

            # Check for ownership change
            if self._is_ownership_change(input_data):
                events.append(ContractEvent(
                    event_type=EventType.OWNERSHIP_CHANGE,
                    contract_address=to_addr,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={
                        "caller": from_addr,
                        "new_owner": self._extract_new_owner(input_data),
                    }
                ))

            # Check for pause/unpause
            if self._is_pause_call(input_data):
                events.append(ContractEvent(
                    event_type=EventType.PAUSE,
                    contract_address=to_addr,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={"caller": from_addr}
                ))
            elif self._is_unpause_call(input_data):
                events.append(ContractEvent(
                    event_type=EventType.UNPAUSE,
                    contract_address=to_addr,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    data={"caller": from_addr}
                ))

        return events

    def _handle_event(self, event: ContractEvent):
        """Handle event by calling registered handlers."""
        for handler in self.event_handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def _is_upgrade_call(self, input_data: str) -> bool:
        """Check if transaction is an upgrade call."""
        upgrade_selectors = [
            "0x3659cfe6",  # upgradeTo(address)
            "0x4f1ef286",  # upgradeToAndCall(address,bytes)
            "0x99a88ec4",  # upgrade(address,address)
        ]
        return any(input_data.startswith(sel) for sel in upgrade_selectors)

    def _is_ownership_change(self, input_data: str) -> bool:
        """Check if transaction is an ownership change."""
        ownership_selectors = [
            "0xf2fde38b",  # transferOwnership(address)
            "0x715018a6",  # renounceOwnership()
            "0x2f54bf6e",  # acceptOwnership()
        ]
        return any(input_data.startswith(sel) for sel in ownership_selectors)

    def _is_pause_call(self, input_data: str) -> bool:
        """Check if transaction is a pause call."""
        return input_data.startswith("0x8456cb59")  # pause()

    def _is_unpause_call(self, input_data: str) -> bool:
        """Check if transaction is an unpause call."""
        return input_data.startswith("0x3f4ba83a")  # unpause()

    def _extract_implementation(self, input_data: str) -> Optional[str]:
        """Extract new implementation address from upgrade call."""
        if len(input_data) >= 74:
            # Address is in first parameter
            return "0x" + input_data[34:74]
        return None

    def _extract_new_owner(self, input_data: str) -> Optional[str]:
        """Extract new owner address from ownership change."""
        if len(input_data) >= 74:
            return "0x" + input_data[34:74]
        return None

    def get_events_by_type(self, event_type: EventType) -> List[ContractEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_for_address(self, address: str) -> List[ContractEvent]:
        """Get all events for a specific address."""
        return [e for e in self.events if e.contract_address == address]

    def get_recent_events(self, limit: int = 100) -> List[ContractEvent]:
        """Get most recent events."""
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_critical_events(self) -> List[ContractEvent]:
        """Get events requiring immediate attention."""
        return [e for e in self.events if e.priority == "critical"]

    def clear_events(self):
        """Clear event history."""
        self.events.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        by_type = {}
        for event_type in EventType:
            by_type[event_type.value] = len(self.get_events_by_type(event_type))

        return {
            "total_events": len(self.events),
            "by_type": by_type,
            "watched_addresses": len(self.config.watch_addresses),
            "last_block": self._last_block,
            "critical_events": len(self.get_critical_events()),
        }
