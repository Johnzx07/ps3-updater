# Changelog

## v2.0.0 — 2026-09-12

This is the full v2 replacement release of **PS3 RPCS3 Game Updater**.

### New experience

- Rebuilt desktop UI with compact artwork cards, filters, title search, title-ID lookups, update state, per-game progress, and an activity log.
- Added an in-window game-details sidebar. Clicking a card or **Details** shows versions, package sizes, available updates, download controls, and the package folder shortcut.
- Added a title-based local library search while keeping the exact title-ID updater lookup.

### Downloads and RPCS3 installation

- Added direct per-game package-folder access.
- Added a post-download confirmation before launching RPCS3’s native package installer.
- Added single-instance-aware install queuing: a confirmed install waits for an already-open RPCS3 to close, then launches automatically without causing RPCS3’s second-instance failure.
- Protected the RPCS3 child process from the frozen updater’s temporary DLL directory, ensuring it uses the correct system/RPCS3 Visual C++ runtime.
- Documented the native RPCS3 game-scan and package-review stages with screenshots.

### Project cleanup

- Renamed the main implementation module, launcher, spec file, executable, configuration identity, and documentation for `ps3-rpcs3-game-updater`.
- Removed the original v1-only GUI test, parser test, setup guide, contribution guide, and test matrix in favor of the v2 release documentation.

[v2.0.0](https://github.com/Johnzx07/ps3-rpcs3-game-updater/releases/tag/v2.0.0)
