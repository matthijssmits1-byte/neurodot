"""Configure bundled model discovery before Cellpose is imported."""

import os
from pathlib import Path
import sys


bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
os.environ["CELLPOSE_LOCAL_MODELS_PATH"] = str(
    bundle_root / "resources" / "models"
)

# PyInstaller normally installs its own Tk runtime hook, but explicitly set
# these paths as well. This prevents Tcl from falling back to directories from
# the build computer when the portable folder is moved to another machine.
tcl_library = bundle_root / "_tcl_data"
tk_library = bundle_root / "_tk_data"
if tcl_library.is_dir():
    os.environ["TCL_LIBRARY"] = str(tcl_library)
if tk_library.is_dir():
    os.environ["TK_LIBRARY"] = str(tk_library)
