"""kaggle_run.py push rewrites serve_model.py; make sure every placeholder it needs exists."""

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PlaceholderTest(unittest.TestCase):
    def test_push_replacements_produce_valid_python(self):
        source = open(os.path.join(ROOT, "kaggle", "serve_model.py")).read()
        replacements = {
            '"__API_KEY__"': json.dumps("sk-test"),
            '"__NGROK_AUTHTOKEN__"': json.dumps("ngrok-test"),
            'os.environ.get("MODEL", "huihui_ai/Qwen3.8-abliterated:27b")': json.dumps("some/model:tag"),
            'float(os.environ.get("MAX_HOURS", "2"))': repr(1.5),
            'float(os.environ.get("IDLE_MINUTES", "30"))': repr(20.0),
        }
        launcher = open(os.path.join(ROOT, "kaggle", "kaggle_run.py")).read()
        for old, new in replacements.items():
            self.assertIn(old, source)
            self.assertIn(repr(old)[1:-1].replace("\\'", "'"), launcher)
            source = source.replace(old, new)
        compile(source, "serve_model.py", "exec")
        self.assertIn('API_KEY = "sk-test"', source)
        self.assertIn("MAX_HOURS = 1.5", source)


if __name__ == "__main__":
    unittest.main()
