"""PSN update lookup — adapter over the verified v2 Sony update logic.

The original module is the single source of truth for:
  * fetch_updates()    – a0.ww.np.dl.playstation.net titlepatch XML
                         (verify=False, scoped to Sony's private-CA chain)
  * fetch_meta()       – TMDB HMAC-SHA1 display name + box-art URL
  * lookup_with_meta() – local-first art priority (ICON0 -> TMDB)

This layer only adapts results into updater.models.UpdateInfo and adds a
convenience wrapper returning the full update list for one serial. No network
behavior is reimplemented here, so CLI and GUI stay in lockstep forever.
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

from .models import UpdateInfo, is_valid_serial

try:  # project root must be importable (dev runs from any cwd / frozen builds)
    import ps3_rpcs3_game_updater as _orig
except ImportError:  # pragma: no cover - path fallback for unusual launch dirs
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import ps3_rpcs3_game_updater as _orig


class PsnLookupError(Exception):
    """Raised when a PSN lookup fails; message is safe to show in the UI."""


# Verified Sony logic — re-exported so callers/tests patch one stable namespace.
fetch_updates = _orig.fetch_updates
fetch_meta = _orig.fetch_meta
download_icon = _orig.download_icon
read_local_icon = _orig.read_local_icon
lookup_with_meta = _orig.lookup_with_meta
sanitize_name = _orig.sanitize_name
version_key = _orig.version_key
fmt_size = _orig.fmt_size


def pkg_to_update(serial: str, pkg: dict) -> UpdateInfo:
    """Convert one Sony pkg dict into an UpdateInfo."""
    return UpdateInfo(
        serial=serial,
        title="",
        version=(pkg.get("version") or "").strip() or None,
        size_bytes=int(pkg.get("size") or 0),
        url=pkg.get("url", ""),
        sha1=(pkg.get("sha1") or "").lower() or None,
        source="psn" + (" (drm-free)" if pkg.get("drm_free") else ""),
    )


def lookup_updates(serial: str, timeout: int = 20) -> Tuple[Optional[str], List[UpdateInfo]]:
    """Full update list for a serial. Returns (game_name, [UpdateInfo] ascending).

    Raises PsnLookupError with a readable message on invalid serial or network
    failure. An empty list means "no updates published" — not an error.
    """
    serial = (serial or "").strip().upper()
    if not is_valid_serial(serial):
        raise PsnLookupError(f"Invalid game serial: {serial!r}")
    try:
        name, pkgs = fetch_updates(serial, timeout=timeout)
    except LookupError as exc:
        raise PsnLookupError(str(exc)) from exc
    except ValueError as exc:
        raise PsnLookupError(str(exc)) from exc
    return (name or None), [pkg_to_update(serial, p) for p in pkgs]


def lookup_latest(serial: str, timeout: int = 20) -> Optional[UpdateInfo]:
    """Newest published update only (None when the title has no updates)."""
    _, updates = lookup_updates(serial, timeout=timeout)
    return updates[-1] if updates else None
