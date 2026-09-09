"""Deterministic tests for ps3_updater.read_games_yml().

Covers BOTH games.yml formats the app documents, using throwaway temp dirs —
no real RPCS3 install is ever touched or modified.

  A) flat format   : "BLUS12345": D:/ROMS/PS3/Games/Game Name [BLUS12345]/
                     (the value IS the game path; name derived from folder)
  B) nested format : "BLUS30675": {name: Some Game, path: ...}
                     (newer RPCS3 builds; explicit 'name' wins)

Also verifies:
  - IDs are detected and upper-cased
  - display names parse correctly in both formats
  - nested 'name' values take priority over the path
  - flat paths derive a clean game name (trailing [SERIAL] stripped)
  - a missing games.yml raises FileNotFoundError
  - an empty file yields {}

Usage: python test_games_yml.py [path-to-ps3_updater.py]
Exit code 0 = all checks passed, 1 = failure. No network access required.
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

APP_PATH = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
            else Path(__file__).with_name("ps3_updater.py"))
if not APP_PATH.exists():
    print(f"usage: test_games_yml.py [path-to-ps3_updater.py]   (default: {APP_PATH})")
    sys.exit(2)

# Load ps3_updater as a module WITHOUT running its __main__ guard.
spec = importlib.util.spec_from_file_location("ps3upd_under_test", APP_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["ps3upd_under_test"] = mod
spec.loader.exec_module(mod)

failures = []


def check(label, cond, detail=""):
    tag = "ok  " if cond else "FAIL"
    print(f"[{tag}] {label}" + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def write_tree(yaml_text):
    """Create a temp RPCS3-like tree with config/games.yml; return its root."""
    d = Path(tempfile.mkdtemp(prefix="gymtest_"))
    cfg = d / "config"
    cfg.mkdir()
    (cfg / "games.yml").write_text(yaml_text, encoding="utf-8")
    return d


# ---------------------------------------------------------------- A) flat --
flat_yaml = (
    'BLUS12345: D:/ROMS/PS3/Games/Game Name [BLUS12345]/\n'
    'BCUS98111: E:\\Games\\God of War III [BCUS98111]\\\n'
)
with tempfile.TemporaryDirectory(prefix="gymtest_flat_") as td:
    root = Path(td) / "rpcs3"
    (root / "config").mkdir(parents=True)
    (root / "config" / "games.yml").write_text(flat_yaml, encoding="utf-8")
    got = mod.read_games_yml(str(root))

check("flat: both IDs detected", set(got) == {"BLUS12345", "BCUS98111"}, str(got))
check("flat: name derived from folder (serial stripped)",
      got.get("BLUS12345") == "Game Name", repr(got.get("BLUS12345")))
check("flat: backslash path derives name too",
      got.get("BCUS98111") == "God of War III", repr(got.get("BCUS98111")))

# ------------------------------------------------------------- B) nested --
nested_yaml = (
    'BLUS30675:\n'
    '  name: Some Game\n'
    '  path: D:/ROMS/PS3/Games/Some Game [BLUS30675]/\n'
    'BCES01234:\n'
    '  name: Another Title\n'
    '  path: /home/user/games/Another Title [BCES01234]\n'
)
with tempfile.TemporaryDirectory(prefix="gymtest_nested_") as td:
    root = Path(td) / "rpcs3"
    (root / "config").mkdir(parents=True)
    (root / "config" / "games.yml").write_text(nested_yaml, encoding="utf-8")
    gotn = mod.read_games_yml(str(root))

check("nested: both IDs detected", set(gotn) == {"BLUS30675", "BCES01234"}, str(gotn))
check("nested: explicit 'name' used (not derived)",
      gotn.get("BLUS30675") == "Some Game", repr(gotn.get("BLUS30675")))
check("nested: second name parsed",
      gotn.get("BCES01234") == "Another Title", repr(gotn.get("BCES01234")))

# ------------------------------------------- nested WITHOUT name -> derive --
mixed_yaml = (
    'NPEA90001:\n'
    '  path: D:/ROMS/PS3/Games/Nobody Saves You [NPEA90001]/\n'
)
with tempfile.TemporaryDirectory(prefix="gymtest_mixed_") as td:
    root = Path(td) / "rpcs3"
    (root / "config").mkdir(parents=True)
    (root / "config" / "games.yml").write_text(mixed_yaml, encoding="utf-8")
    gotm = mod.read_games_yml(str(root))

check("nested-no-name: falls back to path-derived name",
      gotm.get("NPEA90001") == "Nobody Saves You", repr(gotm.get("NPEA90001")))

# ------------------------------------------------- missing file -> error ----
with tempfile.TemporaryDirectory(prefix="gymtest_missing_") as td:
    raised = False
    try:
        mod.read_games_yml(td)  # no config/ here at all
    except FileNotFoundError:
        raised = True
check("missing games.yml raises FileNotFoundError", raised)

# ------------------------------------------------------------- empty -> {} --
with tempfile.TemporaryDirectory(prefix="gymtest_empty_") as td:
    root = Path(td) / "rpcs3"
    (root / "config").mkdir(parents=True)
    (root / "config" / "games.yml").write_text("", encoding="utf-8")
    gotempty = mod.read_games_yml(str(root))
check("empty games.yml yields {}", gotempty == {}, str(gotempty))

# ------------------------------------------------------------- report -------
print("\n===== RESULT =====")
if failures:
    print(f"FAIL — {len(failures)} check(s) failed:")
    for f_ in failures:
        print(f"  - {f_}")
    sys.exit(1)
print("PASS — read_games_yml() handles flat + nested formats, name derivation,"
      " missing-file error and empty file. No real RPCS3 install touched.")
sys.exit(0)
