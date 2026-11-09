# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

# properties dialogues for various editor functions

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QLabel,
    QComboBox,
)


class findProjectEditors(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Find Related Editors")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 20, 10, 20)
        self.relatedEditorsCB = QComboBox()
        self.fLayout.addRow(QLabel("Find Related Editors:"), self.relatedEditorsCB)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()
