"""Data models shared by the updater core and the GUI."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

SERIAL_RE = re.compile(r"^[A-Z0-9]{9}$")


def normalize_serial(raw: str) -> str:
    """Normalize a game serial to uppercase (e.g. 'BLES02657' stays as-is)."""
    return (raw or "").strip().upper()


def is_valid_serial(serial: str) -> bool:
    return bool(SERIAL_RE.match(normalize_serial(serial)))


@dataclass
class GameInfo:
    """A game discovered on disk (from games.yml and/or the install folder)."""

    serial: str = ""
    title: str = ""
    version: Optional[str] = None          # installed base-game version, if known
    path: str = ""                          # absolute path to the game folder
    source: str = "folder"                  # 'yml' | 'folder' | 'both'
    yml_version: Optional[str] = None       # version recorded in games.yml

    @property
    def display_title(self) -> str:
        return self.title or self.serial or "Unknown game"

    @property
    def folder_name(self) -> str:
        if self.path:
            return os.path.basename(os.path.normpath(self.path))
        return self.serial


@dataclass
class UpdateInfo:
    """A PSN update candidate for a game."""

    serial: str = ""
    title: str = ""
    version: Optional[str] = None          # e.g. '01.02'
    size_bytes: int = 0
    url: str = ""
    sha1: Optional[str] = None             # expected SHA-1 of the .pkg, if known
    source: str = "psn"                    # 'psn' | 'local'

    @property
    def display_version(self) -> str:
        return self.version or "?"


@dataclass
class DownloadState:
    """Mutable per-game download progress state."""

    serial: str = ""
    status: str = "idle"                    # idle|downloading|verifying|done|error|cancelled
    percent: float = 0.0
    received_bytes: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    error: Optional[str] = None
    pkg_path: str = ""                      # final .pkg location when done
