# Neurodot Windows installer

## What to copy

Copy every file whose name starts with `Neurodot-Setup` to one folder on the
destination Windows machine. This is the setup executable, three numbered data
files, and `Neurodot-Setup.sha256`. Do not mix files from different builds.

The numbered data files are required because the self-contained Neurodot
runtime is larger than the safe size of one Windows installer executable. Keep
all files together and run only `Neurodot-Setup.exe`.

## Installation

1. Verify every file against `Neurodot-Setup.sha256`.
2. Keep all setup files in one local folder.
3. Run `Neurodot-Setup.exe`.
4. Accept the default per-user installation unless IT requires an all-users
   installation and has administrator rights.
5. Start Neurodot from the Start menu or optional desktop shortcut.
6. Run a representative test dataset and inspect both outputs in Imaris before
   production use.

The installer supplies Python, Cellpose, PyTorch, scientific libraries, the
default local model, graphics, Tcl/Tk, and the Imaris schema donor. Python and
Conda do not need to be installed separately.

## Supported target

This installer targets 64-bit Windows 10 or Windows 11. It is not a macOS or
Linux installer. Allow at least 12 GB of free disk space during installation;
the setup set is about 4.1 GB and the installed application about 6.7 GB. An
NVIDIA GPU is optional. GPU acceleration requires a compatible NVIDIA driver
and GPU access in the physical machine or VM. Without CUDA, Neurodot falls back
to CPU.

Imaris is not required to run Neurodot, but it is required on the machine used
to inspect and edit the generated `.ims` files.

## Security and operations

- The current installer and executable are not code-signed. Windows
  SmartScreen or organisational application control may warn or block them.
- Verify the supplied SHA-256 values and use the normal IT approval process.
- Neurodot opens source `.ims` files read-only and modifies separate output
  copies.
- Existing outputs with the same name may be overwritten. Use unique output
  tags or a fresh output folder.
- Install upgrades into the offered version location and retain the previous
  validated installer for rollback.
- Uninstall Neurodot through Windows Settings, **Installed apps**. User data,
  source images, outputs, settings JSON files, and diagnostic logs are not
  deleted by the uninstaller.

Runtime logs are stored at `%LOCALAPPDATA%\Neurodot\logs\neurodot.log`.
