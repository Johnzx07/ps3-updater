# Setup Guide — What You Need on Your PC

This app is written in **Python** and runs entirely from your own computer.
Here's everything you need, in order. If you already have Python 3 with the
required packages below installed (most people do), you can skip straight to step 4.

## Step 1 — Install Python (skip if you already have it)

Check first: open a terminal and run

```bat
python --version
```

- **Prints `Python 3.x`** → you're good, go to step 2.
- **Says "not recognized" or opens the Microsoft Store** → install Python:

1. Go to https://www.python.org/downloads/ and click **Download Python 3.x**.
2. Run the installer.
3. **IMPORTANT:** on the first installer screen, tick the box
   **"Add python.exe to PATH"** before clicking *Install Now*.
4. When it finishes, close any open terminals and run `python --version` again.

> The app needs Python 3 (any recent version — 3.9 or newer is fine).
> It also uses **tkinter**, the GUI toolkit that ships with the standard
> Windows Python installer — you do not install tkinter separately.

## Step 2 — Install Git (only if you want to update the app later)

The app itself does not need Git. You only need it if you plan to pull future
updates of this project from GitHub:

1. Go to https://git-scm.com/download/win and run the installer with default options.
2. Verify in a new terminal: `git --version`

## Step 3 — Install the packages the app needs: `requests` + `PyYAML` (+ optional `Pillow`)

The app uses Python's built-in standard library (including tkinter) plus **two
required** third-party packages and one optional:

- **`requests`** — makes the PSN network requests and downloads the `.pkg` files.
- **`PyYAML`** — reads your RPCS3 `config\games.yml` so the app knows which games you own.
- **`Pillow`** *(optional)* — renders box-art thumbnails in the results table. The
  app works fine without it; install it only if you want artwork next to each game.

If they aren't already installed, open a terminal in this folder and run:

```bat
python -m pip install requests PyYAML
```

(If `python` isn't recognized but you use the **py** launcher instead, run:)

```bat
py -3 -m pip install requests PyYAML
```

Or install everything at once (required + optional Pillow) from the requirements
file in this folder:

```bat
python -m pip install -r requirements.txt
```

That's all — nothing else to install.

## Step 4 — Run the app

1. Put this folder somewhere convenient (e.g. `C:\Tools\ps3-updater`).
2. Double-click **Start PS3 Updater.bat**.
   - The launcher finds a working Python (tries `py -3.12`, then any `py -3.x`,
     then plain `python`) and checks that **tkinter**, **requests** and
     **PyYAML** are all importable before it starts the app.
   - If it says **"No suitable Python found"**: install Python per step 1 with
     the "Add to PATH" box ticked, then double-click again.
   - If it says **Python was found but required module(s) are missing**, it will
     print exactly which package is absent and the command to run (step 3). Run
     that once in a terminal, then double-click this file again. The launcher
     never installs anything for you on its own.
3. In the window that opens:
   - **RPCS3:** pick your RPCS3 install folder — the one that contains
     `config\games.yml` (the field shows the default location).
   - **Downloads:** where `.pkg` files should be saved.
   - Either click **Scan RPCS3 library (games.yml)** to list every game you own,
     or paste a single serial (e.g. `BLUS30675`) and press **Search updates**.
   - Review the results, then click **Download selected (in order)**.
   - Use **Stop** to cancel mid-download, and **Open downloads folder** to jump
     to where files are saved.

## Step 5 — Install the downloaded updates into RPCS3

The app downloads `.pkg` files; it does not install them itself (RPCS3's own
installer is more reliable). For each game:

1. Open RPCS3 → *File → Install Package(s)* and select a `.pkg`, or
2. Drop the `.pkg` into your RPCS3 `downloads` folder — RPCS3 will offer to
   install it on next launch.

**Important:** many games have several updates, and each one builds on the last.
You must install them in **ascending version order**, not just the newest file.
The app already downloads them in that order (oldest → newest), so simply install
them top-to-bottom as they appear. Installing only the newest `.pkg` can leave a
game with an incomplete or mismatched update set.

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| Double-clicking the .bat does nothing / window flashes closed | Python not on PATH — reinstall with "Add python.exe to PATH" ticked (step 1) |
| Console says `No suitable Python found` | No usable Python 3 is installed, or only a Microsoft Store stub is present — install real Python per step 1 |
| Console says `Python was found … but required module(s) are missing: requests / PyYAML` | Run the command it prints (step 3): `python -m pip install requests PyYAML`, then double-click again |
| Console says a module is missing and lists **tkinter** | tkinter ships with the standard Windows Python installer — reinstall Python from python.org with "Add to PATH" ticked; do not use a stripped/embedded build |
| App opens but scan finds no games (`No games found in games.yml`) | Wrong RPCS3 folder — point it at the one that actually contains `config\games.yml` (step 4) |
| A game shows "Not found" / no updates available | You're offline, or that title has no PSN update for your region; try another serial to confirm connectivity |
| Download finishes but says SHA-1 differs from Sony's listing | The file is kept with a warning (Sony sometimes lists a stale hash). Re-download if RPCS3 rejects it; see README "Security" |
