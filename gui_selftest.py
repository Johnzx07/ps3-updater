"""Automated self-test for ps3_updater's GUI progress display (v4).

Loads a given copy of ps3_updater.py, fakes the network layer, drives the REAL
run_gui() end-to-end and verifies:

Phase 2 — multi-update happy path (one game, two versions):
  1. rows appear after a search in ascending version order,
  2. row Status cells show live "downloading …" progress,
  3. the bottom progress bar fills to exactly maximum (= sum of sizes),
  4. BOTH rows end with a "✓ done" status,
  5. the status label announces plural completion ("Done. 2 update(s)…").

Phase 4 — search error branches:
  6. a serial with no updates yields a row with status "no updates",
  7. an invalid serial (LookupError) yields a row with status "error: …".

Phase 5 — stop mid-download:
  8. clicking Stop aborts the in-flight download (row shows ✗/stopped),
  9. the queue pump survives the failed batch and still announces completion.

Usage: python gui_selftest.py <path-to-ps3_updater.py>
Exit code 0 = all checks passed, 1 = failure (details printed).
"""
import importlib.util
import queue as _queue_mod
import sys
import tempfile
import time
from pathlib import Path

# Standalone: no argument -> test the ps3_updater.py sitting next to this file.
APP_PATH = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
            else Path(__file__).with_name("ps3_updater.py"))
if not APP_PATH.exists():
    print(f"usage: gui_selftest.py [path-to-ps3_updater.py]   (default: {APP_PATH})")
    sys.exit(2)

TOTAL = 4_000_000          # fake package size (bytes) per A/D-small pkg
CHUNK = 500_000            # chunk size -> ~8 progress callbacks per MB-ish
# Downloads go to a temp dir, NEVER next to the app — keeps the real project clean.
OUT_DIR = Path(tempfile.gettempdir()) / "ps3upd_selftest_out"
OUT_DIR.mkdir(exist_ok=True)

SERIAL_A = "BLUS30675"     # two updates (v01.01, v01.02), each TOTAL bytes
SERIAL_B = "BLUS30777"     # no updates available
SERIAL_C = "ZZZ99999"      # invalid serial -> LookupError
SERIAL_D = "BLUS31248"     # one update, 2*TOTAL bytes (long enough to stop mid-way)

# ---------------------------------------------------------------- fakes ----
def fake_fetch_updates(title_id, timeout=20):
    print("DEBUG fetch_updates called:", title_id, flush=True)
    if title_id == SERIAL_A:
        return "Test Game A", [
            {"version": "01.01", "size": TOTAL, "sha1": "",
             "url": f"http://example.invalid/UP0001-TESTA_00-A0101.pkg",
             "pkg": "UP0001-TESTA_00-A0101.pkg", "drm_free": True},
            {"version": "01.02", "size": TOTAL, "sha1": "",
             "url": f"http://example.invalid/UP0001-TESTA_00-A0102.pkg",
             "pkg": "UP0001-TESTA_00-A0102.pkg", "drm_free": True},
        ]
    if title_id == SERIAL_B:
        return "Test Game B", []
    if title_id == SERIAL_D:
        return "Test Game D", [
            {"version": "01.03", "size": 2 * TOTAL, "sha1": "",
             "url": f"http://example.invalid/UP0001-TESTD_00-A0103.pkg",
             "pkg": "UP0001-TESTD_00-A0103.pkg", "drm_free": True},
        ]
    raise LookupError(f"No updates found for {title_id}")


def fake_download_pkg(pkg, dest_dir, stop_event=None, progress_cb=None):
    import os as _os
    fname = _os.path.basename(pkg["url"].split("?")[0]) or f"{pkg['version']}.pkg"
    size = pkg["size"]
    print("DEBUG download_pkg called:", fname, flush=True)
    final = Path(dest_dir) / fname
    final.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        with open(final, "wb") as f:
            written = 0
            while written < size:
                if stop_event is not None and stop_event.is_set():
                    raise InterruptedError("stopped by user")   # mirrors real download_pkg (line ~263)
                n = min(CHUNK, size - written)
                f.write(b"\x7fPKG" + b"\x00" * (n - 4))
                written += n
                if progress_cb:
                    progress_cb(written, size)
                time.sleep(0.12)   # ~1s per TOTAL bytes
    except InterruptedError as e:
        # Mirror the REAL contract exactly: download_pkg catches InterruptedError,
        # deletes the partial file, and RETURNS (path, False, msg) — it never raises.
        final.unlink(missing_ok=True)
        return str(final), False, str(e)
    print(f"DEBUG download_pkg finished in {time.time()-t0:.2f}s", flush=True)
    return str(final), True, "ok"


# ---------------------------------------------------------------- load ----
spec = importlib.util.spec_from_file_location("ps3upd_under_test", APP_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["ps3upd_under_test"] = mod
spec.loader.exec_module(mod)

mod.fetch_updates = fake_fetch_updates          # patched before run_gui binds it
mod.download_pkg = fake_download_pkg            # (module-level names resolved at call time)
# Redirect downloads into the test's temp dir — never touch the user's real folder.
mod.load_config = lambda: {"downloads": str(OUT_DIR), "rpcs3": "", "max_downloads": 4}

# ---------------------------------------------------------------- capture --
captured = {}


class SpyQueue(_queue_mod.Queue):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        captured.setdefault("queues", []).append(self)
        if len(captured["queues"]) == 1:
            captured["cmd_q"] = self   # created first in run_gui (worker commands)
        else:
            captured["ev_q"] = self    # created second (UI events)
    def put(self, item, *a, **k):
        print("DEBUG Q.PUT:", str(item)[:90], flush=True)
        return super().put(item, *a, **k)


_queue_mod.Queue = SpyQueue

import tkinter as tk  # noqa: E402
_orig_Tk = tk.Tk


class CaptureTk(_orig_Tk):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        captured["root"] = self
        # schedule the test phases once the real GUI exists (run_gui keeps going
        # to build widgets + mainloop right after this constructor returns)
        self.after(300, phase1_search)
        self.after(45000, finish)   # safety net


tk.Tk = CaptureTk

# ---------------------------------------------------------------- state ----
tree_ref = {"tree": None}
samples = []          # (t, status_text, bar_value) — live row/bar samples
labels = []           # status-label text captured at each sample time
failures = []


def find_tree(root):
    def walk(w):
        try:
            cls = w.winfo_class()
        except Exception:
            return
        if cls == "Treeview" and not tree_ref.get("tree"):
            tree_ref["tree"] = w
        for c in w.winfo_children():
            walk(c)
    walk(root)


def bar_value(root):
    val = 0.0

    def walk(w):
        nonlocal val
        try:
            if w.winfo_class() in ("Progressbar", "TProgressbar"):
                v = float(w.cget("value"))
                if v > val:
                    val = v
        except Exception:
            pass
        for c in w.winfo_children():
            walk(c)

    walk(root)
    return val


def label_text(root):
    best = ""

    def walk(w):
        nonlocal best
        try:
            if w.winfo_class() in ("Label", "TLabel"):
                txt = str(w.cget("text"))
                if len(txt) > len(best):
                    best = txt
        except Exception:
            pass
        for c in w.winfo_children():
            walk(c)

    walk(root)
    return best


def row_statuses(tree):
    out = []
    for iid in tree.get_children():
        try:
            out.append((iid, str(tree.set(iid, "status"))))
        except Exception as e:
            out.append((iid, f"<err {e}>"))
    return out


def find_button(root, prefix):
    btns = []

    def walk(w):
        try:
            if w.winfo_class() in ("Button", "TButton"):
                if str(w.cget("text")).startswith(prefix):
                    btns.append(w)
        except Exception:
            pass
        for c in w.winfo_children():
            walk(c)

    walk(root)
    return btns


def sample(t):
    root = captured["root"]
    tree = tree_ref.get("tree")
    if not tree or not tree.get_children():
        samples.append((t, "<no row>", bar_value(root)))
        labels.append(label_text(root))
        return
    # sample the FIRST (oldest) row — it is the one downloading first in phase 2
    iid = tree.get_children()[0]
    try:
        status = str(tree.set(iid, "status"))
    except Exception as e:
        status = f"<err {e}>"
    samples.append((t, status, bar_value(root)))
    labels.append(label_text(root))


# ---------------------------------------------------------------- phases ---
def phase1_search():
    print("DEBUG phase1: search A", flush=True)
    captured["cmd_q"].put(("search_one", SERIAL_A))
    root = captured["root"]
    root.after(1800, phase2_download)


def fatal(msg):
    failures.append(msg)
    print("FATAL:", msg, flush=True)
    captured["root"].after(500, finish)


def phase2_download():
    root = captured["root"]
    find_tree(root)
    if not tree_ref.get("tree"):
        fatal("no Treeview widget found in the GUI")
        return
    tree = tree_ref["tree"]
    iids = tree.get_children()
    print(f"DEBUG phase2: rows={iids}", flush=True)
    if len(iids) < 2:
        fatal(f"expected 2 update rows for {SERIAL_A}, got {len(iids)}")
        return
    # version order check: first row must be the lower version
    vers = [str(tree.set(i, "version")) for i in iids[:2]]
    captured["p2_vers"] = vers
    if not (vers[0].startswith("01.01") and vers[1].startswith("01.02")):
        failures.append(f"rows not in ascending version order: {vers}")
    tree.selection_set(iids[:2])
    btns = find_button(root, "Download")
    if not btns:
        fatal("Download button not found")
        return
    t0 = time.time()
    btns[0].invoke()          # start_downloads()
    for dt in (400, 900, 1500, 2300, 3100):
        root.after(dt, lambda d=dt: sample(t0 + d / 1000.0))
    root.after(4200, phase3_verify)   # ~t=6000


def phase3_verify():
    root = captured["root"]
    tree = tree_ref["tree"]
    iids = tree.get_children()[:2]
    captured["p2_rows"] = [str(tree.set(i, "status")) for i in iids]
    captured["p2_bar"] = bar_value(root)
    captured["p2_label"] = label_text(root)
    print(f"DEBUG phase3: rows={captured['p2_rows']} bar={captured['p2_bar']:.0f}", flush=True)
    # now exercise the search error branches
    captured["cmd_q"].put(("search_one", SERIAL_B))   # no updates
    captured["cmd_q"].put(("search_one", SERIAL_C))   # LookupError
    root.after(1500, phase4_verify)


def phase4_verify():
    root = captured["root"]
    tree = tree_ref["tree"]
    captured["p4_statuses"] = [s for _, s in row_statuses(tree)]
    print("DEBUG phase4: statuses=", captured["p4_statuses"], flush=True)
    root.after(500, phase5_search)


def phase5_search():
    captured["cmd_q"].put(("search_one", SERIAL_D))
    captured["root"].after(1500, phase5_download)


def phase5_download():
    root = captured["root"]
    tree = tree_ref["tree"]
    iids = tree.get_children()
    if len(iids) < 5:
        fatal(f"expected D's row to be appended (>=5 rows), got {len(iids)}")
        return
    d_iid = iids[-1]
    captured["p5_iid"] = d_iid
    tree.selection_set(d_iid)
    btns = find_button(root, "Download")
    if not btns:
        fatal("Download button not found (phase 5)")
        return
    btns[0].invoke()          # start downloading D's big pkg
    root.after(800, phase5_stop)      # mid-download (~0.9s into ~1.9s)
    root.after(3200, phase5_verify)


def phase5_stop():
    btns = find_button(captured["root"], "Stop")
    if not btns:
        failures.append("Stop button not found/enabled during download")
        return
    print("DEBUG phase5: clicking Stop", flush=True)
    btns[0].invoke()


def phase5_verify():
    root = captured["root"]
    tree = tree_ref["tree"]
    iid = captured.get("p5_iid")
    try:
        captured["p5_row"] = str(tree.set(iid, "status")) if iid else "<no iid>"
    except Exception as e:
        captured["p5_row"] = f"<err {e}>"
    captured["p5_label"] = label_text(root)
    print(f"DEBUG phase5: row={captured['p5_row']} label={captured['p5_label']!r}", flush=True)
    finish()


def finish():
    print("DEBUG finishing", flush=True)
    try:
        captured["root"].destroy()
    except Exception:
        pass


# ---------------------------------------------------------------- run ------
print(f"TESTING: {APP_PATH}", flush=True)
mod.run_gui()                # blocks in mainloop until the window is destroyed

# ---------------------------------------------------------------- report ---
print("\n===== SAMPLES (t, status cell, bar value) =====", flush=True)
for t, s, v in samples:
    print(f"  t={t:6.2f}s  bar={v:>10.0f}  {s[:95]}", flush=True)

# Phase 2 checks
if not any("downloading" in s for _, s, _ in samples):
    failures.append("no live 'downloading …' progress ever shown in a row")
mid = [v for t, s, v in samples if "downloading" in s]
if mid and max(mid) < TOTAL * 0.3:
    failures.append(f"progress bar never filled (max {max(mid):.0f} of {TOTAL})")
p2_rows = captured.get("p2_rows", [])
if len(p2_rows) != 2 or not all(s.startswith("✓") for s in p2_rows):
    failures.append(f"both rows did not end with '✓ done': {p2_rows}")
p2_bar = captured.get("p2_bar", 0.0)
if p2_bar < 2 * TOTAL - 1:
    failures.append(f"bar did not reach maximum (got {p2_bar:.0f}, want {2*TOTAL})")
p2_label = captured.get("p2_label", "")
if "Done. 2 update(s)" not in p2_label:
    failures.append(f"plural completion announcement missing; label={p2_label!r}")

# Phase 4 checks
p4 = captured.get("p4_statuses", [])
if "no updates" not in p4:
    failures.append(f"'no updates' row never appeared: {p4}")
if not any(s.startswith("error:") for s in p4):
    failures.append(f"'error:' row (invalid serial) never appeared: {p4}")

# Phase 5 checks
p5_row = captured.get("p5_row", "")
if not ("✗" in p5_row or "stopped" in p5_row):
    failures.append(f"stop did not abort the download; row={p5_row!r}")
p5_label = captured.get("p5_label", "")
if "Done." not in p5_label:
    failures.append(f"pump died after failed/stopped batch; label={p5_label!r}")

print("\n===== RESULT =====", flush=True)
if failures:
    print("FAIL:")
    for f_ in failures:
        print(f"  - {f_}")
    sys.exit(1)
print("PASS — multi-update progress + plural completion, error branches, stop mid-download.")
print(f"  phase2 rows={captured.get('p2_rows')} bar={captured.get('p2_bar', 0):.0f}/{2*TOTAL}")
print(f"  phase4 statuses={captured.get('p4_statuses')}")
print(f"  phase5 row={captured.get('p5_row')!r} label={captured.get('p5_label')!r}")
sys.exit(0)
