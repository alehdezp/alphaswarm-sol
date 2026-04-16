"""Heuristic tag extraction tests."""

from __future__ import annotations

import unittest

from alphaswarm_sol.kg.heuristics import classify_auth_modifiers, classify_state_var_name, is_privileged_state


class HeuristicTests(unittest.TestCase):
    def test_classify_state_var_name(self) -> None:
        tags = classify_state_var_name("ownerFeeBps")
        self.assertIn("owner", tags)
        self.assertIn("fee", tags)

    def test_classify_auth_modifiers(self) -> None:
        tags = classify_auth_modifiers(["onlyOwner", "onlyRole", "guardianOnly"])
        self.assertIn("only_owner", tags)
        self.assertIn("role", tags)
        self.assertIn("governance", tags)

    def test_privileged_state(self) -> None:
        self.assertTrue(is_privileged_state(["owner"]))
        self.assertFalse(is_privileged_state(["balance"]))


if __name__ == "__main__":
    unittest.main()
