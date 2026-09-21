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

"""Find/replace dialog for schematic editors.

Searches instances, nets and pins by name pattern (shell wildcards) and
optional property filter, backed by ``schematicScene.findItems`` — nets
resolve through the unified connectivity engine so a hit selects every
member wire of the electrical net. Selecting a row zooms to the hit;
Replace renames via ``schematicScene.replaceHitName``.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

import revedaEditor.gui.editFunctions as edf

_KIND_BY_LABEL = {
    "All": "any",
    "Instances": "instance",
    "Nets": "net",
    "Pins": "pin",
}


class findDialogue(QDialog):
    """Non-modal find/replace panel for one schematic scene."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.scene = parent.centralW.scene
        self.setWindowTitle(
            f"Find/Replace — {parent.cellName} {parent.viewName}")
        self.setMinimumWidth(480)
        self.hits = []

        mainLayout = QVBoxLayout(self)
        formLayout = QFormLayout()

        self.typeCombo = QComboBox(self)
        self.typeCombo.addItems(list(_KIND_BY_LABEL))
        formLayout.addRow(edf.boldLabel("Find", self), self.typeCombo)

        self.findEdit = edf.longLineEdit(self)
        self.findEdit.setPlaceholderText("name pattern, e.g. net<*>, I*")
        formLayout.addRow(edf.boldLabel("Named", self), self.findEdit)

        self.propEdit = edf.longLineEdit(self)
        self.propEdit.setPlaceholderText("instances only: name=value or name")
        formLayout.addRow(edf.boldLabel("Where", self), self.propEdit)

        self.replaceEdit = edf.longLineEdit(self)
        self.replaceEdit.setPlaceholderText("replacement text (optional)")
        formLayout.addRow(edf.boldLabel("Replace", self), self.replaceEdit)
        mainLayout.addLayout(formLayout)

        self.resultsTable = QTableWidget(0, 3, self)
        self.resultsTable.setHorizontalHeaderLabels(["Type", "Name", "Detail"])
        self.resultsTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self.resultsTable.horizontalHeader().setStretchLastSection(True)
        self.resultsTable.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.resultsTable.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.resultsTable.itemSelectionChanged.connect(self._zoomToSelected)
        mainLayout.addWidget(self.resultsTable)

        buttonRow = QHBoxLayout()
        self.findButton = QPushButton("Find", self)
        self.findButton.clicked.connect(self.runFind)
        self.replaceButton = QPushButton("Replace", self)
        self.replaceButton.clicked.connect(self._replaceSelected)
        self.replaceAllButton = QPushButton("Replace All", self)
        self.replaceAllButton.clicked.connect(self._replaceAll)
        self.closeButton = QPushButton("Close", self)
        self.closeButton.clicked.connect(self.reject)
        for button in (self.findButton, self.replaceButton,
                       self.replaceAllButton, self.closeButton):
            buttonRow.addWidget(button)
        mainLayout.addLayout(buttonRow)

        self.findEdit.returnPressed.connect(self.runFind)

    def _kind(self) -> str:
        return _KIND_BY_LABEL[self.typeCombo.currentText()]

    def runFind(self):
        """Populate the results table from the scene."""
        self.hits = self.scene.findItems(
            self._kind(), self.findEdit.text(), self.propEdit.text())
        self.resultsTable.setRowCount(0)
        self.resultsTable.setRowCount(len(self.hits))
        for row, hit in enumerate(self.hits):
            self.resultsTable.setItem(row, 0, QTableWidgetItem(hit.kind))
            self.resultsTable.setItem(row, 1, QTableWidgetItem(hit.name))
            self.resultsTable.setItem(row, 2, QTableWidgetItem(hit.detail))
        if self.scene.editorWindow is not None:
            self.scene.editorWindow.messageLine.setText(
                f"Find: {len(self.hits)} match(es)")

    def _selectedHit(self):
        rows = {index.row() for index in self.resultsTable.selectedIndexes()}
        if len(rows) == 1:
            return rows.pop()
        return None

    def _zoomToSelected(self):
        row = self._selectedHit()
        if row is None or row >= len(self.hits):
            return
        hit = self.hits[row]
        self.scene.clearSelection()
        for item in hit.items:
            item.setSelected(True)
        pad = self.scene.snapGrid * 8
        self.scene.zoomToRect(hit.rect.adjusted(-pad, -pad, pad, pad).toRect())

    def _replaceSelected(self):
        row = self._selectedHit()
        if row is None:
            return
        self._applyReplace(self.hits[row])
        self.runFind()

    def _replaceAll(self):
        for hit in self.hits:
            self._applyReplace(hit)
        self.runFind()

    def _applyReplace(self, hit):
        newName = self.scene.replaceHitName(
            hit, self.findEdit.text().strip(), self.replaceEdit.text().strip())
        if newName and self.scene.editorWindow is not None:
            self.scene.logger.info(
                f"Renamed {hit.kind} {hit.name} -> {newName}")


class markerBrowserDialogue(QDialog):
    """Non-modal browser for check violations (``scene.lastCheckViolations``).

    Lists rule/severity/message per violation; selecting a row zooms to its
    marker rect. Violations persist across save/load via ``mrk`` records, so
    the browser is meaningful immediately after opening a checked design.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.scene = parent.centralW.scene
        self.setWindowTitle(
            f"Check Violations — {parent.cellName} {parent.viewName}")
        self.setMinimumWidth(560)

        mainLayout = QVBoxLayout(self)
        self.resultsTable = QTableWidget(0, 3, self)
        self.resultsTable.setHorizontalHeaderLabels(
            ["Severity", "Rule", "Message"])
        self.resultsTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self.resultsTable.horizontalHeader().setStretchLastSection(True)
        self.resultsTable.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.resultsTable.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.resultsTable.itemSelectionChanged.connect(self._zoomToSelected)
        mainLayout.addWidget(self.resultsTable)

        buttonRow = QHBoxLayout()
        self.refreshButton = QPushButton("Refresh", self)
        self.refreshButton.clicked.connect(self.refresh)
        self.closeButton = QPushButton("Close", self)
        self.closeButton.clicked.connect(self.reject)
        buttonRow.addWidget(self.refreshButton)
        buttonRow.addWidget(self.closeButton)
        mainLayout.addLayout(buttonRow)

        self.refresh()

    def refresh(self):
        violations = getattr(self.scene, "lastCheckViolations", [])
        self.resultsTable.setRowCount(len(violations))
        for row, violation in enumerate(violations):
            severity = ("error" if violation.severity.name == "ERROR"
                        else "warning")
            sevItem = QTableWidgetItem(severity)
            sevItem.setForeground(
                Qt.GlobalColor.red if severity == "error"
                else Qt.GlobalColor.darkMagenta)
            self.resultsTable.setItem(row, 0, sevItem)
            self.resultsTable.setItem(
                row, 1, QTableWidgetItem(violation.ruleId))
            self.resultsTable.setItem(
                row, 2, QTableWidgetItem(violation.message))
        if self.scene.editorWindow is not None:
            self.scene.editorWindow.messageLine.setText(
                f"{len(violations)} violation(s)")

    def _zoomToSelected(self):
        rows = {index.row() for index in self.resultsTable.selectedIndexes()}
        if len(rows) != 1:
            return
        violations = getattr(self.scene, "lastCheckViolations", [])
        row = rows.pop()
        if row >= len(violations):
            return
        markers = violations[row].markers
        if not markers:
            return
        rect = markers[0]
        for marker in markers[1:]:
            rect = rect.united(marker)
        pad = self.scene.snapGrid * 8
        self.scene.zoomToRect(
            rect.adjusted(-pad, -pad, pad, pad).toRect())
