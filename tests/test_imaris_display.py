from pathlib import Path
import sys
import tempfile
import unittest

import h5py
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neurodot.imaris_io import (
    decode_h5_text,
    validate_imaris_channel_display_ranges,
    write_imaris_channel_display_ranges,
)


def text_attribute(value):
    return np.frombuffer(str(value).encode("ascii"), dtype="S1").copy()


class ImarisDisplayRangeTests(unittest.TestCase):
    def test_effective_exposures_are_written_to_physical_channels(self):
        physical_channels = (
            ("405 test", "447.000"),
            ("488 test", "525.000"),
            ("600 test", "600.000"),
            ("708 test", "708.000"),
        )
        exposure = {
            "g": {"black": 207.15, "white": 771.7419},
            "b": {"black": 124.0, "white": 1338.18},
            "r": {"black": 104.0, "white": 546.2},
            "405": {"black": 142.967857, "white": 247.66815},
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-test.ims"
            with h5py.File(path, "w") as h5:
                info = h5.create_group("DataSetInfo")
                for index, (name, emission) in enumerate(physical_channels):
                    channel = info.create_group(f"Channel {index}")
                    channel.attrs["Name"] = text_attribute(name)
                    channel.attrs["LSMEmissionWavelength"] = text_attribute(emission)
                    channel.attrs["ColorRange"] = text_attribute("0.000 1.000")

                written = write_imaris_channel_display_ranges(h5, exposure)
                validate_imaris_channel_display_ranges(h5, exposure)

                self.assertEqual(written["405"][0], 0)
                self.assertEqual(written["g"][0], 1)
                self.assertEqual(written["r"][0], 2)
                self.assertEqual(written["b"][0], 3)
                self.assertEqual(
                    decode_h5_text(info["Channel 1"].attrs["ColorRange"]),
                    "207.150000 771.741900",
                )


if __name__ == "__main__":
    unittest.main()
