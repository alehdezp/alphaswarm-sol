"""
LLM Rate Limiting and Cost Caps Tests (Task 11.11)

Tests for:
1. Token limit enforcement
2. Cost cap enforcement
3. Rate limiting (requests per minute)
4. Clear error messages
5. Usage tracking
"""

import time
import unittest

from alphaswarm_sol.llm.limits import (
    LLMLimits,
    LimitType,
    LimitExceededError,
    UsageReport,
    RateLimiter,
    create_rate_limiter,
    check_budget,
    get_usage_summary,
)


class TestLLMLimits(unittest.TestCase):
    """Tests for LLMLimits dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        limits = LLMLimits()
        self.assertEqual(limits.max_tokens_per_run, 100_000)
        self.assertEqual(limits.max_cost_per_run_usd, 5.00)
        self.assertEqual(limits.max_requests_per_minute, 60)
        self.assertEqual(limits.max_findings_per_run, 200)

    def test_custom_values(self):
        """Should accept custom values."""
        limits = LLMLimits(
            max_tokens_per_run=50_000,
            max_cost_per_run_usd=2.00,
            max_requests_per_minute=30,
        )
        self.assertEqual(limits.max_tokens_per_run, 50_000)
        self.assertEqual(limits.max_cost_per_run_usd, 2.00)

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        limits = LLMLimits()
        d = limits.to_dict()
        self.assertIn("max_tokens_per_run", d)
        self.assertIn("max_cost_per_run_usd", d)


class TestUsageReport(unittest.TestCase):
    """Tests for UsageReport dataclass."""

    def test_default_values(self):
        """Should have zero defaults."""
        report = UsageReport()
        self.assertEqual(report.tokens_used, 0)
        self.assertEqual(report.cost_usd, 0.0)
        self.assertFalse(report.limit_exceeded)

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        report = UsageReport(
            tokens_used=1000,
            cost_usd=0.05,
            requests_made=5,
        )
        d = report.to_dict()
        self.assertEqual(d["tokens_used"], 1000)
        self.assertEqual(d["cost_usd"], 0.05)


class TestRateLimiter(unittest.TestCase):
    """Tests for RateLimiter class."""

    def test_allow_within_limits(self):
        """Should allow requests within limits."""
        limiter = RateLimiter()
        allowed, message = limiter.check_limits(1000)
        self.assertTrue(allowed)
        self.assertEqual(message, "")

    def test_token_limit_exceeded(self):
        """Should reject when token limit exceeded."""
        limits = LLMLimits(max_tokens_per_run=1000)
        limiter = RateLimiter(limits)

        # Record usage close to limit
        limiter.record_usage(900, 0, 0.01)

        # Should reject request that would exceed
        allowed, message = limiter.check_limits(200)
        self.assertFalse(allowed)
        self.assertIn("Token limit", message)

    def test_cost_limit_exceeded(self):
        """Should reject when cost limit exceeded."""
        limits = LLMLimits(max_cost_per_run_usd=0.10)
        limiter = RateLimiter(limits)

        # Record usage that exceeds
        limiter.record_usage(1000, 500, 0.15)

        allowed, message = limiter.check_limits()
        self.assertFalse(allowed)
        self.assertIn("Cost limit", message)

    def test_findings_limit_exceeded(self):
        """Should reject when findings limit exceeded."""
        limits = LLMLimits(max_findings_per_run=5)
        limiter = RateLimiter(limits)

        # Analyze up to limit
        for i in range(5):
            limiter.record_usage(100, 50, 0.01, findings=1)

        allowed, message = limiter.check_limits()
        self.assertFalse(allowed)
        self.assertIn("Findings limit", message)

    def test_hard_limit_raises_exception(self):
        """Hard limit mode should raise exception."""
        limits = LLMLimits(max_tokens_per_run=100, hard_limit=True)
        limiter = RateLimiter(limits)

        limiter.record_usage(90, 0, 0.01)

        with self.assertRaises(LimitExceededError) as ctx:
            limiter.check_and_raise(50)

        self.assertEqual(ctx.exception.limit_type, LimitType.TOKENS)
        self.assertEqual(ctx.exception.maximum, 100)

    def test_soft_limit_warns_only(self):
        """Soft limit mode should only warn."""
        limits = LLMLimits(max_tokens_per_run=100, hard_limit=False)
        limiter = RateLimiter(limits)

        limiter.record_usage(90, 0, 0.01)

        # Should not raise
        limiter.check_and_raise(50)

        # But should add warning
        report = limiter.get_usage_report()
        self.assertTrue(len(report.warnings) > 0)

    def test_record_usage(self):
        """Should track usage correctly."""
        limiter = RateLimiter()

        limiter.record_usage(1000, 500, 0.05, findings=2)

        report = limiter.get_usage_report()
        self.assertEqual(report.tokens_used, 1500)
        self.assertEqual(report.cost_usd, 0.05)
        self.assertEqual(report.findings_analyzed, 2)

    def test_cost_warning_threshold(self):
        """Should warn when cost threshold passed."""
        limits = LLMLimits(warn_cost_threshold_usd=0.05)
        limiter = RateLimiter(limits)

        # Record usage that crosses threshold
        limiter.record_usage(1000, 500, 0.06)

        report = limiter.get_usage_report()
        self.assertTrue(any("warning" in w.lower() for w in report.warnings))

    def test_get_remaining(self):
        """Should calculate remaining budget."""
        limits = LLMLimits(
            max_tokens_per_run=10_000,
            max_cost_per_run_usd=1.00,
        )
        limiter = RateLimiter(limits)

        limiter.record_usage(3000, 0, 0.30)

        remaining = limiter.get_remaining()
        self.assertEqual(remaining["tokens_remaining"], 7000)
        self.assertAlmostEqual(remaining["cost_remaining_usd"], 0.70, places=2)

    def test_reset(self):
        """Should reset all counters."""
        limiter = RateLimiter()
        limiter.record_usage(5000, 2000, 0.50, findings=10)

        limiter.reset()

        report = limiter.get_usage_report()
        self.assertEqual(report.tokens_used, 0)
        self.assertEqual(report.cost_usd, 0.0)
        self.assertEqual(report.findings_analyzed, 0)

    def test_format_status(self):
        """Should format status correctly."""
        limiter = RateLimiter()
        limiter.record_usage(5000, 2000, 0.25, findings=5)

        status = limiter.format_status()
        self.assertIn("7,000", status)  # tokens
        self.assertIn("$0.25", status)  # cost
        self.assertIn("Findings: 5", status)


class TestRateLimitingPerMinute(unittest.TestCase):
    """Tests for requests per minute rate limiting."""

    def test_rate_limit_within_minute(self):
        """Should enforce rate limit within a minute."""
        limits = LLMLimits(max_requests_per_minute=3)
        limiter = RateLimiter(limits)

        # Make 3 requests (at limit)
        for _ in range(3):
            limiter.record_usage(100, 50, 0.01)

        # 4th request should be rejected
        allowed, message = limiter.check_limits()
        self.assertFalse(allowed)
        self.assertIn("Rate limit", message)


class TestLimitExceededError(unittest.TestCase):
    """Tests for LimitExceededError exception."""

    def test_error_attributes(self):
        """Should have correct attributes."""
        error = LimitExceededError(
            LimitType.TOKENS,
            "Token limit exceeded",
            15000,
            10000,
        )
        self.assertEqual(error.limit_type, LimitType.TOKENS)
        self.assertEqual(error.current, 15000)
        self.assertEqual(error.maximum, 10000)


class TestCreateRateLimiter(unittest.TestCase):
    """Tests for create_rate_limiter factory function."""

    def test_creates_with_defaults(self):
        """Should create limiter with defaults."""
        limiter = create_rate_limiter()
        self.assertEqual(limiter.limits.max_tokens_per_run, 100_000)

    def test_creates_with_custom_values(self):
        """Should create limiter with custom values."""
        limiter = create_rate_limiter(
            max_tokens=50_000,
            max_cost=2.00,
            max_rate=30,
            hard_limit=False,
        )
        self.assertEqual(limiter.limits.max_tokens_per_run, 50_000)
        self.assertEqual(limiter.limits.max_cost_per_run_usd, 2.00)
        self.assertFalse(limiter.limits.hard_limit)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def test_check_budget(self):
        """check_budget should work correctly."""
        limiter = create_rate_limiter(max_tokens=1000)
        limiter.record_usage(900, 0, 0.01)

        allowed, message = check_budget(limiter, 200)
        self.assertFalse(allowed)

    def test_get_usage_summary(self):
        """get_usage_summary should return formatted string."""
        limiter = create_rate_limiter()
        limiter.record_usage(5000, 2000, 0.25)

        summary = get_usage_summary(limiter)
        self.assertIsInstance(summary, str)
        self.assertIn("Tokens:", summary)
        self.assertIn("Cost:", summary)


class TestLimitType(unittest.TestCase):
    """Tests for LimitType enum."""

    def test_enum_values(self):
        """Should have expected values."""
        self.assertEqual(LimitType.TOKENS.value, "tokens")
        self.assertEqual(LimitType.COST.value, "cost")
        self.assertEqual(LimitType.RATE.value, "rate")
        self.assertEqual(LimitType.FINDINGS.value, "findings")


class TestMultipleRequests(unittest.TestCase):
    """Tests for handling multiple requests."""

    def test_cumulative_token_tracking(self):
        """Should track tokens cumulatively."""
        limiter = create_rate_limiter(max_tokens=10_000)

        for _ in range(5):
            limiter.record_usage(1000, 500, 0.05)

        report = limiter.get_usage_report()
        self.assertEqual(report.tokens_used, 7500)  # 5 * (1000 + 500)

    def test_cumulative_cost_tracking(self):
        """Should track cost cumulatively."""
        limiter = create_rate_limiter(max_cost=1.00)

        for _ in range(10):
            limiter.record_usage(1000, 500, 0.08)

        report = limiter.get_usage_report()
        self.assertAlmostEqual(report.cost_usd, 0.80, places=2)


class TestUsageReportWithLimits(unittest.TestCase):
    """Tests for usage reports with limit tracking."""

    def test_report_shows_exceeded(self):
        """Report should show when limits exceeded."""
        limits = LLMLimits(max_tokens_per_run=1000)
        limiter = RateLimiter(limits)

        limiter.record_usage(1200, 0, 0.01)

        report = limiter.get_usage_report()
        self.assertTrue(report.limit_exceeded)
        self.assertEqual(report.exceeded_type, LimitType.TOKENS)

    def test_report_shows_not_exceeded(self):
        """Report should show when limits not exceeded."""
        limiter = create_rate_limiter()
        limiter.record_usage(100, 50, 0.01)

        report = limiter.get_usage_report()
        self.assertFalse(report.limit_exceeded)
        self.assertIsNone(report.exceeded_type)


if __name__ == "__main__":
    unittest.main()
