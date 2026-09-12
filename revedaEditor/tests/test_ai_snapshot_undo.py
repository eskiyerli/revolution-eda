"""Tests for the editor-owned AI JSON snapshot undo command."""

from PySide6.QtGui import QUndoCommand, QUndoStack

from revedaEditor.backend.undoStack import replaceDesignSnapshotUndo


def test_snapshot_command_applies_then_undoes_and_redoes():
    applied = []
    current = {"value": b"before"}

    def apply_snapshot(snapshot):
        applied.append(snapshot)
        current["value"] = snapshot
        return True

    stack = QUndoStack()
    command = replaceDesignSnapshotUndo(b"before", b"after", apply_snapshot)
    stack.push(command)

    assert command.lastSuccess
    assert current["value"] == b"after"
    assert applied == [b"after"]

    stack.undo()
    assert command.lastSuccess
    assert current["value"] == b"before"

    stack.redo()
    assert command.lastSuccess
    assert current["value"] == b"after"
    assert applied == [b"after", b"before", b"after"]


def test_snapshot_command_recovers_previous_snapshot_after_failed_apply():
    applied = []
    current = {"value": b"before"}

    def apply_snapshot(snapshot):
        applied.append(snapshot)
        if snapshot == b"after":
            return False
        current["value"] = snapshot
        return True

    stack = QUndoStack()
    command = replaceDesignSnapshotUndo(b"before", b"after", apply_snapshot)
    stack.push(command)

    assert not command.lastSuccess
    assert "could not reload" in command.lastError
    assert current["value"] == b"before"
    assert applied == [b"after", b"before"]


def test_snapshot_command_can_follow_existing_editor_history():
    applied = []
    stack = QUndoStack()
    previous = QUndoCommand("Previous editor action")
    stack.push(previous)
    command = replaceDesignSnapshotUndo(
        b"before", b"after", lambda snapshot: applied.append(snapshot) or True
    )

    stack.push(command)

    assert stack.count() == 2
    assert stack.index() == 2
    assert stack.command(0) is previous
    assert stack.command(1) is command
    assert applied == [b"after"]
