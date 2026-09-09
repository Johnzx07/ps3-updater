# PS3 Updater for RPCS3

Finds and downloads PSN title updates (`.pkg` files) for your RPCS3 games —
straight from Sony's servers. No account needed.

## Requirements

- Windows + Python 3 (any recent version, 3.9 or newer). `tkinter` ships with
  the standard Windows Python installer — nothing extra to install for it.
- Two pip packages:
  - **`requests`** — used for all PSN network requests and downloads.
  - **`PyYAML`** (imported as `yaml`) — used to read your RPCS3
    `config\games.yml`.

  Install both with:

      python -m pip install requests PyYAML

  or, if you use the `py` launcher:

      py -3 -m pip install requests PyYAML

  (or simply `python -m pip install -r requirements.txt`)
- A folder containing your RPCS3 `config\games.yml` file.

**New here? Read [SETUP.md](SETUP.md) first** — it walks through installing
Python (exact steps and commands), the two packages needed, running the app,
and installing the downloaded updates into RPCS3.

## How to run it

**Double-click `Start PS3 Updater.bat`** in this folder. That's all.

The launcher finds a working Python, checks that `tkinter`, `requests` and
`PyYAML` are importable, and only then starts the app. If something is wrong
it tells you exactly what to run (e.g. `python -m pip install requests PyYAML`)
and keeps the window open so you can read it — it never closes silently and
never installs anything without your say-so.

(Do NOT double-click the `.py` file directly — Windows may pick a Python that
is missing libraries and the window will never appear.)

## Using the app

1. **Scan RPCS3 library (games.yml)** — checks every game in your `games.yml`
   at once. On first use pick your RPCS3 install folder (it is remembered).
   Or paste a single serial like `BLUS30675` into the top box and press
   **Search updates**.
2. Rows appear with install order (#), version, size. Games with no updates
   show "no updates".
3. Tick the rows you want → **Download selected (in order)**.
   Updates are incremental: if a game needs 1.06→1.07→1.08, all three must be
   installed in that order — the app downloads them numbered so you can't mix
   them up. Use **Stop** to cancel a running download; partial files are removed.
4. Files land in your downloads folder (default `~/PS3Updates`, changeable from
   the GUI) under:

       PS3Updates/
         PlayStation 3/
           [SERIAL] Game Name/

## Installing into RPCS3

Drag the `.pkg` files onto the RPCS3 window, or use **File → Install Packages**.
For a game with several update packages, install **all of them in ascending
version order** (top-to-bottom by the # column) — do not skip earlier
incremental updates and jump straight to the newest.

## Security / TLS note

Sony's PSN endpoints do not present standard public certificates:

- The XML lookup host (`a0.ww.np.dl.playstation.net`) is signed by Sony's own
  private root CA ("SCEI DNAS Root 05"), which no public trust store contains,
  so normal verification fails for every client.
- The CDN download host (`b0.ww.np.dl.playstation.net`) serves a valid public
  Akamai/DigiCert certificate, but under its internal name rather than the
  requested hostname, so normal verification fails with a hostname mismatch.

Both facts were verified against the live endpoints (control sites such as
google.com and pypi.org verify cleanly). Because of this, the app uses
`verify=False` **only for those two Sony requests** — it is never applied to
any other domain. The trade-off: the connection to Sony's servers is not
certificate-verified. As a compensating control, every downloaded `.pkg` is
checked against the SHA-1 hash in Sony's own metadata (a mismatch keeps the
file but warns you), and RPCS3 verifies PKG signatures itself at install time.

## Notes

- **Intended use:** this tool downloads official title updates that Sony
  publishes for PS3 games, for use with your own legally owned game copies in
  RPCS3. It does not access or modify any Sony account, and it does not
  bypass any DRM — the `.pkg` files are exactly what a real console would
  download from PSN. Use it only with games you own.
- Licensed under MIT (see [LICENSE](LICENSE)). Third-party runtime deps are all
  permissive: `requests` (Apache-2.0), `PyYAML` (MIT); their transitive deps —
  urllib3 (MIT), charset-normalizer (MIT), idna (BSD-3-Clause), certifi (MPL-2.0)
  — are compatible with MIT.
- If a download says "SHA-1 differs from Sony's listing", that's Sony's own
  metadata being stale (confirmed with real packages) — the file is fine and
  RPCS3 verifies it at install time anyway.
- CLI mode: `python ps3_updater.py --cli BLUS30675 -o PS3Updates`

## Testing

Two test suites, both offline/deterministic (no Sony servers required):

    python gui_selftest.py     # drives the real GUI end-to-end with a faked network layer
    python test_games_yml.py   # read_games_yml() against flat + nested games.yml formats

`gui_selftest.py` covers progress, completion, error and stop branches; it runs
standalone from this folder (downloads go to a temp dir, never into `PS3Updates`).
