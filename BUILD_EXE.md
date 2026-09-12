# Building ps3-rpcs3-game-updater.exe

The release executable is a one-file PyInstaller build of `gui_app.py`, the
dark game-library interface.  Its `updater/` package is imported with the
application and the `assets/` folder is bundled by the checked-in spec.

## Prerequisites

- Python 3.9+ with the app's dependencies plus PyInstaller:

      python -m pip install -r requirements.txt pyinstaller

## Build (run from this folder)

```bat
pyinstaller --onefile --windowed --add-data "assets;assets" --icon assets\app.ico --name ps3-rpcs3-game-updater gui_app.py
```

Or use the checked-in spec file (same settings):

```bat
pyinstaller ps3-rpcs3-game-updater.spec
```

Output: `dist\ps3-rpcs3-game-updater.exe` (~43 MB, one-file). Build by-products
are written to `build\ps3-rpcs3-game-updater\` and `dist\` — both are gitignored.

## Verified for v2.0.0 (2026-09-12)

- Build succeeds; no missing critical imports. Warnings are all optional/conditional
  (brotli, h2, socks, chardet, numpy-for-PIL, etc.) — none affect this app.
- `tkinter.ImageTk` warning is a false positive: it IS bundled (see Analysis-00.toc),
  and the `pyi_rth__tkinter` runtime hook + `_tkinter.pyd`/tcl/tk DLLs are present,
  so artwork display works in the EXE.
- Launch test: EXE starts and displays the "PS3 RPCS3 Game Updater" window.
- RPCS3 handoff test: a frozen updater launches the configured RPCS3 executable
  with an isolated DLL directory; RPCS3 loads `VCRUNTIME140.dll` from Windows
  System32 rather than the updater's temporary extraction folder.
- Existing-RPCS3 test: the app detects the single-instance lock and queues an
  approved package handoff until RPCS3 closes.
- `Start PS3 RPCS3 Game Updater.bat` prefers `dist\ps3-rpcs3-game-updater.exe` (Step 0) and falls back to
  running from source when the EXE is absent — verified end-to-end.

## Notes

- One-file EXEs spawn a child process (bootloader + app) — when killing test
  instances, kill both PIDs.
