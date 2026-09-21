#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

"""Cellview lifecycle file state: lock files and autosave files.

Qt-free helpers so both the GUI editors and headless tooling can share the
same on-disk contracts:

- ``<view>.lock`` — JSON ``{"pid", "user", "host", "time"}`` next to the
  cellview JSON. A remote host or live local PID means contention; a dead
  local PID or unreadable lock is treated as stale and taken over.
- ``<view>.autosave`` — periodic snapshot written next to the cellview JSON,
  offered for crash recovery when newer than the primary file.
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path

logger = logging.getLogger("reveda")


def autosavePathFor(viewPath: Path) -> Path:
    """Return the autosave file path for a cellview JSON file.

    ``schematic.json`` -> ``schematic.json.autosave``. Name-appending (rather
    than suffix-replacing) keeps the writers' ``with_suffix(".tmp")`` staging
    files distinct from the primary save's temp file.
    """
    viewPath = Path(viewPath)
    return viewPath.parent / (viewPath.name + ".autosave")


def lockPathFor(viewPath: Path) -> Path:
    """Return the lock file path for a cellview JSON file."""
    viewPath = Path(viewPath)
    return viewPath.parent / (viewPath.name + ".lock")


def isAutosaveNewer(viewPath: Path, autosavePath: Path) -> bool:
    """True when a usable autosave exists and is newer than the primary file."""
    autosavePath = Path(autosavePath)
    viewPath = Path(viewPath)
    if not autosavePath.is_file():
        return False
    try:
        autosaveMtime = autosavePath.stat().st_mtime
        viewMtime = viewPath.stat().st_mtime if viewPath.exists() else 0.0
    except OSError:
        return False
    return autosaveMtime > viewMtime


def isAutosaveUsable(autosavePath: Path) -> bool:
    """True when the autosave parses as a JSON cellview record list.

    A crash mid-write can leave a truncated autosave; offering it for
    recovery would fail to load and re-prompt on every open, so malformed
    files are treated as unusable.
    """
    try:
        with Path(autosavePath).open("r", encoding="utf-8") as f:
            data = json.load(f)
        return isinstance(data, list) and len(data) > 0
    except (OSError, json.JSONDecodeError):
        return False


def processAlive(pid: int) -> bool:
    """Best-effort cross-platform liveness check for a process ID."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform.startswith("win"):
        return _winPidAlive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _winPidAlive(pid: int) -> bool:
    """Windows liveness check via OpenProcess and GetExitCodeProcess."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            exitCode = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exitCode)):
                return False
            return exitCode.value == 259
        finally:
            kernel32.CloseHandle(handle)
    except (AttributeError, OSError, ValueError):
        return False


def lockOwnerInfo() -> dict:
    """Lock record payload identifying this process."""
    return {
        "pid": os.getpid(),
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "time": time.time(),
    }


def writeLockFile(lockPath: Path) -> dict:
    """Atomically replace a lock file with this process's owner record."""
    lockPath = Path(lockPath)
    record = lockOwnerInfo()
    lockPath.parent.mkdir(parents=True, exist_ok=True)
    tempPath = lockPath.with_name(
        f"{lockPath.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        with tempPath.open("w", encoding="utf-8") as f:
            json.dump(record, f)
        tempPath.replace(lockPath)
    finally:
        tempPath.unlink(missing_ok=True)
    return record


def _createLockFile(lockPath: Path) -> dict:
    """Create and own a new lock, failing when the path already exists."""
    lockPath = Path(lockPath)
    record = lockOwnerInfo()
    lockPath.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lockPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f)
    except BaseException:
        lockPath.unlink(missing_ok=True)
        raise
    return record


def readLockFile(lockPath: Path) -> dict | None:
    """Parse a lock file; None when absent or malformed."""
    try:
        with Path(lockPath).open("r", encoding="utf-8") as f:
            record = json.load(f)
        return record if isinstance(record, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def acquireLock(lockPath: Path) -> tuple[str, dict]:
    """Atomically acquire a local lock without replacing remote ownership."""
    lockPath = Path(lockPath)
    localHost = socket.gethostname().casefold()
    existing = None
    for _ in range(3):
        try:
            return "held", _createLockFile(lockPath)
        except FileExistsError:
            existing = readLockFile(lockPath)
        except OSError as e:
            logger.warning(f"Cannot write cellview lock {lockPath}: {e}")
            return "contended", existing or {}

        if existing:
            ownerHost = existing.get("host")
            if isinstance(ownerHost, str) and ownerHost.casefold() != localHost:
                return "contended", existing
            ownerPid = existing.get("pid")
            if ownerPid == os.getpid():
                return "held", existing
            if isinstance(ownerPid, int) and processAlive(ownerPid):
                return "contended", existing

        if readLockFile(lockPath) != existing:
            continue
        stalePath = lockPath.with_name(
            f"{lockPath.name}.stale-{os.getpid()}-{time.time_ns()}")
        try:
            lockPath.replace(stalePath)
        except FileNotFoundError:
            continue
        except OSError as e:
            logger.warning(f"Cannot replace stale cellview lock {lockPath}: {e}")
            return "contended", existing or {}
        try:
            return "held", _createLockFile(lockPath)
        except FileExistsError:
            continue
        except OSError as e:
            logger.warning(f"Cannot write cellview lock {lockPath}: {e}")
            return "contended", existing or {}
        finally:
            stalePath.unlink(missing_ok=True)
    return "contended", readLockFile(lockPath) or existing or {}


def releaseLock(lockPath: Path) -> None:
    """Remove the lock only when it is still owned by this process and host."""
    lockPath = Path(lockPath)
    existing = readLockFile(lockPath)
    if existing is None or existing.get("pid") != os.getpid() or \
            str(existing.get("host", "")).casefold() != socket.gethostname().casefold():
        return
    try:
        lockPath.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"Cannot remove cellview lock {lockPath}: {e}")
