# `revedaEditor/tests/test_ai_snapshot_undo.py`

**Module:** `revedaEditor.tests.test_ai_snapshot_undo`

## Purpose

aiTerminal snapshot/undo integration tests.

## Module docstring

Tests for the editor-owned AI JSON snapshot undo command.

## Functions

- `test_snapshot_command_applies_then_undoes_and_redoes()`
- `test_snapshot_command_recovers_previous_snapshot_after_failed_apply()`
- `test_snapshot_command_can_follow_existing_editor_history()`

## Depends on

- [[revedaEditor/backend/undoStack|revedaEditor.backend.undoStack]]
