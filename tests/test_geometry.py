from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neurodot.geometry import (
    build_counting_rectangle_yx,
    build_counting_region_divider_yx,
    build_selected_counting_region_polygon_yx,
    filter_split_predictions_to_counting_rectangles,
    points_in_polygon_yx,
)


class CountingGeometryTests(unittest.TestCase):
    def setUp(self):
        self.landmarks = {
            "rot_bottom": (100.0, 50.0),
            "rot_top": (0.0, 50.0),
            "ce": (50.0, 50.0),
            "si_L": (50.0, 10.0),
            "bo_L": (100.0, 10.0),
            "to_L": (0.0, 10.0),
            "si_R": (50.0, 90.0),
            "bo_R": (100.0, 90.0),
            "to_R": (0.0, 90.0),
        }

    def test_rectangles_have_no_padding(self):
        left = build_counting_rectangle_yx(self.landmarks, "L")
        right = build_counting_rectangle_yx(self.landmarks, "R")
        self.assertEqual(left.shape, (4, 2))
        self.assertEqual(right.shape, (4, 2))
        self.assertTrue(np.isfinite(left).all())
        self.assertTrue(np.isfinite(right).all())

    def test_regions_partition_rectangle_at_centre(self):
        rectangle = build_counting_rectangle_yx(self.landmarks, "L")
        divider = build_counting_region_divider_yx(self.landmarks, "L")
        dorsal = build_selected_counting_region_polygon_yx(
            self.landmarks, "L", "dorsal"
        )
        ventral = build_selected_counting_region_polygon_yx(
            self.landmarks, "L", "ventral"
        )
        self.assertEqual(divider.shape, (2, 2))
        self.assertGreaterEqual(len(dorsal), 3)
        self.assertGreaterEqual(len(ventral), 3)

    def test_polygon_inclusion(self):
        polygon = np.array([[0, 0], [0, 10], [10, 10], [10, 0]], dtype=float)
        points = np.array([[5, 5], [20, 20]], dtype=float)
        np.testing.assert_array_equal(
            points_in_polygon_yx(points, polygon),
            np.array([True, False]),
        )

    def test_custom_roi_can_include_or_exclude_its_interior(self):
        xyz = np.asarray(
            [[4.5, 4.5, 0.0], [8.5, 8.5, 0.0]],
            dtype=np.float32,
        )
        split = {"L": {"g": xyz}, "R": {"g": xyz}}
        polygon = [[2, 2], [2, 6], [6, 6], [6, 2]]
        rois = {"g": {"L": polygon, "R": polygon}}
        geometry = {
            "min_x": 0.0,
            "max_x": 10.0,
            "min_y": 0.0,
            "max_y": 10.0,
            "nx": 10,
            "ny": 10,
        }

        with (
            patch("neurodot.geometry.get_image_geometry", return_value=geometry),
            patch(
                "neurodot.geometry.counting_rectangle_mask_yx",
                side_effect=lambda points, *args, **kwargs: np.ones(
                    len(points), dtype=bool
                ),
            ),
        ):
            included, _ = filter_split_predictions_to_counting_rectangles(
                split,
                {},
                object(),
                custom_rois_yx=rois,
                custom_roi_modes={"g": {"L": "include", "R": "include"}},
            )
            excluded, _ = filter_split_predictions_to_counting_rectangles(
                split,
                {},
                object(),
                custom_rois_yx=rois,
                custom_roi_modes={"g": {"L": "exclude", "R": "exclude"}},
            )

        for hemisphere in ("L", "R"):
            np.testing.assert_allclose(included[hemisphere]["g"], xyz[:1])
            np.testing.assert_allclose(excluded[hemisphere]["g"], xyz[1:])


if __name__ == "__main__":
    unittest.main()
