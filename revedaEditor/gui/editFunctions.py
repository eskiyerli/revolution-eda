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
