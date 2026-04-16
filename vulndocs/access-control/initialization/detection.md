# Detection: Initialization Vulnerabilities

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| is_initializer | true | YES |
| has_initializer_modifier | false | YES |
| visibility | public, external | YES |
| modifies_owner | true | YES |
| writes_privileged_state | true | YES |

## Semantic Operations

**Vulnerable Pattern:**
- `INITIALIZES_STATE` without initializer guard
- `MODIFIES_OWNER` without initialization check
- Multiple `INITIALIZES_STATE` calls possible

**Safe Pattern:**
- `initializer` modifier followed by `INITIALIZES_STATE`
- `reinitializer(version)` for controlled re-initialization
- `initialized` flag check before `INITIALIZES_STATE`

## Behavioral Signatures

- `INITIALIZES_STATE->!G:initializer` - State initialization without guard
- `W:owner->!G:onlyInitializing` - Owner write without initializing check
- `initialize()->!initialized` - Initialize callable when already initialized

## Detection Checklist

1. Function name contains "init" or "initialize"
2. Function sets owner/admin or critical state
3. No `initializer` or `reinitializer` modifier present
4. No manual `initialized` flag check
5. Function is public or external
6. Contract is upgradeable (proxy pattern)
7. Implementation contract can be initialized directly

## False Positive Indicators

- OpenZeppelin `initializer` modifier present
- `reinitializer(version)` for controlled upgrades
- Manual `initialized` check with proper flag
- Function is constructor (non-upgradeable)
- Contract is not behind a proxy
- Implementation contract is disabled post-deployment
