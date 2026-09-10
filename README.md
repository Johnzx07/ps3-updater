# PS3 Updater for RPCS3

Finds and downloads official PSN title updates (`.pkg` files) for your RPCS3 games — straight from Sony's servers. No account needed.

## Requirements

- Windows + Python 3 (any recent version, 3.9 or newer). `tkinter` ships with the standard Windows Python installer — nothing extra to install for it.
- Two required pip packages, plus one optional:
  - **`requests`** — used for all PSN network requests and downloads.
  - **`PyYAML`** (imported as `yaml`) — used to read your RPCS3 `config\games.yml`.
  - **`Pillow`** *(optional)* — renders box-art thumbnails in the results table; the app works fine without it.

  Install with:

      python -m pip install requests PyYAML

  or, if you use the `py` launcher:

      py -3 -m pip install requests PyYAML

  (or simply `python -m pip install -r requirements.txt`, which also installs optional Pillow)
- A folder containing your RPCS3 `config\games.yml` file.

**New here? Read [SETUP.md](SETUP.md) first** — it walks through installing Python (exact steps and commands), the required packages, running the app, and installing the downloaded updates into RPCS3.

## How to run it

### Option 1: Prebuilt Windows Release (Recommended for normal users)

1. Go to the [GitHub Releases](https://github.com/Johnzx07/ps3-rpcs3-game-updater/releases) page.
2. Download **`PS3Updater.exe`** from the latest release (v1.0.0 and later).
3. Put it anywhere you like and double-click to launch — no Python or other setup needed.
4. Use the app to search for updates, download them, then install via RPCS3 (see below).

   Each release also ships a `SHA256SUMS.txt` so you can verify the download: on Windows run
   `certutil -hashfile PS3Updater.exe SHA256` and compare against the listed hash.

### Option 2: Source / BAT Version (For developers or advanced users)

1. Clone or download this repository.
2. Install dependencies (two required; `Pillow` is optional for box-art thumbnails):

       python -m pip install -r requirements.txt

   Or just the required pair: `python -m pip install requests PyYAML`.

3. Launch using the included batch file:

       Start PS3 Updater.bat

   Or run directly:

       python ps3_updater.py

## Using the app

1. **Scan RPCS3 library (games.yml)** — checks every game in your `games.yml` at once. On first use pick your RPCS3 install folder (it is remembered).
2. **Search by serial/title ID** — paste a single PSN title ID into the top box and press **Search updates**.
3. Results display with:
   - Game icon/artwork (when available from local RPCS3 data or Sony metadata)
   - Game title
   - Title ID / version info
   - Update versions, sizes, and total download size
4. Tick the rows you want → **Download selected (in order)**.
5. Updates are incremental: if a game needs 1.06→1.07→1.08, all three must be installed in that order — the app downloads them numbered so you can't mix them up. Use **Stop** to cancel a running download; partial files are removed.
6. Files land in your downloads folder (default `~/PS3Updates`, changeable from the GUI) under:

       PS3Updates/
         PlayStation 3/
           [SERIAL] Game Name/

## Installing into RPCS3

Drag the `.pkg` files onto the RPCS3 window, or use **File → Install Packages**. For a game with several update packages, install all of them in ascending version order (top-to-bottom by the # column) — do not skip earlier incremental updates and jump straight to the newest.

## Game metadata and artwork

The app prioritizes artwork sources as follows:

1. **Local RPCS3 data** — if you have an installed game, `ICON0.PNG` or `PIC1.png` from your RPCS3 library is used first (offline, instant).
2. **Cached metadata/artwork** — previously downloaded images are reused.
3. **Sony TMDB lookup** — when local art is unavailable, the app queries Sony's Title Metadata Database to fetch box art and titles.

If no artwork can be found, the updater continues normally and displays a placeholder or title ID only. Artwork availability does not affect update downloads.

## Security / TLS note

Sony's PSN endpoints do not present standard public certificates:

- The XML lookup host (`a0.ww.np.dl.playstation.net`) is signed by Sony's own private root CA ("SCEI DNAS Root 05"), which no public trust store contains, so normal verification fails for every client.
- The CDN download host (`b0.ww.np.dl.playstation.net`) serves a valid public Akamai/DigiCert certificate, but under its internal name rather than the requested hostname, so normal verification fails with a hostname mismatch.

Both facts were verified against the live endpoints (control sites such as google.com and pypi.org verify cleanly). Because of this, the app uses `verify=False` **only for those two Sony requests** — it is never applied to any other domain. The trade-off: the connection to Sony's servers is not certificate-verified. As a compensating control, every downloaded `.pkg` is checked against the SHA-1 hash in Sony's own metadata (a mismatch keeps the file but warns you), and RPCS3 verifies PKG signatures itself at install time.

## Notes

- **Intended use:** this tool downloads official title updates that Sony publishes for PS3 games, for use with your own legally owned game copies in RPCS3. It does not access or modify any Sony account, and it does not bypass any DRM — the `.pkg` files are exactly what a real console would download from PSN. Use it only with games you own.
- Licensed under MIT (see [LICENSE](LICENSE)). Third-party runtime deps are all permissive: `requests` (Apache-2.0), `PyYAML` (MIT); their transitive deps — urllib3 (MIT), charset-normalizer (MIT), idna (BSD-3-Clause), certifi (MPL-2.0) — are compatible with MIT.
- If a download says "SHA-1 differs from Sony's listing", that's Sony's own metadata being stale (confirmed with real packages) — the file is fine and RPCS3 verifies it at install time anyway.
- CLI mode: `python ps3_updater.py --cli BLUS30675 -o PS3Updates`

## Testing

Two test suites, both offline/deterministic (no Sony servers required):

    python gui_selftest.py     # drives the real GUI end-to-end with a faked network layer
    python test_games_yml.py   # read_games_yml() against flat + nested games.yml formats

`gui_selftest.py` covers progress, completion, error and stop branches; it runs standalone from this folder (downloads go to a temp dir, never into `PS3Updates`).

## Troubleshooting

- **Game not found** — verify the title ID is correct. Common prefixes: `BLUSxxxxx`, `BLESxxxxx`, `BCUSxxxxx`, `BCESxxxxx`, `NPUBxxxxx`, `NPEBxxxxx`.
- **No updates available** — the game may already be fully updated, or Sony hasn't published an update for it.
- **Invalid serial/title ID** — check for typos; ensure you're using a valid PSN title ID (not just a filename).
- **RPCS3 library not detected** — confirm your RPCS3 install folder contains a `config\games.yml` file and that the app can read it.
- **Metadata image missing** — artwork may not be available for some titles; the updater will still download updates correctly.
- **Download failed** — check your internet connection, try again later, or verify antivirus isn't blocking the Sony domains (`a0.ww.np.dl.playstation.net`, `b0.ww.np.dl.playstation.net`).
- **Windows SmartScreen / Antivirus warning for EXE** — this is expected for unsigned community-built executables. Download only from the official GitHub Releases page, verify the SHA256 checksum, and if you prefer, build the EXE yourself from source to confirm it matches your environment.

## SHA256 Verification (Prebuilt Release)

Each release publishes `SHA256SUMS.txt` alongside `PS3Updater.exe`. After downloading,
verify the executable against it:

```powershell
Get-FileHash "PS3Updater.exe" -Algorithm SHA256
```

or in a regular terminal:

```bat
certutil -hashfile PS3Updater.exe SHA256
```

The output should match the hash listed for `PS3Updater.exe` in `SHA256SUMS.txt`.
If it does not, delete the file and download it again.

## Support & Subscribe

This tool is built and maintained by **The New Game+**. If it saves you time, the best thanks are:

- **Subscribe on YouTube** — [youtube.com/@TheNewGamePluss](https://www.youtube.com/@TheNewGamePluss) (PlayStation, emulation and PC tutorials).
- **Support with a donation** — [ko-fi.com/thenewgameplus](https://ko-fi.com/thenewgameplus) (buy me a coffee; every bit helps keep the tool maintained).

## License

MIT — see [LICENSE](LICENSE).
