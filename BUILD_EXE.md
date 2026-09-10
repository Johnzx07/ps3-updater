# Building PS3Updater.exe

The release executable is a one-file PyInstaller build of `ps3_updater.py`.

## Prerequisites

- Python 3.9+ with the app's dependencies plus PyInstaller:

      python -m pip install -r requirements.txt pyinstaller

## Build (run from this folder)

```bat
pyinstaller --onefile --windowed --name PS3Updater ps3_updater.py
```

Or use the checked-in spec file (same settings):

```bat
pyinstaller PS3Updater.spec
```

Output: `dist\PS3Updater.exe` (~20 MB, one-file). Build by-products also produced
here: `build\PS3Updater\` and `dist\` — both are gitignored.

## Verified (2026-09-09)

- Build succeeds; no missing critical imports. Warnings are all optional/conditional
  (brotli, h2, socks, chardet, numpy-for-PIL, etc.) — none affect this app.
- `tkinter.ImageTk` warning is a false positive: it IS bundled (see Analysis-00.toc),
  and the `pyi_rth__tkinter` runtime hook + `_tkinter.pyd`/tcl/tk DLLs are present,
  so artwork display works in the EXE.
- Launch test: EXE starts, shows window "PS3 Updater — RPCS3 game updates", stays
  alive 30+ s with no crash; clean shutdown via taskkill.
- `Start PS3 Updater.bat` prefers `dist\PS3Updater.exe` (Step 0) and falls back to
  running from source when the EXE is absent — verified end-to-end.

## Notes

- One-file EXEs spawn a child process (bootloader + app) — when killing test
  instances, kill both PIDs.
