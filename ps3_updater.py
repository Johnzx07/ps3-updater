#!/usr/bin/env python3
"""
PS3 Updater for RPCS3
=====================
Scans your RPCS3 library (games.yml) or a single serial, finds available
title updates on Sony's PSN servers, downloads the .pkg files in correct
install order, and verifies each one with SHA-1.

Usage:  python ps3_updater.py          (GUI)
        python ps3_updater.py --cli BLUS30089   (headless test / scripting)

Only stdlib + requests + PyYAML are required.
"""

import argparse
import configparser
import hashlib
import os
import queue
import re
import sys
import threading
import time
import traceback
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency 'requests'. Install with:  pip install requests")
    sys.exit(1)

APP_NAME = "PS3Updater"
UPDATE_XML_URL = "https://a0.ww.np.dl.playstation.net/tpl/np/{tid}/{tid}-ver.xml"
DEFAULT_MAX_DOWNLOADS = 4


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
def config_dir() -> Path:
    if sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("linux"):
        d = Path.home() / ".config" / APP_NAME
    else:
        appdata = os.environ.get("APPDATA", str(Path.home()))
        d = Path(appdata) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config() -> dict:
    cfg = configparser.ConfigParser()
    path = config_dir() / "config.ini"
    if path.exists():
        cfg.read(path)
    downloads = cfg.get("paths", "downloads", fallback=str(Path.home() / "PS3Updates"))
    rpcs3 = cfg.get("paths", "rpcs3", fallback="")
    max_dl = cfg.getint("settings", "max_downloads", fallback=DEFAULT_MAX_DOWNLOADS)
    return {"downloads": downloads, "rpcs3": rpcs3, "max_downloads": max_dl}


def save_config(cfg: dict):
    p = configparser.ConfigParser()
    p.add_section("paths")
    p.set("paths", "downloads", cfg["downloads"])
    p.set("paths", "rpcs3", cfg.get("rpcs3", ""))
    p.add_section("settings")
    p.set("settings", "max_downloads", str(cfg.get("max_downloads", DEFAULT_MAX_DOWNLOADS)))
    with open(config_dir() / "config.ini", "w") as f:
        p.write(f)


# --------------------------------------------------------------------------
# PSN update lookup (pure functions — testable without the GUI)
# --------------------------------------------------------------------------
def sanitize_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_\- \u3000-\u303F\u3040-\u30FF\u4E00-\u9FFF\uFF00-\uFFEF]", "", name or "")
    return re.sub(r"[\s.]+$", "", name).strip()


def version_key(v: str):
    """Sort key for PS3 versions like '01.02' -> (1, 2)."""
    parts = []
    for chunk in v.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def fmt_size(n):
    """Human-readable byte size."""
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024


def fetch_updates(title_id: str, timeout: int = 20):
    """Query Sony's PSN update endpoint.

    Returns (game_name, [pkg dicts]) where each pkg dict has keys:
      version, size (int bytes), sha1, url, drm_free (bool)
    Raises LookupError for invalid/unknown serials, ValueError on network errors.
    """
    title_id = title_id.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{9}", title_id):
        raise LookupError(f"Invalid serial format: {title_id!r} (expected 9 chars, e.g. BLUS30675)")

    url = UPDATE_XML_URL.format(tid=title_id)
    # TLS note (verified against the live endpoint — see README "Security"):
    # Sony's XML host presents a certificate chain rooted in its own private CA
    # ("SCEI DNAS Root 05"), which is absent from every public trust store, so
    # standard verification (verify=True) fails for EVERY client here — the same
    # situation PySN/Rusty-PSN work around. verify=False is therefore scoped to
    # THIS Sony request only and must never be reused for unrelated domains.
    try:
        r = requests.get(url, timeout=timeout, verify=False)
    except requests.RequestException as e:
        raise ValueError(f"Network error contacting PSN: {e}") from e

    if r.status_code != 200 or not r.text.strip():
        # 'Not found' body or empty => no updates (or unknown id; both look the same)
        return None, []

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        raise ValueError(f"Unexpected response from PSN for {title_id}: {e}") from e

    if root.tag != "titlepatch":
        return None, []

    # Game name lives in the first package's paramsfo (may be TITLE child or text)
    game_name = ""
    pkgs = []
    for pkg_el in root.iter("package"):
        ver = pkg_el.get("version", "")
        size_s = pkg_el.get("size", "0")
        sha1 = pkg_el.get("sha1sum", "")
        url_ = pkg_el.get("url", "")
        if not game_name:
            pfo = pkg_el.find("paramsfo")
            if pfo is not None:
                t = pfo.find("TITLE")
                game_name = (t.text if t is not None else pfo.text) or ""
        if url_:
            pkgs.append({
                "version": ver,
                "size": int(size_s or 0),
                "sha1": sha1.lower(),
                "url": url_,
                "drm_free": False,
            })

    # DRM-free updates: <tag ...><package .../><url>...</url></tag> style entries
    for tag_el in root.iter("tag"):
        for u_el in tag_el.findall("url"):
            ver = (u_el.get("version") or "").strip()
            size_s = u_el.get("size", "0")
            sha1 = u_el.get("sha1sum", "")
            url_ = u_el.text.strip() if u_el.text else ""
            if not url_:
                continue
            pkgs.append({
                "version": ver,
                "size": int(size_s or 0),
                "sha1": sha1.lower(),
                "url": url_,
                "drm_free": True,
            })

    # De-duplicate (some titles list the same pkg twice) and sort by version
    seen = set()
    unique = []
    for p in pkgs:
        key = (p["version"], p["sha1"])
        if key in seen or not p["url"]:
            continue
        seen.add(key)
        unique.append(p)
    unique.sort(key=lambda p: version_key(p["version"]))

    return sanitize_name(game_name), unique


def read_games_yml(rpcs3_dir: str):
    """Return {title_id: name} from an RPCS3 install's config/games.yml.

    Handles both formats:
      "BLUS12345":            (flat — value is the game path)
        D:/ROMS/PS3/Games/Game Name [BLUS12345]/
      "BLUS12345":            (nested — newer RPCS3 builds)
        name: Game Name
        path: D:/...
    """
    import yaml  # local import so --cli works even if yaml is missing for GUI-only use
    yml = Path(rpcs3_dir) / "config" / "games.yml"
    if not yml.is_file():
        raise FileNotFoundError(f"No games.yml at {yml}")
    with open(yml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}
    for tid, info in data.items():
        name = ""
        path_s = ""
        if isinstance(info, dict):
            name = str(info.get("name", "") or "")
            path_s = str(info.get("path", "") or "")
        else:
            path_s = str(info or "")  # flat format: the value IS the path
        if not name and path_s:
            # Derive a display name from the folder, e.g.
            # "D:/ROMS/PS3/Games/God of War III [BCUS98111]/" -> "God of War III"
            parts = [p for p in Path(path_s.replace("\\", "/")).parts
                     if p and not p.endswith(":") and p.lower() != "game"]
            cand = next((p for p in reversed(parts)), "")
            name = re.sub(r"\s*\[[A-Z0-9]{9}\]\s*$", "", cand).strip()
        out[str(tid).upper()] = sanitize_name(name)
    return out


# --------------------------------------------------------------------------
# Downloading (pure functions — testable without the GUI)
# --------------------------------------------------------------------------
def sha1_of_file(path: Path, chunk: int = 1 << 20):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def download_pkg(pkg: dict, dest_dir: Path, progress_cb=None, stop_event=None):
    """Download one pkg to dest_dir/<basename>. Returns (path, ok, message).

    progress_cb(done_bytes, total_bytes) is called periodically.
    Skips re-download if a file of the right size already exists.
    SHA-1 is checked against Sony's metadata; on mismatch the file is KEPT
    with a warning — Sony has stale hashes for some re-issued packages, and
    RPCS3 verifies PKG signatures itself at install time (final gate).
    Partial files are deleted on network failure.
    """
    fname = os.path.basename(pkg["url"].split("?")[0]) or f"{pkg['version']}.pkg"
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / fname
    tmp = dest_dir / (fname + ".part")

    if final.exists() and final.stat().st_size == pkg["size"]:
        return str(final), True, "already present"

    try:
        # TLS note (verified against the live endpoint — see README "Security"):
        # The CDN host b0.ww.np.dl.playstation.net serves a valid public
        # Akamai/DigiCert certificate, but for its internal name (a248.e.akamai.net),
        # not the requested hostname — so standard verification fails with a
        # hostname mismatch for EVERY client. verify=False is scoped to THIS Sony
        # CDN request only and must never be reused for unrelated domains.
        with requests.get(pkg["url"], stream=True, timeout=60, verify=False) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or pkg["size"] or 0)
            done = 0
            last_report = 0.0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if stop_event is not None and stop_event.is_set():
                        raise InterruptedError("stopped by user")
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if progress_cb and (now - last_report > 0.15 or done == total):
                        progress_cb(done, total)
                        last_report = now

        digest = sha1_of_file(tmp)
        if pkg["sha1"] and digest != pkg["sha1"]:
            os.replace(tmp, final)  # keep it — see docstring; RPCS3 re-verifies at install
            return str(final), True, f"downloaded (SHA-1 differs from Sony's listing: {digest[:8]}… vs {pkg['sha1'][:8]}…)"
        os.replace(tmp, final)
        if progress_cb:
            progress_cb(total or done, total or done)
        return str(final), True, "ok"
    except InterruptedError as e:
        tmp.unlink(missing_ok=True)
        return str(final), False, str(e)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return str(final), False, f"{type(e).__name__}: {e}"


def plan_downloads(game_name: str, title_id: str, pkgs, base_dir: Path):
    """Build the ordered download list for one game.

    Returns [(pkg, dest_path)] in install order (ascending version).
    Folders are named  '<base>/PlayStation 3/[ID] Name' like PySN does.
    """
    name = sanitize_name(game_name) or title_id
    folder = base_dir / "PlayStation 3" / f"[{title_id}] {name}"
    out = []
    for p in pkgs:  # already sorted ascending by fetch_updates()
        fname = os.path.basename(p["url"].split("?")[0]) or f"{p['version']}.pkg"
        if p["drm_free"]:
            fname = "DRM-Free " + fname
        out.append((p, folder / fname))
    return out


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    cfg = load_config()
    # Two queues on purpose: cmd_q carries commands TO the worker threads,
    # ev_q carries events FROM them to the UI. One shared queue would let an
    # idle worker steal (and silently drop) UI events — that was exactly why
    # download progress never showed up in the table.
    cmd_q: "queue.Queue" = queue.Queue()
    ev_q: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    state = {
        "rows": {},          # iid -> dict(game, id, ver, size, status, path, pkg)
        "downloading": False,
        "total_bytes": 0,
        "done_bytes": 0,     # bytes of finished packages (drives the bar)
        "inflight_bytes": 0, # bytes received on the current package
    }

    root = tk.Tk()
    root.title("PS3 Updater — RPCS3 game updates")
    root.geometry("980x620")
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    # ---- top bar ----------------------------------------------------------
    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    entry = ttk.Entry(top, font=("Consolas", 11))
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    btn_search = ttk.Button(top, text="Search updates")

    def do_search():
        tid = entry.get().strip()
        if not tid:
            return
        entry.delete(0, "end")
        cmd_q.put(("search_one", tid.upper()))

    btn_search.configure(command=do_search)
    btn_search.pack(side="left")
    entry.bind("<Return>", lambda e: do_search())

    top2 = ttk.Frame(root, padding=(8, 0, 8, 4))
    top2.pack(fill="x")
    btn_scan = ttk.Button(top2, text="Scan RPCS3 library (games.yml)")

    def do_scan():
        rpcs3_dir = cfg.get("rpcs3", "")
        if not rpcs3_dir:
            chosen = filedialog.askdirectory(title="Select your RPCS3 install folder")
            if not chosen:
                return
            cfg["rpcs3"] = chosen
            save_config(cfg)
        try:
            games = read_games_yml(rpcs3_dir)
        except Exception as e:
            messagebox.showerror("PS3 Updater", f"Could not read library:\n{e}")
            return
        if not games:
            messagebox.showinfo("PS3 Updater", "No games found in games.yml.")
            return
        cmd_q.put(("search_many", list(games.keys()), {k: v for k, v in games.items()}))

    btn_scan.configure(command=do_scan)
    btn_scan.pack(side="left")

    # ---- settings row -----------------------------------------------------
    setrow = ttk.Frame(root, padding=(8, 0, 8, 4))
    setrow.pack(fill="x")
    ttk.Label(setrow, text="Downloads:").pack(side="left")
    dl_var = tk.StringVar(value=cfg.get("downloads", ""))
    ttk.Entry(setrow, textvariable=dl_var).pack(side="left", fill="x", expand=True, padx=(4, 4))

    def pick_downloads():
        d = filedialog.askdirectory(title="Choose download folder")
        if d:
            dl_var.set(d)
            cfg["downloads"] = d
            save_config(cfg)

    ttk.Button(setrow, text="Browse…", command=pick_downloads).pack(side="left")
    ttk.Label(setrow, text="   RPCS3:").pack(side="left")
    rpcs3_var = tk.StringVar(value=cfg.get("rpcs3", ""))
    ttk.Entry(setrow, textvariable=rpcs3_var, width=28).pack(side="left", fill="x", expand=True, padx=(4, 4))

    def pick_rpcs3():
        d = filedialog.askdirectory(title="Choose RPCS3 install folder")
        if d:
            rpcs3_var.set(d)
            cfg["rpcs3"] = d
            save_config(cfg)

    ttk.Button(setrow, text="Browse…", command=pick_rpcs3).pack(side="left")

    # ---- results table ----------------------------------------------------
    mid = ttk.Frame(root, padding=(8, 0))
    mid.pack(fill="both", expand=True)
    cols = ("order", "game", "id", "version", "size", "status")
    tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
    for c, w in (("order", 46), ("game", 300), ("id", 105), ("version", 78), ("size", 92), ("status", 220)):
        tree.heading(c, text={"order": "# (install order)", "game": "Game", "id": "Serial",
                              "version": "Version", "size": "Size", "status": "Status"}[c])
        tree.column(c, width=w, anchor="w" if c in ("game", "status") else "center")
    vsb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def add_row(game, tid, ver, size, status, pkg=None):
        iid = tree.insert("", "end", values=("", game, tid, ver, fmt_size(size), status))
        state["rows"][iid] = {"game": game, "id": tid, "ver": ver, "raw_ver": (pkg or {}).get("version", ""),
                              "size": size, "status": status, "pkg": pkg}
        return iid

    def set_row(iid, **kw):
        r = state["rows"].get(iid)
        if not r:
            return
        r.update(kw)
        # Rebuild the display row from the (now updated) record. Reading back
        # with tree.set() would just re-write the OLD values — a no-op.
        vals = [tree.set(iid, "order"), r.get("game", ""), r.get("id", ""),
                r.get("ver", "—"), fmt_size(r.get("size")), r.get("status", "—")]
        tree.item(iid, values=vals)

    # ---- bottom bar -------------------------------------------------------
    bot = ttk.Frame(root, padding=8)
    bot.pack(fill="x", side="bottom")
    btn_dl = ttk.Button(bot, text="Download selected (in order)")
    btn_stop = ttk.Button(bot, text="Stop", state="disabled")
    btn_open = ttk.Button(bot, text="Open downloads folder")
    btn_dl.pack(side="left")
    btn_stop.pack(side="left", padx=6)
    btn_open.pack(side="right")

    def open_folder():
        d = dl_var.get() or cfg.get("downloads", "")
        if not d:
            return
        try:
            os.startfile(d)  # Windows
        except Exception:
            pass

    btn_open.configure(command=open_folder)

    overall = ttk.Progressbar(bot, mode="determinate")
    overall.pack(fill="x", pady=(8, 2))
    status_lbl = ttk.Label(root, text="Ready. Paste a serial (e.g. BLUS30675) and press Search, or scan your library.", padding=(10, 4), anchor="w")
    status_lbl.pack(fill="x", side="bottom")

    # ---- worker: searches -------------------------------------------------
    def search_worker():
        while True:
            msg = cmd_q.get()
            kind = msg[0]
            if kind == "search_one":
                tid = msg[1]
                ev_q.put(("status", f"Searching PSN for {tid}…"))
                try:
                    name, pkgs = fetch_updates(tid)
                except LookupError as e:
                    ev_q.put(("result_error", tid, str(e)))
                    continue
                except ValueError as e:
                    ev_q.put(("result_error", tid, str(e)))
                    continue
                if not pkgs:
                    ev_q.put(("result_none", tid, name))
                else:
                    ev_q.put(("results", tid, name, pkgs))
            elif kind == "search_many":
                tids = msg[1]
                names_hint = msg[2]
                ev_q.put(("status", f"Searching PSN for {len(tids)} games…"))
                with ThreadPoolExecutor(max_workers=6) as ex:
                    futs = {ex.submit(fetch_updates, t): t for t in tids}
                    done_n = 0
                    for fut in futs:
                        tid = futs[fut]
                        try:
                            name, pkgs = fut.result(timeout=120)
                        except LookupError as e:
                            ev_q.put(("result_error", tid, str(e)))
                        except Exception as e:
                            ev_q.put(("result_error", tid, f"{type(e).__name__}: {e}"))
                        else:
                            if not pkgs:
                                ev_q.put(("result_none", tid, name or names_hint.get(tid, "")))
                            else:
                                ev_q.put(("results", tid, name or names_hint.get(tid, ""), pkgs))
                        done_n += 1
                        ev_q.put(("status", f"Searching… {done_n}/{len(tids)}"))

    threading.Thread(target=search_worker, daemon=True).start()

    # ---- worker: downloads ------------------------------------------------
    def download_worker(order):
        """order: list of (iid, pkg, dest_path) in install order."""
        for idx, (iid, pkg, dest) in enumerate(order, 1):
            if stop_event.is_set():
                ev_q.put(("dl_status", iid, "stopped"))
                continue
            ev_q.put(("dl_status", iid, f"downloading ({idx}/{len(order)})…"))

            def cb(done, total, _iid=iid):
                ev_q.put(("dl_progress", _iid, done, total))

            path, ok, msg = download_pkg(pkg, dest.parent, progress_cb=cb, stop_event=stop_event)
            if ok:
                ev_q.put(("dl_done", iid, path, msg))
            else:
                ev_q.put(("dl_fail", iid, msg))
        ev_q.put(("dl_all_done", None))

    def start_downloads():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("PS3 Updater", "Select one or more update rows first.")
            return
        base = Path(dl_var.get().strip())
        if not base:
            messagebox.showerror("PS3 Updater", "Choose a download folder first (top row).")
            return
        # group by game, keep ascending version order within each game
        per_game = {}
        for iid in sel:
            r = state["rows"][iid]
            if not r.get("pkg"):
                continue
            per_game.setdefault(r["id"], []).append((r.get("raw_ver") or r["ver"], iid, r["pkg"]))
        order = []
        for tid in sorted(per_game):
            for ver, iid, pkg in sorted(per_game[tid], key=lambda x: version_key(x[0])):
                p, dest = plan_downloads(state["rows"][iid]["game"], tid, [pkg], base)[0]
                order.append((iid, pkg, dest))
        if not order:
            return
        state["downloading"] = True
        stop_event.clear()
        btn_dl.configure(state="disabled")
        btn_stop.configure(state="normal")
        total = sum(p["size"] for _, p, _ in order)
        ev_q.put(("dl_total", total))
        threading.Thread(target=download_worker, args=(order,), daemon=True).start()

    def stop_downloads():
        stop_event.set()
        status_lbl.configure(text="Stopping after current chunk…")

    btn_dl.configure(command=start_downloads)
    btn_stop.configure(command=stop_downloads)

    # ---- queue pump -------------------------------------------------------
    def poll_queue():
        try:
            while True:
                msg = ev_q.get_nowait()
                kind = msg[0]
                if kind == "status":
                    status_lbl.configure(text=msg[1])
                elif kind == "results":
                    _, tid, name, pkgs = msg
                    # number rows in install order for this game
                    for i, p in enumerate(pkgs, 1):
                        tag = " DRM-free" if p["drm_free"] else ""
                        iid = add_row(name or tid, tid, f"{p['version']}{tag}", p["size"], "available", pkg=p)
                        tree.set(iid, "order", str(i))
                elif kind == "result_none":
                    _, tid, name = msg
                    add_row(name or "No updates available", tid, "", 0, "no updates")
                elif kind == "result_error":
                    _, tid, err = msg
                    add_row(err.split(":")[0], tid, "", 0, f"error: {err}")
                elif kind == "dl_total":
                    state["total_bytes"] = msg[1]
                    state["done_bytes"] = 0
                    state["inflight_bytes"] = 0
                    overall.configure(maximum=max(msg[1], 1), value=0)
                elif kind == "dl_status":
                    set_row(msg[1], status=msg[2])
                elif kind == "dl_progress":
                    _, iid, done, total = msg
                    r = state["rows"].get(iid)
                    if r:
                        pct = f"{done/total*100:.0f}%" if total else ""
                        set_row(iid, status=f"downloading {fmt_size(done)}/{fmt_size(total)} ({pct})")
                        state["inflight_bytes"] = done
                        overall.configure(value=state["done_bytes"] + done)
                elif kind == "dl_done":
                    _, iid, path, msg2 = msg
                    r = state["rows"].get(iid)
                    if r:
                        state["done_bytes"] += r.get("size", 0)
                        state["inflight_bytes"] = 0
                        overall.configure(value=state["done_bytes"])
                        set_row(iid, status=f"✓ {msg2} — {path}")
                elif kind == "dl_fail":
                    _, iid, err = msg
                    state["inflight_bytes"] = 0
                    set_row(iid, status=f"✗ failed: {err}")
                elif kind == "dl_all_done":
                    state["downloading"] = False
                    btn_dl.configure(state="normal")
                    btn_stop.configure(state="disabled")
                    overall.configure(value=state["done_bytes"])
                    n_ok = sum(1 for r in state["rows"].values() if str(r.get("status", "")).startswith("✓"))
                    status_lbl.configure(text=f"Done. {n_ok} update(s) ready to install — drag the .pkg files into RPCS3 or use File → Install Packages.")
                else:
                    print(f"[ps3_updater] unknown event: {msg!r}", file=sys.stderr, flush=True)
        except queue.Empty:
            pass
        except Exception:
            # A single bad event must never kill the pump — if it did, every
            # later progress/completion update would vanish silently.
            print("[ps3_updater] poll_queue error:", file=sys.stderr, flush=True)
            traceback.print_exc()
        root.after(100, poll_queue)

    poll_queue()
    root.mainloop()


# --------------------------------------------------------------------------
# CLI (headless) — also used for smoke-testing the core logic
# --------------------------------------------------------------------------
def run_cli(serials, out_dir):
    base = Path(out_dir).expanduser()
    total_ok = 0
    for tid in serials:
        print(f"== {tid} ==")
        try:
            name, pkgs = fetch_updates(tid)
        except (LookupError, ValueError) as e:
            print(f"   error: {e}")
            continue
        if not pkgs:
            print("   no updates available")
            continue
        print(f"   {name or tid}: {len(pkgs)} update(s)")
        plan = plan_downloads(name, tid, pkgs, base)
        for i, (p, dest) in enumerate(plan, 1):
            print(f"   [{i}] v{p['version']}  {fmt_size(p['size'])}  {'DRM-free ' if p['drm_free'] else ''}{dest.name}")

        def cb(done, total):
            print(f"\r      downloading {done/1048576:.1f}/{total/1048576:.1f} MB ({done/total*100:.0f}%)", end="", flush=True)

        for i, (p, dest) in enumerate(plan, 1):
            path, ok, msg = download_pkg(p, dest.parent, progress_cb=cb)
            print()
            if ok:
                total_ok += 1
                print(f"   [{i}] OK ({msg}): {path}")
            else:
                print(f"   [{i}] FAILED: {msg}")
    print(f"\nDone. {total_ok} package(s) downloaded to {base}")


def main():
    # Silence urllib3 InsecureRequestWarning — emitted only by the two Sony PSN
    # requests above that use verify=False (see their TLS notes and README "Security").
    requests.packages.urllib3.disable_warnings()
    ap = argparse.ArgumentParser(description="PS3 Updater for RPCS3")
    ap.add_argument("--cli", nargs="+", metavar="SERIAL", help="headless mode: search+download given serials")
    ap.add_argument("-o", "--out", default=str(Path.home() / "PS3Updates"), help="output folder (CLI mode)")
    args = ap.parse_args()
    if args.cli:
        run_cli(args.cli, args.out)
    else:
        run_gui()


if __name__ == "__main__":
    main()
