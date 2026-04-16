"""Semgrep-compatible heuristics derived from VKG signals."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


BIDI_CHARS = {
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}


SECURITY_RULES = {
    "accessible-selfdestruct",
    "arbitrary-low-level-call",
    "bad-transferfrom-access-control",
    "balancer-readonly-reentrancy-getpooltokens",
    "balancer-readonly-reentrancy-getrate",
    "basic-arithmetic-underflow",
    "basic-oracle-manipulation",
    "compound-borrowfresh-reentrancy",
    "compound-precision-loss",
    "compound-sweeptoken-not-restricted",
    "curve-readonly-reentrancy",
    "delegatecall-to-arbitrary-address",
    "encode-packed-collision",
    "erc20-public-burn",
    "erc20-public-transfer",
    "erc677-reentrancy",
    "erc721-arbitrary-transferfrom",
    "erc721-reentrancy",
    "erc777-reentrancy",
    "exact-balance-check",
    "gearbox-tokens-path-confusion",
    "incorrect-use-of-blockhash",
    "keeper-network-oracle-manipulation",
    "missing-assignment",
    "msg-value-multicall",
    "no-bidi-characters",
    "no-slippage-check",
    "olympus-dao-staking-incorrect-call-order",
    "openzeppelin-ecdsa-recover-malleable",
    "oracle-price-update-not-restricted",
    "oracle-uses-curve-spot-price",
    "proxy-storage-collision",
    "public-transfer-fees-supporting-tax-tokens",
    "redacted-cartel-custom-approval-bug",
    "rigoblock-missing-access-control",
    "sense-missing-oracle-access-control",
    "superfluid-ctx-injection",
    "tecra-coin-burnfrom-bug",
    "thirdweb-vulnerability",
    "uniswap-callback-not-protected",
    "uniswap-v4-callback-not-protected",
    "unrestricted-transferownership",
}

PERFORMANCE_RULES = {
    "array-length-outside-loop",
    "inefficient-state-variable-increment",
    "init-variables-with-default-value",
    "non-optimal-variables-swap",
    "non-payable-constructor",
    "state-variable-read-in-a-loop",
    "unnecessary-checked-arithmetic-in-loop",
    "use-custom-error-not-require",
    "use-multiple-require",
    "use-nested-if",
    "use-prefix-decrement-not-postfix",
    "use-prefix-increment-not-postfix",
    "use-short-revert-string",
}

CONTRACT_RULES = {
    "no-bidi-characters",
    "proxy-storage-collision",
    "thirdweb-vulnerability",
}


@dataclass(frozen=True)
class FunctionContext:
    name: str
    visibility: str | None
    mutability: str | None
    has_access_gate: bool
    has_reentrancy_guard: bool
    has_user_input: bool
    uses_call: bool
    uses_delegatecall: bool
    has_external_calls: bool
    uses_msg_value: bool
    call_target_user_controlled: bool
    call_data_user_controlled: bool
    call_value_user_controlled: bool
    delegatecall_target_user_controlled: bool
    uses_ecrecover: bool
    uses_block_hash: bool
    reads_state: bool
    reads_dex_reserves: bool
    reads_twap_with_window: bool
    has_slippage_check: bool
    swap_like: bool
    uses_erc20_transfer: bool
    uses_erc20_transfer_from: bool
    uses_erc20_burn: bool
    uses_erc721_safe_transfer: bool
    uses_erc777_send: bool
    uses_erc777_operator_send: bool
    state_write_after_external_call: bool | None
    has_loops: bool
    is_constructor: bool
    payable: bool | None
    writes_state: bool
    parameter_types: list[str]
    require_exprs: list[str]
    source: str


@dataclass(frozen=True)
class ContractContext:
    name: str
    is_proxy_like: bool
    has_storage_gap: bool
    state_var_count: int
    inherits_erc2771: bool
    has_multicall: bool
    has_bidi_chars: bool


def detect_semgrep_contract_rules(ctx: ContractContext) -> set[str]:
    rules: set[str] = set()
    if ctx.has_bidi_chars:
        rules.add("no-bidi-characters")
    if ctx.is_proxy_like and ctx.state_var_count > 0 and not ctx.has_storage_gap:
        rules.add("proxy-storage-collision")
    if ctx.inherits_erc2771 and ctx.has_multicall:
        rules.add("thirdweb-vulnerability")
    return rules


def detect_semgrep_function_rules(ctx: FunctionContext) -> set[str]:
    rules: set[str] = set()
    lowered = _strip_comments(ctx.source).lower()

    if _has_selfdestruct(lowered) and _is_public_without_gate(ctx):
        rules.add("accessible-selfdestruct")

    if ctx.uses_delegatecall and ctx.delegatecall_target_user_controlled and not ctx.has_access_gate:
        rules.add("delegatecall-to-arbitrary-address")

    if ctx.uses_call and (ctx.call_target_user_controlled or ctx.call_data_user_controlled) and not ctx.has_access_gate:
        rules.add("arbitrary-low-level-call")

    if ctx.uses_erc20_transfer_from and not ctx.has_access_gate:
        rules.add("bad-transferfrom-access-control")
        rules.add("redacted-cartel-custom-approval-bug")

    if ctx.uses_erc20_transfer and not ctx.has_access_gate and _name_contains(ctx.name, "transfer"):
        rules.add("erc20-public-transfer")

    if ctx.uses_erc20_burn and not ctx.has_access_gate and _name_contains(ctx.name, "burn"):
        rules.add("erc20-public-burn")
        rules.add("tecra-coin-burnfrom-bug")

    if _matches_transfer_from(lowered) and ctx.has_user_input and not ctx.has_access_gate:
        rules.add("erc721-arbitrary-transferfrom")

    if ctx.uses_erc721_safe_transfer and _reentrancy_risk(ctx):
        rules.add("erc721-reentrancy")

    if (ctx.uses_erc777_send or ctx.uses_erc777_operator_send) and _reentrancy_risk(ctx):
        rules.add("erc777-reentrancy")

    if _matches_erc677(lowered) and _reentrancy_risk(ctx):
        rules.add("erc677-reentrancy")

    if _matches_compound_borrowfresh(lowered) and _reentrancy_risk(ctx):
        rules.add("compound-borrowfresh-reentrancy")

    if _matches_readonly_pool_call(lowered, "get_virtual_price") and _readonly_reentrancy(ctx):
        rules.add("curve-readonly-reentrancy")

    if _matches_readonly_pool_call(lowered, "getrate") and _readonly_reentrancy(ctx):
        rules.add("balancer-readonly-reentrancy-getrate")

    if _matches_readonly_pool_call(lowered, "getpooltokens") and _readonly_reentrancy(ctx):
        rules.add("balancer-readonly-reentrancy-getpooltokens")

    if _is_underflow_risk(lowered, ctx.require_exprs):
        rules.add("basic-arithmetic-underflow")

    if ctx.reads_dex_reserves and not ctx.reads_twap_with_window:
        rules.add("basic-oracle-manipulation")

    if _matches_compound_precision_loss(lowered):
        rules.add("compound-precision-loss")

    if _matches_name(lowered, "sweeptoken") and not ctx.has_access_gate:
        rules.add("compound-sweeptoken-not-restricted")

    if _matches_encode_packed_collision(lowered, ctx.parameter_types):
        rules.add("encode-packed-collision")

    if _matches_exact_balance_check(lowered):
        rules.add("exact-balance-check")

    if _matches_gearbox_path_confusion(lowered):
        rules.add("gearbox-tokens-path-confusion")

    if _matches_incorrect_blockhash(lowered, ctx.uses_block_hash):
        rules.add("incorrect-use-of-blockhash")

    if _matches_keeper_oracle(lowered):
        rules.add("keeper-network-oracle-manipulation")

    if _matches_missing_assignment(ctx.source):
        rules.add("missing-assignment")

    if ctx.uses_msg_value and _matches_multicall(lowered):
        rules.add("msg-value-multicall")

    if ctx.swap_like and not ctx.has_slippage_check:
        rules.add("no-slippage-check")

    if _matches_olympus_call_order(lowered):
        rules.add("olympus-dao-staking-incorrect-call-order")

    if ctx.uses_ecrecover and not _checks_sig_s(ctx.require_exprs):
        rules.add("openzeppelin-ecdsa-recover-malleable")

    if _matches_oracle_update(lowered) and not ctx.has_access_gate:
        rules.add("oracle-price-update-not-restricted")
        rules.add("sense-missing-oracle-access-control")

    if _matches_curve_spot_price(lowered):
        rules.add("oracle-uses-curve-spot-price")

    if _matches_public_transfer_fees(lowered) and not ctx.has_access_gate:
        rules.add("public-transfer-fees-supporting-tax-tokens")

    if _matches_rigoblock_allowance(lowered) and not ctx.has_access_gate:
        rules.add("rigoblock-missing-access-control")

    if _matches_superfluid_ctx(lowered):
        rules.add("superfluid-ctx-injection")

    if _matches_uniswap_callback(lowered) and not ctx.has_access_gate and not _has_msg_sender_guard(ctx.require_exprs):
        rules.add("uniswap-callback-not-protected")

    if _matches_uniswap_v4_callback(lowered) and not ctx.has_access_gate:
        rules.add("uniswap-v4-callback-not-protected")

    if _matches_transfer_ownership(lowered) and not ctx.has_access_gate:
        rules.add("unrestricted-transferownership")

    _apply_performance_rules(ctx, lowered, rules)

    return rules


def _apply_performance_rules(ctx: FunctionContext, lowered: str, rules: set[str]) -> None:
    if ctx.has_loops and ".length" in lowered:
        rules.add("array-length-outside-loop")
        if ctx.reads_state:
            rules.add("state-variable-read-in-a-loop")

    if ctx.writes_state and _matches_state_increment(lowered):
        rules.add("inefficient-state-variable-increment")

    if _matches_default_init(lowered):
        rules.add("init-variables-with-default-value")

    if _matches_temp_swap(lowered):
        rules.add("non-optimal-variables-swap")

    if ctx.is_constructor and not ctx.payable:
        rules.add("non-payable-constructor")

    if ctx.has_loops and "unchecked" not in lowered:
        rules.add("unnecessary-checked-arithmetic-in-loop")

    if _matches_require_with_string(lowered):
        rules.add("use-custom-error-not-require")

    if len(ctx.require_exprs) > 1:
        rules.add("use-multiple-require")

    if lowered.count("if (") > 1 or lowered.count("if(") > 1:
        rules.add("use-nested-if")

    if _matches_postfix(lowered, "++"):
        rules.add("use-prefix-increment-not-postfix")

    if _matches_postfix(lowered, "--"):
        rules.add("use-prefix-decrement-not-postfix")

    if _matches_long_string(lowered):
        rules.add("use-short-revert-string")


def _is_public_without_gate(ctx: FunctionContext) -> bool:
    return (ctx.visibility in {"public", "external"}) and not ctx.has_access_gate


def _reentrancy_risk(ctx: FunctionContext) -> bool:
    if ctx.has_reentrancy_guard:
        return False
    return bool(ctx.state_write_after_external_call)


def _readonly_reentrancy(ctx: FunctionContext) -> bool:
    if ctx.mutability not in {"view", "pure"}:
        return False
    return ctx.has_external_calls


def _has_selfdestruct(lowered: str) -> bool:
    return "selfdestruct(" in lowered or "suicide(" in lowered


def _matches_transfer_from(lowered: str) -> bool:
    return "transferfrom(" in lowered


def _matches_name(lowered: str, token: str) -> bool:
    return token in lowered


def _matches_erc677(lowered: str) -> bool:
    return "transferandcall(" in lowered or "ontokentransfer" in lowered


def _matches_compound_borrowfresh(lowered: str) -> bool:
    return "borrowfresh" in lowered or "dotransferout" in lowered


def _matches_readonly_pool_call(lowered: str, token: str) -> bool:
    return token in lowered


def _is_underflow_risk(lowered: str, require_exprs: Iterable[str]) -> bool:
    if "safemath" in lowered:
        return False
    if "-=" in lowered or "-" in lowered:
        return True
    return any("-" in expr for expr in require_exprs)


def _matches_compound_precision_loss(lowered: str) -> bool:
    return "redeemfresh" in lowered or "collateralfactor" in lowered


def _matches_encode_packed_collision(lowered: str, parameter_types: list[str]) -> bool:
    if "abi.encodepacked" not in lowered:
        return False
    return any("string" in param or "bytes" in param for param in parameter_types)


def _matches_exact_balance_check(lowered: str) -> bool:
    return "==" in lowered and ("balance" in lowered or "balanceof" in lowered)


def _matches_gearbox_path_confusion(lowered: str) -> bool:
    return "path" in lowered and "decode" in lowered and "uniswap" in lowered


def _matches_incorrect_blockhash(lowered: str, uses_block_hash: bool) -> bool:
    if not uses_block_hash:
        return False
    return "blockhash(block.number" in lowered


def _matches_keeper_oracle(lowered: str) -> bool:
    return "keep3r" in lowered or ("current(" in lowered and "oracle" in lowered)


def _matches_missing_assignment(source: str) -> bool:
    cleaned = _strip_comments(source)
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        lowered = stripped.lower()
        if lowered.startswith(("require", "assert")):
            continue
        if re.match(r"^[a-zA-Z0-9_.()]+\s*(==|!=)\s*[^;]+;", stripped):
            return True
    return False


def _matches_multicall(lowered: str) -> bool:
    return "multicall" in lowered or "batch" in lowered


def _matches_olympus_call_order(lowered: str) -> bool:
    if "transferfrom" not in lowered or "rebase" not in lowered:
        return False
    return lowered.find("rebase") < lowered.find("transferfrom")


def _checks_sig_s(require_exprs: Iterable[str]) -> bool:
    for expr in require_exprs:
        lowered = expr.lower()
        if "s" in lowered and ("secp256" in lowered or "0x7f" in lowered or "<=" in lowered):
            return True
    return False


def _matches_oracle_update(lowered: str) -> bool:
    return ("oracle" in lowered and "update" in lowered) or "updateprice" in lowered


def _matches_curve_spot_price(lowered: str) -> bool:
    return "get_p(" in lowered


def _matches_public_transfer_fees(lowered: str) -> bool:
    return "transferfeessupportingtax" in lowered


def _matches_rigoblock_allowance(lowered: str) -> bool:
    return "setmultipleallowances" in lowered


def _matches_superfluid_ctx(lowered: str) -> bool:
    return "ctx" in lowered and "superfluid" in lowered


def _matches_uniswap_callback(lowered: str) -> bool:
    return "uniswapv2call" in lowered or "uniswapv3swapcallback" in lowered


def _matches_uniswap_v4_callback(lowered: str) -> bool:
    callback_tokens = (
        "beforeinitialize",
        "afterinitialize",
        "beforeswap",
        "afterswap",
        "beforeaddliquidity",
        "afteraddliquidity",
        "beforeremoveliquidity",
        "afterremoveliquidity",
        "beforedonate",
        "afterdonate",
    )
    return any(token in lowered for token in callback_tokens)


def _has_msg_sender_guard(require_exprs: Iterable[str]) -> bool:
    for expr in require_exprs:
        lowered = expr.lower()
        if "msg.sender" in lowered or "_msgsender" in lowered:
            return True
    return False


def _matches_transfer_ownership(lowered: str) -> bool:
    return "transferownership" in lowered


def _matches_state_increment(lowered: str) -> bool:
    return "++" in lowered or "+= 1" in lowered


def _matches_default_init(lowered: str) -> bool:
    patterns = ("= 0;", "= false;", "= 0x0;")
    return any(pattern in lowered for pattern in patterns)


def _matches_temp_swap(lowered: str) -> bool:
    return ("tmp" in lowered or "temp" in lowered) and "=" in lowered


def _matches_require_with_string(lowered: str) -> bool:
    return "require(" in lowered and "\"" in lowered


def _matches_postfix(lowered: str, token: str) -> bool:
    return re.search(rf"\w+\s*{re.escape(token)}", lowered) is not None


def _matches_long_string(lowered: str) -> bool:
    for match in re.finditer(r"\"([^\"]+)\"", lowered):
        if len(match.group(1)) > 32:
            return True
    return False


def _strip_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\\*.*?\\*/", "", source, flags=re.DOTALL)
    return source


def _name_contains(name: str, token: str) -> bool:
    return token in (name or "").lower()


def has_bidi_chars(text: str) -> bool:
    return any(ch in BIDI_CHARS for ch in text)
