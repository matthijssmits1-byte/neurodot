# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


project_root = Path(SPECPATH).parent
source_root = project_root / "src"
resources = project_root / "resources"
environment_root = Path(sys.prefix)

datas = [
    (str(resources / "graphics"), "resources/graphics"),
    (str(resources / "models" / "cpsam_v2"), "resources/models"),
    (str(resources / "templates"), "resources/templates"),
]
datas += collect_data_files("cellpose", include_py_files=False)
datas += copy_metadata("cellpose")

hiddenimports = [
    "cellpose.core",
    "cellpose.dynamics",
    "cellpose.models",
    "cellpose.transforms",
    "cellpose.utils",
    "cellpose.vit",
    "cv2",
    "h5py",
    "numba",
    "scipy.ndimage",
    "torch",
]

# The current CUDA-enabled PyTorch installation is a Conda build. Its CUDA
# runtime resides in ``env/bin`` rather than the locations inspected by the
# standard PyInstaller Torch hook. Netlib BLAS also needs MinGW runtime DLLs.
# Collect these explicitly so NumPy works on a clean computer and GPU support
# does not depend on the build workstation's Conda environment.
binaries = []
for dll in sorted((environment_root / "bin").glob("*.dll")):
    binaries.append((str(dll), "."))
for dll in sorted((environment_root / "Library" / "mingw-w64" / "bin").glob("*.dll")):
    binaries.append((str(dll), "."))

a = Analysis(
    [str(project_root / "run_neurodot.py")],
    pathex=[str(source_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / "packaging" / "runtime_hook.py")],
    excludes=[
        "cellpose.gui",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Neurodot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(resources / "graphics" / "Icon.ico"),
    version=str(project_root / "packaging" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Neurodot",
)
