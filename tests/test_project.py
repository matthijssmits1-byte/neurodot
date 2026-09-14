from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import neurodot
from neurodot import config
from neurodot.workflow import main


class ProjectTests(unittest.TestCase):
    def test_entrypoint_is_available(self):
        self.assertEqual(neurodot.__version__, "1.0.0")
        self.assertTrue(callable(main))

    def test_runtime_directories_are_project_local(self):
        self.assertEqual(config.IMS_INPUT_DIR, PROJECT_ROOT / "ims_to_inject")
        self.assertEqual(config.OUTPUT_SCENE_DIR, PROJECT_ROOT / "exported_scenes")

    def test_required_development_resources_resolve(self):
        self.assertTrue(config.SCHEMA_DONOR_IMS.is_file())
        self.assertTrue(Path(config.CELLPOSE_MODEL_PATH).is_file())
        self.assertTrue(config.GUI_ICON_PATH.is_file())
        self.assertTrue(config.GUI_ICON_ICO_PATH.is_file())

    def test_source_contains_no_known_mojibake(self):
        bad_sequences = ("â", "Â", "Ã", "ðŸ", "ï¸", "�")
        package_dir = PROJECT_ROOT / "src" / "neurodot"
        for source in package_dir.glob("*.py"):
            text = source.read_text(encoding="utf-8")
            for sequence in bad_sequences:
                self.assertNotIn(sequence, text, source.name)

    def test_startup_settings_update_dependent_paths(self):
        original = (
            config.IMS_INPUT_DIR,
            config.OUTPUT_SCENE_DIR,
            config.OUTPUT_FILE_TAG,
            config.CELLPOSE_MODEL_PATH,
            config.EXPOSURE_SETTINGS_JSON,
            config.PREDICTED_SPOT_DIAMETER_UM,
            config.PREDICTED_SPOT_RADIUS_UM,
            config.PREDICTED_CENTER_POINT_SIZE_PX,
        )
        try:
            input_dir = PROJECT_ROOT / "ims_to_inject"
            output_dir = PROJECT_ROOT / "test-output"
            config.apply_startup_settings(
                input_dir=input_dir,
                output_dir=output_dir,
                output_file_tag="_test",
                model_path=None,
                spot_diameter_um=10.0,
            )
            self.assertEqual(config.IMS_INPUT_DIR, input_dir.resolve())
            self.assertEqual(config.OUTPUT_SCENE_DIR, output_dir.resolve())
            self.assertEqual(config.OUTPUT_FILE_TAG, "_test")
            self.assertEqual(config.CELLPOSE_MODEL_PATH, "")
            self.assertEqual(config.PREDICTED_SPOT_DIAMETER_UM, 10.0)
            self.assertEqual(config.PREDICTED_SPOT_RADIUS_UM, 5.0)
            self.assertEqual(config.PREDICTED_CENTER_POINT_SIZE_PX, 10)
            self.assertTrue(
                all(group["radius_um"] == 5.0 for group in config.PREDICTED_GROUPS)
            )
            self.assertEqual(
                config.EXPOSURE_SETTINGS_JSON,
                output_dir.resolve() / "cellpose_window_settings.json",
            )
        finally:
            (
                config.IMS_INPUT_DIR,
                config.OUTPUT_SCENE_DIR,
                config.OUTPUT_FILE_TAG,
                config.CELLPOSE_MODEL_PATH,
                config.EXPOSURE_SETTINGS_JSON,
                config.PREDICTED_SPOT_DIAMETER_UM,
                config.PREDICTED_SPOT_RADIUS_UM,
                config.PREDICTED_CENTER_POINT_SIZE_PX,
            ) = original
            for group in config.PREDICTED_GROUPS:
                group["radius_um"] = config.PREDICTED_SPOT_RADIUS_UM
            for settings in config.SPOT_SETTINGS.values():
                settings["display_radius_um"] = config.PREDICTED_SPOT_RADIUS_UM


if __name__ == "__main__":
    unittest.main()
