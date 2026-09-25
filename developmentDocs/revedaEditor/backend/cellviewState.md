# `revedaEditor\backend\cellviewState.py`

**Module:** `revedaEditor.backend.cellviewState`

## Purpose

Cellview lifecycle file state: lock files and autosave files.

## Functions

- `autosavePathFor()` — Return the autosave file path for a cellview JSON file.
- `lockPathFor()` — Return the lock file path for a cellview JSON file.
- `isAutosaveNewer()` — True when a usable autosave exists and is newer than the primary file.
- `isAutosaveUsable()` — True when the autosave parses as a JSON cellview record list.
- `processAlive()` — Best-effort cross-platform liveness check for a process ID.
- `_winPidAlive()` — Windows liveness check via OpenProcess and GetExitCodeProcess.
- `lockOwnerInfo()` — Lock record payload identifying this process.
- `writeLockFile()` — Atomically replace a lock file with this process's owner record.
- `_createLockFile()` — Create and own a new lock, failing when the path already exists.
- `readLockFile()` — Parse a lock file; None when absent or malformed.
- `acquireLock()` — Atomically acquire a local lock without replacing remote ownership.
- `releaseLock()` — Remove the lock only when it is still owned by this process and host.

## Used by

- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\tests\test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
