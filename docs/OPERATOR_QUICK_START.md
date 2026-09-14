# Neurodot operator quick start

## Before starting

- Put the source `.ims` files in one input folder.
- Choose a separate output folder with enough free space. Neurodot creates two
  full `.ims` outputs per input image.
- Keep the default bundled local Cellpose model unless the study requires a
  different validated model.
- Use a new output tag when rerunning a dataset. Files with the same output
  name can be overwritten.

## Run the job

1. Open `Neurodot.exe`.
2. Select the input folder and output folder.
3. Check the output tag, model, and output Spot diameter, then select
   **Continue**. The standard diameter is 5.0 µm; changing it affects Imaris
   Spot metadata and centre-point width, not which cells Cellpose detects.
4. For each image, place the bottom midline point and drag to place the top
   midline point. Check the automatically derived centre.
5. Place `si`, `bo`, and `to` for the left and right hemispheres.
6. For each enabled channel, set exposure with the weakest positive and
   brightest background points, or select **Use series average**.
7. Choose Whole, Dorsal, or Ventral for each channel.
8. Optionally draw a separate ROI for each hemisphere. Inclusive mode keeps the
   inside. Exclusion mode removes the inside.
9. Run the Cellpose preview and review the retained count shown in the status.
   Only outlines and centroids that satisfy the current counting rules appear.
10. Save a settings JSON at any time if the work may need to be resumed.
11. Select **Save & Continue** only after all images have the required
    landmarks. Neurodot then runs the full batch and shows processing progress.

## Closing without finishing

The window X and **Cancel** button ask whether to save first.

- **Yes** opens a JSON save dialog and closes only after the save succeeds.
- **No** closes without saving.
- **Cancel** returns to the main window.

Closing the GUI intentionally is a normal exit and does not modify `.ims`
files.

## After processing

- Expect `<source><tag>_L.ims` and `<source><tag>_R.ims` in the output folder.
- Open both files in Imaris and verify image alignment, display ranges, Spot
  groups, landmarks, rotation metadata, and representative Cellpose results.
- Keep the settings JSON with the analysis record.
- If anything fails, provide `%LOCALAPPDATA%\Neurodot\logs\neurodot.log` to the
  maintainer.
