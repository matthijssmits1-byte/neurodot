# Neurodot

Neurodot is a Windows desktop application for guided, reproducible cell
detection in multichannel Imaris microscopy images. It combines Cellpose with
operator-selected landmarks, exposure calibration, channel and anatomical-area
selection, and inclusive or exclusion ROIs. Counted center points and display
settings are written to Imaris-compatible output files.

This is the source-development project. It does not contain an executable,
portable build, installer, trained model, Imaris donor, or microscopy data.

## Open in VS Code

Open `Neurodot.code-workspace`, select a Python 3.12 environment containing the
project dependencies, and choose a launch target:

- **Neurodot (modular)** runs the complete application from `src/neurodot/`.
- **Neurodot (quality overview only)** opens the series overview without moving
  or processing files, making UI development fast and safe.
- **Neurodot (single file)** runs the automatically generated `Neurodot.py`
  backup copy.

The modular package is the only source of truth. Do not manually edit
`Neurodot.py`.

## Environment setup

From the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Run the application with:

```powershell
python run_neurodot.py
```

Cellpose's built-in model is selected automatically when no authorized local
model exists. Imaris output creation requires a compatible authorized donor at
`resources/templates/donor_1_point_each_with_to.ims`.

## Runtime folders

- Put source `.ims` files in `data/input/`, or select another input folder in
  the startup window.
- Generated files go to `data/output/`, or the selected output folder.
- Files excluded during image-quality review move to
  `<input>/_excluded_from_analysis/` after confirmation. A manifest records the
  original and new paths, and name collisions never overwrite an existing file.

Input data, output data, donor files, model weights, JSON settings, and logs are
excluded from source control.

## Development cycle

1. Edit modules under `src/neurodot/`.
2. Run the relevant VS Code launch target.
3. Run the test suite:

   ```powershell
   python -m unittest discover -s tests -v
   ```

4. Regenerate the optional single-file copy:

   ```powershell
   python tools/build_monolith.py
   ```

5. Run the tests again; they verify that the generated file matches the modules.

Executable and portable packaging are intentionally outside this development
cycle and should only be added for a validated release.

## Source layout

```text
src/neurodot/
  config.py          Settings and runtime defaults
  startup_gui.py     Folder, tag, model, and Spot-size selection
  quality_review.py  Zoomable series overview and recoverable exclusions
  image_io.py        Imaris image and MIP reading
  detection.py       Exposure processing and Cellpose execution
  geometry.py        Landmarks, hemispheres, regions, and ROIs
  gui.py             Main landmark, exposure, and preview interface
  imaris_io.py       Imaris scene and metadata writing
  workflow.py        End-to-end orchestration
```

See [Architecture](docs/ARCHITECTURE.md) for the data flow and maintenance
rules. Neurodot is research software; operators must validate its output for
their imaging protocol and model.
