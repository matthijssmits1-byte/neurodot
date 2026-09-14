# Neurodot portable release acceptance checklist

## Package

- [ ] ZIP filename and release version match
- [ ] SHA-256 matches the supplied checksum file
- [ ] ZIP was extracted completely to a local folder
- [ ] The previous verified version remains available for rollback
- [ ] Antivirus or application-control approval is documented

## VM

- [ ] User can read the input folder
- [ ] User can create and overwrite files in the output folder
- [ ] Free disk includes the application and two output copies per input file
- [ ] Packaged `--self-test` returns exit code 0
- [ ] `self_test.json` records the expected CPU or CUDA device

## Representative run

- [ ] Startup window opens without white flashes or symbol corruption
- [ ] Spot diameter defaults to 5.0 µm and accepts a validated custom value
- [ ] Main GUI loads an `.ims` series
- [ ] Native white placement cursor remains responsive
- [ ] Channel enable/disable controls preview navigation
- [ ] Midline derives the centre and the centre remains editable
- [ ] Whole, Dorsal, and Ventral selections filter the preview correctly
- [ ] Left and right inclusion/exclusion ROIs filter the preview correctly
- [ ] Saving and loading a partial JSON restores the work
- [ ] Closing offers Yes, No, and Cancel without an error dialog
- [ ] Progress windows remain visible during loading and output writing

## Imaris review

- [ ] Both `_L.ims` and `_R.ims` outputs open
- [ ] Image pixels and physical geometry align with the source
- [ ] Channel display ranges match the GUI exposure settings
- [ ] Spot groups `g`, `b`, `r`, and `405` contain expected detections
- [ ] Predicted Spots remain centre points; their physical diameter statistics
      and centre-point pixel width match the startup selection
- [ ] `ce`, `bo`, `si`, `to`, and rotation metadata are present
- [ ] Empty-channel placeholders are inside the rectangle and separated
- [ ] Representative counts agree with manual review
- [ ] Reviewer, date, source data, model, settings JSON, and release checksum
      are recorded
