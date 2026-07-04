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

    def test_required_env_rejects_placeholder_values(self):
        with patch.object(
            Config,
            "_ENV_VALUES",
            {"SMARTVOICE_TEST_KEY": "your_api_key"},
        ), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Config.ConfigError):
                Config.require_env("SMARTVOICE_TEST_KEY")

    def test_placeholder_dotenv_value_can_use_environment_fallback(self):
        with patch.object(
            Config,
            "_ENV_VALUES",
            {"SMARTVOICE_TEST_KEY": "your_api_key"},
        ), patch.dict(
            os.environ,
            {"SMARTVOICE_TEST_KEY": "from-environment"},
            clear=False,
        ):
            self.assertEqual(
                Config.get_env("SMARTVOICE_TEST_KEY"),
                "from-environment",
            )

    def test_config_setup_can_be_satisfied_by_environment(self):
        env_values = {
            "Username": "User",
            "Assistantname": "SmartVoice",
            "CohereAPIKey": "cohere-key",
            "GroqAPIKey": "groq-key",
            "SerperAPIkey": "serper-key",
            "HuggingFaceAPIKey": "huggingface-key",
        }
        with patch.object(Config, "_ENV_VALUES", {}), patch.object(
            Config,
            "reload_env",
            return_value={},
        ), patch.dict(os.environ, env_values, clear=True):
            self.assertFalse(Config.config_needs_setup())


if __name__ == "__main__":
    unittest.main()
