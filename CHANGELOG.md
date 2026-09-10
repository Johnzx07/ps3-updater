# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Support links in the GUI** — header buttons for the YouTube channel
  ([@TheNewGamePluss](https://www.youtube.com/@TheNewGamePluss)) and Ko-fi
  ([thenewgameplus](https://ko-fi.com/thenewgameplus)), plus an **About…** dialog
  with both links and the repository URL.

### Changed
- README: release link now points to the renamed public repository
  (`ps3-rpcs3-game-updater`); new "Support & Subscribe" section.

## [1.0.0] - 2026-09-10

Initial public release. A small Windows tool that finds and downloads PSN title
updates (`.pkg` files) for RPCS3 games directly from Sony's public update servers —
no account required.

### Added
- **GUI (tkinter)** with:
  - RPCS3 install-folder field (auto-finds `config\games.yml`) and a Downloads folder field.
  - **Scan RPCS3 library (games.yml)** to list every owned game, or paste a single
    serial and press **Search updates**.
  - Results table showing version, size, and SHA-1 for each available update, with
    box-art thumbnails when local RPCS3 artwork is available.
  - **Download selected (in order)** — downloads in ascending version order with
    live per-row progress and an overall progress bar.
  - **Stop** to cancel mid-download; **Open downloads folder** shortcut.
- **CLI mode** (`python ps3_updater.py --cli BLUS30675 -o PS3Updates`) for headless use.
- **SHA-1 verification** of every downloaded file against Sony's metadata, with a
  keep-with-warning behavior when the listed hash is stale.
- **`Start PS3 Updater.bat`** launcher that prefers a packaged `dist\PS3Updater.exe`
  when present and otherwise locates a working Python, verifying `tkinter`,
  `requests`, and `PyYAML` are importable before launch (it never auto-installs packages).
- **`requirements.txt`** listing the runtime dependencies (`requests`, `PyYAML`,
  plus optional `Pillow`).
- **Prebuilt Windows executable** published as a GitHub Release asset
  (`PS3Updater.exe`, one-file PyInstaller build) with a matching `SHA256SUMS.txt`.
- Documentation: `README.md`, `SETUP.md`, `BUILD_EXE.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `TEST_MATRIX.md`.
- Tests: `gui_selftest.py` (headless GUI logic) and `test_games_yml.py`
  (deterministic parser test, temp dirs only).

### Changed
- **Professional Windows UI pass** (`ps3_updater.py`, GUI only — core lookup,
  download, SHA-1 and CLI code untouched):
  - Header bar with app title/subtitle; native theme (vista/winnative/clam) plus
    consistent Segoe UI typography.
  - Folders moved into a labeled **Folders** group box (Downloads + RPCS3).
  - New summary line above the table: per-game update count, total size and
    latest version after each search; install-order hint ("Install top to
    bottom — the # column is install order.").
  - Rows are color-coded by state: green ✓ done, red ✗ failed / error rows,
    blue while downloading.
  - Status bar announces download start with total size; window has a sensible
    minimum size (920×560).
- `Scan RPCS3 library` now honors a path typed into the RPCS3 field even if it
  was never saved via Browse.

### Notes
- Downloads are saved under `<Downloads folder>\PlayStation 3\[<TITLE_ID>] <Name>`;
  the default downloads folder is `~/PS3Updates`.
- The app talks to Sony's public PSN update endpoints (`a0.ww.np.dl.playstation.net`
  and the CDN) using `verify=False`, scoped to those two requests only, because
  Sony's certificate chains do not validate against standard public CAs — see
  README "Security".

[1.0.0]: https://github.com/Johnzx07/ps3-rpcs3-game-updater/releases/tag/v1.0.0
