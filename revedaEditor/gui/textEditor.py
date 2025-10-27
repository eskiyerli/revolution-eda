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
import pathlib
import sys

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QFileDialog, QToolBar,
                               QFontDialog, QInputDialog, QMessageBox, QLabel, )
from PySide6.QtGui import (QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QAction,
                           QIcon, )

from PySide6.QtCore import (Signal, )
import re
import revedaEditor.resources.resources
import revedaEditor.backend.dataDefinitions as ddef
from pathlib import Path


class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []
        self.commentFormat = QTextCharFormat()
        self.commentFormat.setForeground(QColor("#007F00"))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)
        self.highlightComments(text)

    def highlightComments(self, text):
        pass


class JsonHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        # String format (green)
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#009900"))
        self.highlightingRules.append((r'"(?:\\.|[^"\\])*"', stringFormat))

        # Number format (blue)
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#0000FF"))
        self.highlightingRules.append(
            (r'\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', numberFormat))

        # Boolean format (purple)
        booleanFormat = QTextCharFormat()
        booleanFormat.setForeground(QColor("#990099"))
        self.highlightingRules.append((r'\b(true|false)\b', booleanFormat))

        # Null format (red)
        nullFormat = QTextCharFormat()
        nullFormat.setForeground(QColor("#FF0000"))
        self.highlightingRules.append((r'\bnull\b', nullFormat))

        # Object key format (brown)
        keyFormat = QTextCharFormat()
        keyFormat.setForeground(QColor("#8B4513"))
        keyFormat.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r'"([^"\\]|\\.)*"\s*:', keyFormat))

        # Braces and brackets format (dark gray)
        bracesFormat = QTextCharFormat()
        bracesFormat.setForeground(QColor("#666666"))
        bracesFormat.setFontWeight(QFont.Bold)
        self.highlightingRules.append((r'[{}\[\]]', bracesFormat))


class VerilogAHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#0000FF"))
        keywordFormat.setFontWeight(QFont.Bold)

        keywords = ["module", "endmodule", "input", "output", "inout", "parameter",
                    "analog", "real", "electrical", "discipline", "nature"]
        self.highlightingRules.append((r'\b(' + '|'.join(keywords) + r')\b', keywordFormat))

        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor("#00FF00"))
        functionFormat.setFontWeight(QFont.Bold)

        functions = ["cos", "sin", "ln", "log", "min", "pow", "sinh", "sqrt", "tan", "tanh",
                     "exp", "cosh", "ddt", "ddx", "idt", "laplace_nd", "laplace_zd"]
        self.highlightingRules.append(
            (r'\b(' + '|'.join(functions) + r')\b', functionFormat))

    def highlightComments(self, text):
        self.highlightSingleLineComments(text, '//')
        self.highlightMultiLineComments(text, r'/\*', r'\*/')

    def highlightSingleLineComments(self, text, commentStart):
        expression = re.compile(commentStart + '.*$')
        for match in expression.finditer(text):
            start, end = match.span()
            self.setFormat(start, end - start, self.commentFormat)

    def highlightMultiLineComments(self, text, commentStart, commentEnd):
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = text.find(commentStart)

        while startIndex >= 0:
            endIndex = text.find(commentEnd, startIndex)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + len(commentEnd)

            self.setFormat(startIndex, commentLength, self.commentFormat)
            startIndex = text.find(commentStart, startIndex + commentLength)


class XyceHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#0000FF"))
        keywordFormat.setFontWeight(QFont.Bold)

        keywords = [".print", ".plot", ".include", ".subckt", ".end", ".ends", ".param",
                    ".model", ".lib", ".sweep"]
        self.highlightingRules.append((r'\b(' + '|'.join(keywords) + r')\b', keywordFormat))

        analysisFormat = QTextCharFormat()
        analysisFormat.setForeground(QColor("#00FF0F"))
        analysisFormat.setFontWeight(QFont.Bold)

        analyses = [".ac", ".dc", ".tran", ".hb", ".noise", ".op"]
        self.highlightingRules.append(
            (r'\b(' + '|'.join(analyses) + r')\b', analysisFormat))

        componentFormat = QTextCharFormat()
        componentFormat.setForeground(QColor("#FF0000"))

        components = "RCLVIQMDJBEFGHKTSWZUOPXx"
        self.highlightingRules.append((r'^[' + components + r']', componentFormat))

    def highlightComments(self, text):
        self.highlightSingleLineComments(text, r'\*')

    def highlightSingleLineComments(self, text, commentStart):
        expression = re.compile('^' + commentStart + '.*$')
        for match in expression.finditer(text):
            start, end = match.span()
            self.setFormat(start, end - start, self.commentFormat)


class textEditor(QMainWindow):
    closedSignal = Signal(QObject)

    def __init__(self, filePathObj: Path):
        super().__init__()
        self.filePathObj = filePathObj if filePathObj.exists() else pathlib.Path.cwd()
        self.textEdit = QTextEdit()
        self.setCentralWidget(self.textEdit)

        self.createActions()
        self.createMenus()
        self.createToolbar()

        self.statusLine = self.statusBar()
        self.statusLabel = QLabel()
        self.statusLine.addPermanentWidget(self.statusLabel)
        self.textEdit.cursorPositionChanged.connect(self.updateStatus)
        self.cellViewTuple = ddef.viewTuple("", "", "")
        self.resize(600, 800)
        self.initEditor()

    def initEditor(self):
        if self.filePathObj.exists():
            with self.filePathObj.open("r") as file:
                text = file.read()
                self.textEdit.setPlainText(text)

    def createActions(self):
        documentOpenIcon = QIcon(":/icons/document-task.png")
        self.openAction = QAction(documentOpenIcon, "&Open", self)
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.setStatusTip("Open File")
        self.openAction.triggered.connect(self.openFile)
        
        reloadIcon = QIcon(":/icons/arrow-circle.png")
        self.reloadAction = QAction(reloadIcon, "&Reload", self)
        self.reloadAction.setShortcut("F5")
        self.reloadAction.setStatusTip("Reload File")
        self.reloadAction.triggered.connect(self.reloadFile)

        saveIcon = QIcon(":/icons/document.png")
        self.saveAction = QAction(saveIcon, "&Save", self)
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.setStatusTip("Save File")
        self.saveAction.triggered.connect(self.saveFile)

        saveAsIcon = QIcon(":/icons/document--plus.png")
        self.saveAsAction = QAction(saveAsIcon, "Save &As", self)
        self.saveAsAction.setStatusTip("Save File As...")
        self.saveAsAction.triggered.connect(self.saveAsFile)

        quitIcon = QIcon(":/icons/external.png")
        self.quitAction = QAction(quitIcon, "&Quit", self)
        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.setStatusTip("Quit")
        self.quitAction.triggered.connect(self.close)

        fontIcon = QIcon(":icons/ui-label.png")
        self.fontAction = QAction(fontIcon, "&Font", self)
        self.fontAction.setShortcut("Ctrl+F")
        self.fontAction.setStatusTip("Select Font")
        self.fontAction.triggered.connect(self.changeFont)

        cutIcon = QIcon(":/icons/cutter.png")
        self.cutAction = QAction(cutIcon, "&Cut", self)
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.setStatusTip("Cut Text")
        self.cutAction.triggered.connect(self.textEdit.cut)

        copyIcon = QIcon(":/icons/document-copy.png")
        self.copyAction = QAction(copyIcon, "&Copy", self)
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.setStatusTip("Copy Text")
        self.copyAction.triggered.connect(self.textEdit.copy)

        pasteIcon = QIcon(":/icons/clipboard-paste.png")
        self.pasteAction = QAction(pasteIcon, "&Paste", self)
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.setStatusTip("Paste Text")
        self.pasteAction.triggered.connect(self.textEdit.paste)

        findIcon = QIcon(":/icons/clipboard--pencil.png")
        self.findAction = QAction(findIcon, "&Find", self)
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.setStatusTip("Find Text")
        self.findAction.triggered.connect(self.findText)

        replaceIcon = QIcon(":/icons/clipboard-search-result.png")
        self.replaceAction = QAction(replaceIcon, "&Replace", self)
        self.replaceAction.setShortcut("Ctrl+H")
        self.replaceAction.setStatusTip("Replace Text")
        self.replaceAction.triggered.connect(self.replaceText)

    def createMenus(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.reloadAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.saveAsAction)
        fileMenu.addAction(self.quitAction)

        format_menu = menubar.addMenu("&Format")
        format_menu.addAction(self.fontAction)

        editMenu = menubar.addMenu("&Edit")
        editMenu.addAction(self.cutAction)
        editMenu.addAction(self.copyAction)
        editMenu.addAction(self.pasteAction)
        editMenu.addAction(self.findAction)
        editMenu.addAction(self.replaceAction)

    def createToolbar(self):
        toolbar = QToolBar("Toolbar")
        self.addToolBar(toolbar)

        toolbar.addAction(self.openAction)
        toolbar.addAction(self.reloadAction)
        toolbar.addAction(self.saveAction)
        toolbar.addAction(self.saveAsAction)
        toolbar.addAction(self.quitAction)
        toolbar.addSeparator()
        toolbar.addAction(self.fontAction)
        toolbar.addSeparator()
        toolbar.addAction(self.cutAction)
        toolbar.addAction(self.copyAction)
        toolbar.addAction(self.pasteAction)
        toolbar.addSeparator()
        toolbar.addAction(self.findAction)
        toolbar.addAction(self.replaceAction)

    def openFile(self):
        (fileName, _) = QFileDialog.getOpenFileName(self, "Open File", str(self.filePathObj),
                                                         "JSON Files (*.json);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj.exists():
                with self.filePathObj.open("r") as file:
                    text = file.read()
                    self.textEdit.setPlainText(text)

    def saveFile(self):
        if self.filePathObj.exists():
            with self.filePathObj.open("w") as file:
                text = self.textEdit.toPlainText()
                file.write(text)
        else:
            self.saveAsFile()

    def saveAsFile(self):
        (fileName, _) = QFileDialog.getSaveFileName(self, "Save File", str(self.filePathObj),
                                                    "JSON Files (*.json);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj.exists():
                with self.filePathObj.open("w") as file:
                    text = self.textEdit.toPlainText()
                    file.write(text)
                
    def reloadFile(self):
        if self.filePathObj.exists():
            cursor_position = self.textEdit.textCursor().position()
            with self.filePathObj.open("r") as file:
                text = file.read()
                self.textEdit.setPlainText(text)
            # Try to restore cursor position if possible
            cursor = self.textEdit.textCursor()
            cursor.setPosition(min(cursor_position, len(self.textEdit.toPlainText())))
            self.textEdit.setTextCursor(cursor)
        else:
            QMessageBox.information(self, "Reload", "No file is currently open.")

    def changeFont(self):
        ok, font = QFontDialog.getFont(self.textEdit.font(), self)
        if ok:
            self.textEdit.setFont(font)

    def findText(self):
        text, ok = QInputDialog.getText(self, "Find", "Enter text to find:")
        if ok:
            document = self.textEdit.document()
            cursor = document.find(text)
            if cursor.isNull():
                QMessageBox.information(self, "Find", "Text not found.")
            else:
                self.textEdit.setTextCursor(cursor)

    def replaceText(self):
        findText, ok1 = QInputDialog.getText(self, "Replace", "Enter text to find:")
        if ok1:
            replace_text, ok2 = QInputDialog.getText(self, "Replace",
                                                     "Enter replacement text:")
            if ok2:
                document = self.textEdit.document()
                cursor = document.find(findText)
                if cursor.isNull():
                    QMessageBox.information(self, "Replace", "Text not found.")
                else:
                    cursor.insertText(replace_text)

    def updateStatus(self):
        cursor = self.textEdit.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.statusLabel.setText(f"Line: {line}, Column: {column}")

    def closeEvent(self, event):
        self.closedSignal.emit(self)
        super().closeEvent(event)


class jsonEditor(textEditor):
    def __init__(self, filePathObj: Path):
        super().__init__(filePathObj)
        self.initEditor()
        self.setWindowTitle("JSON Editor")

    def initEditor(self):
        self.highlighter = JsonHighlighter(self.textEdit.document())
        super().initEditor()


class verilogaEditor(textEditor):
    def __init__(self, filePathObj):
        super().__init__(filePathObj)
        self.initEditor()
        self.setWindowTitle("Verilog-A Editor")

    def initEditor(self):
        self.highlighter = VerilogAHighlighter(self.textEdit.document())
        super().initEditor()

    def openFile(self):
        (fileName, _) = QFileDialog.getOpenFileName(self, "Open File", "",
                                                         "Verilog-A Files (*.va);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj.exists():
                with self.filePathObj.open("rw") as file:
                    text = file.read()
                    self.textEdit.setPlainText(text)


    def saveAsFile(self):
        (fileName, _) = QFileDialog.getSaveFileName(self, "Save File", str(self.filePathObj),
                                                         "Verilog-A Files (*.va);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj.exists():
                with self.filePathObj.open("w") as file:
                    text = self.textEdit.toPlainText()
                    file.write(text)


class spiceEditor(textEditor):
    def __init__(self, filePathObj:Path):
        super().__init__(filePathObj)
        self.initEditor()
        self.setWindowTitle("Xyce/SPICE Editor")

    def initEditor(self):
        self.highlighter = XyceHighlighter(self.textEdit.document())
        super().initEditor()

    def openFile(self):
        (fileName, _) = QFileDialog.getOpenFileName(self, "Open File", "",
                                                         "Xyce Files (*.sp);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj.exists():
                with self.filePathObj.open("r") as file:
                    text = file.read()
                    self.textEdit.setPlainText(text)

    def saveAsFile(self):

        (fileName, _) = QFileDialog.getSaveFileName(self, "Save File", str(self.filePathObj),
                                                         "Xyce Files (*.sp);;All Files (*)")
        if fileName:
            self.filePathObj = Path(fileName)
            if self.filePathObj:
                with self.filePathObj.open("w") as file:
                    text = self.textEdit.toPlainText()
                    file.write(text)


def main():
    app = QApplication(sys.argv)
    editor = verilogaEditor(None, '')
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
