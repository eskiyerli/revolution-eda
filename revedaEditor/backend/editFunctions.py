# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

from pathlib import Path

from PySide6.QtCore import (
    QSettings,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QLabel, QLineEdit, QWidget

APP_SETTINGS_FILE = Path.home() / ".reveda" / "reveda_settings.ini"


def appSettings() -> QSettings:
    """Return QSettings backed by the shared ~/.reveda/reveda_settings.ini."""
    APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    return QSettings(str(APP_SETTINGS_FILE), QSettings.IniFormat)


class shortLineEdit(QLineEdit):
    def __init__(self, value: str = ""):
        super().__init__(None)
        self.setMaximumWidth(90)
        if isinstance(value, str):
            self.setText(value)
        else:
            self.setText(str(value))


class boldLabel(QLabel):
    def __init__(self, text: str, parent: QWidget = None):
        super().__init__(text, parent)
        self.setTextFormat(Qt.RichText)
        self.setText("<b>" + text + "</b>")


class longLineEdit(QLineEdit):
    cursorPlaced = Signal()

    def __init__(self, value: str = ""):
        super().__init__(None)
        self.setMaximumWidth(800)
        self.setMinimumWidth(200)
        if isinstance(value, str):
            self.setText(value)
        else:
            self.setText(str(value))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.cursorPlaced.emit()
