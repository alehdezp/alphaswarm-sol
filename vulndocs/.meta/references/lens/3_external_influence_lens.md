# External Influence Lens - Ultra-Expanded Detection Patterns

> Comprehensive oracle manipulation, price feed security, and input validation
> vulnerability detection for AlphaSwarm.sol

---

## Table of Contents
1. [Oracle Manipulation](#1-oracle-manipulation)
2. [Price Feed Security](#2-price-feed-security)
3. [TWAP & Oracle Best Practices](#3-twap--oracle-best-practices)
4. [Chainlink Integration Issues](#4-chainlink-integration-issues)
5. [Flash Loan Oracle Attacks](#5-flash-loan-oracle-attacks)
6. [L2 & Cross-Chain Oracle Issues](#6-l2--cross-chain-oracle-issues)
7. [Input Validation - Addresses](#7-input-validation---addresses)
8. [Input Validation - Amounts](#8-input-validation---amounts)
9. [Input Validation - Arrays](#9-input-validation---arrays)
10. [Input Validation - Time & Deadlines](#10-input-validation---time--deadlines)
11. [Calldata & ABI Decoding](#11-calldata--abi-decoding)
12. [External Data Integrity](#12-external-data-integrity)

---

## 1. Oracle Manipulation

### 1.1 Spot Price Manipulation
**CWE-20, CWE-345**

#### Detection Phrases (NL Queries)
```
price calculations using spot reserves from single DEX pool
functions reading price without TWAP or multiple oracle sources
balance or reserve queries in same transaction as swap
oracle price used without staleness check
collateral valuation using manipulable on-chain source
liquidation thresholds computed from single block price
spot price from AMM used for lending decisions
price calculation from getReserves without protection
exchange rate derived from single pool balance
price oracle reading current slot reserves
spot price used for vault share calculation
reserve-based pricing without manipulation protection
price from pool balance used for liquidation
single-block price in collateral valuation
spot exchange rate for position sizing
price derived from token balances in pool
reserve ratio used for swap pricing
spot price for margin requirements
single-source price for loan origination
reserve-based exchange rate for withdrawals
price from AMM without time-weighted average
spot balance ratio for yield calculations
single-pool price for derivative settlement
reserve query for price in same transaction
spot price without multi-source aggregation
pool balance-based pricing for options
single-block exchange rate for staking rewards
reserve-derived price for insurance claims
spot price from DEX for governance weight
balance ratio for cross-chain price bridging
single-source reserve price for arbitrage detection
spot pool price for NFT floor pricing
reserve-based rate for stable swap
single-block price for synthetic asset minting
spot exchange rate for cross-margin
pool reserve price for auto-compounding
single-source spot for stop-loss triggers
reserve ratio for rebalancing decisions
spot price for auction reserve price
single-pool balance for fair value calculation
```

#### Detection Rules
```yaml
rule: spot-price-manipulation
conditions:
  all:
    - function.reads_pool_reserves == true
    - OR:
      - function.has_twap_validation == false
      - function.has_multi_source_oracle == false
    - function.uses_price_for_value_calculation == true
severity: critical
flow_analysis:
  - trace: reserve_query -> value_calculation
    constraint: same_transaction_possible
```

### 1.2 Single Source Oracle Risk
**CWE-345**

#### Detection Phrases
```
oracle price from single data source
price feed without fallback oracle
single provider oracle for critical calculations
oracle without secondary source validation
price from one exchange only
single oracle for liquidation decisions
one data feed for collateral valuation
oracle without cross-reference validation
single source for interest rate oracle
price feed from single DEX
one oracle for synthetic pricing
single data source for index calculation
oracle without redundancy for critical paths
single feed for margin requirements
one source for perpetual funding rate
oracle from single centralized provider
single price feed for option settlement
one oracle source for governance pricing
single data feed for insurance calculations
oracle without backup for critical operations
single source for cross-chain price relay
one feed for stablecoin peg monitoring
single oracle for yield optimization
one price source for auto-liquidation
single data feed for vault rebalancing
oracle without multi-source aggregation
single provider for on-chain index
one oracle for derivative mark price
single source for AMM oracle integration
one feed for lending rate calculation
```

### 1.3 Reserve Manipulation
**CWE-345**

#### Detection Phrases
```
reserves queryable and manipulable in same block
pool reserves used directly for price calculation
getReserves call used for exchange rate
reserve balance affecting price without delay
reserves manipulable via large trade before query
pool balances used for spot pricing
reserve ratio used without historical check
getReserves in price-sensitive calculation
reserves queryable after manipulation in same tx
pool balance ratio for pricing without TWAP
reserve manipulation affecting downstream pricing
getReserves call vulnerable to sandwich
reserves used for pricing without time buffer
pool balances affecting collateral valuation
reserve ratio manipulation via flash swap
getReserves for exchange rate without protection
reserves affecting liquidation price
pool balance query for pricing in swap path
reserve manipulation window before oracle read
getReserves used for vault share pricing
reserves queryable post-manipulation in block
pool balance ratio for synthetic minting
reserve-based price without manipulation delay
getReserves call in same block as attack trade
reserves for pricing without minimum time gap
pool balance used for options pricing
reserve ratio vulnerable to atomic manipulation
getReserves in yield calculation path
reserves affecting governance token pricing
pool balance ratio for insurance pricing
```

---

## 2. Price Feed Security

### 2.1 Stale Price Data
**CWE-672**

#### Detection Phrases
```
Chainlink oracle calls without checking updatedAt timestamp
price feeds used without validating roundId or answeredInRound
oracle responses used without sequencer uptime check on L2
latestAnswer calls without heartbeat validation
oracle price used without freshness check
price feed without timestamp validation
stale oracle data in time-sensitive calculation
oracle response without recency verification
price used beyond acceptable staleness threshold
oracle data without last update check
price feed timestamp not validated
stale price affecting collateral valuation
oracle data used without freshness assertion
price from feed potentially hours old
oracle response without staleness rejection
price feed used without update time check
stale oracle affecting liquidation trigger
price data without heartbeat verification
oracle timestamp not checked against threshold
price feed potentially stale in volatile market
oracle data without maximum age validation
stale price in interest rate calculation
oracle response used without time bound
price feed staleness not enforced
oracle data potentially outdated for trading
stale price affecting position valuation
oracle without configurable staleness threshold
price data freshness not verified
oracle staleness check missing
stale feed price affecting protocol decisions
```

#### Detection Rules
```yaml
rule: stale-oracle-data
conditions:
  all:
    - function.calls_oracle == true
    - function.oracle_type IN [chainlink, custom_oracle]
    - NOT function.validates_oracle_timestamp
    - NOT function.checks_staleness_threshold
severity: high
```

### 2.2 Round Completeness Issues
**CWE-345**

#### Detection Phrases
```
Chainlink round not checked for completion
answeredInRound not compared to roundId
oracle round potentially incomplete
roundId validation missing in oracle call
incomplete round data used for pricing
oracle answer from potentially stale round
round completeness check missing
answeredInRound validation absent
oracle data from incomplete aggregation
roundId comparison not performed
incomplete round affecting price accuracy
oracle answer potentially from wrong round
round validation missing in Chainlink call
answeredInRound check absent
oracle round data not verified complete
roundId not validated for completeness
incomplete aggregation round used
oracle answer from potentially outdated round
round completion not enforced
answeredInRound missing from validation
oracle data integrity not verified via round
roundId freshness not checked
incomplete round price affecting calculations
oracle round not verified current
answeredInRound comparison missing
round completeness validation absent
oracle answer from stale round possible
roundId not checked against answeredInRound
incomplete oracle round not rejected
round validation missing for price feed
```

### 2.3 Zero/Negative Price Handling
**CWE-754**

#### Detection Phrases
```
oracle price not checked for zero value
negative price from oracle not handled
oracle returning zero used in division
price feed zero value causing revert
oracle price without positive assertion
zero oracle price causing calculation error
negative price not rejected from feed
oracle answer zero not filtered
price from feed potentially zero or negative
oracle response without sanity check
zero price affecting collateral calculation
negative oracle value not handled
price feed returning zero used directly
oracle answer not validated positive
zero or negative price in pricing logic
oracle price sanity check missing
negative value from price feed possible
zero oracle response not rejected
price without lower bound validation
oracle answer potentially invalid
zero price causing division by zero
negative oracle price accepted
price feed value not bounded
oracle response zero in calculation path
negative or zero price not rejected
oracle answer without validity check
zero price from stale feed
negative value from oracle in formula
price feed without positive constraint
oracle returning invalid price not caught
```

---

## 3. TWAP & Oracle Best Practices

### 3.1 TWAP Implementation Issues
**CWE-682**

#### Detection Phrases
```
TWAP window too short for manipulation resistance
time-weighted price with insufficient history
TWAP period shorter than block time variance
moving average window manipulable
TWAP observation count insufficient
time-weighted calculation with gaps
TWAP vulnerable to first observation manipulation
moving average with insufficient data points
TWAP window smaller than reasonable attack cost
time-weighted price with single observation vulnerability
TWAP calculation with timestamp manipulation
moving average period too brief
TWAP susceptible to end-point manipulation
time-weighted average with cardinality issues
TWAP vulnerable to observation array manipulation
moving average calculation precision loss
TWAP window not accounting for volatility
time-weighted price with stale observation
TWAP period fixed without market consideration
moving average susceptible to flash loan
TWAP vulnerable to price spike inclusion
time-weighted calculation with overflow
TWAP observation timestamp not verified
moving average with incorrect weighting
TWAP susceptible to manipulation during low volume
time-weighted price without minimum samples
TWAP calculation ignoring price bounds
moving average with gap interpolation issues
TWAP vulnerable to coordinated manipulation
time-weighted average precision insufficient
```

### 3.2 Oracle Aggregation Issues
**CWE-345**

#### Detection Phrases
```
oracle aggregation without outlier rejection
multiple sources without median calculation
oracle aggregation with incorrect weighting
sources aggregated without staleness per-source
oracle combination without deviation check
multiple feeds aggregated incorrectly
oracle sources not cross-validated
aggregation without minimum source count
oracle combination vulnerable to single bad source
sources aggregated without freshness per-feed
oracle aggregation without confidence bounds
multiple sources without proper averaging
oracle combination with single point of failure
aggregation accepting stale from subset
oracle sources with inconsistent decimals in aggregation
multiple feeds combined without normalization
oracle aggregation without sanity bounds
sources combined with incorrect precision
oracle combination susceptible to manipulation of one
aggregation without source health check
oracle sources aggregated without weighting by reliability
multiple feeds without deviation threshold
oracle combination without fallback on disagreement
aggregation not rejecting obvious outliers
oracle sources with different update frequencies aggregated
multiple feeds combined without time alignment
oracle aggregation without minimum agreement
sources aggregated despite large deviation
oracle combination without circuit breaker
aggregation continuing despite source failures
```

### 3.3 Oracle Update Patterns
**CWE-345**

#### Detection Phrases
```
oracle update callable by untrusted parties
price feed update without source validation
oracle setter without access control
price update without sanity bounds
oracle modifiable by non-authorized caller
price feed settable without verification
oracle update without rate limiting
price setter without historical check
oracle update allowing arbitrary values
price feed modification without delay
oracle setter without signature verification
price update without deviation threshold
oracle callable by anyone with valid format
price feed update without timestamp check
oracle modification without proper authorization
price setter without source verification
oracle update without multi-sig requirement
price feed modifiable without time lock
oracle setter without freshness requirement
price update allowing manipulation via rapid calls
oracle modification without proper validation
price feed update rate not limited
oracle setter allowing backdated prices
price update without sequence validation
oracle modification window exploitable
price feed setter without proper guards
oracle update without cross-reference check
price modification without proper authority
oracle setter vulnerable to front-running
price feed update without proper sequencing
```

---

## 4. Chainlink Integration Issues

### 4.1 latestRoundData Validation
**CWE-345, CWE-252**

#### Detection Phrases
```
latestRoundData called without full validation
Chainlink response not checking all return values
latestRoundData answer used without roundId check
oracle call missing answeredInRound validation
latestRoundData without updatedAt verification
Chainlink feed without startedAt check
latestRoundData price without staleness validation
oracle response used without round validation
latestRoundData without proper error handling
Chainlink call missing complete validation
latestRoundData answer assumed valid
oracle response without freshness checks
latestRoundData without zero price check
Chainlink feed used without all validations
latestRoundData roundId not compared
oracle call without answeredInRound check
latestRoundData potentially returning stale
Chainlink response without round completeness
latestRoundData used without try-catch
oracle call missing updatedAt validation
latestRoundData without negative check
Chainlink feed without timestamp bounds
latestRoundData answer used directly
oracle response freshness not verified
latestRoundData without sanity checks
Chainlink call without staleness threshold
latestRoundData potentially zero answer
oracle response without positive assertion
latestRoundData missing standard validations
Chainlink feed without proper checks
```

#### Detection Rules
```yaml
rule: chainlink-validation
conditions:
  all:
    - function.calls_chainlink_latest_round_data == true
    - any_missing:
      - validates_answer_positive
      - validates_updatedAt_recent
      - validates_answeredInRound_matches_roundId
      - handles_revert
severity: high
```

### 4.2 Chainlink Decimals Handling
**CWE-682**

#### Detection Phrases
```
Chainlink decimals not queried dynamically
oracle price assumed 8 decimals
Chainlink feed decimals hardcoded
price scaling with wrong decimal assumption
oracle answer not adjusted for decimals
Chainlink price used without decimal conversion
feed decimals not fetched from contract
price calculation with incorrect scaling
oracle response not normalized for decimals
Chainlink answer assumed fixed precision
feed price used without decimal adjustment
oracle decimals hardcoded as constant
Chainlink response not scaled correctly
price with mismatched decimal handling
oracle answer precision not verified
Chainlink feed decimal mismatch
price calculation with hardcoded decimals
oracle response scaled incorrectly
Chainlink price without proper normalization
feed answer with wrong decimal assumption
oracle decimals not checked at runtime
Chainlink response precision incorrect
price scaling hardcoded for one feed
oracle answer decimal handling wrong
Chainlink feed without decimals() call
price with incorrect precision adjustment
oracle response not properly scaled
Chainlink answer precision assumed
feed price decimal conversion incorrect
oracle decimals fixed in code
```

### 4.3 Feed Deprecation Handling
**CWE-672**

#### Detection Phrases
```
Chainlink feed address hardcoded
oracle feed not updateable post-deprecation
Chainlink price without feed migration path
feed address immutable after deployment
oracle using potentially deprecated feed
Chainlink feed without replacement mechanism
price feed hardcoded without upgrade path
oracle feed deprecation not handled
Chainlink address not configurable
feed replacement requiring contract upgrade
oracle without feed address setter
Chainlink feed immutable in storage
price feed update requiring proxy upgrade
oracle feed migration not supported
Chainlink address without admin setter
feed replacement mechanism absent
oracle feed deprecation awareness missing
Chainlink feed without fallback
price feed hardcoded with no update
oracle without deprecated feed handling
Chainlink address upgrade path missing
feed deprecation causing permanent failure
oracle feed not migratable
Chainlink feed update not supported
price feed replacement not implemented
oracle without feed health monitoring
Chainlink deprecation causing oracle failure
feed address change not possible
oracle feed stuck on deprecated source
Chainlink migration path not designed
```

### 4.4 Sequencer Uptime (L2)
**CWE-345**

#### Detection Phrases
```
L2 oracle without sequencer uptime check
Chainlink on L2 without sequencer feed
oracle price on L2 without uptime validation
sequencer status not checked before oracle use
L2 price feed without sequencer health check
oracle on Arbitrum/Optimism without uptime feed
sequencer uptime feed not integrated
L2 oracle price potentially stale after downtime
sequencer grace period not implemented
oracle on L2 without sequencer validation
sequencer downtime not accounted for
L2 price feed used without uptime check
oracle price valid during sequencer outage
sequencer status feed not checked
L2 oracle without downtime protection
sequencer uptime validation missing
oracle on rollup without sequencer check
L2 price feed during sequencer recovery
sequencer grace period not enforced
oracle potentially stale post-sequencer-restart
L2 without sequencer uptime integration
sequencer status not validated
oracle on L2 without proper uptime handling
sequencer downtime price staleness
L2 oracle missing sequencer feed check
sequencer recovery window not implemented
oracle price on L2 after outage not validated
sequencer uptime feed missing
L2 price feed without proper L2 checks
sequencer status ignored in oracle usage
```

---

## 5. Flash Loan Oracle Attacks

### 5.1 Flash Loan Price Manipulation
**CWE-362**

#### Detection Phrases
```
balance checks vulnerable to flash loan inflation
governance votes weighted by token balance in single block
reward calculations based on instantaneous liquidity
price derived from reserves that can be manipulated atomically
flash loan enabling instant balance inflation
token balance-based pricing vulnerable to flash manipulation
governance weight from balance exploitable via flash loan
reward rate from balance manipulable atomically
price oracle vulnerable to flash loan balance manipulation
instantaneous balance for voting weight
flash-inflatable balance affecting calculations
token balance governance weight exploitable
reserve-based price flash loan attackable
balance-weighted voting via flash loan
instant liquidity manipulation affecting price
flash loan balance inflation for rewards
governance power via flash borrowed tokens
reserve manipulation via flash loan for pricing
balance-based calculations vulnerable to atomic attack
flash loan enabling instant governance influence
price manipulation via flash loan reserves
token balance voting flash loan exploitable
reserve-based oracle flash loan vulnerable
governance via flash loan borrowed tokens
instant balance inflation affecting price feed
flash loan price manipulation surface
balance-weighted rewards exploitable atomically
reserve manipulation for oracle attack via flash loan
governance weight inflation via flash loan
price derived from flash-manipulable source
```

#### Detection Rules
```yaml
rule: flash-loan-price-manipulation
conditions:
  all:
    - function.reads_balance_or_reserves == true
    - function.balance_used_for_pricing_or_voting == true
    - NOT function.has_flash_loan_guard
    - NOT function.uses_historical_snapshot
severity: critical
```

### 5.2 Flash Loan Governance Attacks
**CWE-362**

#### Detection Phrases
```
governance votes countable during flash loan
voting power from current balance exploitable
governance quorum achievable via flash loan
proposal execution during flash loan window
voting weight from token balance not snapshot
governance manipulation via borrowed voting power
quorum reached with flash borrowed tokens
proposal vote counting current balance
governance attack via flash loan voting power
voting power inflatable via flash loan
quorum manipulation via flash borrowed tokens
governance proposal passable with flash loan
vote weight from balance not historical
governance voting flash loan vulnerable
quorum achievable via atomic borrowing
proposal outcome manipulable via flash loan
voting power not snapshot-based exploitable
governance decision via flash borrowed power
quorum threshold reachable via flash loan
proposal execution with flash loan votes
governance weight from current balance
voting manipulation via flash borrowed tokens
quorum artificial via flash loan
governance attack during voting window
vote counting vulnerable to flash loan
proposal passage via borrowed voting power
governance quorum flash loan achievable
voting weight manipulation via flash loan
quorum reached via atomic balance inflation
governance outcome determined by flash loan
```

### 5.3 Flash Loan Collateral Attacks
**CWE-362**

#### Detection Phrases
```
collateral valuation from current balance
flash loan collateral deposit for instant leverage
collateral ratio from spot balance exploitable
lending collateral from flash-inflatable source
collateral value from manipulable reserves
flash loan collateral attack surface
instant collateral via flash loan deposit
collateral ratio manipulation via flash loan
lending position from flash borrowed collateral
collateral valuation vulnerable to flash inflation
flash loan collateral for overcollateralization
instant leverage via flash collateral deposit
collateral health from current balance
flash loan enabling artificial collateralization
collateral ratio from flash-manipulable price
lending attack via flash loan collateral
instant collateral deposit and borrow
collateral valuation from reserves vulnerable
flash loan collateral manipulation
artificial collateral via flash loan
instant leverage via flash borrowed assets
collateral health check exploitable via flash loan
lending overcollateralization via flash loan
collateral value from atomic manipulation
flash loan collateral for liquidation avoidance
instant collateral position via flash loan
collateral ratio from manipulated reserves
lending attack via artificial collateral
flash loan enabling undercollateralized borrow
collateral valuation atomic manipulation
```

---

## 6. L2 & Cross-Chain Oracle Issues

### 6.1 Cross-Chain Price Consistency
**CWE-345**

#### Detection Phrases
```
cross-chain price without source verification
L2 oracle price not validated against L1
bridge price feed without consistency check
cross-chain price potentially stale or wrong
oracle price bridged without verification
L2 price feed divergence not detected
cross-chain oracle without source validation
bridge price without freshness on destination
oracle price across chains not reconciled
L2 price potentially outdated vs L1
cross-chain price relay without proof
bridge oracle without consistency validation
cross-chain price divergence not handled
L2 oracle potentially stale vs mainnet
price bridge without verification mechanism
cross-chain oracle relay vulnerable
L2 price consistency not validated
bridge price without source chain check
cross-chain price without timestamp comparison
oracle bridged without proper validation
L2 price feed without L1 verification
cross-chain price relay exploitable
bridge oracle consistency not ensured
price across chains potentially divergent
cross-chain oracle without reconciliation
L2 price validity not verified
bridge price freshness not checked
cross-chain price without proof verification
oracle price bridged without validation
L2 vs L1 price consistency not checked
```

### 6.2 L2 Specific Vulnerabilities
**CWE-345**

#### Detection Phrases
```
L2 block timestamp potentially manipulable
rollup oracle without proper L1 anchoring
L2 price feed during reorg window
sequencer-dependent oracle without fallback
L2 timestamp assumptions incorrect
rollup block time variance not accounted
L2 oracle during challenge period
sequencer timestamp manipulation possible
L2 price during fraud proof window
rollup oracle finality not considered
L2 timestamp reliability assumptions
sequencer uptime affecting oracle freshness
L2 oracle price during soft finality
rollup block production variance
L2 timestamp manipulation by sequencer
sequencer-controlled timestamp affecting oracle
L2 oracle during potential reorg
rollup finality not considered for oracle
L2 block time assumptions for oracle
sequencer timestamp affecting price freshness
L2 oracle validity during challenge
rollup timestamp manipulation surface
L2 price feed finality assumptions
sequencer downtime oracle implications
L2 block timestamp reliability
rollup oracle during potential rollback
L2 timestamp for oracle staleness check
sequencer-dependent oracle reliability
L2 price during state transition
rollup oracle finality considerations
```

### 6.3 Bridge Oracle Security
**CWE-345**

#### Detection Phrases
```
bridge oracle without message verification
cross-chain price relay without proof
bridge oracle relayer trust assumptions
cross-chain oracle without source validation
bridge price without authenticity proof
oracle message bridge without verification
cross-chain price without merkle proof
bridge oracle message replay possible
cross-chain oracle without nonce
bridge price relay without sequencing
oracle bridge without proper authorization
cross-chain price message tamperable
bridge oracle without consensus verification
cross-chain oracle susceptible to relayer attack
bridge price without source chain proof
oracle message bridge unauthorized
cross-chain price replay possible
bridge oracle without proper validation
cross-chain oracle message integrity
bridge price relayer manipulation
oracle bridge susceptible to front-running
cross-chain price without ordering guarantee
bridge oracle finality not ensured
cross-chain oracle susceptible to reorg
bridge price without confirmation depth
oracle message bridge vulnerable
cross-chain price message validation missing
bridge oracle authorization insufficient
cross-chain oracle without replay protection
bridge price integrity not verified
```

---

## 7. Input Validation - Addresses

### 7.1 Zero Address Validation
**CWE-20**

#### Detection Phrases
```
functions accepting address parameters without zero-address check
address parameter used without validation against address(0)
recipient address not checked for zero
token transfer to address without zero validation
address input without null check
function parameter address(0) not rejected
recipient not validated before transfer
address parameter allowing zero address
token send without zero address check
function accepting address without validation
recipient zero address not caught
address input zero not rejected
token recipient without zero check
function parameter null address accepted
recipient address validation missing
address(0) not checked on input
token transfer address not validated
function address parameter without require
recipient zero address possible
address input without existence check
token to address without validation
function address zero not rejected
recipient without zero address validation
address parameter null check missing
token transfer null recipient possible
function accepting null address
recipient address not requiring non-zero
address(0) check missing
token to zero address possible
function parameter address not validated
```

#### Detection Rules
```yaml
rule: zero-address-check
conditions:
  all:
    - function.accepts_address_parameter == true
    - address_parameter.used_for_transfer == true
    - NOT function.validates_address_nonzero
severity: medium
```

### 7.2 Contract Address Validation
**CWE-20**

#### Detection Phrases
```
address parameter not checked for contract existence
target address extcodesize not validated
contract address accepted without code check
address used for call without contract verification
external call target without existence validation
contract address parameter not verified
target not checked for deployed contract
address for delegatecall without code check
external interaction without contract validation
target address assumed to be contract
contract existence not verified before call
address parameter contract status not checked
target extcodesize check missing
contract address without deployment verification
address for call assumed to have code
external call without target validation
contract parameter without code existence check
target address without contract verification
address used for interaction not validated
external call target code check missing
contract address existence not ensured
target not verified as deployed contract
address parameter without isContract check
external interaction target not validated
contract code existence not verified
target address assumed deployed
address for external call not validated
contract verification missing on address
target without extcodesize validation
address parameter contract not verified
```

### 7.3 Address Collision/Confusion
**CWE-20**

#### Detection Phrases
```
address parameter confused between EOA and contract
self-address check missing for critical operations
address parameter allowing this address incorrectly
address(this) comparison missing in validation
contract self-call not properly rejected
address parameter allowing self-reference
this address confusion in authorization
address allowing contract self-interaction incorrectly
self-address in critical path not checked
address parameter without self-rejection
contract address(this) not filtered
address allowing self-referential operation
this address not rejected in validation
address confusion allowing self-call
contract self-address not properly checked
address parameter self-reference possible
this check missing in address validation
address allowing contract self-referencing
self-address possible in address parameter
address(this) in input not rejected
contract self-reference not validated
address confusion between self and external
this address filtering missing
address parameter allowing self incorrectly
contract address confusion
self-address not checked in function
address parameter accepting address(this)
contract self-call possible via parameter
this address not filtered from input
address validation self-exclusion missing
```

---

## 8. Input Validation - Amounts

### 8.1 Amount Bounds Validation
**CWE-20**

#### Detection Phrases
```
amount parameters used in transfers without sanity checks
percentage or basis point inputs without max value validation
amount parameter used without minimum check
value input without upper bound validation
amount accepted without range verification
quantity parameter without bounds check
value input exceeding reasonable limits possible
amount without maximum validation
quantity accepted without upper bound
value parameter without minimum requirement
amount input bounds not enforced
quantity without range check
value accepted without sanity validation
amount parameter minimum not enforced
quantity input without maximum limit
value without reasonable bounds
amount accepted without validation
quantity parameter bounds missing
value input without range enforcement
amount without upper limit check
quantity accepted without minimum
value parameter without bounds validation
amount input maximum not checked
quantity without limit enforcement
value accepted beyond reasonable range
amount parameter without validation
quantity input without bounds
value without minimum or maximum check
amount bounds validation missing
quantity parameter without range
```

### 8.2 Zero Amount Handling
**CWE-20**

#### Detection Phrases
```
amount parameter allowing zero value
zero amount transfer not rejected
quantity zero not checked
value input zero accepted
amount zero in financial calculation
zero transfer amount possible
quantity parameter zero allowed
value zero not rejected
amount zero causing incorrect calculation
zero amount in reward distribution
quantity zero accepted without check
value parameter zero possible
amount zero in share calculation
zero transfer not validated
quantity zero not rejected
value zero accepted in calculation
amount zero in fee computation
zero amount in division denominator
quantity zero causing calculation error
value zero not checked before division
amount zero in percentage calculation
zero quantity accepted
value zero possible in formula
amount zero not rejected
zero amount in accounting operation
quantity zero without validation
value parameter zero allowed
amount zero in rate calculation
zero amount possible in operation
quantity zero not validated
```

### 8.3 Amount Manipulation
**CWE-682**

#### Detection Phrases
```
amount calculation with precision loss
user amount input affecting fee calculation
amount manipulation via rounding exploitation
value input affecting share calculation incorrectly
amount calculation vulnerable to manipulation
user amount in precision-sensitive formula
value manipulation via input amount
amount affecting calculation with rounding
user input amount in vulnerable calculation
value amount precision exploitation
amount input affecting rate calculation
user amount manipulating output value
value calculation with amount manipulation
amount in formula with precision issues
user input affecting calculated amount
value amount manipulation surface
amount calculation exploitable via input
user amount in rounding-sensitive operation
value manipulation via crafted amount
amount input affecting precision-sensitive math
user amount exploiting calculation
value amount in manipulable formula
amount calculation vulnerable to gaming
user input amount affecting outcome
value manipulation via amount crafting
amount in calculation with gaming potential
user amount affecting fee or reward
value amount calculation exploitable
amount input in vulnerable formula path
user amount manipulation potential
```

---

## 9. Input Validation - Arrays

### 9.1 Array Length Validation
**CWE-119, CWE-400**

#### Detection Phrases
```
array length parameters used without bounds validation
unbounded array length in loop
array size not limited on input
length parameter without maximum check
array input length not validated
size parameter allowing DoS via large array
array length without upper bound
length input causing gas exhaustion
array size parameter not limited
length validation missing on array input
array length in loop without bound
size input without maximum validation
array parameter length unchecked
length allowing excessive iteration
array size without limit enforcement
length parameter enabling gas attack
array input without size validation
length without reasonable maximum
array parameter unbounded
length input not checked for limit
array size enabling loop DoS
length parameter without validation
array input length manipulation
size without upper bound check
array length gas limit issue
length parameter allowing large arrays
array size validation missing
length enabling iteration DoS
array input size unchecked
length without gas consideration
```

### 9.2 Array Index Validation
**CWE-119**

#### Detection Phrases
```
array access at user-provided index without bounds check
index parameter without array length validation
array index from input not validated
user-controlled index without bounds check
array access index unchecked
index input allowing out-of-bounds
array index parameter not validated
user index without length comparison
array access bounds check missing
index input allowing invalid access
array index validation absent
user-provided index unchecked
array access without index validation
index parameter without bounds
array index from user not checked
index allowing out-of-bounds access
array index input validation missing
user index without array bounds
array access user index unchecked
index input not validated against length
array index bounds missing
user-controlled array index
array access without bounds validation
index parameter unchecked
array index from input unchecked
user index array access
array access index not validated
index without bounds comparison
array index user input
access at unvalidated index
```

### 9.3 Array Length Mismatch
**CWE-119**

#### Detection Phrases
```
multiple arrays without length matching check
paired arrays with different lengths accepted
array length mismatch not validated
multiple array inputs without length comparison
paired array parameters length not matched
arrays of different lengths accepted
length mismatch between input arrays
multiple arrays without equal length check
paired arrays length validation missing
array inputs without matching lengths
length comparison between arrays missing
multiple array lengths not validated
paired input arrays mismatch possible
arrays without length equality check
length of multiple arrays not compared
paired arrays without length match
array mismatch in batch operation
multiple arrays length not ensured equal
paired parameters without length check
arrays in batch without length validation
length mismatch possible in arrays
multiple array inputs mismatch
paired arrays length not verified
array length equality not enforced
multiple arrays without length assertion
paired array lengths not matched
batch arrays without length check
multiple array parameters mismatch
paired inputs length not validated
arrays without matching length requirement
```

---

## 10. Input Validation - Time & Deadlines

### 10.1 Deadline Validation
**CWE-20**

#### Detection Phrases
```
deadline parameters without minimum or maximum bounds
deadline accepting past timestamp
expiry parameter without current time check
deadline not validated against block.timestamp
deadline allowing already expired value
expiry input without minimum future check
deadline accepting zero or very small value
deadline parameter without sanity bounds
expiry not checked for reasonable future
deadline allowing manipulation via past time
deadline input without minimum validation
expiry parameter accepting expired value
deadline not requiring future timestamp
deadline accepting block.timestamp directly
expiry input without proper validation
deadline parameter past time possible
deadline not enforced as future time
expiry accepting current or past timestamp
deadline input without reasonable bounds
deadline parameter not validated
expiry not checked against current time
deadline allowing immediate expiry
deadline input accepting past
expiry parameter without time check
deadline not requiring minimum buffer
deadline accepting expired timestamp
expiry input allowing zero
deadline parameter without future requirement
deadline validation missing
expiry not validated for futurity
```

### 10.2 Time-Based Input Issues
**CWE-20**

#### Detection Phrases
```
duration parameter without reasonable bounds
lock period accepting very short duration
vesting time without minimum validation
duration allowing instant completion
time period parameter without sanity check
lock duration accepting zero
vesting period without minimum requirement
duration input without reasonable minimum
time lock accepting bypassed duration
period parameter without lower bound
duration allowing immediate unlock
time period zero accepted
lock duration without minimum validation
vesting time accepting instant completion
duration parameter minimum not enforced
time lock zero duration possible
period input without reasonable bounds
duration accepting unreasonable values
time period minimum not validated
lock period allowing bypass
duration without sensible bounds
time parameter accepting zero
period duration minimum missing
lock time accepting instant unlock
duration input validation missing
time period without lower bound
lock duration zero possible
vesting period zero accepted
duration bounds not enforced
time parameter without minimum
```

---

## 11. Calldata & ABI Decoding

### 11.1 Calldata Validation
**CWE-20**

#### Detection Phrases
```
calldata slicing without length validation
user calldata decoded without bounds check
calldata length not validated before decode
raw calldata used without validation
calldata slice without length verification
user calldata accepted without validation
calldata length check missing
raw calldata decoded unsafely
calldata slice potentially out of bounds
user calldata without bounds verification
calldata length not checked before use
raw calldata slice unsafe
calldata without minimum length check
user calldata length not validated
calldata slice without safety check
raw calldata length assumption
calldata validation missing
user calldata bounds not checked
calldata slice length not verified
raw calldata used directly
calldata minimum length not enforced
user calldata without validation
calldata slice unsafe access
raw calldata length not checked
calldata bounds check missing
user calldata length assumption
calldata slice without validation
raw calldata without bounds check
calldata length validation absent
user calldata slice unsafe
```

### 11.2 ABI Decode Safety
**CWE-20**

#### Detection Phrases
```
abi.decode without try-catch wrapper
abi decoding assuming valid data format
decode operation without error handling
abi.decode on potentially malformed data
decoding without length verification
abi.decode without validation
decode operation assuming success
abi decoding without try-catch
decode on user data without check
abi.decode potentially reverting
decoding without proper error handling
abi.decode on untrusted data
decode without format validation
abi decoding reverts not caught
decode operation without safety
abi.decode without bounds check
decoding potentially failing on malformed
abi.decode assuming valid format
decode without proper validation
abi decoding without error catch
decode on arbitrary data unsafe
abi.decode reverts not handled
decoding without data validation
abi.decode on user bytes
decode potentially panicking
abi decoding unsafe
decode without try wrapper
abi.decode on malformed possible
decoding reverts not caught
abi.decode safety missing
```

---

## 12. External Data Integrity

### 12.1 External Data Validation
**CWE-345**

#### Detection Phrases
```
external data used without integrity check
off-chain data accepted without signature
external input without proof validation
data from external source without verification
off-chain value without authenticity check
external data without source validation
input from off-chain without signature
data integrity not verified for external
off-chain data without proof
external input authenticity not checked
data from source without validation
off-chain input without verification
external data source not authenticated
input authenticity not verified
data from external without integrity check
off-chain value without signature validation
external source data unverified
input from outside without proof
data integrity for external missing
off-chain data source not validated
external input without integrity
data authenticity not checked
off-chain value unverified
external data without validation
input source not authenticated
data from off-chain unverified
external source without integrity check
input authenticity missing
data validation for external absent
off-chain source not verified
```

### 12.2 Merkle Proof Validation
**CWE-345**

#### Detection Phrases
```
merkle proof without proper leaf hashing
proof validation with incorrect leaf format
merkle proof leaf collision possible
proof verification without domain separation
merkle leaf same format as internal node
proof validation vulnerable to second preimage
merkle proof without proper hashing
proof leaf format not separated from internal
merkle verification leaf collision risk
proof validation without leaf tagging
merkle proof format vulnerability
proof verification leaf node collision
merkle leaf without domain separator
proof validation internal node collision
merkle proof second preimage risk
proof verification without proper leaf format
merkle leaf format collision possible
proof validation vulnerable to manipulation
merkle proof without leaf distinction
proof verification format vulnerability
merkle leaf internal node same format
proof validation leaf collision risk
merkle proof vulnerable to collision
proof verification without domain separation
merkle leaf format not properly tagged
proof validation second preimage vulnerability
merkle proof internal collision risk
proof verification leaf format unsafe
merkle validation without proper hashing
proof leaf internal format collision
```

---

## Complex Query Examples for External Influence Lens

### Query 1: Oracle Manipulation Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "reads_pool_reserves", "op": "eq", "value": true},
      {"property": "uses_price_for_calculation", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_twap_validation", "op": "eq", "value": true},
      {"property": "has_multi_source_oracle", "op": "eq", "value": true},
      {"property": "has_flash_loan_guard", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Chainlink Integration Issues
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "calls_chainlink_oracle", "op": "eq", "value": true}
    ],
    "any_missing": [
      {"property": "validates_oracle_timestamp"},
      {"property": "validates_round_completeness"},
      {"property": "validates_positive_price"},
      {"property": "handles_oracle_revert"}
    ]
  },
  "explain_mode": true
}
```

### Query 3: Input Validation Gaps
```json
{
  "query_kind": "flow",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]}
    ]
  },
  "flow": {
    "from_kinds": ["parameter"],
    "target_type": "StateVariable",
    "constraints": {
      "no_validation_between": true
    }
  },
  "explain_mode": true
}
```

### Query 4: Flash Loan Vulnerability Surface
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "any": [
      {"property": "reads_token_balance", "op": "eq", "value": true},
      {"property": "reads_pool_reserves", "op": "eq", "value": true}
    ],
    "all": [
      {"property": "uses_for_pricing_or_voting", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "uses_snapshot", "op": "eq", "value": true},
      {"property": "has_flash_loan_protection", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: External Influence Lens Complete

```yaml
# Save as patterns/external-influence-lens.yaml
patterns:
  - id: ext-001
    name: Spot Price Manipulation
    severity: critical
    cwe: [20, 345]

  - id: ext-002
    name: Stale Oracle Data
    severity: high
    cwe: [672]

  - id: ext-003
    name: Chainlink Incomplete Validation
    severity: high
    cwe: [345]

  - id: ext-004
    name: Flash Loan Price Attack
    severity: critical
    cwe: [362]

  - id: ext-005
    name: L2 Sequencer Uptime Missing
    severity: high
    cwe: [345]

  - id: ext-006
    name: Missing Zero Address Check
    severity: medium
    cwe: [20]

  - id: ext-007
    name: Missing Amount Bounds
    severity: medium
    cwe: [20]

  - id: ext-008
    name: Array Length Manipulation
    severity: high
    cwe: [119, 400]

  - id: ext-009
    name: Deadline Validation Missing
    severity: medium
    cwe: [20]

  - id: ext-010
    name: Unsafe ABI Decode
    severity: medium
    cwe: [20]

  - id: ext-011
    name: Merkle Proof Leaf Collision
    severity: high
    cwe: [345]

  - id: ext-012
    name: Single Source Oracle
    severity: high
    cwe: [345]
```
