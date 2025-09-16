#    “Commons Clause” License Condition v1.0
#   #
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
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QToolBar,
    QFileDialog,
    QComboBox,
    QLabel,
    QMessageBox,
)


class stippleView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, parent=None, size: int = 32):
        super().__init__(scene, parent)
        self._size = size
        self._gridStep = 20
        self.setRenderHint(QPainter.Antialiasing)
        # self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setCursor(Qt.ArrowCursor)

        self.setSceneRect(
            0, 0, self._size * self._gridStep, self._size * self._gridStep
        )
        self.drawGrid()

        self.gridSquares = [[None] * self._size for _ in range(self._size)]

    def drawGrid(self):
        pen = QPen(Qt.lightGray)
        for x in range(0, self._size * self._gridStep + 1, self._gridStep):
            self.scene().addLine(x, 0, x, self._size * self._gridStep, pen)
        for y in range(0, self._size * self._gridStep + 1, self._gridStep):
            self.scene().addLine(0, y, self._size * self._gridStep, y, pen)

    def drawDot(self, row, col):
        try:
            square = self.scene().addRect(
                col * self._gridStep,
                row * self._gridStep,
                self._gridStep,
                self._gridStep,
                Qt.NoPen,
                Qt.black,
            )
            self.gridSquares[row][col] = square
        except IndexError:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Error")
            msgBox.setText("Please select a square inside the grid.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            self.scene().removeItem(square)

    def clearDot(self, row, col):
        square = self.gridSquares[row][col]
        if square is not None:
            self.scene().removeItem(square)
            self.gridSquares[row][col] = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            col = int(pos.x() // self._gridStep)
            row = int(pos.y() // self._gridStep)
            try:
                if self.gridSquares[row][col] is not None:
                    self.clearDot(row, col)
                else:
                    self.drawDot(row, col)
            except IndexError:
                pass
        else:
            super().mousePressEvent(event)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size

    @property
    def gridStep(self):
        return self._gridStep


class stippleScene(QGraphicsScene):
    def __init__(self, parent):
        super().__init__(parent)


class stippleEditor(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Stipple Editor")
        self.scene = stippleScene(self)
        self.view = stippleView(self.scene, self, 32)
        self.setCentralWidget(self.view)
        self.sizeCB = QComboBox(self)
        self._createActions()
        self._createMenuBar()
        self._createToolBar()

    def _createActions(self):
        clearIcon = QIcon(":/icons/node-delete.png")
        self.clearAction = QAction(clearIcon, "Clear", self)
        self.clearAction.triggered.connect(self.clearPattern)
        self.clearAction.setToolTip("Clear Pattern")

        exportImageIcon = QIcon(":/icons/image-export.png")
        self.exportImageAction = QAction(exportImageIcon, "Export as Image", self)
        self.exportImageAction.triggered.connect(self.exportPatternAsImage)
        self.exportImageAction.setToolTip("Export Pattern as Image")

        exportTextIcon = QIcon(":/icons/script-text.png")
        self.exportTextAction = QAction(exportTextIcon, "Save Pattern", self)
        self.exportTextAction.triggered.connect(self.exportPatternAsText)
        self.exportTextAction.setToolTip("Save Pattern as Text File")

        loadTextIcon = QIcon(":/icons/property-blue.png")
        self.loadTextAction = QAction(loadTextIcon, "Load...", self)
        self.loadTextAction.triggered.connect(self.loadPatternFromText)
        self.loadTextAction.setToolTip("Load Pattern from File")

        exitIcon = QIcon(":/icons/external.png")
        self.exitAction = QAction(exitIcon, "Close Window", self)
        self.exitAction.setShortcut("Ctrl+Q")

    def _createMenuBar(self):
        self.editorMenuBar = self.menuBar()
        self.editorMenuBar.setNativeMenuBar(False)
        # Returns QMenu object.
        self.menuFile = self.editorMenuBar.addMenu("&File")
        self.menuFile.addAction(self.loadTextAction)
        self.menuFile.addAction(self.exportTextAction)
        self.menuFile.addAction(self.exportImageAction)
        self.menuEdit = self.editorMenuBar.addMenu("&Edit")
        self.menuEdit.addAction(self.clearAction)

    def _createToolBar(self):
        toolbar = QToolBar(self)
        toolbar.addAction(self.clearAction)
        toolbar.addAction(self.exportImageAction)
        toolbar.addAction(self.exportTextAction)
        toolbar.addAction(self.loadTextAction)

        self.sizeCB.addItems(["8x8", "16x16", "32x32"])
        self.sizeCB.setCurrentIndex(2)
        self.sizeCB.currentIndexChanged.connect(self.matrixSizeChanged)
        toolbar.addWidget(QLabel("Stipple Matrix Size: "))
        toolbar.addWidget(self.sizeCB)
        self.addToolBar(toolbar)

    def clearPattern(self):
        self.view.scene().clear()
        self.view.gridSquares = [[None] * self.view.size for _ in range(self.view.size)]
        self.view.drawGrid()

    def exportPatternAsImage(self):
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("png")
        file_dialog.setNameFilter("PNG Image (*.png)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.imageExportToFile(file_path)

    def imageExportToFile(self, file_path):
        image = QImage(
            self.view.size * self.view.gridStep,
            self.view.size * self.view.gridStep,
            QImage.Format_RGB32,
        )
        image.fill(Qt.white)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        for row in self.view.gridSquares:
            for square in row:
                if square is not None:
                    painter.fillRect(square.rect(), Qt.black)
        painter.end()
        image.save(file_path)

    def exportPatternAsText(self):
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("txt")
        file_dialog.setNameFilter("Text File (*.txt)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]

            pattern = []
            for row in range(self.view.size):
                row_data = []
                for col in range(self.view.size):
                    square = self.view.gridSquares[row][col]
                    if square is not None:
                        row_data.append("1")
                    else:
                        row_data.append("0")
                pattern.append(" ".join(row_data))

            with open(file_path, "w") as file:
                file.write("\n".join(pattern))

    def loadPatternFromText(self):
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptOpen)
        file_dialog.setDefaultSuffix("txt")
        file_dialog.setNameFilter("Text File (*.txt)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]

            self.clearPattern()

            self.loadPatternFromFile(file_path)

    def loadPatternFromFile(self, file_path):
        with open(file_path, "r") as file:
            lines = file.readlines()
        index = 2
        match len(lines):
            case 8:
                index = 0
            case 16:
                index = 1
            case 32:
                index = 2
        self.sizeCB.setCurrentIndex(index)
        self.matrixSizeChanged(index)
        for row, line in enumerate(lines):
            row_data = line.strip().split()
            for col, data in enumerate(row_data):
                if data == "1":
                    self.view.drawDot(row, col)

    def matrixSizeChanged(self, index: int):
        self.view.scene().clear()
        match index:
            case 0:
                self.view.size = 8
            case 1:
                self.view.size = 16
            case 2:
                self.view.size = 32
        self.view.gridSquares = [[None] * self.view.size for _ in range(self.view.size)]
        self.view.drawGrid()
