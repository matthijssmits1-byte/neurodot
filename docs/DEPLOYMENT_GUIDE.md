# Neurodot portable deployment guide

## Recommended deployment method

Use the portable ZIP for a controlled Windows virtual machine. This is the
simplest handover because it includes Python, Cellpose, PyTorch, scientific
libraries, Tcl/Tk, the default model, graphics, and the Imaris schema donor.
The VM team does not need to install Python or create a Conda environment.

The release is a folder-based portable application, not a single standalone
`.exe`. Every file in the extracted `Neurodot` folder must stay together.

Current release files:

- `Neurodot-portable.zip`
- `Neurodot-portable.sha256`
- ZIP size: 4,624,354,672 bytes
- Extracted size: approximately 6.65 GiB across about 3,600 files

## VM requirements

- 64-bit Windows 10 or Windows 11
- A local disk location for the extracted application
- Read access to input `.ims` files
- Create, write, and overwrite permission in the selected output folder
- Enough RAM for full-resolution maximum-intensity projections and Cellpose
- Enough free disk for the 6.65 GiB application plus two full output copies of
  every input `.ims` file and working headroom

An NVIDIA GPU is optional. GPU use requires a compatible NVIDIA driver and GPU
access inside the VM through passthrough or the organisation's virtual-GPU
solution. The portable folder contains the CUDA-enabled PyTorch runtime, but it
cannot contain the host NVIDIA driver. Neurodot falls back to CPU when CUDA is
unavailable, which can be much slower.

The VM does not need Imaris to run Neurodot. An Imaris installation is needed
where users will inspect and edit the resulting `.ims` files.

## Installation

1. Copy both the ZIP and checksum file to the VM.
2. Verify the transfer in PowerShell:

   ```powershell
   Get-FileHash .\Neurodot-portable.zip -Algorithm SHA256
   ```

   Expected SHA-256:

   ```text
   8F1E7F01C5CE2AC6B4B3A0F9567F00783C4F336F71BA66BD241875474E08867C
   ```

3. Extract the ZIP completely to a local path such as
   `C:\Applications\Neurodot`. Do not run the program from inside the ZIP.
4. Keep the extracted folder intact. Do not copy only `Neurodot.exe`.
5. If organisational antivirus or application-control policy blocks the
   executable, approve the verified release through the normal IT process.
   The current executable is not code-signed, so Windows SmartScreen may warn.

No administrator rights are normally required when the application and data
folders are writable by the user.

## Technical validation

Run the packaged self-test before giving the VM to users:

```powershell
$process = Start-Process `
    .\Neurodot\Neurodot.exe `
    -ArgumentList '--self-test' `
    -Wait `
    -PassThru
$process.ExitCode
```

Exit code `0` means the self-test passed. The detailed report is written to:

```text
%USERPROFILE%\Documents\Neurodot\self_test.json
```

Check the report for resource validation, model loading, Tk initialization,
and CUDA detection. CUDA should be reported as available only on a GPU-enabled
VM.

Then process a representative non-production `.ims` file and verify both the
left and right outputs in the organisation's Imaris version. This acceptance
test matters because a software self-test cannot judge biological accuracy or
future Imaris-version behaviour.

## File and data safety

### Protections

- Neurodot opens source `.ims` files read-only during image reading and
  inference.
- It creates left and right output copies in the selected output folder and
  modifies those copies.
- Cancelling the GUI before batch processing is a normal exit and writes no
  `.ims` outputs.
- The GUI can save incomplete work as JSON before closing.
- The program validates image geometry, required resources, Spot coordinates,
  and the generated Imaris structures.
- Failures are recorded in a persistent diagnostic log.

### Important limits

- An existing output file with the same name can be overwritten. Use a fresh
  output folder or a unique output tag for every production run.
- A failure after output creation can leave a partial output file. Treat only
  files from a successfully completed and reviewed run as final.
- Neurodot runs with the current user's filesystem permissions. It is not a
  security sandbox.
- The default local model runs offline. Selecting Cellpose's built-in model may
  involve Cellpose's own model-cache behaviour, so offline deployments should
  use the bundled local model.
- The executable is unsigned. The checksum proves that a copied ZIP matches
  this release, but it does not replace organisational code review, malware
  scanning, or code signing.

## Scientific safety

Neurodot reduces repetitive manual work. It does not replace scientific
review. The operator still controls the landmarks, exposure, enabled channels,
anatomical region, and custom ROIs. Cellpose previews use the same spatial
filters as final counting, and the outputs remain editable in Imaris.

For a new tissue type, microscope configuration, marker panel, model, or Imaris
version, validate Neurodot against a manually reviewed reference set before
production use. Record the Neurodot version, ZIP checksum, model selection,
settings JSON, source files, and reviewer approval.

## Operations and support

- Run the application and datasets from local VM storage when possible. Large
  `.ims` files and thousands of portable-library files perform poorly over a
  network share.
- Keep input and output folders separate.
- Preserve the previous verified portable ZIP for rollback.
- Upgrade by extracting a new version into a new folder. Do not merge new and
  old portable folders.
- Diagnostic log:
  `%LOCALAPPDATA%\Neurodot\logs\neurodot.log`
- Self-test report:
  `%USERPROFILE%\Documents\Neurodot\self_test.json`

When reporting a problem, provide the Neurodot version, ZIP checksum, Windows
version, CPU/GPU details, self-test report, diagnostic log, and the stage at
which the failure occurred. Share microscopy data only through an approved
data-handling route.
