import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neurodot.detection import suggest_setup_preview_white
from neurodot.image_io import _choose_qc_resolution_level
from neurodot.quality_review import (
    EXCLUDED_FOLDER_NAME,
    OVERVIEW_CHANNELS,
    ImageQualityOverviewWindow,
    move_excluded_files,
)
import neurodot.workflow as workflow


class _QueuedFuture:
    def __init__(self):
        self._cancelled = False
        self._callbacks = []

    def cancel(self):
        self._cancelled = True
        for callback in self._callbacks:
            callback(self)
        return True

    def cancelled(self):
        return self._cancelled

    def add_done_callback(self, callback):
        self._callbacks.append(callback)


class _QueuedExecutor:
    def submit(self, _function, *_arguments):
        return _QueuedFuture()


class QualityReviewTests(unittest.TestCase):
    def test_overview_channel_order(self):
        self.assertEqual(OVERVIEW_CHANNELS, ("g", "b", "r", "405"))

    def test_visible_channel_is_prioritized_while_other_channels_preload(self):
        window = ImageQualityOverviewWindow.__new__(ImageQualityOverviewWindow)
        window.ims_files = [Path("one.ims"), Path("two.ims")]
        window.current_channel = "g"
        window.preview_cache = {}
        window.pending = set()
        window.foreground_futures = {}
        window.background_futures = {}
        window.foreground_executor = _QueuedExecutor()
        window.background_executor = _QueuedExecutor()
        window._load_preview = lambda *_args: None
        window._update_status = lambda: None

        window._queue_channel_loads()
        window._queue_background_preloads()

        self.assertEqual(
            {key[1] for key in window.foreground_futures},
            {"g"},
        )
        self.assertEqual(
            {key[1] for key in window.background_futures},
            {"b", "r", "405"},
        )

        window.current_channel = "b"
        window._queue_channel_loads()
        self.assertEqual(
            {key[1] for key in window.foreground_futures},
            {"b"},
        )

    def test_background_preload_does_not_block_visible_channel(self):
        window = ImageQualityOverviewWindow.__new__(ImageQualityOverviewWindow)
        window.pending = {
            (Path("one.ims"), "r"),
            (Path("two.ims"), "405"),
        }
        self.assertFalse(window._channel_is_loading("g"))
        self.assertTrue(window._channel_is_loading("r"))

    def test_preview_white_is_adaptive_and_bounded(self):
        self.assertEqual(
            suggest_setup_preview_white(np.linspace(0, 120, 10000)),
            200.0,
        )
        middle = suggest_setup_preview_white(np.linspace(0, 300, 10000))
        self.assertGreater(middle, 290.0)
        self.assertLess(middle, 300.0)
        self.assertEqual(
            suggest_setup_preview_white(np.linspace(0, 2000, 10000)),
            400.0,
        )

    def test_qc_reader_selects_a_small_level_without_upsampling(self):
        level, logical_shape = _choose_qc_resolution_level(
            {
                0: (24, 2048, 1024),
                1: (24, 1024, 512),
                2: (24, 512, 256),
                3: (24, 256, 128),
            },
            logical_shape_zyx=(24, 2000, 1000),
            target_size=400,
        )

        self.assertEqual(level, 2)
        self.assertEqual(logical_shape, (24, 500, 250))
        self.assertAlmostEqual(logical_shape[1] / logical_shape[2], 2.0)

    def test_exclusions_are_manifested_without_overwriting(self):
        with TemporaryDirectory() as temporary:
            input_dir = Path(temporary)
            source = input_dir / "sample.ims"
            source.write_bytes(b"new")
            excluded_dir = input_dir / EXCLUDED_FOLDER_NAME
            excluded_dir.mkdir()
            (excluded_dir / "sample.ims").write_bytes(b"existing")

            moved = move_excluded_files([source], input_dir)

            self.assertEqual(moved[0].name, "sample__2.ims")
            self.assertEqual(moved[0].read_bytes(), b"new")
            self.assertFalse(source.exists())
            manifest = json.loads(
                (excluded_dir / "exclusion_manifest.json").read_text(encoding="utf-8")
            )
            self.assertTrue(manifest[-1]["moved_to"].endswith("sample__2.ims"))

    def test_overview_precedes_model_loading(self):
        workflow = (PROJECT_ROOT / "src" / "neurodot" / "workflow.py").read_text(
            encoding="utf-8"
        )
        review_position = workflow.index("choose_image_quality_overview(")
        model_position = workflow.index("initialize_models(", review_position)
        self.assertLess(review_position, model_position)

    def test_direct_continue_skips_quality_review(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "sample.ims").write_bytes(b"test")

            with (
                patch.object(workflow, "IMS_INPUT_DIR", input_dir),
                patch.object(workflow, "OUTPUT_SCENE_DIR", output_dir),
                patch.object(workflow, "SCHEMA_DONOR_IMS", root / "missing.ims"),
                patch.object(
                    workflow,
                    "choose_image_quality_overview",
                    side_effect=AssertionError("QC should have been skipped"),
                ) as review,
            ):
                with self.assertRaises(FileNotFoundError):
                    workflow.main(use_quality_review=False)

            review.assert_not_called()


if __name__ == "__main__":
    unittest.main()
