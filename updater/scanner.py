"""RPCS3 discovery: locate the install, parse config/games.yml, scan game data."""
from __future__ import annotations

import os
import re
import struct
from typing import Dict, List, Optional

from .models import GameInfo, is_valid_serial

GAMES_YML_RELPATH = os.path.join("config", "games.yml")
DEV_HDD_GAME_RELPATH = os.path.join("dev_hdd0", "game")


# --------------------------------------------------------------------------- #
# RPCS3 folder detection
# --------------------------------------------------------------------------- #

def _looks_like_rpcs3(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return (
        os.path.isfile(os.path.join(path, "rpcs3.exe"))
        or os.path.isfile(os.path.join(path, GAMES_YML_RELPATH))
        or os.path.isdir(os.path.join(path, "dev_hdd0"))
    )


def detect_rpcs3_dir() -> Optional[str]:
    """Best-effort detection of the RPCS3 installation folder."""
    candidates: List[str] = []

    env = os.environ.get("RPCS3_DIR") or os.environ.get("RPCS3_PATH")
    if env:
        candidates.append(env)

    try:
        import winreg  # type: ignore

        for hive, sub in (
            (winreg.HKEY_CURRENT_USER, r"Software\RPCS3"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\RPCS3"),
        ):
            try:
                with winreg.OpenKey(hive, sub) as key:
                    for i in range(64):
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if isinstance(value, str) and os.path.isdir(value):
                                candidates.append(value)
                        except OSError:
                            break
            except OSError:
                pass
    except Exception:  # pragma: no cover - non-Windows
        pass

    home = os.path.expanduser("~")
    candidates.extend(
        [
            os.path.join(home, "RPCS3"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "rpcs3"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "rpcs3"),
        ]
    )

    for cand in candidates:
        if not cand:
            continue
        try:
            real = os.path.realpath(cand)
        except OSError:
            continue
        if _looks_like_rpcs3(real):
            return real
    return None


# --------------------------------------------------------------------------- #
# games.yml parsing (minimal YAML, no external dependency)
# --------------------------------------------------------------------------- #

def parse_games_yml(text: str) -> List[Dict[str, str]]:
    """Parse the simple list-of-mappings format used by RPCS3's games.yml."""
    entries: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        elif current is None or not raw_line[:1].isspace():
            # A top-level key outside a list item ends the previous entry.
            if current is not None and ":" in stripped:
                entries.append(current)
                current = {}
            else:
                continue

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if current is not None:
                current[key] = value

    if current is not None:
        entries.append(current)

    return [e for e in entries if any(e.values())]


def load_games_yml(rpcs3_dir: str) -> List[Dict[str, str]]:
    """Load config/games.yml via the verified v2 parser module.

    The original returns {serial: name} and handles both RPCS3 formats — flat
    (value is the game path) and nested (name:/path:) — deriving display names
    from folder paths like '.../Game Name [BLUS12345]/'. Falls back to the
    built-in minimal parser when the v2 core or PyYAML is unavailable.
    """
    mapping = None
    try:
        import sys as _sys

        try:
            import ps3_rpcs3_game_updater as _orig
        except ImportError:
            _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import ps3_rpcs3_game_updater as _orig

        mapping = _orig.read_games_yml(rpcs3_dir)
    except Exception:  # noqa: BLE001 - missing file / PyYAML -> built-in fallback
        mapping = None
    if isinstance(mapping, dict):
        return [{"serial": str(k).upper(), "title": v or ""} for k, v in mapping.items()]

    path = os.path.join(rpcs3_dir, GAMES_YML_RELPATH)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return parse_games_yml(fh.read())
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# PARAM.SFO reader (minimal, strings only)
# --------------------------------------------------------------------------- #

def read_sfo_strings(path: str) -> Dict[str, str]:
    """Read string values from a PS3 PARAM.SFO file. Returns {} on failure."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(1024 * 1024)
    except OSError:
        return {}
    if len(data) < 64 or data[:4] != b"SFB\x00":
        return {}
    try:
        _version, max_entries, entry_size, num_entries = struct.unpack_from("<IIII", data, 8)
    except struct.error:
        return {}
    if not (1 <= num_entries <= max_entries and 32 <= entry_size <= 512):
        return {}

    out: Dict[str, str] = {}
    base = 64
    for i in range(num_entries):
        off = base + i * entry_size
        if off + entry_size > len(data):
            break
        key_end = data.index(b"\x00", off, min(off + 16, len(data)))
        key = data[off:key_end].decode("ascii", "ignore").strip()
        if not key:
            continue
        _type, size, value_off = struct.unpack_from("<BII", data, off + 16)
        if _type != 0x01 or value_off + size > len(data):
            continue
        raw_val = data[value_off:value_off + size]
        val_end = raw_val.find(b"\x00")
        out[key] = (raw_val[:val_end] if val_end >= 0 else raw_val).decode("utf-8", "ignore").strip()
    return out


# --------------------------------------------------------------------------- #
# Game folder scanning
# --------------------------------------------------------------------------- #

_VERSION_DIR_RE = re.compile(r"^\d{2}\.\d{2}(?:\.\d{2})?$")


def _installed_version_from_folder(game_dir: str) -> Optional[str]:
    """Detect an installed update version from a version-named subfolder."""
    for root, dirs, files in os.walk(game_dir):
        depth = root[len(os.path.normpath(game_dir)):].count(os.sep)
        if depth > 2:
            dirs[:] = []
            continue
        for d in list(dirs):
            if _VERSION_DIR_RE.match(d):
                sfo = os.path.join(root, d, "PARAM.SFO")
                if os.path.isfile(sfo):
                    return d
        # don't descend into PS3_GAME content trees deeper than needed
        dirs[:] = [d for d in dirs if d.upper() not in ("PS3_GAME",)] or dirs[:16]
    return None


def _folder_game_info(folder: str) -> Optional[GameInfo]:
    name = os.path.basename(os.path.normpath(folder))
    has_ps3_game = os.path.isdir(os.path.join(folder, "PS3_GAME"))
    sfo_path = os.path.join(folder, "PARAM.SFO")
    if not (has_ps3_game or os.path.isfile(sfo_path)):
        return None

    title = ""
    serial = name.upper()
    if os.path.isfile(sfo_path):
        strings = read_sfo_strings(sfo_path)
        title = strings.get("TITLE", "")
        sfo_serial = (strings.get("SERIAL") or "").upper()
        if is_valid_serial(sfo_serial):
            serial = sfo_serial

    return GameInfo(
        serial=serial,
        title=title,
        version=_installed_version_from_folder(folder),
        path=os.path.normpath(folder),
        source="folder",
    )


def scan_games_root(games_root: str) -> List[GameInfo]:
    """Scan a dev_hdd0/game style folder for installed games."""
    found: List[GameInfo] = []
    if not os.path.isdir(games_root):
        return found
    try:
        names = sorted(os.listdir(games_root))
    except OSError:
        return found
    for name in names:
        folder = os.path.join(games_root, name)
        if not os.path.isdir(folder):
            continue
        info = _folder_game_info(folder)
        if info is not None:
            found.append(info)
    return found


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #

def build_library(rpcs3_dir: str, games_root: Optional[str] = None) -> List[GameInfo]:
    """Combine games.yml entries with on-disk game folders.

    Folder data wins for paths; yml provides titles/versions when the folder
    has no readable metadata. Result is sorted by title (case-insensitive).
    """
    merged: Dict[str, GameInfo] = {}

    for entry in load_games_yml(rpcs3_dir):
        serial = (entry.get("serial") or "").strip().upper()
        if not is_valid_serial(serial):
            continue
        info = GameInfo(
            serial=serial,
            title=(entry.get("title") or entry.get("name") or "").strip(),
            version=(entry.get("version") or None),
            yml_version=(entry.get("version") or None),
            source="yml",
        )
        merged[serial] = info

    root = games_root or os.path.join(rpcs3_dir, DEV_HDD_GAME_RELPATH)
    for folder_info in scan_games_root(root):
        serial = folder_info.serial
        existing = merged.get(serial)
        if existing is None:
            merged[serial] = folder_info
        else:
            existing.path = folder_info.path
            existing.source = "both"
            if not existing.title and folder_info.title:
                existing.title = folder_info.title
            if folder_info.version:
                existing.version = folder_info.version

    library = sorted(merged.values(), key=lambda g: (g.display_title.lower(), g.serial))
    return library
