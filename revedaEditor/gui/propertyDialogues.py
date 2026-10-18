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

# properties dialogues for various editor functions

import pathlib

from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QFontDatabase,
    QIntValidator,
)
from quantiphy import Quantity
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import revedaEditor.common.labels as lbl
import revedaEditor.common.net as net
import revedaEditor.common.params as prm
import revedaEditor.common.shapes as shp
import revedaEditor.gui.editFunctions as edf
from revedaEditor.backend.pdkLoader import lazyPDKModule

fabproc = lazyPDKModule("process")


def paramValueWidget(pdef: prm.ParamDef, value: str, parent=None):
    """Build the editor widget for a typed parameter.

    Returns ``(widget, getValue, setValue)`` where ``getValue() -> str``
    and ``setValue(str)``. This is the single widget-construction path
    shared by the instance properties form and the place-with-params
    form."""
    if pdef.type == "boolean":
        widget = QCheckBox(parent)
        widget.setChecked(str(value).strip().lower() in prm._BOOL_TRUE)
        return (widget,
                lambda w=widget: "true" if w.isChecked() else "false",
                lambda v, w=widget: w.setChecked(
                    str(v).strip().lower() in prm._BOOL_TRUE))
    if pdef.type == "choice":
        widget = QComboBox(parent)
        widget.setEditable(True)  # tolerate legacy values outside choices
        widget.addItems(list(pdef.choices))
        widget.setCurrentText(str(value))
        return (widget,
                lambda w=widget: w.currentText(),
                lambda v, w=widget: w.setCurrentText(str(v)))
    # float / int / string: quantiphy-capable line edit
    widget = edf.longLineEdit()
    widget.setText(str(value))
    hints = [pdef.type]
    if pdef.minimum:
        hints.append(f"min {pdef.minimum}")
    if pdef.maximum:
        hints.append(f"max {pdef.maximum}")
    if pdef.parse and pdef.type in ("float", "int"):
        hints.append("SI suffixes allowed")
    hints.append("{expr} deferred to simulator")
    widget.setToolTip(", ".join(hints))
    return (widget,
            lambda w=widget: w.text(),
            lambda v, w=widget: w.setText(str(v)))


class placeInstanceDialog(QDialog):
    """Label-driven schematic placement options form.

    The optional source summary and mosaic controls mirror layout placement
    options. Label rows remain the single source of schematic parameter
    values: a matching ``paramDef`` only enriches an editable NLP label with
    typing and validation.
    """

    def __init__(self, parent, labelRows: list,
                 initialValues: dict | None = None,
                 onValuesChanged=None, sourceTuple=None,
                 arraySpec: tuple[int, int, int, int] | None = None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Schematic Instance Options")
        self.setMinimumWidth(400)
        self.labelRows = []
        self.paramRows = []  # Legacy/test-facing ``[(ParamDef, getValue)]``.
        self._onValuesChanged = onValuesChanged
        self._refreshTimer = QTimer(self)
        self._refreshTimer.setSingleShot(True)
        self._refreshTimer.timeout.connect(self._emitValuesChanged)

        # Compatibility for the original ParamDef-only public constructor.
        if all(isinstance(row, prm.ParamDef) for row in labelRows):
            supplied = {
                f"@{name.lstrip('@')}": value
                for name, value in (initialValues or {}).items()
            }
            defaults = prm.applyDefaults(labelRows, supplied)
            labelRows = [{
                "labelName": f"@{pdef.name}",
                "valueKey": pdef.name,
                "value": defaults.get(f"@{pdef.name}", pdef.default),
                "paramDef": pdef,
                "isEditable": pdef.display,
                "isVisible": pdef.display,
                "isPyLabel": False,
            } for pdef in labelRows]

        mainLayout = QVBoxLayout()
        if sourceTuple is not None:
            sourceGroup = QGroupBox("Instance Parameters")
            sourceLayout = QFormLayout()
            sourceGroup.setLayout(sourceLayout)
            for title, value in (
                    ("Library:", sourceTuple.libraryName),
                    ("Cell:", sourceTuple.cellName),
                    ("View:", sourceTuple.viewName)):
                field = edf.longLineEdit()
                field.setText(str(value))
                field.setReadOnly(True)
                sourceLayout.addRow(title, field)
            mainLayout.addWidget(sourceGroup)

        supplied = initialValues or {}
        self._validationContext = {
            row["labelName"]: next(
                (supplied[key] for key in (row["labelName"], row["labelName"].lstrip("@"))
                 if key in supplied),
                row.get("value", ""),
            )
            for row in labelRows
            if not row.get("isVisible", True)
        }
        formLayout = QFormLayout()
        section = None
        for sourceRow in labelRows:
            row = dict(sourceRow)
            if not row.get("isVisible", True):
                continue
            rowSection = row.get("section")
            if rowSection and rowSection != section:
                formLayout.addRow(edf.boldLabel(rowSection, self))
                section = rowSection
            labelName = row["labelName"]
            pdef = row.get("paramDef")
            isEditable = row.get("isEditable", not row.get("isPyLabel", False))
            value = next((supplied[key] for key in (labelName,
                                                     labelName.lstrip("@"))
                          if key in supplied), row.get("value", ""))
            if pdef is not None:
                widget, getValue, setValue = paramValueWidget(pdef, value, self)
            else:
                widget = edf.longLineEdit()
                widget.setText(str(value))
                getValue = widget.text
                setValue = widget.setText
            if not isEditable:
                if hasattr(widget, "setReadOnly"):
                    widget.setReadOnly(True)
                else:
                    widget.setEnabled(False)
                widget.setToolTip("Computed or literal label (Read Only)")
            formLayout.addRow(edf.boldLabel(labelName.lstrip("@"), self), widget)
            row.update({
                "isEditable": isEditable,
                "valueEdit": widget,
                "getValue": getValue,
                "setValue": setValue,
                "valueKey": row.get("valueKey", labelName),
            })
            self.labelRows.append(row)
            if pdef is not None and isEditable:
                self.paramRows.append((pdef, getValue))
            if isEditable:
                self._connectValueChanged(widget)
        if self.labelRows:
            mainLayout.addLayout(formLayout)

        self.arrayGroup = QGroupBox("Instance Array (Mosaic)")
        arrayLayout = QFormLayout()
        self.arrayGroup.setLayout(arrayLayout)
        self.rowsEdit = edf.shortLineEdit()
        self.rowsEdit.setValidator(QIntValidator(1, 100000, self))
        arrayLayout.addRow(edf.boldLabel("Rows:"), self.rowsEdit)
        self.columnsEdit = edf.shortLineEdit()
        self.columnsEdit.setValidator(QIntValidator(1, 100000, self))
        arrayLayout.addRow(edf.boldLabel("Columns:"), self.columnsEdit)
        self.xPitchEdit = edf.shortLineEdit()
        self.xPitchEdit.setValidator(QIntValidator(0, 1000000000, self))
        arrayLayout.addRow(edf.boldLabel("X Pitch:"), self.xPitchEdit)
        self.yPitchEdit = edf.shortLineEdit()
        self.yPitchEdit.setValidator(QIntValidator(0, 1000000000, self))
        arrayLayout.addRow(edf.boldLabel("Y Pitch:"), self.yPitchEdit)
        rows, columns, xPitch, yPitch = arraySpec or (1, 1, 0, 0)
        self.rowsEdit.setText(str(rows))
        self.columnsEdit.setText(str(columns))
        self.xPitchEdit.setText(str(xPitch))
        self.yPitchEdit.setText(str(yPitch))
        # Legacy generic ParamDef callers do not represent a placement source.
        self.arrayGroup.setVisible(sourceTuple is not None)
        mainLayout.addWidget(self.arrayGroup)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self._validateAndAccept)
        buttonBox.rejected.connect(self.reject)

    def _connectValueChanged(self, widget):
        if isinstance(widget, QCheckBox):
            widget.toggled.connect(self._scheduleValuesChanged)
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(self._scheduleValuesChanged)
        else:
            widget.textChanged.connect(self._scheduleValuesChanged)

    def _scheduleValuesChanged(self, *_args):
        self._refreshTimer.start(0)

    def _emitValuesChanged(self):
        if self._onValuesChanged is not None:
            self._onValuesChanged(self.paramValues())

    def refreshPreview(self):
        """Synchronously refresh read-only callback values in this form."""
        self._emitValuesChanged()

    def arraySpec(self) -> tuple[int, int, int, int] | None:
        """Return rows, columns, X pitch, Y pitch or ``None`` for 1×1."""
        try:
            rows = max(1, int(self.rowsEdit.text() or "1"))
            columns = max(1, int(self.columnsEdit.text() or "1"))
            xPitch = int(self.xPitchEdit.text() or "0")
            yPitch = int(self.yPitchEdit.text() or "0")
        except ValueError:
            return None
        if rows * columns <= 1:
            return None
        return rows, columns, max(0, xPitch), max(0, yPitch)

    def _validateAndAccept(self):
        errors = []
        values = {**self._validationContext, **self.paramValues()}
        for row in self.labelRows:
            pdef = row.get("paramDef")
            if not row["isEditable"] or pdef is None:
                continue
            errors.extend(
                f"{pdef.name}: {error}"
                for error in prm.validateValue(pdef, row["getValue"](), values))
        if errors:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid parameters", "\n".join(errors))
            return
        self.accept()

    def paramValues(self) -> dict:
        """Current editable label values, keyed by their persistent names."""
        return {row["valueKey"]: row["getValue"]()
                for row in self.labelRows if row["isEditable"]}


class rectPropertyDialog(QDialog):
    """
    Property dialog for symbol rectangles.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumWidth(300)
        self.setWindowTitle("Rectangle Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 20, 10, 20)
        self.rectWidthLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Width:"), self.rectWidthLine)
        self.rectHeightLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Height:"), self.rectHeightLine)
        self.rectLeftLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("X Origin:"), self.rectLeftLine)
        self.rectTopLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Y Origin:"), self.rectTopLine)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class circlePropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumWidth(300)
        self.setWindowTitle("Circle Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        self.centerXEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("center x-coord:"), self.centerXEdit)
        self.centerYEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("center y-coord:"), self.centerYEdit)
        self.radiusEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("radius:"), self.radiusEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class arcPropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Arc Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        # self.mainLayout.addWidget(self.arcTypeCombo)
        self.startXEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("X Origin:"), self.startXEdit)
        self.startYEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("Y Origin:"), self.startYEdit)
        self.widthEdit = edf.shortLineEdit()

        self.fLayout.addRow(edf.boldLabel("Width:"), self.widthEdit)
        self.heightEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("Height:"), self.heightEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class linePropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Line Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        self.startXLine = QLineEdit()

        self.fLayout.addRow(QLabel("Start (X):"), self.startXLine)
        self.startYLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Start (Y):"), self.startYLine)
        self.endXLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("End (X):"), self.endXLine)
        self.endYLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("End (Y):"), self.endYLine)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class pointsTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Del.", 'X', "Y"])
        self.setColumnWidth(0, 8)
        self.setShowGrid(True)
        self.setGridStyle(Qt.SolidLine)


class symbolPolygonProperties(QDialog):
    def __init__(self, parent: QWidget, tupleList: list):
        super().__init__(parent)
        self.tupleList = tupleList
        self.setWindowTitle("Symbol Polygon Properties")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        self.tableWidget = pointsTableWidget(self)
        mainLayout.addWidget(self.tableWidget)
        mainLayout.addWidget(self.buttonBox)
        self.populateTable()

    def populateTable(self):
        self.tableWidget.setRowCount(len(self.tupleList) + 1)  # Add one extra row

        for row, item in enumerate(self.tupleList):
            self.addRow(row, item)

        # Add an empty row at the end
        self.addEmptyRow(len(self.tupleList))

        # Connect cellChanged signal to handle when the last row is edited
        self.tableWidget.cellChanged.connect(self.handleCellChange)

    def addRow(self, row, item):

        delete_checkbox = QCheckBox()
        self.tableWidget.setCellWidget(row, 0, delete_checkbox)

        self.tableWidget.setItem(row, 1, QTableWidgetItem(str(item[0])))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(str(item[1])))
        delete_checkbox.stateChanged.connect(
            lambda state, r=row: self.deleteRow(r, state)
        )

    def addEmptyRow(self, row):

        # self.table_widget.insertRow(row)
        delete_checkbox = QCheckBox()
        self.tableWidget.setCellWidget(row, 0, delete_checkbox)
        delete_checkbox.stateChanged.connect(
            lambda state, r=row: self.deleteRow(r, state))

        self.tableWidget.setItem(row, 1, QTableWidgetItem(""))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(""))

    def handleCellChange(self, row, column):
        if (
                row == self.tableWidget.rowCount() - 1
        ):  # Check if last row and tuple text column
            if self.tableWidget.item(row, 2) is not None:
                text1 = self.tableWidget.item(row, 1).text()
                text2 = self.tableWidget.item(row, 2).text()
                if text1 != "" and text2 != "":
                    self.tableWidget.insertRow(row + 1)
                    self.addEmptyRow(row + 1)

    def deleteRow(self, row, state):
        if state == 2:  # Checked state
            self.tableWidget.removeRow(row)


class createPinDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Pin")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.pinName = edf.shortLineEdit()
        self.pinName.setPlaceholderText("Pin Name")
        self.pinName.setToolTip("Enter pin name")
        self.fLayout.addRow(QLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(shp.symbolPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        self.fLayout.addRow(QLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(shp.symbolPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        self.fLayout.addRow(QLabel("Pin Type"), self.pinType)
        self.netExprEdit = edf.longLineEdit()
        self.netExprEdit.setPlaceholderText("[@name] or [@name:default]")
        self.netExprEdit.setToolTip(
            "Net expression for inherited connections, e.g. [@vdd:vdd!]")
        self.fLayout.addRow(QLabel("Net Expression"), self.netExprEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class pinPropertyDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Pin Properties")
        self.pinXLine = edf.shortLineEdit()
        self.pinXLine.setToolTip("X Coordinate")
        self.fLayout.addRow(QLabel("X:"), self.pinXLine)
        self.pinYLine = edf.shortLineEdit()
        self.pinYLine.setToolTip("Y Coordinate")
        self.fLayout.addRow(QLabel("Y:"), self.pinYLine)


class createSymbolLabelDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Label")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.labelDefinition = QLineEdit()
        self.labelDefinition.setPlaceholderText("Label Definition")
        self.labelDefinition.setToolTip("Enter label Definition")
        self.fLayout.addRow(QLabel("Label Definition"), self.labelDefinition)
        self.labelHeightEdit = QLineEdit()
        self.labelHeightEdit.setPlaceholderText("Label Height")
        self.labelHeightEdit.setToolTip("Enter label Height")
        self.fLayout.addRow(QLabel("Label Height"), self.labelHeightEdit)
        self.labelAlignCombo = QComboBox()
        self.labelAlignCombo.addItems(lbl.symbolLabel.labelAlignments)
        self.fLayout.addRow(QLabel("Label Alignment"), self.labelAlignCombo)
        self.labelOrientCombo = QComboBox()
        self.labelOrientCombo.addItems(lbl.symbolLabel.labelOrients)
        self.fLayout.addRow(QLabel("Label Orientation"), self.labelOrientCombo)
        self.labelUseCombo = QComboBox()
        self.labelUseCombo.addItems(lbl.symbolLabel.labelUses)
        self.fLayout.addRow(QLabel("Label Use"), self.labelUseCombo)
        self.labelVisiCombo = QComboBox()
        self.labelVisiCombo.addItems(["Yes", "No"])
        self.fLayout.addRow(QLabel("Label Visible"), self.labelVisiCombo)
        self.mainLayout.addLayout(self.fLayout)
        self.labelTypeGroup = QGroupBox("Label Type")
        self.labelTypeLayout = QHBoxLayout()
        self.normalType = QRadioButton(lbl.symbolLabel.labelTypes[0])
        self.normalType.setChecked(True)
        self.NLPType = QRadioButton(lbl.symbolLabel.labelTypes[1])
        self.pyLType = QRadioButton(lbl.symbolLabel.labelTypes[2])
        self.labelTypeLayout.addWidget(self.normalType)
        self.labelTypeLayout.addWidget(self.NLPType)
        self.labelTypeLayout.addWidget(self.pyLType)
        self.labelTypeGroup.setLayout(self.labelTypeLayout)
        self.mainLayout.addWidget(self.labelTypeGroup)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class labelPropertyDialog(createSymbolLabelDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Label Properties")
        self.labelXLine = edf.shortLineEdit()
        self.labelXLine.setToolTip("X Coordinate")
        self.fLayout.addRow(QLabel("X:"), self.labelXLine)
        self.labelYLine = edf.shortLineEdit()
        self.labelYLine.setToolTip("Y Coordinate")
        self.fLayout.addRow(QLabel("Y:"), self.labelYLine)


class symbolLabelsDialogue(QDialog):
    """
    Dialog for changing symbol labels and attributes. Symbol properties... menu item.
    """

    def __init__(self, parent, items: list, attributes: list):
        super().__init__(parent)
        self.parent = parent
        self.items = items
        self.attributes = attributes
        self.setWindowTitle("Cellview Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        tabWidget = QTabWidget(self)
        tabWidget.addTab(self._buildLabelsTable(), "Definition")
        tabWidget.addTab(self._buildAttrsTable(), "Symbol Attributes")
        tabWidget.addTab(self._buildParamsTable(), "Parameters")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(tabWidget)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.resize(800, 480)

    _PARAMDEF_COL = {"name": 1, "type": 2, "default": 3, "min": 4,
                     "max": 5, "choices": 6, "display": 7, "parse": 8}

    def _buildLabelsTable(self):
        """Definition tab: one row per symbol label."""
        self.labelsTable = QTableWidget(self)
        self.labelsTable.setColumnCount(6)
        self.labelsTable.setHorizontalHeaderLabels(
            ["Definition", "Height", "Alignment", "Orientation", "Use",
             "Type"])
        self.labelItemList = [item for item in self.items
                              if type(item) == lbl.symbolLabel]
        self.labelsTable.setRowCount(len(self.labelItemList))
        for row, item in enumerate(self.labelItemList):
            definition = QTableWidgetItem(item.labelDefinition)
            definition.setFlags(
                definition.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.labelsTable.setItem(row, 0, definition)
            self.labelsTable.setItem(
                row, 1, QTableWidgetItem(str(item.labelHeight)))
            for col, choices, current in (
                    (2, lbl.symbolLabel.labelAlignments, item.labelAlign),
                    (3, lbl.symbolLabel.labelOrients, item.labelOrient),
                    (4, lbl.symbolLabel.labelUses, item.labelUse),
                    (5, lbl.symbolLabel.labelTypes, item.labelType)):
                combo = QComboBox()
                combo.addItems(choices)
                combo.setCurrentText(current)
                self.labelsTable.setCellWidget(row, col, combo)
        labelsHeader = self.labelsTable.horizontalHeader()
        labelsHeader.setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            labelsHeader.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        return self.labelsTable

    def labelValues(self) -> list:
        """Edited (height, align, orient, use, type) per ``labelItemList``."""
        values = []
        for row in range(len(self.labelItemList)):
            heightItem = self.labelsTable.item(row, 1)
            values.append(
                (heightItem.text() if heightItem else "",
                 self.labelsTable.cellWidget(row, 2).currentText(),
                 self.labelsTable.cellWidget(row, 3).currentText(),
                 self.labelsTable.cellWidget(row, 4).currentText(),
                 self.labelsTable.cellWidget(row, 5).currentText()))
        return values

    def _buildAttrsTable(self):
        """Symbol Attributes tab: free-form name/definition pairs.

        The reserved ``paramDefs`` attribute is edited structurally on the
        Parameters tab, not as raw JSON here."""
        self.attrsTable = QTableWidget(self)
        self.attrsTable.setColumnCount(2)
        self.attrsTable.setHorizontalHeaderLabels(
            ["Attribute Name", "Definition"])
        attrs = [item for item in self.attributes
                 if item.name != prm.PARAMDEFS_ATTR]
        self.attrsTable.setRowCount(len(attrs) + 1)
        for row, item in enumerate(attrs):
            self.attrsTable.setItem(row, 0, QTableWidgetItem(item.name))
            self.attrsTable.setItem(row, 1, QTableWidgetItem(item.definition))
        self.attrsTable.cellChanged.connect(self._attrCellChanged)
        attrsHeader = self.attrsTable.horizontalHeader()
        attrsHeader.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        attrsHeader.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        return self.attrsTable

    def _attrCellChanged(self, row: int, column: int):
        """Auto-append a row when a cell in the last row is filled."""
        if row == self.attrsTable.rowCount() - 1:
            item = self.attrsTable.item(row, column)
            if item is not None and item.text().strip():
                self.attrsTable.insertRow(row + 1)

    def symbolAttributes(self) -> list:
        """(name, definition) pairs from the attributes table."""
        attrs = []
        for row in range(self.attrsTable.rowCount()):
            nameItem = self.attrsTable.item(row, 0)
            name = nameItem.text().strip() if nameItem else ""
            if name:
                defItem = self.attrsTable.item(row, 1)
                attrs.append((name, defItem.text() if defItem else ""))
        return attrs

    def _buildParamsTable(self):
        """Parameters tab: typed parameter definitions (CDF-lite) editing
        the reserved ``paramDefs`` attribute structurally."""
        self.paramsTable = QTableWidget(self)
        self.paramsTable.setColumnCount(9)
        self.paramsTable.setHorizontalHeaderLabels(
            ["Del.", "Name", "Type", "Default", "Min", "Max", "Choices",
             "Display", "Parse"])
        self._populateParamsTable()
        return self.paramsTable

    def _populateParamsTable(self):
        """Fill the parameters table from the ``paramDefs`` attribute."""
        paramDefsAttr = next(
            (item for item in self.attributes
             if item.name == prm.PARAMDEFS_ATTR), None)
        self._paramDefs, errors = prm.paramDefsFromJson(
            paramDefsAttr.definition if paramDefsAttr else "")
        for err in errors:
            self.paramsTable.setToolTip(f"paramDefs warnings: {'; '.join(errors)}")
        self.paramsTable.setRowCount(len(self._paramDefs) + 1)
        for row, pdef in enumerate(self._paramDefs):
            self._setParamRow(row, pdef)
        self._setParamRow(len(self._paramDefs), None)
        self.paramsTable.cellChanged.connect(self._paramCellChanged)

    def _setParamRow(self, row: int, pdef):
        deleteBox = QCheckBox()
        deleteBox.stateChanged.connect(
            lambda _state, r=row: self.paramsTable.removeRow(r))
        self.paramsTable.setCellWidget(row, 0, deleteBox)
        self.paramsTable.setItem(
            row, 1, QTableWidgetItem(pdef.name if pdef else ""))
        typeCombo = QComboBox()
        typeCombo.addItems(list(prm.PARAM_TYPES))
        typeCombo.setCurrentText(pdef.type if pdef else "string")
        self.paramsTable.setCellWidget(row, 2, typeCombo)
        for col, text in ((3, pdef.default if pdef else ""),
                          (4, pdef.minimum if pdef else ""),
                          (5, pdef.maximum if pdef else ""),
                          (6, ", ".join(pdef.choices) if pdef else "")):
            self.paramsTable.setItem(row, col, QTableWidgetItem(text))
        for col, checked in ((7, pdef.display if pdef else True),
                             (8, pdef.parse if pdef else True)):
            box = QCheckBox()
            box.setChecked(checked)
            self.paramsTable.setCellWidget(row, col, box)

    def _paramCellChanged(self, row: int, column: int):
        """Auto-append a row when the last row's name field is filled."""
        if row == self.paramsTable.rowCount() - 1 and column == 1:
            item = self.paramsTable.item(row, column)
            if item is not None and item.text().strip():
                self.paramsTable.insertRow(row + 1)
                self._setParamRow(row + 1, None)

    def paramDefs(self) -> list:
        """ParamDefs edited in the parameters table."""
        defs = []
        for row in range(self.paramsTable.rowCount()):
            nameItem = self.paramsTable.item(row, 1)
            name = nameItem.text().strip() if nameItem else ""
            if not name:
                continue
            typeCombo = self.paramsTable.cellWidget(row, 2)
            cell = lambda c: (self.paramsTable.item(row, c).text().strip()
                              if self.paramsTable.item(row, c) else "")
            defs.append(prm.ParamDef(
                name=name,
                type=typeCombo.currentText() if typeCombo else "string",
                default=cell(3),
                minimum=cell(4),
                maximum=cell(5),
                choices=tuple(
                    c.strip() for c in cell(6).split(",") if c.strip()),
                display=(self.paramsTable.cellWidget(row, 7).isChecked()
                         if self.paramsTable.cellWidget(row, 7) else True),
                parse=(self.paramsTable.cellWidget(row, 8).isChecked()
                       if self.paramsTable.cellWidget(row, 8) else True)))
        return defs


class instanceProperties(QDialog):
    def __init__(self, parent, availableViews=None):
        # assert isinstance(instance, shp.symbolShape)
        super().__init__(parent)
        self.parent = parent
        self.availableViews = availableViews if availableViews else []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Instance Properties")
        tabWidget = QTabWidget()
        mainLayout = QVBoxLayout()
        QBtn = (QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Apply
                | QDialogButtonBox.StandardButton.Cancel)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.applyButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        formLayout = QFormLayout()
        self.libNameEdit = edf.longLineEdit()
        self.libNameEdit.setReadOnly(True)
        self.libNameEdit.setToolTip("Library Name (Read Only)")
        formLayout.addRow(edf.boldLabel("Library Name", self), self.libNameEdit)
        self.cellNameEdit = edf.longLineEdit()
        self.cellNameEdit.setReadOnly(True)
        self.cellNameEdit.setToolTip("Cell Name (Read Only)")
        formLayout.addRow(edf.boldLabel("Cell Name", self), self.cellNameEdit)
        
        # Changed from read-only line edit to editable combo box
        self.viewNameEdit = QComboBox()
        self.viewNameEdit.setEditable(True)
        if self.availableViews:
            self.viewNameEdit.addItems(self.availableViews)
        self.viewNameEdit.setToolTip("Select or enter the view name")
        formLayout.addRow(edf.boldLabel("View Name", self), self.viewNameEdit)
        
        self.instNameEdit = edf.longLineEdit()
        self.instNameEdit.setToolTip("Instance Name")
        formLayout.addRow(edf.boldLabel("Instance Name", self), self.instNameEdit)
        self.xLocationEdit = edf.shortLineEdit()
        formLayout.addRow(edf.boldLabel("x location", self), self.xLocationEdit)
        self.yLocationEdit = edf.shortLineEdit()
        formLayout.addRow(edf.boldLabel("y location", self), self.yLocationEdit)
        self.angleEdit = edf.longLineEdit()

        formLayout.addRow(edf.boldLabel("Angle", self), self.angleEdit)
        self.netSetEdit = edf.longLineEdit()
        self.netSetEdit.setPlaceholderText("name=net,name=net")
        self.netSetEdit.setToolTip(
            "Inherited-connection overrides (netSet): binds the "
            "subcircuit's net-expression names to local nets, "
            "e.g. vdd=vdd!,avss=gnd!")
        formLayout.addRow(edf.boldLabel("Net Set", self), self.netSetEdit)
        formLayout.setVerticalSpacing(10)
        mainLayout.addLayout(formLayout)
        propertiesGroup = QGroupBox()
        self.instanceLabelsLayout = QGridLayout()
        self.instanceLabelsLayout.setColumnMinimumWidth(0, 100)
        self.instanceLabelsLayout.setColumnMinimumWidth(1, 200)
        self.instanceLabelsLayout.setColumnMinimumWidth(2, 100)
        self.instanceLabelsLayout.setColumnStretch(0, 0)
        self.instanceLabelsLayout.setColumnStretch(1, 1)
        self.instanceLabelsLayout.setColumnStretch(2, 0)
        propertiesGroup.setLayout(self.instanceLabelsLayout)
        tabWidget.addTab(propertiesGroup, "Instance Properties")
        attributesGroup = QGroupBox()
        self.instanceAttributesLayout = QGridLayout()
        self.instanceAttributesLayout.setColumnMinimumWidth(0, 100)
        self.instanceAttributesLayout.setColumnMinimumWidth(1, 200)
        self.instanceAttributesLayout.setColumnStretch(0, 0)
        self.instanceAttributesLayout.setColumnStretch(1, 1)
        attributesGroup.setLayout(self.instanceAttributesLayout)
        tabWidget.addTab(attributesGroup, "Instance Attributes")
        mainLayout.addWidget(tabWidget)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


class schematicCheckRulesDialogue(QDialog):
    """Checkbox dialogue selecting which schematic check rules are applied.
    All rules passed in ``enabledIds`` start checked (all rules on by
    default)."""

    def __init__(self, parent, rules, enabledIds):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Schematic Check Rules")
        self.setMinimumWidth(380)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        mainLayout = QVBoxLayout()
        rulesGroup = QGroupBox("Applied Rules")
        rulesLayout = QVBoxLayout()
        self.ruleCheckBoxes = {}
        for rule in rules:
            checkBox = QCheckBox(
                f"{rule.name}  [{rule.severity.name.title()}]")
            checkBox.setToolTip(rule.description)
            checkBox.setChecked(rule.ruleId in enabledIds)
            rulesLayout.addWidget(checkBox)
            self.ruleCheckBoxes[rule.ruleId] = checkBox
        rulesGroup.setLayout(rulesLayout)
        mainLayout.addWidget(rulesGroup)

        selectLayout = QHBoxLayout()
        selectAllButton = QPushButton("Select All", self)
        selectAllButton.clicked.connect(lambda: self._setAllChecked(True))
        selectNoneButton = QPushButton("Select None", self)
        selectNoneButton.clicked.connect(lambda: self._setAllChecked(False))
        selectLayout.addWidget(selectAllButton)
        selectLayout.addWidget(selectNoneButton)
        selectLayout.addStretch(1)
        mainLayout.addLayout(selectLayout)

        buttonBox = QDialogButtonBox(QBtn)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def _setAllChecked(self, checked: bool):
        for checkBox in self.ruleCheckBoxes.values():
            checkBox.setChecked(checked)

    def selectedRuleIds(self) -> set:
        return {ruleId for ruleId, checkBox in self.ruleCheckBoxes.items()
                if checkBox.isChecked()}


class netNameDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Add Net Name")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        buttonBox = QDialogButtonBox(QBtn)
        mainLayout = QVBoxLayout()
        formLayout = QFormLayout()
        self.netNameEdit = edf.longLineEdit()
        self.netNameEdit.setToolTip("Enter net name")
        formLayout.addRow(edf.boldLabel("Net Name", self), self.netNameEdit)
        mainLayout.addLayout(formLayout)
        mainLayout.addSpacing(40)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)


class netProperties(QDialog):
    def __init__(self, parent):
        # assert isinstance(instance, shp.symbolShape)
        super().__init__(parent)
        self.parent = parent
        self.net = net
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Net Properties")
        mainLayout = QVBoxLayout()
        okButton = QDialogButtonBox.Ok
        cancelButton = QDialogButtonBox.Cancel
        QBtn = okButton | cancelButton
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.button(QDialogButtonBox.Ok).setDefault(True)
        netPointsBox = QGroupBox("Net Points")
        netPointsLayout = QFormLayout()
        netPointsBox.setLayout(netPointsLayout)
        self.netStartPointEditX = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("Net Start X:"), self.netStartPointEditX)
        self.netStartPointEditY = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("Net Start Y:"), self.netStartPointEditY)
        self.netEndPointEditX = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("End Point X:"), self.netEndPointEditX)
        self.netEndPointEditY = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("End Point X:"), self.netEndPointEditY)

        netWidthGroupBox = QGroupBox('Net Width')
        netWidthLayout = QHBoxLayout()
        narrowNetButton = QRadioButton('Narrow')
        wideNetButton = QRadioButton('Wide')
        netWidthLayout.addWidget(narrowNetButton)
        netWidthLayout.addWidget(wideNetButton)
        self.widthButtonGroup = QButtonGroup(self)
        self.widthButtonGroup.addButton(narrowNetButton)
        self.widthButtonGroup.addButton(wideNetButton)
        self.widthButtonGroup.setId(narrowNetButton, 0)
        self.widthButtonGroup.setId(wideNetButton, 1)
        netWidthGroupBox.setLayout(netWidthLayout)
        mainLayout.addWidget(netWidthGroupBox)
        formBox = QGroupBox("Net Properties")
        formLayout = QFormLayout()
        self.netNameEdit = edf.longLineEdit()
        formLayout.addRow(edf.boldLabel("Net Name", self), self.netNameEdit)
        self.netExprEdit = edf.longLineEdit()
        self.netExprEdit.setPlaceholderText("[@name] or [@name:default]")
        self.netExprEdit.setToolTip(
            "Net expression for inherited connections, e.g. [@vdd:vdd!]")
        formLayout.addRow(edf.boldLabel("Net Expression", self),
                          self.netExprEdit)
        formBox.setLayout(formLayout)
        mainLayout.addWidget(formBox)
        mainLayout.addSpacing(20)
        mainLayout.addWidget(netPointsBox)
        mainLayout.addSpacing(40)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.show()


class createSchematicPinDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Create Schematic Pin")


class schematicPinPropertiesDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Pin Properties")
        self.xlocationEdit = edf.shortLineEdit()
        self.xlocationEdit.setToolTip("x location of pin")
        self.fLayout.addRow("x location:", self.xlocationEdit)
        self.ylocationEdit = edf.shortLineEdit()
        self.ylocationEdit.setToolTip("y location of pin")
        self.fLayout.addRow("y location:", self.ylocationEdit)
        self.angleEdit = edf.shortLineEdit()
        self.angleEdit.setToolTip("angle of pin")
        self.fLayout.addRow("angle:", self.angleEdit)


class symbolNameDialog(QDialog):
    def __init__(self, cellPath: pathlib.Path, cellName: str, parent):
        super().__init__(parent)
        self.cellPath = cellPath
        self.cellName = cellName
        self.symbolViewNames = [
            view.stem for view in cellPath.iterdir() if "symbol" in view.stem
        ]
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Create a symbol?")
        self.mainLayout = QVBoxLayout()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        formLayout = QFormLayout()
        formLayout.addRow(
            edf.boldLabel("Library Name"), QLabel(self.cellPath.parent.stem)
        )
        formLayout.addRow(edf.boldLabel("Cell Name"), QLabel(self.cellPath.stem))
        self.symbolViewsCB = QComboBox()
        self.symbolViewsCB.addItems(self.symbolViewNames)
        self.symbolViewsCB.setEditable(True)
        formLayout.addRow(edf.boldLabel("Symbol View Name:"), self.symbolViewsCB)
        self.mainLayout.addLayout(formLayout)
        self.mainLayout.addSpacing(40)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


class symbolCreateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Create Symbol")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.mainLayout = QVBoxLayout()

        self.fLayout = QFormLayout()
        self.topPinsEdit = edf.longLineEdit()
        self.topPinsEdit.setToolTip("Enter top pins")
        self.fLayout.addRow(edf.boldLabel("Top Pins:"), self.topPinsEdit)
        self.leftPinsEdit = edf.longLineEdit()
        self.leftPinsEdit.setToolTip("Enter left pins")
        self.fLayout.addRow(edf.boldLabel("Left Pins:"), self.leftPinsEdit)
        self.bottomPinsEdit = edf.longLineEdit()
        self.bottomPinsEdit.setToolTip("Enter bottom pins")
        self.fLayout.addRow(edf.boldLabel("Bottom Pins:"), self.bottomPinsEdit)
        self.rightPinsEdit = edf.longLineEdit()
        self.rightPinsEdit.setToolTip("Enter right pins")
        self.fLayout.addRow(edf.boldLabel("Right Pins:"), self.rightPinsEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.mainLayout.addSpacing(20)
        self.geomLayout = QFormLayout()
        self.stubLengthEdit = QLineEdit()
        self.stubLengthEdit.setText("60")
        self.stubLengthEdit.setToolTip("Enter stub lengths")
        self.geomLayout.addRow(edf.boldLabel("Stub Length:"), self.stubLengthEdit)
        self.pinDistanceEdit = QLineEdit()
        self.pinDistanceEdit.setText("80")
        self.pinDistanceEdit.setToolTip("Enter pin spacing")
        self.geomLayout.addRow(edf.boldLabel("Pin spacing:"), self.pinDistanceEdit)
        self.mainLayout.addLayout(self.geomLayout)
        self.mainLayout.addSpacing(40)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class noteTextEdit(QDialog):
    """
    Set text properties.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Edit Text")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        mainLayout = QVBoxLayout()
        self.plainTextEdit = QTextEdit()
        mainLayout.addWidget(self.plainTextEdit)
        fontFamilies = QFontDatabase.families(QFontDatabase.Latin)
        fixedFamilies = [
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        ]
        formLayout = QFormLayout()
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        formLayout.addRow(edf.boldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        formLayout.addRow(edf.boldLabel("Font Style"), self.fontStyleCB)
        self.fontsizeCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.fontsizeCB.addItems(self.fontSizes)
        formLayout.addRow(edf.boldLabel("Font Size"), self.fontsizeCB)
        self.textAlignmCB = QComboBox()
        self.textAlignmCB.addItems(shp.text.textAlignments)
        formLayout.addRow(edf.boldLabel("Text Alignment"), self.textAlignmCB)
        self.textOrientCB = QComboBox()
        self.textOrientCB.addItems(shp.text.textOrients)
        formLayout.addRow(edf.boldLabel("Text Orientation"), self.textOrientCB)
        mainLayout.addLayout(formLayout)
        mainLayout.addSpacing(40)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def familyFontStyles(self, s):
        self.fontStyleCB.clear()
        self.fontStyles = QFontDatabase.styles(self.familyCB.currentText())
        self.fontStyleCB.addItems(self.fontStyles)

    def styleFontSizes(self, s):
        self.fontsizeCB.clear()
        selectedFamily = self.familyCB.currentText()
        selectedStyle = self.fontStyleCB.currentText()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(selectedFamily, selectedStyle)
        ]
        self.fontsizeCB.addItems(self.fontSizes)


class displayConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Display Options")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.vLayout = QVBoxLayout()
        gridValueGroup = QGroupBox("Grid Values")
        self.fLayout = QFormLayout()
        gridValueGroup.setLayout(self.fLayout)
        self.majorGridEntry = QLineEdit()
        self.majorGridEntry.setToolTip(
            "Enter Dot or Line Grid Spacing Value as a multiple of scene grid"
        )
        self.fLayout.addRow("GridSpacing:", self.majorGridEntry)
        self.snapGridEdit = QLineEdit()
        self.snapGridEdit.setToolTip(
            "Enter the Snap Grid Value as a multiple of scene grid"
        )
        self.fLayout.addRow("Snap Distance", self.snapGridEdit)
        self.snapConnectEdit = QLineEdit()
        self.snapConnectEdit.setToolTip(
            "Enter the Snap Connect Distance for wire/pin endpoint snapping"
        )
        self.fLayout.addRow("Snap Connect Distance:", self.snapConnectEdit)

        gridTypeGroup = QGroupBox("Grid Type")
        gridTypeLayout = QHBoxLayout()
        self.dotType = QRadioButton("Dot Grid")
        self.dotType.setChecked(True)
        self.lineType = QRadioButton("Line Grid")
        self.noType = QRadioButton("No Grid")
        gridTypeLayout.addWidget(self.dotType)
        gridTypeLayout.addWidget(self.lineType)
        gridTypeLayout.addWidget(self.noType)
        gridTypeGroup.setLayout(gridTypeLayout)

        self.vLayout.addWidget(gridValueGroup)
        self.vLayout.addWidget(gridTypeGroup)
        self.vLayout.addStretch(1)

        self.vLayout.addWidget(self.buttonBox)
        self.setLayout(self.vLayout)



class layoutDisplayConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Layout Display Options")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.vLayout = QVBoxLayout()
        gridValueGroup = QGroupBox("Grid Values")
        self.fLayout = QFormLayout()
        gridValueGroup.setLayout(self.fLayout)
        self.dbuEntry = edf.shortLineEdit()
        self.dbuEntry.setToolTip("Number of points per um")
        self.dbuEntry.setReadOnly(True)
        self.fLayout.addRow("Process Points per um:", self.dbuEntry)
        self.majorGridEntry = QLineEdit()
        self.majorGridEntry.setToolTip(
            "Enter Dot or Line Grid Spacing Value in um"
        )
        self.fLayout.addRow("GridSpacing (um):", self.majorGridEntry)
        self.snapGridEdit = QLineEdit()
        self.snapGridEdit.setToolTip(
            "Enter the Snap Grid Value in um"
        )
        self.fLayout.addRow("Snap Distance (um):", self.snapGridEdit)
        self.snapConnectEdit = QLineEdit()
        self.snapConnectEdit.setToolTip(
            "Enter the Snap Connect Distance in um for wire/pin endpoint snapping"
        )
        self.fLayout.addRow("Snap Connect Distance (um):", self.snapConnectEdit)
        self.lodThresholdEdit = edf.shortLineEdit()
        self.lodThresholdEdit.setToolTip(
            "Level-of-detail threshold for instance simplification when zooming out.\n"
            "Lower values delay simplification; higher values simplify sooner.\n"
            "Typical range: 0.001 – 0.1  (default 0.02)"
        )
        self.fLayout.addRow("Instance LOD Threshold:", self.lodThresholdEdit)
        gridTypeGroup = QGroupBox("Grid Type")
        gridTypeLayout = QHBoxLayout()
        self.dotType = QRadioButton("Dot Grid")
        self.dotType.setChecked(True)
        self.dotType.setToolTip("Display grid as dots")
        self.lineType = QRadioButton("Line Grid")
        self.lineType.setToolTip("Display grid as lines")
        self.noType = QRadioButton("No Grid")
        self.noType.setToolTip("Hide grid")
        gridTypeLayout.addWidget(self.dotType)
        gridTypeLayout.addWidget(self.lineType)
        gridTypeLayout.addWidget(self.noType)
        gridTypeGroup.setLayout(gridTypeLayout)

        hierGroup = QGroupBox("Hierarchy")
        formLayout = QFormLayout(hierGroup)
        self.hierLevelSpin = QSpinBox()
        self.hierLevelSpin.setRange(0, 20)
        self.hierLevelSpin.setToolTip(
            "Instances deeper than this level are drawn as labelled "
            "bounding boxes. 0 = top-level instances only; 20 = all levels."
        )
        formLayout.addRow("Display Level:", self.hierLevelSpin)

        self.vLayout.addWidget(gridValueGroup)
        self.vLayout.addWidget(gridTypeGroup)
        self.vLayout.addWidget(hierGroup)
        self.vLayout.addStretch(1)

        self.vLayout.addWidget(self.buttonBox)
        self.setLayout(self.vLayout)




class selectConfigDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Selection Options")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vLayout = QVBoxLayout()
        selectionTypeGroup = QGroupBox("Selection Type")
        selectionTypeLayout = QHBoxLayout()
        self.fullSelection = QRadioButton("Full")
        self.partialSelection = QRadioButton("Partial")
        selectionTypeLayout.addWidget(self.fullSelection)
        selectionTypeLayout.addWidget(self.partialSelection)
        selectionTypeGroup.setLayout(selectionTypeLayout)
        vLayout.addWidget(selectionTypeGroup)
        # snapDistanceGroup = QGroupBox("Snap Distance")
        # snapDistanceLayout = QFormLayout()
        # self.snapDistanceEntry = edf.shortLineEdit()
        # snapDistanceLayout.addRow("Snap Distance", self.snapDistanceEntry)
        # snapDistanceGroup.setLayout(snapDistanceLayout)
        # vLayout.addWidget(snapDistanceGroup)
        vLayout.addStretch(1)
        vLayout.addWidget(self.buttonBox)
        self.setLayout(vLayout)
        self.show()


class moveByDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Move By...")
        self.setMinimumWidth(250)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout = QVBoxLayout()
        coordsGroup = QGroupBox("Move By")
        coordsLayout = QFormLayout()
        self.xEdit = edf.shortLineEdit()
        self.yEdit = edf.shortLineEdit()
        coordsLayout.addRow("Move By in X:", self.xEdit)
        coordsLayout.addRow("Move By in Y:", self.yEdit)
        coordsGroup.setLayout(coordsLayout)
        self.mainLayout.addWidget(coordsGroup)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


class copyOptionsDialogue(QDialog):
    """Modeless copy-options form (Virtuoso F3 convention): place the
    armed copy as a rows×columns array with Delta X/Y pitch.

    Apply/Ok write the values into ``scene.copyOptions`` and call
    ``scene.rearmClipboardPaste()`` so the floating ghost rebuilds live.
    Delta fields accept quantiphy suffixes ("2u", "0.5"); layout values
    are entered in user units (um) and converted through ``fabproc.dbu``.
    An empty/zero delta means "use the copied fragment's bbox size".
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.editor = parent
        self.scene = parent.centralW.scene
        self.setWindowTitle("Copy Options")
        self.setMinimumWidth(280)
        mainLayout = QVBoxLayout()
        arrayGroup = QGroupBox("Copy Array")
        formLayout = QFormLayout(arrayGroup)
        opts = self.scene.copyOptions
        self.rowsEdit = edf.shortLineEdit(str(opts.rows))
        self.rowsEdit.setValidator(QIntValidator(1, 1000, self))
        formLayout.addRow(edf.boldLabel("Rows:"), self.rowsEdit)
        self.colsEdit = edf.shortLineEdit(str(opts.columns))
        self.colsEdit.setValidator(QIntValidator(1, 1000, self))
        formLayout.addRow(edf.boldLabel("Columns:"), self.colsEdit)
        pitchX, pitchY = self._displayPitch(opts.xOffset, opts.yOffset)
        self.deltaXEdit = edf.shortLineEdit(pitchX)
        self.deltaXEdit.setToolTip(
            "Column pitch; empty or 0 uses the copied selection's width")
        formLayout.addRow(edf.boldLabel("Delta X:"), self.deltaXEdit)
        self.deltaYEdit = edf.shortLineEdit(pitchY)
        self.deltaYEdit.setToolTip(
            "Row pitch; empty or 0 uses the copied selection's height")
        formLayout.addRow(edf.boldLabel("Delta Y:"), self.deltaYEdit)
        mainLayout.addWidget(arrayGroup)
        QBtn = (QDialogButtonBox.StandardButton.Apply
                | QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.Apply).clicked.connect(
            lambda: self._applyOptions(False))
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.Ok).clicked.connect(
            lambda: self._applyOptions(True))
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def _unitScale(self) -> float:
        """Display-units-per-scene-unit for the pitch fields: layout
        edits in user units (um), schematic/symbol in scene units."""
        if self.editor.__class__.__name__ == "layoutEditor" and fabproc:
            return fabproc.dbu
        return 1.0

    def _displayPitch(self, xOffset: float, yOffset: float) -> tuple:
        scale = self._unitScale()
        return f"{xOffset / scale:g}", f"{yOffset / scale:g}"

    def _applyOptions(self, closeDialog: bool):
        from PySide6.QtWidgets import QMessageBox
        try:
            rows = max(1, int(self.rowsEdit.text() or "1"))
            cols = max(1, int(self.colsEdit.text() or "1"))
            scale = self._unitScale()
            dx = float(Quantity(self.deltaXEdit.text() or "0").real) * scale
            dy = float(Quantity(self.deltaYEdit.text() or "0").real) * scale
        except Exception as error:
            QMessageBox.warning(
                self, "Invalid copy options",
                f"Rows/Columns must be positive integers and the deltas "
                f"numeric values.\n{error}")
            return
        opts = self.scene.copyOptions
        opts.rows, opts.columns = rows, cols
        opts.xOffset, opts.yOffset = dx, dy
        self.scene.rearmClipboardPaste()
        if closeDialog:
            self.accept()
