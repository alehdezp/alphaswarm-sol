# Arithmetic Vulnerability Patterns

## Vulnerable Patterns

### Pattern 1: Unchecked Arithmetic Operations (Pre-0.8.0)

**Vulnerable Code:**
```solidity
// Unchecked subtraction - can underflow
uint256 public balance = 1;
function withdraw(uint256 amount) public {
    balance -= amount;  // VULNERABLE: No SafeMath, no check
}
```

**Operations:** `PERFORMS_ARITHMETIC`, `MODIFIES_STATE`, `NO_OVERFLOW_CHECK`
**Signature:** `R:state->A:unchecked->W:state`

### Pattern 2: Batch Operation Overflow (BEC Token)

**Vulnerable Code:**
```solidity
// BEC Token batchTransfer overflow
function batchTransfer(address[] _receivers, uint256 _value) public {
    uint cnt = _receivers.length;
    uint256 amount = uint256(cnt) * _value;  // OVERFLOW HERE
    require(_value > 0 && balances[msg.sender] >= amount);

    balances[msg.sender] = balances[msg.sender].sub(amount);
    for (uint i = 0; i < cnt; i++) {
        balances[_receivers[i]] = balances[_receivers[i]].add(_value);
    }
}
```

**Attack:** Pass `cnt=2, _value=2^255` to overflow multiplication, bypass balance check
**Operations:** `PERFORMS_ARITHMETIC`, `ITERATES_ARRAY`, `MODIFIES_BALANCES`
**Signature:** `A:mul->O:overflow->C:bypass`

## Safe Patterns

### Pattern 1: SafeMath Library (Pre-0.8.0)

**Safe Code:**
```solidity
using SafeMath for uint256;

uint256 public balance = 1;
function withdraw(uint256 amount) public {
    balance = balance.sub(amount);  // SAFE: SafeMath checks
}
```

**SafeMath Protection:**
```solidity
function sub(uint256 a, uint256 b) internal pure returns (uint256) {
    require(b <= a, "SafeMath: subtraction overflow");
    return a - b;
}

function mul(uint256 a, uint256 b) internal pure returns (uint256) {
    if (a == 0) return 0;
    uint256 c = a * b;
    require(c / a == b, "SafeMath: multiplication overflow");
    return c;
}
```

### Pattern 2: Solidity 0.8.0+ Checked Math

**Safe Code:**
```solidity
// Solidity 0.8.0+ automatically checks for overflow/underflow
uint256 public balance = 1;
function withdraw(uint256 amount) public {
    balance -= amount;  // SAFE: Automatic overflow check, reverts on underflow
}
```

### Pattern 3: Explicit Bounds Checking

**Safe Code:**
```solidity
function batchTransfer(address[] _receivers, uint256 _value) public {
    uint cnt = _receivers.length;
    require(cnt > 0 && cnt <= 20, "Invalid batch size");
    require(_value > 0, "Invalid value");
    require(_value <= type(uint256).max / cnt, "Overflow risk");  // Explicit check

    uint256 amount = uint256(cnt) * _value;
    require(balances[msg.sender] >= amount, "Insufficient balance");

    balances[msg.sender] = balances[msg.sender].sub(amount);
    for (uint i = 0; i < cnt; i++) {
        balances[_receivers[i]] = balances[_receivers[i]].add(_value);
    }
}
```

**Operations:** `CHECKS_OVERFLOW_BEFORE_ARITHMETIC`, `PERFORMS_SAFE_ARITHMETIC`
**Signature:** `C:bounds->A:checked->W:state`
