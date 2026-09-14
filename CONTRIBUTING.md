# Contributing

Bug reports and focused improvements are welcome once the public repository is
available.

Before submitting a change:

1. Do not commit `.ims` files, trained models, generated output, logs, settings
   JSON, portable builds, installers, or other research data.
2. Run `python -m unittest discover -s tests -v`.
3. Describe any effect on cell counts, coordinates, ROI filtering, exposure
   metadata, or Imaris output compatibility.
4. Keep the modules under `src/neurodot/` as the maintained source of truth.
   Regenerate `Neurodot.py` with `python tools/build_monolith.py` after a
   modular change.

Do not include confidential filenames, patient or sample identifiers, or
screenshots containing restricted metadata in issues or pull requests.
