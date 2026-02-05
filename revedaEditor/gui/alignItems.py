#     "Commons Clause" License Condition v1.0
#    #
#     The Software is provided to you by the Licensor under the License, as defined
#     below, subject to the following condition.
#  #
#     Without limiting other conditions in the License, the grant of rights under the
#     License will not include, and the License does not grant to you, the right to
#     Sell the Software.
#  #
#     For purposes of the foregoing, "Sell" means practicing any or all of the rights
#     granted to you under the License to provide to third parties, for a fee or other
#     consideration (including without limitation fees for hosting) a product or service whose value
#     derives, entirely or substantially, from the functionality of the Software. Any
#     license notice or attribution required by the License must also include this
#     Commons Clause License Condition notice.
#  #
#    Add-ons and extensions developed for this software may be distributed
#    under their own separate licenses.
#  #
#     Software: Revolution EDA
#     License: Mozilla Public License 2.0
#     Licensor: Revolution Semiconductor (Registered in the Netherlands)


from typing import TYPE_CHECKING, Union

from PySide6.QtCore import (
    QLineF,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsItem,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
)
from quantiphy.quantiphy import Quantity

import revedaEditor.gui.editFunctions as edf
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.common.shapes import alignLine

process = importPDKModule("process")
if TYPE_CHECKING:
    from revedaEditor.gui.editorWindow import editorWindow


# Assuming layout units are given, this is the conversion factor between


class alignItemsDialogue(QDialog):
    def __init__(self, parentW: "editorWindow"):
        super().__init__(parentW)
        self.editor = parentW
        self.scene = parentW.centralW.scene
        self.alignLine = QLineF()
        self.setWindowTitle("Align Layout items")
        self.setMinimumWidth(300)
        self.setMinimumHeight(400)
        mainLayout = QVBoxLayout()
        alignMethodGroup = QGroupBox("Align Method")
        alignMethodLayout = QHBoxLayout(alignMethodGroup)
        alignMethodGroup.setLayout(alignMethodLayout)
        alignButtonGroup = QButtonGroup(alignMethodGroup)
        self.alignEdgesButton = QRadioButton("Align Edges")
        self.alignEdgesButton.setChecked(True)
        self.alignEdgesButton.pressed.connect(self.edgeAlignmentMessageShow)
        alignButtonGroup.addButton(self.alignEdgesButton)
        self.alignLineButton = QRadioButton("Align To Line")
        self.alignLineButton.pressed.connect(self.lineAlignmentMessageShow)
        alignButtonGroup.addButton(self.alignLineButton)
        alignMethodLayout.addWidget(self.alignEdgesButton)
        alignMethodLayout.addWidget(self.alignLineButton)
        mainLayout.addWidget(alignMethodGroup)
        alignDirectionGroup = QGroupBox("Align Direction")
        alignButtonGroup = QButtonGroup(alignDirectionGroup)
        alignLayout = QHBoxLayout(alignDirectionGroup)
        self.horizontalAlignButton = QRadioButton("Horizontal")
        self.horizontalAlignButton.pressed.connect(self.showHorizonalAlignments)
        alignButtonGroup.addButton(self.horizontalAlignButton)
        self.verticalAlignButton = QRadioButton("Vertical")
        self.verticalAlignButton.pressed.connect(self.showVerticalAlignments)
        alignButtonGroup.addButton(self.verticalAlignButton)
        self.horizontalAlignButton.setChecked(True)
        alignLayout.addWidget(self.horizontalAlignButton)
        alignLayout.addWidget(self.verticalAlignButton)
        alignDirectionGroup.setLayout(alignLayout)
        mainLayout.addWidget(alignDirectionGroup)
        alignOptionsGroup = QGroupBox("Align Options")
        alignOptionsLayout = QFormLayout(alignOptionsGroup)
        alignOptionsGroup.setLayout(alignOptionsLayout)
        self.alignSpacingTextEdit = edf.shortLineEdit()
        alignOptionsLayout.addRow(edf.boldLabel("Spacing:"), self.alignSpacingTextEdit)
        mainLayout.addWidget(alignOptionsGroup)

        self.horizontalAlignGroup = QGroupBox("Horizontal Align Options")
        horizontalAlignLayout = QHBoxLayout(self.horizontalAlignGroup)
        self.horizontalAlignGroup.setLayout(horizontalAlignLayout)
        horizontalButtonGroup = QButtonGroup(self.horizontalAlignGroup)
        self.topHorizontalAlignButton = QRadioButton("Top")
        self.topHorizontalAlignButton.setChecked(True)
        horizontalButtonGroup.addButton(self.topHorizontalAlignButton)
        self.centreHorizontalAlignButton = QRadioButton("Centre")
        horizontalButtonGroup.addButton(self.centreHorizontalAlignButton)
        self.bottomHorizontalAlignButton = QRadioButton("Bottom")
        horizontalButtonGroup.addButton(self.bottomHorizontalAlignButton)
        horizontalAlignLayout.addWidget(self.topHorizontalAlignButton)
        horizontalAlignLayout.addWidget(self.centreHorizontalAlignButton)
        horizontalAlignLayout.addWidget(self.bottomHorizontalAlignButton)
        mainLayout.addWidget(self.horizontalAlignGroup)

        self.verticalAlignGroup = QGroupBox("Vertical Align Options")
        verticalAlignLayout = QHBoxLayout(self.verticalAlignGroup)
        self.verticalAlignGroup.setLayout(verticalAlignLayout)
        verticalButtonGroup = QButtonGroup(self.verticalAlignGroup)
        self.leftVerticalAlignButton = QRadioButton("Left")
        self.leftVerticalAlignButton.setChecked(True)
        verticalButtonGroup.addButton(self.leftVerticalAlignButton)
        self.centerVerticalAlignButton = QRadioButton("Centre")
        verticalButtonGroup.addButton(self.centerVerticalAlignButton)
        self.rightVerticalAlignButton = QRadioButton("Right")
        verticalButtonGroup.addButton(self.rightVerticalAlignButton)
        verticalAlignLayout.addWidget(self.leftVerticalAlignButton)
        verticalAlignLayout.addWidget(self.centerVerticalAlignButton)
        verticalAlignLayout.addWidget(self.rightVerticalAlignButton)
        self.verticalAlignGroup.hide()
        mainLayout.addWidget(self.verticalAlignGroup)

        QBtn = (
                QDialogButtonBox.StandardButton.Apply
                | QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)

        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.editor.messageLine.setText("Select items to be aligned.")
        self.show()

    def edgeAlignmentMessageShow(self):
        self.editor.messageLine.setText("Select items to be aligned.")

    def lineAlignmentMessageShow(self):
        self.editor.messageLine.setText(
            "Select Reference Line and items to be aligned."
        )

    def showHorizonalAlignments(self):
        self.horizontalAlignGroup.show()
        self.verticalAlignGroup.hide()

    def showVerticalAlignments(self):
        self.horizontalAlignGroup.hide()
        self.verticalAlignGroup.show()


def alignItemsEdgeHorizontally(
        selectedItems: list[QGraphicsItem], alignment: str, spacing: Union[float, str]
):
    # if len(selectedItems) < 2:
    #     return
    # Sort items by x position for distribution
    sorted_items = sorted(
        selectedItems, key=lambda item: item.sceneBoundingRect().left()
    )
    match alignment:
        case "top":
            target_y = min(item.sceneBoundingRect().top() for item in selectedItems)
            for item in sorted_items:
                current_top = item.sceneBoundingRect().top()
                item.moveBy(0, target_y - current_top)
        case "center":
            target_y = sum(
                item.sceneBoundingRect().center().y() for item in selectedItems
            ) / len(selectedItems)
            for item in sorted_items:
                current_center = item.sceneBoundingRect().center().y()
                item.moveBy(0, target_y - current_center)
        case "bottom":
            target_y = max(item.sceneBoundingRect().bottom() for item in selectedItems)
            for item in sorted_items:
                current_bottom = item.sceneBoundingRect().bottom()
                item.moveBy(0, target_y - current_bottom)
    # If no spacing value is given, return
    if spacing == "":
        return
    # Distribute with spacing
    current_x = sorted_items[0].sceneBoundingRect().left()
    for item in sorted_items[1:]:
        current_x += sorted_items[
                         sorted_items.index(item) - 1
                         ].sceneBoundingRect().width() + float(spacing)
        item.moveBy(current_x - item.sceneBoundingRect().left(), 0)


def alignItemsEdgeVertically(
        selectedItems: list[QGraphicsItem], alignment: str, spacing: Union[float, str]
):
    # if len(selectedItems) < 2:
    #     return
    # Sort items by x position for distribution
    sorted_items = sorted(
        selectedItems, key=lambda item: item.sceneBoundingRect().left()
    )
    match alignment:
        case "left":
            target_x = min(item.sceneBoundingRect().left() for item in selectedItems)
            for item in sorted_items:
                current_left = item.sceneBoundingRect().left()
                item.moveBy(target_x - current_left, 0)
        case "center":
            target_x = sum(
                item.sceneBoundingRect().center().x() for item in selectedItems
            ) / len(selectedItems)
            for item in sorted_items:
                current_center = item.sceneBoundingRect().center().x()
                item.moveBy(target_x - current_center, 0)
        case "right":
            target_x = max(item.sceneBoundingRect().right() for item in selectedItems)
            for item in sorted_items:
                current_right = item.sceneBoundingRect().bottom()
                item.moveBy(target_x - current_right, 0)

    if spacing == "":
        return
    # Distribute with spacing
    current_y = sorted_items[0].sceneBoundingRect().top()
    for item in sorted_items[1:]:
        current_y += sorted_items[
                         sorted_items.index(item) - 1
                         ].sceneBoundingRect().height() + float(spacing)
        item.moveBy(0, current_y - item.sceneBoundingRect().top())


def alignItemsLineHorizontally(
        selectedItems: list[QGraphicsItem],
        alignment: str,
        spacing: Union[float, str],
        target_y: int,
):
    # Sort items by x position for distribution
    sorted_items = sorted(
        selectedItems, key=lambda item: item.sceneBoundingRect().left()
    )
    match alignment:
        case "top":
            for item in sorted_items:
                current_top = item.sceneBoundingRect().top()
                item.moveBy(0, target_y - current_top)
        case "center":
            for item in sorted_items:
                current_center = item.sceneBoundingRect().center().y()
                item.moveBy(0, target_y - current_center)
        case "bottom":
            for item in sorted_items:
                current_bottom = item.sceneBoundingRect().bottom()
                item.moveBy(0, target_y - current_bottom)
    # If no spacing value is given, return
    if spacing == "":
        return
    # Distribute with spacing
    current_x = sorted_items[0].sceneBoundingRect().left()
    for item in sorted_items[1:]:
        current_x += sorted_items[
                         sorted_items.index(item) - 1
                         ].sceneBoundingRect().width() + float(spacing)
        item.moveBy(current_x - item.sceneBoundingRect().left(), 0)


def alignItemsLineVertically(
        selectedItems: list[QGraphicsItem],
        alignment: str,
        spacing: Union[float, str],
        target_x: int,
):
    # if len(selectedItems) < 2:
    #     return
    # Sort items by x position for distribution
    sorted_items = sorted(
        selectedItems, key=lambda item: item.sceneBoundingRect().left()
    )
    match alignment:
        case "left":
            for item in sorted_items:
                current_left = item.sceneBoundingRect().left()
                item.moveBy(target_x - current_left, 0)
        case "center":
            for item in sorted_items:
                current_center = item.sceneBoundingRect().center().x()
                item.moveBy(target_x - current_center, 0)
        case "right":
            for item in sorted_items:
                current_right = item.sceneBoundingRect().bottom()
                item.moveBy(target_x - current_right, 0)

    if spacing == "":
        return
    # Distribute with spacing
    current_y = sorted_items[0].sceneBoundingRect().top()
    for item in sorted_items[1:]:
        current_y += sorted_items[
                         sorted_items.index(item) - 1
                         ].sceneBoundingRect().height() + float(spacing)
        item.moveBy(0, current_y - item.sceneBoundingRect().top())


def handleAlignAction(dlg: alignItemsDialogue, closeDialog: bool):
    # handles apply or OK key presses in the dialogue

    selectedItems = dlg.scene.selectedItems()
    spacingText = dlg.alignSpacingTextEdit.text().strip()
    if dlg.editor.__class__.__name__ in ("schematicEditor", "symbolEditor"):
        spacing = int(Quantity(dlg.alignSpacingTextEdit.text()).real)
    elif dlg.editor.__class__.__name__ in ("layoutEditor"):
        spacing = (int(Quantity(spacingText).real * process.dbu) if spacingText != ""
                   else "")

    if dlg.alignEdgesButton.isChecked():
        if len(selectedItems) < 2:
            dlg.scene.logger.error("Less than 2 items are selected.")
            return
        if dlg.horizontalAlignButton.isChecked():
            if dlg.topHorizontalAlignButton.isChecked():
                alignItemsEdgeHorizontally(selectedItems, "top", spacing)
            elif dlg.centreHorizontalAlignButton.isChecked():
                alignItemsEdgeHorizontally(selectedItems, "center", spacing)
            elif dlg.bottomHorizontalAlignButton.isChecked():
                alignItemsEdgeHorizontally(selectedItems, "bottom", spacing)
        else:
            if dlg.leftVerticalAlignButton.isChecked():
                alignItemsEdgeVertically(selectedItems, "left", spacing)
            elif dlg.centerVerticalAlignButton.isChecked():
                alignItemsEdgeVertically(selectedItems, "center", spacing)
            elif dlg.rightVerticalAlignButton.isChecked():
                alignItemsEdgeVertically(selectedItems, "right", spacing)
    elif dlg.alignLineButton.isChecked() and not dlg.alignLine.isNull():
        if dlg.horizontalAlignButton.isChecked():
            target_y = int(dlg.alignLine.y1())
            if dlg.topHorizontalAlignButton.isChecked():
                alignItemsLineHorizontally(selectedItems, "top", spacing, target_y)
            elif dlg.centreHorizontalAlignButton.isChecked():
                alignItemsLineHorizontally(selectedItems, "center", spacing, target_y)
            elif dlg.bottomHorizontalAlignButton.isChecked():
                alignItemsLineHorizontally(selectedItems, "bottom", spacing, target_y)
        else:
            target_x = int(dlg.alignLine.x1())
            if dlg.leftVerticalAlignButton.isChecked():
                alignItemsLineVertically(selectedItems, "left", spacing, target_x)
            elif dlg.centerVerticalAlignButton.isChecked():
                alignItemsLineVertically(selectedItems, "center", spacing, target_x)
            elif dlg.rightVerticalAlignButton.isChecked():
                alignItemsLineVertically(selectedItems, "right", spacing, target_x)
        dlg.scene.newAlignLine = None
    if closeDialog:
        dlg.scene.removeItem(dlg.scene.newAlignLine)
        dlg.scene.undoStack.removeLastCommand()
        dlg.accept()


def startLineAlign(scene, dlg: alignItemsDialogue):
    scene.editorWindow.messageLine.setText("Start Drawing Alignment Reference Line.")
    scene.editModes.setMode("alignItems")


def startEdgeAlign(scene, dlg: alignItemsDialogue):
    scene.editorWindow.messageLine.setText("Select Items will be aligned.")
    scene.clearSelection()
    scene.deselectAll()
    scene.editModes.setMode("selectItem")


def alignToLine(newAlignLine: alignLine):
    scene = newAlignLine.scene()
    openAlignDialogues = [
        w
        for w in QApplication.topLevelWidgets()
        if isinstance(w, alignItemsDialogue) and w.isVisible() and w.scene == scene
    ]
    # there must be only one dialogue that meets the criteria.
    if openAlignDialogues:
        openAlignDialogues[0].alignLine = newAlignLine.draftLine
        scene.editModes.setMode("selectItems")
