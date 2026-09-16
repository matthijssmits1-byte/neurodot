from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import neurodot
from neurodot import config
from neurodot import paths
from neurodot.startup_gui import StartupWindow
from neurodot.workflow import main


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FailOnMessage:
    def showerror(self, title, message):
        raise AssertionError(f"Unexpected startup validation error: {title}: {message}")


class _Root:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class ProjectTests(unittest.TestCase):
    def test_entrypoint_is_available(self):
        self.assertEqual(neurodot.__version__, "1.0.0")
        self.assertTrue(callable(main))

    def test_initial_heavy_import_uses_animated_progress_task(self):
        package_entry = (
            PROJECT_ROOT / "src" / "neurodot" / "__init__.py"
        ).read_text(encoding="utf-8")
        monolith_builder = (
            PROJECT_ROOT / "tools" / "build_monolith.py"
        ).read_text(encoding="utf-8")
        self.assertIn("run = progress.run_task(load_workflow)", package_entry)
        self.assertIn(
            "progress.run_task(_load_heavy_dependencies)",
            monolith_builder,
        )

    def test_completion_window_resizes_after_buttons_are_added(self):
        progress_source = (
            PROJECT_ROOT / "src" / "neurodot" / "progress_gui.py"
        ).read_text(encoding="utf-8")
        pack_position = progress_source.index(
            'self.close_button.pack(side="right")'
        )
        resize_position = progress_source.index(
            "self._centre_window()",
            pack_position,
        )
        show_position = progress_source.index("self.show()", resize_position)
        self.assertLess(pack_position, resize_position)
        self.assertLess(resize_position, show_position)

    def test_startup_continue_choice_is_returned(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for use_quality_review in (True, False):
                window = StartupWindow.__new__(StartupWindow)
                window.input_var = _Value(str(root))
                window.output_var = _Value(str(root / "output"))
                window.tag_var = _Value("_test")
                window.spot_diameter_var = _Value("5.0")
                window.model_mode = _Value("builtin")
                window.model_var = _Value("")
                window.messagebox = _FailOnMessage()
                window.root = _Root()
                window.result = None

                window._continue(use_quality_review=use_quality_review)

                self.assertEqual(
                    window.result["use_quality_review"],
                    use_quality_review,
                )
                self.assertTrue(window.root.destroyed)

    def test_startup_output_can_be_set_to_input_folder(self):
        window = StartupWindow.__new__(StartupWindow)
        window.input_var = _Value(r"C:\data\input")
        window.output_var = _Value(r"C:\data\output")

        window._use_input_as_output()

        self.assertEqual(window.output_var.get(), r"C:\data\input")

    def test_runtime_directories_are_project_local(self):
        self.assertEqual(config.IMS_INPUT_DIR, PROJECT_ROOT / "data" / "input")
        self.assertEqual(config.OUTPUT_SCENE_DIR, PROJECT_ROOT / "data" / "output")

    def test_resource_locations_are_project_local(self):
        self.assertEqual(
            config.SCHEMA_DONOR_IMS,
            PROJECT_ROOT / "resources" / "templates" / "donor_1_point_each_with_to.ims",
        )
        primary_model = PROJECT_ROOT / "resources" / "models" / "cpsam_v2"
        fallback_model = (
            PROJECT_ROOT / "resources" / "models" / "cpsam_v2_sweeney"
        )
        expected_model = (
            primary_model
            if primary_model.exists() or not fallback_model.exists()
            else fallback_model
        )
        self.assertEqual(Path(config.CELLPOSE_MODEL_PATH), expected_model)
        self.assertTrue((PROJECT_ROOT / "resources" / "templates" / "README.md").is_file())
        self.assertTrue((PROJECT_ROOT / "resources" / "models" / "README.md").is_file())
        self.assertTrue(config.GUI_ICON_PATH.is_file())
        self.assertTrue(config.GUI_ICON_ICO_PATH.is_file())

    def test_resource_resolver_uses_existing_fallback_name(self):
        with TemporaryDirectory() as temporary:
            bundle_root = Path(temporary)
            fallback = bundle_root / "resources" / "models" / "fallback"
            fallback.parent.mkdir(parents=True)
            fallback.write_bytes(b"model")
            with patch.object(paths, "BUNDLE_ROOT", bundle_root):
                resolved = paths.resolve_resource(
                    "models/missing-primary",
                    "models/fallback",
                )
            self.assertEqual(resolved, fallback)

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
            input_dir = PROJECT_ROOT / "data" / "input"
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

    def test_project_has_no_historical_filename_branding(self):
        import re

        pattern = re.compile(r"\bv[0-9]+\b|Neurodotv[0-9]+", re.IGNORECASE)
        text_suffixes = {".py", ".md", ".json", ".toml", ".code-workspace"}
        for path in PROJECT_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in text_suffixes:
                continue
            if "__pycache__" in path.parts:
                continue
            self.assertIsNone(
                pattern.search(path.read_text(encoding="utf-8")),
                str(path.relative_to(PROJECT_ROOT)),
            )


if __name__ == "__main__":
    unittest.main()
