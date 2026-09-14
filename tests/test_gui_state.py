from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neurodot.config import (
    CHANNEL_PROCESSING_ORDER,
    DEFAULT_COUNTING_REGION,
    MANUAL_GUI_LANDMARKS,
)
from neurodot.gui import ExposureWindowGUI


class Variable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Canvas:
    def __init__(self):
        self.items = {}
        self.created = 0
        self.cursor = None

    def configure(self, **kwargs):
        if "cursor" in kwargs:
            self.cursor = kwargs["cursor"]

    def find_withtag(self, tag):
        return (tag,) if tag in self.items else ()

    def create_line(self, *coordinates, **kwargs):
        self.created += 1
        for tag in kwargs.get("tags", ()):
            self.items[tag] = list(coordinates)

    def coords(self, tag, *coordinates):
        self.items[tag] = list(coordinates)

    def itemconfigure(self, _tag, **_kwargs):
        pass

    def tag_raise(self, _tag):
        pass

    def delete(self, tag):
        self.items.pop(tag, None)


class Event:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class GuiStateTests(unittest.TestCase):
    def make_gui(self):
        gui = ExposureWindowGUI.__new__(ExposureWindowGUI)
        gui.current_file_index = 0
        gui.current_channel = CHANNEL_PROCESSING_ORDER[0]
        gui.exposure_pick_mode = None
        gui.exposure_finalized_keys = set()
        gui.exposure_calibration_picks = {}
        gui.manual_landmarks_yx = {0: {}}
        return gui

    def test_finalized_exposure_disables_temporary_preview(self):
        gui = self.make_gui()
        gui.exposure_finalized_keys.add((0, gui.current_channel))
        self.assertFalse(gui._use_forced_black_preview_mode())

    def test_incomplete_initial_landmarks_still_enable_preview(self):
        gui = self.make_gui()
        self.assertTrue(gui._use_forced_black_preview_mode())

    def test_one_shot_landmark_replacement_does_not_restart_calibration(self):
        gui = self.make_gui()
        gui.manual_landmarks_yx[0] = {
            key: [1.0, 1.0]
            for key in MANUAL_GUI_LANDMARKS
        }
        gui.landmark_var = Variable("to_R")
        gui.current_landmark = "to_R"
        gui.landmark_sequence_active = False
        gui._update_landmark_button_styles = lambda: None
        gui._update_preview_cursor = lambda: None

        def unexpected_calibration(_mode):
            self.fail("Landmark replacement restarted exposure calibration")

        gui._set_exposure_pick_mode = unexpected_calibration
        gui._commit_landmark_yx("to_R", 20, 30)

        self.assertEqual(gui.manual_landmarks_yx[0]["to_R"], [20.0, 30.0])
        self.assertEqual(gui.landmark_var.get(), "")
        self.assertIsNone(gui.current_landmark)

    def test_work_in_progress_snapshot_keeps_partial_landmarks_and_roi_mode(self):
        gui = self.make_gui()
        gui.ims_files = [Path("unfinished.ims")]
        gui._series_average = lambda _channel: {"black": 1.0, "white": 10.0}
        gui._effective_exposure = lambda _index, _channel: {
            "black": 1.0,
            "white": 10.0,
            "source": "series_average",
        }
        gui.manual_landmarks_yx = {0: {"rot_bottom": [12.0, 34.0]}}
        gui.custom_counting_rois_yx = {
            (0, "g", "L"): [[0, 0], [0, 5], [5, 5]]
        }
        gui.custom_counting_roi_modes = {(0, "g", "L"): "exclude"}
        gui.channel_counting_regions = {
            channel: DEFAULT_COUNTING_REGION
            for channel in CHANNEL_PROCESSING_ORDER
        }
        gui.channel_enabled_vars = {
            channel: Variable(True)
            for channel in CHANNEL_PROCESSING_ORDER
        }

        snapshot = gui._collect_current_settings()

        self.assertEqual(
            snapshot["manual_landmarks_yx"]["unfinished.ims"],
            {"rot_bottom": [12.0, 34.0]},
        )
        self.assertEqual(
            snapshot["custom_counting_roi_modes"]["unfinished.ims"]["g"]["L"],
            "exclude",
        )

    def test_placement_uses_native_cursor_without_canvas_motion_drawing(self):
        gui = self.make_gui()
        gui.preview_canvas = Canvas()
        gui.placement_cursor = "@native-white-cross.cur"
        gui.custom_roi_draw_active = False
        gui.exposure_pick_mode = "positive"
        gui.current_landmark = None

        gui._update_preview_cursor()

        self.assertEqual(gui.preview_canvas.cursor, gui.placement_cursor)
        self.assertEqual(gui.preview_canvas.created, 0)
        self.assertFalse(hasattr(gui, "on_preview_motion"))

    def test_cellpose_preview_uses_rectangle_region_and_custom_roi_rules(self):
        gui = self.make_gui()
        gui.manual_landmarks_yx = {0: {
            "rot_bottom": [90, 50], "rot_top": [10, 50], "ce": [50, 50],
            "bo_L": [90, 10], "to_L": [10, 10], "si_L": [50, 10],
            "bo_R": [90, 90], "to_R": [10, 90], "si_R": [50, 90],
        }}
        gui.channel_counting_regions = {gui.current_channel: "dorsal"}
        gui.custom_counting_rois_yx = {}
        gui.custom_counting_roi_modes = {}
        centers = np.asarray([
            [25, 25], [75, 25], [25, 75], [75, 75], [25, 5],
        ], dtype=np.float32)

        keep = gui._cellpose_preview_keep_mask(centers)
        self.assertEqual(keep.tolist(), [True, False, True, False, False])

        gui.custom_counting_rois_yx[(0, gui.current_channel, "R")] = [
            [15, 65], [15, 85], [35, 85], [35, 65],
        ]
        gui.custom_counting_roi_modes[(0, gui.current_channel, "R")] = "exclude"
        keep = gui._cellpose_preview_keep_mask(centers)
        self.assertEqual(keep.tolist(), [True, False, False, False, False])

    def test_close_prompt_cancel_keeps_gui_open_and_no_closes_it(self):
        gui = self.make_gui()
        gui.root = object()
        close_calls = []
        gui.cancel = lambda: close_calls.append(True)

        class MessageBox:
            choice = None

            @classmethod
            def askyesnocancel(cls, *_args, **_kwargs):
                return cls.choice

        gui.messagebox = MessageBox
        gui.request_close()
        self.assertEqual(close_calls, [])

        MessageBox.choice = False
        gui.request_close()
        self.assertEqual(close_calls, [True])

    def test_close_prompt_only_closes_after_successful_save(self):
        gui = self.make_gui()
        gui.root = object()
        gui.messagebox = type(
            "MessageBox",
            (),
            {"askyesnocancel": staticmethod(lambda *_args, **_kwargs: True)},
        )
        close_calls = []
        gui.cancel = lambda: close_calls.append(True)
        gui.save_window_settings_json = lambda closing=False: False
        gui.request_close()
        self.assertEqual(close_calls, [])

        gui.save_window_settings_json = lambda closing=False: closing
        gui.request_close()
        self.assertEqual(close_calls, [True])


if __name__ == "__main__":
    unittest.main()
