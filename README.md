# Neurodot

Neurodot is a desktop application for guided, reproducible cell detection in
multichannel Imaris microscopy images. It combines Cellpose segmentation with
user-defined landmarks, exposure calibration, channel selection, anatomical
regions, and inclusive or exclusion ROIs, then writes counted center points
and display settings back into Imaris-compatible output files.

This repository contains source code and documentation only. It deliberately
does not distribute microscopy data, the custom Cellpose model, the Imaris
schema donor, portable builds, or installers. Those large or potentially
restricted files must only be distributed after their ownership, metadata,
and redistribution terms have been reviewed.

`Neurodot.py` is an optional self-contained single-file copy generated from
the current modular implementation. The modules under `src/neurodot/` remain
the maintained source of truth. Regenerate it after modular changes with:

```powershell
python .\tools\build_monolith.py
```

## Run without Python

Distribute the entire `dist/Neurodot/` folder and start `Neurodot.exe`. Do not
copy only the executable; its `_internal` folder is part of the application.
The safest transfer method is to zip the complete `Neurodot` folder, copy that
single archive, and extract it on the destination computer. Running the EXE
directly from inside a zip archive is not supported.

For a portable release, copy `Neurodot-portable.zip`, extract it fully,
open the extracted `Neurodot` folder, and run `Neurodot.exe`. Its SHA-256 is
recorded in `Neurodot-portable.sha256`; compare it after transfer with:

```powershell
Get-FileHash .\Neurodot-portable.zip -Algorithm SHA256
```

The portable release does not require Python, Conda, Cellpose, PyTorch, or the
model to be installed separately. GPU acceleration still requires a compatible
NVIDIA GPU and driver; Cellpose can fall back to CPU when CUDA is unavailable.

User input and output defaults are created under `Documents/Neurodot/`. Runtime
logs are written to `%LOCALAPPDATA%/Neurodot/logs/neurodot.log`.

For users who prefer a conventional Windows installation, the generated
`installer` folder contains `Neurodot-Setup.exe` and its numbered data
files. Keep that complete folder together and follow the
[installer deployment guide](docs/INSTALLER_DEPLOYMENT.md).

## Open in VS Code

Open `Neurodot.code-workspace`, then choose the **Neurodot (modular)** launch
configuration and press F5. The workspace is configured to use the existing
`cellpose_imaris` Conda environment.

To run the single-file copy, select **Neurodot (single file)** from the Run
and Debug menu and press F5.

You can also start it from the project directory:

```powershell
python run_neurodot.py
```

When running from source, input `.ims` files belong in `ims_to_inject/` and
generated scenes are written to `exported_scenes/`.

At startup, a small preflight window lets the user override both folders, the
output filename tag, Imaris Spot diameter, and the Cellpose model for that run.
The local trained model remains the default; the built-in `cpsam_v2` model is
also available. Spot diameter changes output metadata and center-point width,
not Cellpose detection.

## Source layout

- `config.py` contains user-adjustable settings and defaults.
- `imaris_io.py` owns donor discovery, HDF5 scene writing, and validation.
  Exported files also store each channel's effective GUI black/white exposure
  in Imaris `ColorRange` metadata so those display ranges reopen in Imaris.
- `image_io.py` owns channel mapping, logical image dimensions, and MIP reads.
- `detection.py` owns exposure windowing and Cellpose execution.
- `geometry.py` owns landmarks, hemispheres, counting rectangles, custom ROIs,
  inclusive/exclusion ROI selection, dorsal/ventral selection, and placeholder
  geometry.
- `gui.py` contains the exposure, landmark, channel, and ROI interface.
  Work-in-progress JSON can be saved without closing; completed exposure
  selections retain their true preview, landmark corrections are one-shot, and
  placement uses a native white crosshair without Canvas-motion redraws.
  Cellpose previews obey the final rectangle, anatomical-region, and custom-ROI
  filters. Closing offers to save partial work and exits without error dialogs.
- `startup_gui.py` collects run-specific paths, filename tag, Spot diameter,
  and model choice.
- `progress_gui.py` reports IMS loading, Cellpose processing, and output status
  when the portable application has no console.
- `workflow.py` coordinates batch inference and output creation.
- `paths.py` keeps project, resource, and eventual packaged-app paths stable.

Dependencies flow in one direction:

```text
config -> Imaris/image I/O -> detection -> geometry -> GUI -> workflow
```

The GUI remains a large module because splitting the class itself is a second,
higher-risk refactor. Its computational behavior has already been moved behind
the lower-level modules, which is the useful stability boundary.

## Handover documentation

- [Handover index](docs/HANDOVER_INDEX.md) lists exactly what to give IT and
  operators, and what to retain with a validated release.
- [Neurodot in simple terms](docs/ELI5_OVERVIEW.md) explains the complete
  pipeline for non-developers.
- [Operator quick start](docs/OPERATOR_QUICK_START.md) is the short day-to-day
  procedure for scientists.
- [Portable VM deployment guide](docs/DEPLOYMENT_GUIDE.md) covers installation,
  GPU requirements, file safety, validation, support, and rollback.
- [Windows installer deployment](docs/INSTALLER_DEPLOYMENT.md) covers the
  conventional Start-menu installation and uninstallation workflow.
- [Release acceptance checklist](docs/RELEASE_ACCEPTANCE_CHECKLIST.md) gives IT
  and scientific reviewers a repeatable sign-off test.
- The pipeline presentation is maintained separately because its source file
  is large and may contain material that requires its own publication review.

## Runtime resources

The public source repository does not include the trained Cellpose model or
Imaris donor scene. For an authorized local build, place the model at
`resources/models/cpsam_v2` and a compatible donor at
`resources/templates/donor_1_point_each_with_to.ims`. Do not publish either
resource unless you have confirmed that redistribution is permitted and that
the donor contains no sensitive acquisition metadata.

Neurodot processes images locally; the authored source does not upload images
or results to a remote service. Runtime logs can contain filenames and local
paths, so review them before sharing.

## Publication status

No open-source licence has been selected yet. Until a licence is added, the
source is publicly readable but no general permission to reuse, modify, or
redistribute it is granted. Confirm code ownership and choose a licence before
announcing the repository as open source.

## Verification

Run the lightweight regression tests with Python's built-in test runner:

```powershell
python -m unittest discover -s tests -v
```

The packaged executable also has a non-interactive diagnostic mode:

```powershell
.\dist\Neurodot\Neurodot.exe --self-test
```

It verifies imports, resources, donor structure, model loading, CUDA detection,
and Imaris center-point size metadata, then writes
`Documents/Neurodot/self_test.json`.

Before replacing v21 in production, process the same representative `.ims`
series with both versions and compare Spot counts, coordinates, landmarks,
rotation metadata, placeholders, and Imaris editability.

## Rebuilding the standalone release

PyInstaller must be installed in the `cellpose_imaris` environment. From this
project directory:

```powershell
.\packaging\build_portable.ps1
.\packaging\verify_portable.ps1
.\packaging\make_portable_zip.ps1
```

The PyInstaller specification deliberately bundles the CUDA and MinGW runtime
DLLs required by this Conda environment. The resulting portable folder is
about 6.6 GiB.

The current executable is unsigned. Windows SmartScreen may therefore warn on
other computers until it is signed with a trusted code-signing certificate.

After building and verifying the portable folder, create the Windows installer
with:

```powershell
.\packaging\build_installer.ps1
```

This requires Inno Setup 6 on the build machine only. Target machines do not
need Inno Setup or any Python tooling.
