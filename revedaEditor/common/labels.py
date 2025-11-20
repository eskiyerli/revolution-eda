#    “Commons Clause” License Condition v1.0
#
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

from typing import Tuple

from PySide6.QtCore import (
    QPoint,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGraphicsSimpleTextItem, QGraphicsItem
from dotenv import load_dotenv
from quantiphy import Quantity

load_dotenv()
from revedaEditor.backend.pdkPaths import importPDKModule # noqa: E402

schlyr = importPDKModule("schLayers")
symlyr = importPDKModule("symLayers")
cb = importPDKModule("callbacks")


class symbolLabel(QGraphicsSimpleTextItem):
    """
    label: text class definition for symbol drawing.
    labelText is what is shown on the symbol in a schematic
    """

    labelAlignments = ["Left", "Center", "Right"]
    labelOrients = ["R0", "R90", "R180", "R270", "MX", "MX90", "MY", "MY90"]
    labelUses = ["Normal", "Instance", "Pin", "Device", "Annotation"]
    labelTypes = ["Normal", "NLPLabel", "PyLabel"]
    predefinedLabels = [
        "[@libName]",
        "[@cellName]",
        "[@viewName]",
        "[@instName]",
        "[@modelName]",
        "[@elementNum]",
    ]

    def __init__(
        self,
        start: QPoint,
        labelDefinition: str,
        labelType: str,
        labelHeight: int,
        labelAlign: str,
        labelOrient: str,
        labelUse: str,
    ):
        super().__init__("")
        self._start = start  # top left corner
        self._labelDefinition = labelDefinition
        # label definition is what is entered in the symbol editor
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self._labelName = ""  # label Name
        self._labelValue = ""  # label value
        self._labelText = ""  # Displayed label
        self._labelHeight = labelHeight
        self._labelAlign = labelAlign
        self._labelOrient = labelOrient
        self._labelUse = labelUse
        self._labelType = labelType
        self._labelFont = QFont("Arial")
        self._labelFont.setPointSize(int(float(self._labelHeight)))
        self._labelFont.setKerning(False)
        self._labelVisible: bool = False

        self._angle = 0.0  # rotation angle
        self._flipTuple = (1, 1)
        self.setBrush(symlyr.labelBrush)
        self.setPos(self._start)

        match self._labelOrient:
            case "R0":
                self.setRotation(0)
            case "R90":
                self.setRotation(90)
            case "R180":
                self.setRotation(180)
            case "R270":
                self.setRotation(270)
            case _:
                self.setRotation(0)

    def __repr__(self):
        return (
            f"symbolLabel({self._start},{self._labelDefinition},"
            f" {self._labelType}, {self._labelHeight}, {self._labelAlign}, {self._labelOrient},"
            f" {self._labelUse})"
        )

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.scene() and self.scene().editModes.moveItem:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def itemChange(self, change, value):
        if self.scene():
            match change:
                case QGraphicsItem.ItemSelectedHasChanged:
                    if value:
                        self.setBrush(symlyr.selectedLabelBrush)
                        self.setZValue(self.zValue() + 10)
                    else:
                        self.setBrush(symlyr.labelBrush)
                        self.setZValue(self.zValue() - 10)
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        self.scene().itemContextMenu.exec_(event.screenPos())

    @property
    def start(self) -> QPoint:
        return self._start

    @start.setter
    def start(self, start: QPoint):
        self._start = start

    @property
    def labelName(self):
        return self._labelName

    @labelName.setter
    def labelName(self, labelName: str):
        self._labelName = labelName

    @property
    def labelDefinition(self):
        return self._labelDefinition

    @labelDefinition.setter
    def labelDefinition(self, labelDefinition: str):
        if isinstance(labelDefinition, str):
            self._labelDefinition = labelDefinition.strip()
            self.labelDefs()

    @property
    def labelValue(self):
        return self._labelValue

    @labelValue.setter
    def labelValue(self, labelValue):
        self._labelValue = labelValue
        # if label value is set.
        self.labelDefs()

    @property
    def labelText(self):
        return self._labelText

    @labelText.setter
    def labelText(self, labelText):
        self._labelText = labelText
        self.labelDefs()

    @property
    def labelType(self):
        return self._labelType

    @labelType.setter
    def labelType(self, labelType):
        if labelType in self.labelTypes:
            self._labelType = labelType
            self.labelDefs()
        elif self.scene():
            self.scene().logger.error("Invalid label type")

    @property
    def labelAlign(self):
        return self._labelAlign

    @labelAlign.setter
    def labelAlign(self, labelAlignment):
        if labelAlignment in self.labelAlignments:
            self._labelAlign = labelAlignment
        elif self.scene():
            self.scene().logger.error("Invalid label alignment")

    @property
    def labelHeight(self):
        return self._labelHeight

    @labelHeight.setter
    def labelHeight(self, labelHeight):
        self.prepareGeometryChange()
        self._labelHeight = int(float(labelHeight))
        self._labelFont.setPointSize(self._labelHeight)
        self.setFont(self._labelFont)

    @property
    def labelOrient(self):
        return self._labelOrient

    @labelOrient.setter
    def labelOrient(self, labelOrient):
        if labelOrient in self.labelOrients:
            self._labelOrient = labelOrient
        else:
            self.scene().logger.error("Invalid label orientation")

    @property
    def labelUse(self):
        return self._labelUse

    @labelUse.setter
    def labelUse(self, labelUse):
        if labelUse in self.labelUses:
            self._labelUse = labelUse
        elif self.scene():
            self.scene().logger.error("Invalid label use")

    @property
    def labelFont(self):
        return self._labelFont

    @labelFont.setter
    def labelFont(self, labelFont: QFont):
        self._labelFont = labelFont

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        self.prepareGeometryChange()
        self.setRotation(value)

    @property
    def labelVisible(self) -> bool:
        return self._labelVisible

    @labelVisible.setter
    def labelVisible(self, value: bool):
        assert isinstance(value, bool)
        if value:
            self.setOpacity(1)
            self._labelVisible = True
        else:
            self.setOpacity(0.001)
            self._labelVisible = False

    @property
    def flipTuple(self):
        return self._flipTuple

    @flipTuple.setter
    def flipTuple(self, flipState: Tuple[int, int]):
        self.prepareGeometryChange()
        # Get the current transformation
        transform = self.transform()

        # Apply the scaling
        transform.scale(*flipState)

        # Set the new transformation
        self.setTransform(transform)
        self._flipTuple = (transform.m11(), transform.m22())

    def labelDefs(self):
        """
        This method creates label name, value, and text from a label definition.
        It should be called when a label is defined or redefined.
        """
        self.prepareGeometryChange()

        if self._labelType == symbolLabel.labelTypes[0]:  # normal label
            # Set label name, value, and text to label definition
            self._labelName = f"@{self._labelDefinition}"
            self._labelValue = self._labelDefinition
            self._labelText = self._labelDefinition
        elif self._labelType == symbolLabel.labelTypes[1]:  # NLPLabel
            (self._labelName, self._labelText, self._labelValue) = self.createNLPLabel(self._labelDefinition, self._labelValue)
        elif self._labelType == symbolLabel.labelTypes[2]:  # pyLabel
            self.createPyLabel()
        self.setText(self._labelText)


    def createNLPLabel(self, labelDefinition: str, labelValue: str = "") -> Tuple[str, str, str]:
        """
        Parse NLP label definition and return (labelName, labelText, labelValue).

        Args:
            labelDefinition: Label definition string in format [@name:format:default]
            labelValue: Current label value

        Returns:
            Tuple of (labelName, labelText, labelValue)
        """
        try:
            # Validate input format
            if not labelDefinition.strip().startswith("[@"):
                return ("", "", "")

            # Extract expression from brackets
            end_index = labelDefinition.find("]")
            if end_index == -1:
                return ("", "", "")

            expression = labelDefinition[1:end_index]
            parts = expression.split(":")
            labelName = parts[0].strip()

            # Symbol editor case
            if self.parentItem() is None:
                return (labelName, labelDefinition, labelValue)

            # Predefined labels case
            if labelDefinition in symbolLabel.predefinedLabels:
                return self._createPredefinedLabels(labelDefinition)

            # Handle different part counts
            if len(parts) == 1:
                return (labelName, labelName, labelValue)

            # Extract format string and default value
            formatString = parts[1].strip() if len(parts) > 1 else labelName
            defaultValue = self._extractDefaultValue(parts[2].strip()) if len(parts) > 2 else ""

            # Use default value if no current value
            finalValue = labelValue or defaultValue

            # Generate label text
            labelText = formatString.replace("%", finalValue) if "%" in formatString else formatString

            return (labelName, labelText, finalValue)

        except Exception as e:
            if self.scene():
                self.scene().logger.error(f"Error parsing label definition: {labelDefinition}, {e}")
            return ("", "", "")

    def _extractDefaultValue(self, defaultString: str) -> str:
        """Extract default value from default string, handling 'key=value' format."""
        if "=" in defaultString:
            return defaultString.split("=")[1].strip()
        return defaultString

    def _createPredefinedLabels(self, labelDefinition: str) -> Tuple[str, str, str]:
        labelName = labelDefinition[1:-1]
        labelValue = ""

        match labelName:
            case "@cellName":
                # Set label name to "cellName" and value and text to parent item's cell name
                labelValue = self.parentItem().cellName
            case "@instName":
                # Set label name to "instName" and value and text to parent item's counter with prefix "I"
                labelValue = getattr(
                    self.parentItem(), "instanceName", f"I{self.parentItem().counter}"
                )

            case "@libName":
                # Set label name to "libName" and value and text to parent item's library name
                labelValue = self.parentItem().libraryName

            case "@viewName":
                # Set label name to "viewName" and value and text to parent item's view name
                labelValue = self.parentItem().viewName

            case "@modelName":
                # Set label name to "modelName" and value and text to parent item's "modelName" attribute
                labelValue = self.parentItem().symattrs.get("modelName", "")

            case "@elementNum":
                # Set label name to "elementNum" and value and text to parent item's counter
                labelValue = f"{self.parentItem().counter}"
        return labelName, labelValue, labelValue

    def createPyLabel(self):
        """
        Create a PyLabel using the label definition and parent item information.
        """
        try:
            labelName, labelFunction = map(str.strip, self._labelDefinition.split("="))
            self._labelName = f"@{labelName}"
            self._labelValue = "?"
            parentItem = self.parentItem()

            if parentItem and hasattr(parentItem, "cellName"):
                callbackClass = getattr(cb, parentItem.cellName)
                callbackObj = callbackClass(parentItem.labels)
                if hasattr(callbackObj, labelFunction):
                    self._labelValue =  Quantity(getattr(callbackObj, labelFunction)()).render(prec=3)

            self._labelText = f"{labelName}={self._labelValue}"


        except Exception as e:
            if self.scene():
                self.scene().logger.error(f"PyLabel Error: {e}")
