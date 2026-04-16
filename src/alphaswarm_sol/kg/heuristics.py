"""Heuristics for tagging security-relevant semantics."""

from __future__ import annotations

import re
from typing import Iterable

_TOKEN_SPLIT_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _tokenize(name: str) -> set[str]:
    raw = name.replace("-", "_").replace(".", "_")
    parts = set()
    for chunk in raw.split("_"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for piece in _TOKEN_SPLIT_RE.sub("_", chunk).split("_"):
            if piece:
                parts.add(piece.lower())
    return parts


def classify_state_var_name(name: str) -> list[str]:
    tokens = _tokenize(name)
    tags: set[str] = set()

    if {"owner", "admin"} & tokens:
        tags.add("owner")
    if "role" in tokens or "roles" in tokens:
        tags.add("role")
    if "fee" in tokens or "fees" in tokens or "bps" in tokens:
        tags.add("fee")
    if "balance" in tokens or "balances" in tokens or "bal" in tokens:
        tags.add("balance")
    if "supply" in tokens or "totalsupply" in tokens:
        tags.add("supply")
    if {"stake", "staking", "staked"} & tokens:
        tags.add("stake")
    if {"collateral", "collat"} & tokens:
        tags.add("collateral")
    if {"debt", "borrow", "loan", "liability"} & tokens:
        tags.add("debt")
    if {"liquidity", "liquid"} & tokens:
        tags.add("liquidity")
    if {"reserve", "reserves"} & tokens:
        tags.add("reserve")
    if "pool" in tokens or "pools" in tokens:
        tags.add("pool")
    if "vault" in tokens or "vaults" in tokens:
        tags.add("vault")
    if {"position", "positions"} & tokens:
        tags.add("position")
    if {"claim", "claimable"} & tokens:
        tags.add("claimable")
    if {"pending"} & tokens:
        tags.add("pending")
    if {"reward", "rewards", "emission", "emissions", "vesting", "vest"} & tokens:
        tags.add("reward")
    if {"asset", "assets", "principal"} & tokens:
        tags.add("asset")
    if {"cap", "limit", "max", "min"} & tokens:
        tags.add("cap")
    if {"config", "settings", "params", "parameter", "merkle"} & tokens:
        tags.add("config")
    if {"upgrade", "upgrader", "implementation", "impl", "proxy", "logic", "beacon"} & tokens:
        tags.add("upgrade")
    if {"pause", "paused", "pausable", "pauser"} & tokens:
        tags.add("pause")
    if {"whitelist", "allowlist", "allow", "allowed"} & tokens:
        tags.add("allowlist")
    if {"blacklist", "denylist", "blocked"} & tokens:
        tags.add("denylist")
    if {"oracle", "price", "twap", "feed", "pricefeed"} & tokens:
        tags.add("oracle")
    if {"treasury", "vault", "reserve"} & tokens:
        tags.add("treasury")
    if {"nonce", "nonces"} & tokens:
        tags.add("nonce")
    if {"signer", "signers", "validator", "validators"} & tokens:
        tags.add("signer")
    if {
        "governance",
        "governor",
        "timelock",
        "council",
        "quorum",
        "voting",
        "proposal",
        "threshold",
        "delay",
        "guardian",
    } & tokens:
        tags.add("governance")
    if {"share", "shares"} & tokens:
        tags.add("shares")
    if {"lock", "locked", "mutex", "guard", "reentrancy"} & tokens:
        tags.add("lock")
    if {
        "router",
        "strategy",
        "adapter",
        "module",
        "bridge",
        "relayer",
        "endpoint",
        "messaging",
        "amm",
        "dex",
        "pair",
        "pool",
        "vault",
        "controller",
        "manager",
        "aggregator",
        "lending",
        "borrow",
        "staking",
        "farm",
    } & tokens:
        tags.add("dependency")

    return sorted(tags)


def classify_auth_modifiers(modifiers: Iterable[str]) -> list[str]:
    tags: set[str] = set()
    for modifier in modifiers:
        lowered = modifier.lower()
        if "only" in lowered and "owner" in lowered:
            tags.add("only_owner")
        if "only" in lowered and "admin" in lowered:
            tags.add("only_admin")
        if "role" in lowered or "accesscontrol" in lowered:
            tags.add("role")
        if "governor" in lowered or "governance" in lowered or "guardian" in lowered:
            tags.add("governance")
        if "whitelist" in lowered or "allowlist" in lowered:
            tags.add("allowlist")
        if "pauser" in lowered or "pause" in lowered:
            tags.add("pause")
    return sorted(tags)


def is_privileged_state(tags: Iterable[str]) -> bool:
    privileged = {
        "owner",
        "role",
        "governance",
        "upgrade",
        "pause",
        "allowlist",
        "denylist",
        "oracle",
        "treasury",
        "signer",
    }
    return any(tag in privileged for tag in tags)
