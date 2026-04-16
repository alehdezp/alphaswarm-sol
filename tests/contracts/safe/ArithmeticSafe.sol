// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ArithmeticSafe
 * @notice Safe implementations of arithmetic patterns.
 * @dev These contracts demonstrate proper arithmetic handling.
 */

/**
 * @title DivisionSafe
 * @notice Safe: Division with zero-check and precision handling
 */
contract DivisionSafe {
    uint256 public constant PRECISION = 1e18;

    // SAFE: Check for division by zero
    function safeDivide(uint256 a, uint256 b) public pure returns (uint256) {
        require(b > 0, "Division by zero");
        return a / b;
    }

    // SAFE: Division with precision scaling to avoid truncation
    function divideWithPrecision(uint256 a, uint256 b) public pure returns (uint256) {
        require(b > 0, "Division by zero");
        // Scale up before division, then scale back
        return (a * PRECISION) / b;
    }

    // SAFE: Multiply before divide to minimize precision loss
    function calculateRate(uint256 amount, uint256 numerator, uint256 denominator) public pure returns (uint256) {
        require(denominator > 0, "Division by zero");
        // Multiply first, then divide
        return (amount * numerator) / denominator;
    }

    // SAFE: Round up division for safety
    function divideRoundUp(uint256 a, uint256 b) public pure returns (uint256) {
        require(b > 0, "Division by zero");
        return (a + b - 1) / b;
    }
}

/**
 * @title MultiplicationSafe
 * @notice Safe: Multiplication with overflow protection (built-in in Solidity 0.8+)
 */
contract MultiplicationSafe {
    uint256 public constant MAX_MULTIPLIER = 1e18;

    // SAFE: Solidity 0.8+ has built-in overflow protection
    function safeMultiply(uint256 a, uint256 b) public pure returns (uint256) {
        return a * b; // Will revert on overflow
    }

    // SAFE: Check before multiply for custom bounds
    function boundedMultiply(uint256 a, uint256 b) public pure returns (uint256) {
        require(a <= MAX_MULTIPLIER, "Multiplier too large");
        require(b <= MAX_MULTIPLIER, "Multiplicand too large");
        return a * b;
    }

    // SAFE: Scale multiplication to avoid intermediate overflow
    function scaledMultiply(uint256 a, uint256 b, uint256 scale) public pure returns (uint256) {
        require(scale > 0, "Scale is zero");
        // Divide by scale to prevent overflow
        return (a / scale) * b;
    }
}

/**
 * @title UncheckedBlockSafe
 * @notice Safe: Unchecked blocks with explicit bounds checking
 */
contract UncheckedBlockSafe {
    // SAFE: Bounds checked before unchecked block
    function incrementWithBounds(uint256 value, uint256 max) public pure returns (uint256) {
        require(value < max, "Would overflow");

        unchecked {
            return value + 1;
        }
    }

    // SAFE: Decrement only when positive
    function decrementSafe(uint256 value) public pure returns (uint256) {
        require(value > 0, "Would underflow");

        unchecked {
            return value - 1;
        }
    }

    // SAFE: Loop counter optimization with bounds
    function sumArray(uint256[] calldata arr) public pure returns (uint256) {
        uint256 sum = 0;
        uint256 length = arr.length;

        for (uint256 i = 0; i < length;) {
            sum += arr[i]; // Will revert on overflow

            unchecked {
                ++i; // Safe: i < length is checked
            }
        }

        return sum;
    }
}

/**
 * @title PrecisionLossSafe
 * @notice Safe: Handle precision loss correctly
 */
contract PrecisionLossSafe {
    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS = 10000;

    // SAFE: Scale to higher precision first
    function calculateFee(uint256 amount, uint256 feeBps) public pure returns (uint256) {
        require(feeBps <= BPS, "Fee too high");
        // Multiply first to preserve precision
        return (amount * feeBps) / BPS;
    }

    // SAFE: Use full precision for intermediate calculations
    function calculateShare(
        uint256 userAmount,
        uint256 totalAmount,
        uint256 totalShares
    ) public pure returns (uint256) {
        require(totalAmount > 0, "Division by zero");

        // Scale up for precision
        uint256 userShare = (userAmount * PRECISION) / totalAmount;

        // Apply to total shares
        return (userShare * totalShares) / PRECISION;
    }

    // SAFE: Round in favor of protocol
    function calculateWithdraw(
        uint256 shares,
        uint256 totalShares,
        uint256 totalAssets
    ) public pure returns (uint256) {
        require(totalShares > 0, "No shares");

        // Round down (favor protocol)
        return (shares * totalAssets) / totalShares;
    }
}

/**
 * @title ArrayBoundsSafe
 * @notice Safe: Array bounds checking
 */
contract ArrayBoundsSafe {
    uint256[] public values;

    function addValue(uint256 value) external {
        values.push(value);
    }

    // SAFE: Explicit bounds check
    function getValue(uint256 index) external view returns (uint256) {
        require(index < values.length, "Index out of bounds");
        return values[index];
    }

    // SAFE: Check both start and end
    function getSlice(uint256 start, uint256 end) external view returns (uint256[] memory) {
        require(start < values.length, "Start out of bounds");
        require(end <= values.length, "End out of bounds");
        require(start < end, "Invalid range");

        uint256[] memory slice = new uint256[](end - start);
        for (uint256 i = start; i < end; i++) {
            slice[i - start] = values[i];
        }
        return slice;
    }

    // SAFE: Validate matching array lengths
    function processPairs(
        uint256[] calldata keys,
        uint256[] calldata vals
    ) external pure returns (uint256) {
        require(keys.length == vals.length, "Length mismatch");

        uint256 sum = 0;
        for (uint256 i = 0; i < keys.length; i++) {
            sum += keys[i] * vals[i];
        }
        return sum;
    }
}

/**
 * @title PercentageSafe
 * @notice Safe: Percentage calculations
 */
contract PercentageSafe {
    uint256 public constant PERCENT_DIVISOR = 100;
    uint256 public constant BPS_DIVISOR = 10000;

    // SAFE: Validate percentage range
    function applyPercentage(uint256 amount, uint256 percent) external pure returns (uint256) {
        require(percent <= 100, "Invalid percentage");
        return (amount * percent) / PERCENT_DIVISOR;
    }

    // SAFE: Use basis points for higher precision
    function applyBps(uint256 amount, uint256 bps) external pure returns (uint256) {
        require(bps <= BPS_DIVISOR, "Invalid bps");
        return (amount * bps) / BPS_DIVISOR;
    }

    // SAFE: Ensure percentages sum to 100
    function validateDistribution(uint256[] calldata percentages) external pure returns (bool) {
        uint256 total = 0;
        for (uint256 i = 0; i < percentages.length; i++) {
            total += percentages[i];
        }
        return total == PERCENT_DIVISOR;
    }
}

/**
 * @title TimestampSafe
 * @notice Safe: Safe timestamp usage
 */
contract TimestampSafe {
    uint256 public constant MIN_DELAY = 1 hours;
    uint256 public constant MAX_DELAY = 7 days;

    // SAFE: Validate timestamp is reasonable
    function validateDeadline(uint256 deadline) external view returns (bool) {
        return deadline > block.timestamp && deadline <= block.timestamp + MAX_DELAY;
    }

    // SAFE: Use timestamp range instead of exact value
    function isWithinTimeWindow(
        uint256 startTime,
        uint256 endTime
    ) external view returns (bool) {
        return block.timestamp >= startTime && block.timestamp <= endTime;
    }

    // SAFE: Calculate with timestamp bounds
    function calculateTimeBasedValue(
        uint256 startTime,
        uint256 endTime,
        uint256 startValue,
        uint256 endValue
    ) external view returns (uint256) {
        require(startTime < endTime, "Invalid time range");
        require(block.timestamp >= startTime, "Not started");

        if (block.timestamp >= endTime) {
            return endValue;
        }

        uint256 elapsed = block.timestamp - startTime;
        uint256 duration = endTime - startTime;

        return startValue + ((endValue - startValue) * elapsed) / duration;
    }
}

/**
 * @title SafeMathEdgeCasesSafe
 * @notice Safe: Handle edge cases in arithmetic
 */
contract SafeMathEdgeCasesSafe {
    // SAFE: Handle potential zero values
    function safeDivisionOrZero(uint256 a, uint256 b) public pure returns (uint256) {
        if (b == 0) return 0;
        return a / b;
    }

    // SAFE: Handle max value cases
    function incrementCapped(uint256 value, uint256 cap) public pure returns (uint256) {
        if (value >= cap) return cap;
        return value + 1;
    }

    // SAFE: Calculate average without overflow
    function average(uint256 a, uint256 b) public pure returns (uint256) {
        // (a + b) / 2 can overflow, so use this instead
        return (a & b) + (a ^ b) / 2;
    }

    // SAFE: Difference without underflow
    function absDifference(uint256 a, uint256 b) public pure returns (uint256) {
        return a >= b ? a - b : b - a;
    }
}
