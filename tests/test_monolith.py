import json
from pathlib import Path
import unittest

from tools.build_monolith import OUTPUT_PATH, render_monolith


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MonolithTests(unittest.TestCase):
    def test_monolith_is_in_sync_with_modular_source(self):
        self.assertTrue(OUTPUT_PATH.is_file())
        self.assertEqual(
            OUTPUT_PATH.read_text(encoding="utf-8"),
            render_monolith(),
        )

    def test_monolith_contains_no_package_relative_imports(self):
        source = OUTPUT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from .", source)
        self.assertIn('__version__ = "1.0.0"', source)

    def test_vscode_has_full_single_file_and_overview_launches(self):
        launch = json.loads(
            (PROJECT_ROOT / ".vscode" / "launch.json").read_text(encoding="utf-8")
        )
        programs = {
            configuration.get("program")
            for configuration in launch.get("configurations", [])
        }
        self.assertIn("${workspaceFolder}/run_neurodot.py", programs)
        self.assertIn("${workspaceFolder}/Neurodot.py", programs)
        self.assertIn(
            "${workspaceFolder}/tools/run_quality_overview.py",
            programs,
        )


if __name__ == "__main__":
    unittest.main()
