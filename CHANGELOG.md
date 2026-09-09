# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-08

Initial release. A small Windows tool that finds and downloads PSN title updates
(`.pkg` files) for RPCS3 games directly from Sony's public update servers — no
account required.

### Added
- **GUI (tkinter)** with:
  - RPCS3 install-folder field (auto-finds `config\games.yml`) and a Downloads folder field.
  - **Scan RPCS3 library (games.yml)** to list every owned game, or paste a single
    serial and press **Search updates**.
  - Results table showing version, size, and SHA-1 for each available update.
  - **Download selected (in order)** — downloads in ascending version order with
    live per-row progress and an overall progress bar.
  - **Stop** to cancel mid-download; **Open downloads folder** shortcut.
- **CLI mode** (`python ps3_updater.py --cli BLUS30675 -o PS3Updates`) for headless use.
- **SHA-1 verification** of every downloaded file against Sony's metadata, with a
  keep-with-warning behavior when the listed hash is stale.
- **`Start PS3 Updater.bat`** launcher that locates a working Python and verifies
  `tkinter`, `requests`, and `PyYAML` are importable before launch, printing exact
  fix-it commands (it never auto-installs packages).
- **`requirements.txt`** listing the two third-party runtime dependencies.
- Documentation: `README.md`, `SETUP.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- Tests: `gui_selftest.py` (headless GUI logic) and `test_games_yml.py`
  (deterministic parser test, temp dirs only).

### Notes
- Downloads are saved under `<Downloads folder>\PlayStation 3\[<TITLE_ID>] <Name>`;
  the default downloads folder is `~/PS3Updates`.
- The app talks to Sony's public PSN update endpoints (`a0.ww.np.dl.playstation.net`
  and the CDN) using `verify=False`, scoped to those two requests only, because
  Sony's certificate chains do not validate against standard public CAs — see
  README "Security".

[1.0.0]: https://github.com/Johnzx07/ps3-updater/releases/tag/v1.0.0
