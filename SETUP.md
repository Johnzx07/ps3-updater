# Setup Guide — What You Need on Your PC

This app is written in **Python** and runs entirely from your own computer.
Here's everything you need, in order. If you already have Python 3 with the
standard libraries (most people do), you can skip straight to step 4.

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
> It does **not** need anything else installed: no extra packages, no pip
> installs, no internet account. Everything it uses ships with Python itself.

## Step 2 — Install Git (only if you want to update the app later)

The app itself does not need Git. You only need it if you plan to pull future
updates of this project from GitHub:

1. Go to https://git-scm.com/download/win and run the installer with default options.
2. Verify in a new terminal: `git --version`

## Step 3 — Install the one package the app needs: `requests`

The app uses Python's built-in standard library plus **one** third-party
package, `requests`. If it isn't already installed, open a terminal and run:

```bat
python -m pip install requests
```

(If you get an error about `pip`, try `py -3 -m pip install requests`.)
That's the only dependency — nothing else to install.

## Step 4 — Run the app

1. Put this folder somewhere convenient (e.g. `C:\Tools\ps3-updater`).
2. Double-click **Start PS3 Updater.bat**.
   - The launcher automatically finds a suitable Python (tries 3.12, then any
     3.x, then plain `python`) and starts the app.
   - If it says no Python was found: install Python per step 1 with the
     "Add to PATH" box ticked, then double-click again.
3. In the window that opens:
   - **Games file:** pick your RPCS3 `config\games.yml` (default location is
     shown in the field).
   - **Downloads folder:** where `.pkg` files should be saved.
   - Click **Scan for updates**, review the list, click **Download all**.

## Step 5 — Install the downloaded updates into RPCS3

The app downloads `.pkg` files; it does not install them itself (RPCS3's own
installer is more reliable). For each game:

1. Open RPCS3 → *File → Install Package(s)* and select the newest `.pkg`, or
2. Drop the `.pkg` into your RPCS3 `downloads` folder — RPCS3 will offer to
   install it on next launch.

Install updates in **ascending version order** if a game has several (the app
already downloads them in that order, so just install them top-to-bottom).

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| Double-clicking the .bat does nothing / window flashes closed | Python not on PATH — reinstall with "Add python.exe to PATH" ticked |
| `No suitable Python found` message in console | Same as above, or only a Microsoft Store stub is installed |
| Console says `Missing dependency 'requests'...` and closes | Run `python -m pip install requests` (step 3) |
| App opens but scan finds no games | Wrong `games.yml` path — it's inside your RPCS3 folder under `config\` |
| "Not found" for every game | You're offline, or the title IDs in games.yml are wrong |
