import os
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_FILES = PROJECT_ROOT / "Frontend" / "Files"


def _subprocess_env():
    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(PROJECT_ROOT),
            "CohereAPIKey": "test-cohere-key",
            "GroqAPIKey": "test-groq-key",
            "SerperAPIkey": "test-serper-key",
            "HuggingFaceAPIKey": "test-huggingface-key",
        }
    )
    return env


class ImportSideEffectTests(unittest.TestCase):
    def test_image_generation_import_does_not_start_watcher(self):
        FRONTEND_FILES.mkdir(parents=True, exist_ok=True)
        request_file = FRONTEND_FILES / "ImageGeneration.data"
        existed = request_file.exists()
        original = request_file.read_text(encoding="utf-8") if existed else None
        request_file.write_text("unit test prompt,True", encoding="utf-8")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import Backend.ImageGeneration; print('image import ok')",
                ],
                cwd=PROJECT_ROOT,
                env=_subprocess_env(),
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("image import ok", result.stdout)
            self.assertNotIn("Generating Images", result.stdout)
            self.assertEqual(
                request_file.read_text(encoding="utf-8"),
                "unit test prompt,True",
            )
        finally:
            if existed:
                request_file.write_text(original, encoding="utf-8")
            else:
                request_file.unlink(missing_ok=True)

    def test_main_import_does_not_mutate_frontend_data_files(self):
        FRONTEND_FILES.mkdir(parents=True, exist_ok=True)
        before = {
            path.name: path.read_text(encoding="utf-8", errors="replace")
            for path in FRONTEND_FILES.glob("*.data")
        }

        result = subprocess.run(
            [sys.executable, "-c", "import main; print('main import ok')"],
            cwd=PROJECT_ROOT,
            env=_subprocess_env(),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

        after = {
            path.name: path.read_text(encoding="utf-8", errors="replace")
            for path in FRONTEND_FILES.glob("*.data")
        }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("main import ok", result.stdout)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
