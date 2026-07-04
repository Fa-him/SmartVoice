import os
import sys
import types
import unittest

os.environ.setdefault("CohereAPIKey", "test-cohere-key")

fake_cohere = types.ModuleType("cohere")
fake_cohere.Client = lambda api_key: object()
sys.modules.setdefault("cohere", fake_cohere)

fake_config = types.ModuleType("Backend.Config")
fake_config.require_env = lambda name: "test-key"
sys.modules.setdefault("Backend.Config", fake_config)

from Backend.Model import ParseDecisionResponse

if sys.modules.get("Backend.Config") is fake_config:
    sys.modules.pop("Backend.Config", None)
    backend_package = sys.modules.get("Backend")
    if backend_package is not None and getattr(backend_package, "Config", None) is fake_config:
        delattr(backend_package, "Config")


class ModelParserTests(unittest.TestCase):
    def test_general_query_keeps_comma_text(self):
        self.assertEqual(
            ParseDecisionResponse(
                "general Hae amio valo achi, amr porshudin idp er defence amk kisu tips daw."
            ),
            [
                "general Hae amio valo achi, amr porshudin idp er defence amk kisu tips daw."
            ],
        )

    def test_multiple_command_tasks_still_split(self):
        self.assertEqual(
            ParseDecisionResponse("open chrome, close notepad, general how are you?"),
            ["open chrome", "close notepad", "general how are you?"],
        )


if __name__ == "__main__":
    unittest.main()
