"""Rule map for flexible NL pattern selection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from alphaswarm_sol.queries.patterns import PatternDefinition


@dataclass(frozen=True)
class RuleEntry:
    pattern_id: str
    phrases: list[str]


_SYNONYMS: dict[str, list[str]] = {
    "weak-access-control": ["missing access control", "no access gate"],
    "initializer-no-gate": ["unprotected initializer", "unguarded initialize"],
    "upgrade-without-guard": ["unguarded upgrade", "unprotected upgrade"],
    "upgrade-missing-storage-gap": ["missing storage gap", "storage gap missing"],
    "reentrancy-basic": ["reentrancy risk", "external call before state write"],
    "state-write-after-call": ["state write after external call", "writes after call"],
    "value-movement-classic-reentrancy": ["classic reentrancy", "state after external call"],
    "value-movement-eth-transfer-reentrancy": ["eth transfer reentrancy", "value transfer reentrancy"],
    "value-movement-loop-reentrancy": ["loop reentrancy", "external call in loop"],
    "value-movement-cross-function-reentrancy": ["cross-function reentrancy", "shared state reentrancy"],
    "value-movement-read-only-reentrancy": ["read-only reentrancy", "view reentrancy"],
    "value-movement-token-callback-reentrancy": ["token callback reentrancy", "erc token reentrancy"],
    "value-movement-unchecked-low-level-call": ["unchecked low-level call", "call return unchecked"],
    "value-movement-unchecked-erc20-transfer": ["unchecked erc20 transfer", "erc20 return unchecked"],
    "value-movement-arbitrary-delegatecall": ["arbitrary delegatecall", "delegatecall target controlled"],
    "value-movement-approval-race": ["approval race", "approve race condition"],
    "value-movement-flash-loan-callback": ["flash loan callback", "flashloan callback safety"],
    "value-movement-flash-loan-sensitive-operation": ["flash loan manipulation", "flash loan sensitive"],
    "auth-001": ["unprotected state writer", "missing access control"],
    "auth-002": ["tx.origin authentication", "tx origin auth"],
    "auth-003": ["missing signature validation", "ecrecover missing checks"],
    "auth-004": ["signature replay", "missing nonce"],
    "auth-005": ["single point of failure", "centralization risk"],
    "auth-006": ["unprotected initializer", "initializer without guard"],
    "auth-007": ["privilege escalation", "self grant role"],
    "auth-008": ["missing timelock", "no timelock"],
    "auth-009": ["bypassable access control", "access control bypass"],
    "auth-010": ["cross contract auth", "auth confusion"],
    "auth-011": ["unprotected value transfer", "unauthorized transfer"],
    "auth-012": ["unprotected admin function", "admin function without auth"],
    "auth-013": ["inconsistent access control", "mixed access control"],
    "auth-014": ["missing revoke", "no role revoke"],
    "auth-015": ["default admin missing", "missing default admin"],
    "auth-016": ["dangerous admin function", "admin can drain funds"],
    "auth-017": ["missing authentication", "no authentication"],
    "auth-018": ["weak authentication", "timestamp auth"],
    "auth-019": ["callback without authorization", "unauthorized callback"],
    "auth-020": ["time based access", "timestamp privileged access"],
    "auth-045": ["public wrapper without access control", "public wrapper no gate"],
    "auth-046": ["governance vote without snapshot", "vote without snapshot"],
    "auth-047": ["multisig threshold change without auth", "multisig threshold no gate"],
    "auth-048": ["multisig signer change without auth", "multisig signer no gate"],
    "auth-049": ["emergency delegatecall bypass", "emergency delegatecall unvalidated"],
    "auth-050": ["multicall batching without guard", "multicall no reentrancy guard"],
    "auth-051": ["timelock admin without access control", "timelock admin no gate"],
    "auth-052": ["delegatecall context sensitive without access control", "delegatecall msg.sender no gate"],
    "auth-053": ["public tx.origin usage", "tx.origin public"],
    "auth-054": ["time-based access without auth", "timestamp access without auth"],
    "auth-055": ["delegatecall without access control", "unprotected delegatecall"],
    "auth-056": ["low-level call without access control", "call without auth"],
    "auth-057": ["weak authentication source without gate", "weak auth source no gate"],
    "auth-058": ["role grant without access control", "grant role without auth"],
    "auth-059": ["role revoke without access control", "revoke role without auth"],
    "auth-060": ["role modification without access control", "role change without auth"],
    "auth-061": ["selfdestruct without access control", "public selfdestruct"],
    "auth-062": ["reinitializer without guard", "reinitialize without guard"],
    "auth-063": ["public payable without access control", "payable no gate"],
    "auth-064": ["payable fallback without access control", "payable receive no gate"],
    "auth-065": ["external call without access control", "external call no gate"],
    "auth-066": ["user input state write without access control", "user input no gate"],
    "auth-067": ["access gate uses tx.origin", "tx.origin access gate"],
    "auth-068": ["timelock parameter missing check", "timelock without enforcement"],
    "auth-069": ["multisig threshold zero", "multisig threshold 0"],
    "auth-070": ["upgrade without access control", "unprotected upgrade"],
    "auth-071": ["oracle update without access control", "oracle update no gate"],
    "auth-072": ["governance quorum without snapshot", "quorum without snapshot"],
    "auth-073": ["governance execute without timelock", "governance execute no timelock"],
    "auth-074": ["multisig threshold change without validation", "multisig threshold no validation"],
    "auth-075": ["multisig signer change without validation", "multisig signer no validation"],
    "auth-076": ["governance execute without quorum", "execute without quorum"],
    "auth-077": ["governance execute without vote period", "execute without voting period"],
    "auth-078": ["multisig execute without nonce", "multisig execute no nonce"],
    "auth-079": ["weak auth extcodesize", "auth extcodesize"],
    "auth-080": ["weak auth extcodehash", "auth extcodehash"],
    "auth-081": ["weak auth gasleft", "auth gasleft"],
    "auth-082": ["tx.origin fallback", "tx.origin receive"],
    "auth-083": ["default admin zero address", "default admin address zero"],
    "auth-084": ["owner uninitialized", "owner not set"],
    "auth-085": ["owner uninitialized privileged", "owner uninitialized privileged ops"],
    "auth-086": ["access gate block timestamp", "auth block timestamp"],
    "auth-087": ["access gate block number", "auth block number"],
    "auth-088": ["access gate blockhash", "auth blockhash"],
    "auth-089": ["access gate chainid", "auth chainid"],
    "auth-090": ["access gate msg.value", "auth msg.value"],
    "auth-091": ["timelock admin without check", "timelock admin no check"],
    "auth-092": ["multisig execute nonce not updated", "multisig nonce not updated"],
    "auth-093": ["governance vote flashloan risk", "flash loan voting risk"],
    "auth-094": ["multisig signer change without signature validation", "multisig signer change no signature"],
    "auth-095": ["weak auth balance check", "auth balance check"],
    "auth-096": ["multisig threshold change without approval", "multisig threshold single owner"],
    "auth-097": ["multisig signer change without approval", "multisig signer single owner"],
    "auth-098": ["multisig execute without signature validation", "multisig execute no signature"],
    "auth-099": ["multisig signer removal without minimum check", "multisig remove signer no min"],
    "auth-100": ["multisig threshold without owner count check", "threshold without owner count"],
    "auth-101": ["weak auth contract address", "auth address(this)"],
    "auth-102": ["weak auth hash compare", "auth keccak compare"],
    "auth-103": ["role grant without events", "role grant no event"],
    "auth-104": ["mixed tx.origin msg.sender", "tx.origin and msg.sender auth"],
    "auth-105": ["access gate if return", "auth if return"],
    "auth-106": ["access gate without sender", "auth without sender source"],
    "auth-107": ["context dependent auth external calls", "auth external calls context"],
    "auth-042": ["weak authentication source", "weak auth source"],
    "auth-043": ["time based access control", "timestamp access control"],
    "auth-044": ["governance without timelock", "governance no timelock"],
    "auth-108": ["unprotected pause", "pause without auth", "unprotected unpause"],
    "auth-109": ["unprotected list management", "whitelist without auth", "blacklist without auth"],
    "auth-110": ["unprotected governance parameter update", "quorum without auth", "voting period without auth"],
    "auth-111": ["unprotected reward update", "emission update without auth", "vesting update without auth"],
    "auth-112": ["unprotected cross-chain config", "bridge config without auth", "relayer update without auth"],
    "auth-113": ["privileged external call without reentrancy guard", "auth external call no guard"],
    "auth-114": ["unprotected fee update", "rate update without auth", "slippage update without auth"],
    "auth-115": ["unprotected emergency operation", "rescue without auth", "recover without auth"],
    "auth-116": ["unprotected merkle root update", "merkle root without auth"],
    "auth-117": ["unprotected oracle update", "price feed without auth"],
    "auth-118": ["unprotected fee recipient update", "treasury without auth"],
    "auth-119": ["implementation initializer without proxy guard", "initializer without onlyProxy"],
    "auth-120": ["unprotected fallback", "unprotected receive", "fallback without auth"],
    "dos-unbounded-loop": ["unbounded loop", "loop without bound", "loop"],
    "dos-unbounded-deletion": ["unbounded delete loop", "delete in unbounded loop"],
    "dos-external-call-in-loop": ["external call in loop", "call inside loop", "loop call", "loop"],
    "mev-missing-slippage-parameter": ["missing slippage", "no slippage parameter"],
    "mev-missing-deadline-parameter": ["missing deadline", "no deadline parameter"],
    "oracle-freshness-missing-staleness": ["missing staleness check", "oracle stale"],
    "oracle-freshness-missing-sequencer": ["missing sequencer check", "l2 sequencer"],
    "ext-001": ["spot price manipulation", "spot price oracle"],
    "ext-002": ["stale oracle data", "oracle staleness"],
    "ext-003": ["chainlink incomplete validation", "latest round data missing checks"],
    "ext-004": ["flash loan price attack", "flash loan price manipulation"],
    "ext-005": ["sequencer uptime missing", "l2 sequencer uptime"],
    "ext-006": ["missing zero address check", "zero address validation"],
    "ext-007": ["missing amount bounds", "amount bounds missing"],
    "ext-008": ["array length manipulation", "array length missing check"],
    "ext-009": ["deadline validation missing", "deadline missing check"],
    "ext-010": ["unsafe abi decode", "abi decode unsafe"],
    "ext-011": ["merkle proof leaf collision", "merkle leaf collision"],
    "ext-012": ["single source oracle", "single oracle source"],
    "ext-013": ["twap window missing", "twap missing window"],
    "ext-014": ["oracle aggregation missing sanity", "oracle outlier missing"],
    "ext-015": ["chainlink decimals missing", "oracle decimals missing"],
    "ext-016": ["oracle feed not upgradeable", "feed deprecation handling"],
    "ext-017": ["cross chain oracle missing validation", "bridge oracle missing validation"],
    "ext-018": ["contract address not verified", "missing contract code check"],
    "ext-019": ["self address not rejected", "address this not rejected"],
    "ext-020": ["zero amount not rejected", "amount zero check missing"],
    "ext-021": ["array index not validated", "array index unchecked"],
    "ext-022": ["array length mismatch", "array length mismatch missing"],
    "ext-023": ["external data integrity missing", "offchain data without integrity"],
    "ext-024": ["oracle update without access control", "oracle update unprotected"],
    "arith-001": ["unchecked arithmetic", "unchecked block arithmetic"],
    "arith-002": ["division before multiplication", "division order precision"],
    "arith-003": ["unsafe narrowing cast", "narrowing cast"],
    "arith-004": ["division by zero", "zero divisor"],
    "arith-005": ["share inflation", "share calculation issue"],
    "arith-006": ["fee precision loss", "fee precision"],
    "arith-007": ["token decimal mismatch", "decimal mismatch"],
    "arith-008": ["multiplication overflow", "large multiplication"],
    "arith-009": ["rounding exploitation", "rounding error"],
    "arith-010": ["percentage overflow", "percentage calculation overflow"],
    "arith-011": ["pre-0.8 overflow", "pre 0.8 arithmetic"],
    "arith-012": ["loop counter overflow", "loop counter small type"],
    "arith-013": ["financial truncation", "truncation in financial calculation"],
    "arith-014": ["signed to unsigned cast", "signed unsigned conversion"],
    "arith-015": ["address to uint cast", "address to integer"],
    "arith-016": ["division precision loss", "division precision"],
    "arith-017": ["price amount overflow", "price times amount"],
    "arith-018": ["basis points precision", "bps precision loss"],
    "arith-019": ["ratio calculation issue", "ratio precision"],
    "arith-020": ["fee accumulation overflow", "fee accumulation"],
    "arith-021": ["timestamp arithmetic", "timestamp math"],
    "arith-022": ["duration calculation issue", "duration bounds missing"],
    "arith-023": ["decimal scaling issue", "decimal scaling"],
    "logic-001": ["invalid state transition", "state machine transition"],
    "logic-002": ["balance invariant violation", "balance invariant"],
    "logic-003": ["missing balance check", "balance sufficiency check"],
    "logic-004": ["double counting", "double counted"],
    "logic-005": ["variable shadowing", "shadowing"],
    "logic-006": ["unprotected selfdestruct", "public selfdestruct"],
    "logic-007": ["extcodesize bypass", "extcodesize constructor"],
    "logic-008": ["uninitialized storage", "storage uninitialized"],
    "logic-009": ["missing event emission", "missing events"],
    "logic-010": ["incomplete state cleanup", "state cleanup missing"],
    "logic-011": ["state race condition", "state race"],
    "logic-012": ["collateral invariant violation", "collateral invariant"],
    "logic-013": ["pool invariant violation", "pool invariant"],
    "logic-014": ["missing return value check", "unchecked return value"],
    "logic-015": ["missing boundary checks", "missing bounds check"],
    "logic-016": ["ordering sequencing flaw", "ordering flaw"],
    "logic-017": ["conditional logic flaw", "conditional bypass"],
    "logic-018": ["protocol interaction flaw", "external protocol assumption"],
    "logic-019": ["missing accounting updates", "accounting update missing"],
    "logic-020": ["rounding accumulation", "rounding accumulation error"],
    "logic-021": ["override missing super", "override without super"],
    "logic-022": ["diamond inheritance", "multiple inheritance conflict"],
    "logic-023": ["forced ether via selfdestruct", "forced ether selfdestruct"],
    "logic-024": ["contract vs eoa assumption", "contract eoa assumption"],
    "logic-025": ["boolean default issue", "uninitialized bool"],
    "logic-026": ["incorrect event parameters", "event parameter mismatch"],
}


def build_rule_map(patterns: Iterable[PatternDefinition]) -> list[RuleEntry]:
    entries: list[RuleEntry] = []
    for pattern in patterns:
        phrases: list[str] = []
        phrases.append(pattern.id.replace("-", " "))
        if pattern.name:
            phrases.append(pattern.name)
        if pattern.description:
            phrases.append(pattern.description)
        phrases.extend(pattern.lens)
        phrases.extend(_SYNONYMS.get(pattern.id, []))
        phrases = _normalize_phrases(phrases)
        entries.append(RuleEntry(pattern_id=pattern.id, phrases=phrases))
    return entries


def resolve_rule_matches(text: str, patterns: Iterable[PatternDefinition]) -> tuple[list[str], float, list[dict[str, float]]]:
    lowered = _normalize(text)
    entries = build_rule_map(patterns)
    matches: list[tuple[int, str]] = []
    for entry in entries:
        for phrase in entry.phrases:
            if not phrase:
                continue
            if phrase in lowered:
                matches.append((len(phrase), entry.pattern_id))
                break
    if not matches:
        tokens = [token for token in re.split(r"\s+", lowered) if token]
        for entry in entries:
            hits = sum(1 for phrase in entry.phrases if phrase in tokens)
            if hits:
                matches.append((hits, entry.pattern_id))
    matches.sort(reverse=True)
    seen: set[str] = set()
    result: list[str] = []
    for _, pattern_id in matches:
        if pattern_id in seen:
            continue
        seen.add(pattern_id)
        result.append(pattern_id)
    confidence = 0.0
    if matches:
        confidence = min(1.0, matches[0][0] / max(len(lowered), 1))
    candidates = [
        {"pattern_id": pattern_id, "score": length / max(len(lowered), 1)}
        for length, pattern_id in matches[:5]
    ]
    return result, confidence, candidates


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s:_-]", " ", text.lower())


def _normalize_phrases(phrases: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for phrase in phrases:
        candidate = _normalize(phrase).strip()
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized
