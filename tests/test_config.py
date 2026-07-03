import os
import unittest
from unittest.mock import patch

from Backend import Config


class ConfigTests(unittest.TestCase):
    def test_get_env_uses_environment_fallback(self):
        with patch.object(Config, "_ENV_VALUES", {}), patch.dict(
            os.environ,
            {"SMARTVOICE_TEST_KEY": "from-environment"},
            clear=False,
        ):
            self.assertEqual(
                Config.get_env("SMARTVOICE_TEST_KEY"),
                "from-environment",
            )

    def test_dotenv_value_takes_priority(self):
        with patch.object(
            Config,
            "_ENV_VALUES",
            {"SMARTVOICE_TEST_KEY": "from-dotenv"},
        ), patch.dict(
            os.environ,
            {"SMARTVOICE_TEST_KEY": "from-environment"},
            clear=False,
        ):
            self.assertEqual(Config.get_env("SMARTVOICE_TEST_KEY"), "from-dotenv")

    def test_require_env_raises_clear_error_when_missing(self):
        with patch.object(Config, "_ENV_VALUES", {}), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Config.ConfigError) as ctx:
                Config.require_env("SMARTVOICE_MISSING_KEY")

        self.assertIn("SMARTVOICE_MISSING_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
