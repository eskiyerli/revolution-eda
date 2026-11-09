# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

from PySide6.QtCore import (
    Qt, Signal,
)
from PySide6.QtWidgets import QLineEdit, QLabel, QWidget


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
        self.setMaximumWidth(500)
        self.setMinimumWidth(200)
        if isinstance(value, str):
            self.setText(value)
        else:
            self.setText(str(value))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.cursorPlaced.emit()
