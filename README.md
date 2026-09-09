# PS3 Updater for RPCS3

Finds and downloads PSN title updates (`.pkg` files) for your RPCS3 games —
straight from Sony's servers. No account needed.

## Requirements

- Windows + Python 3 (any recent version, 3.9 or newer).
- One package: `requests` — install with `python -m pip install requests`.
- A folder with your RPCS3 `config\games.yml` file.

**New here? Read [SETUP.md](SETUP.md) first** — it walks through installing
Python (exact steps and commands), the one package needed, running the app,
and installing the downloaded updates into RPCS3.

## How to run it

**Double-click `Start PS3 Updater.bat`** in this folder. That's all.

(Do NOT double-click the `.py` file directly — Windows may pick a Python that
is missing libraries and the window will never appear. The .bat always uses
the right one, and if anything goes wrong it shows you the error instead of
closing silently.)

## Using the app

1. **Scan RPCS3 library** — checks every game in your `games.yml` at once.
   On first use pick your RPCS3 install folder (it is remembered). Or paste a
   single serial like `BLUS30675` into the top box and press
   **Search updates**.
2. Rows appear with install order (#), version, size. Games with no updates
   show "no updates".
3. Tick the rows you want → **Download selected (in order)**.
   Updates are incremental: if a game needs 1.06→1.07→1.08, all three must be
   installed in that order — the app downloads them numbered so you can't mix
   them up.
4. Files land in `PS3Updates\PlayStation 3\[SERIAL] Game Name\` (this folder).

## Installing into RPCS3

Drag the `.pkg` files onto the RPCS3 window, or use **File → Install Packages**.
Install them top-to-bottom by the # column for multi-update games.

## Notes

- **Intended use:** this tool downloads official title updates that Sony
  publishes for PS3 games, for use with your own legally owned game copies in
  RPCS3. It does not access or modify any Sony account, and it does not
  bypass any DRM — the `.pkg` files are exactly what a real console would
  download from PSN. Use it only with games you own.
- Licensed under MIT (see [LICENSE](LICENSE)).
- If a download says "SHA-1 differs from Sony's listing", that's Sony's own
  metadata being stale (confirmed with real packages) — the file is fine and
  RPCS3 verifies it at install time anyway.
- CLI mode: `python ps3_updater.py --cli BLUS30675 -o PS3Updates`

## Testing

`gui_selftest.py` drives the real GUI end-to-end with a faked network layer —
progress, completion, error and stop branches. Run it standalone from this
folder (downloads go to a temp dir, never into `PS3Updates`):

    python gui_selftest.py
