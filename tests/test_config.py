"""Configuration tests for environment settings and logging."""

from __future__ import annotations

import logging
import os
import unittest
from unittest.mock import patch

from alphaswarm_sol import config


class ConfigTests(unittest.TestCase):
    def test_load_settings_with_env_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRUE_VKG_NEO4J_URI": "bolt://example:9999",
                "TRUE_VKG_NEO4J_USER": "neo-user",
                "TRUE_VKG_CHROMA_PORT": "7777",
            },
            clear=False,
        ):
            settings = config.load_settings()
        self.assertEqual(settings.neo4j_uri, "bolt://example:9999")
        self.assertEqual(settings.neo4j_user, "neo-user")
        self.assertEqual(settings.chroma_port, 7777)

    def test_configure_logging_handles_unknown_level(self) -> None:
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.NOTSET)
        config.configure_logging("nope")
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.INFO)


if __name__ == "__main__":
    unittest.main()
