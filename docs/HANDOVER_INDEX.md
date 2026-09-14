# Neurodot handover pack

## Give the VM or IT team

- All files beginning with `Neurodot-Setup`: the setup `.exe`, its three
  numbered `.bin` files, and the `.sha256` manifest
- `INSTALLER_DEPLOYMENT.md`
- `RELEASE_ACCEPTANCE_CHECKLIST.md`

Run `Neurodot-Setup.exe` with every numbered `.bin` file beside it. The
installer is the simplest normal Windows deployment and avoids a separate
Python, Conda, Cellpose, PyTorch, and model installation.

The v25 setup files remain rollback artifacts; do not mix their `.bin` files
with the setup executable.

`Neurodot-portable.zip`, its checksum, and `DEPLOYMENT_GUIDE.md` remain an
alternative when IT prefers an application folder that is not installed.

## Give operators

- `OPERATOR_QUICK_START.md`
- `ELI5_OVERVIEW.md`
- `Neurodot_pipeline_showcase_v25.pptx`

## Keep with the validated release

- The original installer files and their SHA-256 checksum
- The portable ZIP and checksum, if that deployment method is retained
- The source-code version used to build it
- A representative acceptance-test dataset and reviewed outputs
- The selected Cellpose model
- Settings JSON files from production runs
- The completed release acceptance checklist

Do not replace a validated release without rerunning the technical and
scientific acceptance checks. Retain the previous installer so the last
verified version remains available for rollback.
