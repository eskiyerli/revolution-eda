""" Console
Interactive console widget.  Use to add an interactive python interpreter
in a GUI application.
"""

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

import code
import re
from typing import Callable

from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QSize,
)
from PySide6.QtGui import QTextCharFormat, QBrush, QColor, QFont
from PySide6.QtWidgets import QLineEdit, QWidget, QGridLayout, QPlainTextEdit


class LineEdit(QLineEdit):
    """QLIneEdit with a history buffer for recalling previous lines.
    I also accept tab as input (4 spaces).
    """

    newline = Signal(str)  # Signal when return key pressed

    def __init__(self, history: int = 100) -> "LineEdit":
        super().__init__()
        self.historymax = history
        self.clearhistory()
        self.promptpattern = re.compile("^[>\.]")

    def clearhistory(self) -> None:
        """Clear history buffer"""
        self.historyindex = 0
        self.historylist = []

    def event(self, ev: QEvent) -> bool:
        """Intercept tab and arrow key presses.  Insert 4 spaces
        when tab pressed instead of moving to next contorl.  WHen
        arrow up or down are pressed select a line from the history
        buffer.  Emit newline signal when return key is pressed.
        """
        if ev.type() == QEvent.KeyPress:
            if ev.key() == int(Qt.Key_Tab):
                self.insert("    ")
                return True
            elif ev.key() == int(Qt.Key_Up):
                self.recall(self.historyindex - 1)
                return True
            elif ev.key() == int(Qt.Key_Down):
                self.recall(self.historyindex + 1)
                return True
            elif ev.key() == int(Qt.Key_Home):
                self.recall(0)
                return True
            elif ev.key() == int(Qt.Key_End):
                self.recall(len(self.historylist) - 1)
                return True
            elif ev.key() == int(Qt.Key_Return):
                self.returnkey()
                return True
        return super().event(ev)

    def returnkey(self) -> None:
        """Return key was pressed.  Add line to history and emit
        the newline signal.
        """
        text = self.text().rstrip()
        self.record(text)
        self.newline.emit(text)
        self.setText("")

    def recall(self, index: int) -> None:
        """Select a line from the history list"""
        length = len(self.historylist)
        if length > 0:
            index = max(0, min(index, length - 1))
            self.setText(self.historylist[index])
            self.historyindex = index

    def record(self, line: str) -> None:
        """Add line to history buffer"""
        self.historyindex += 1
        while len(self.historylist) >= self.historymax - 1:
            self.historylist.pop()
        self.historylist.append(line)
        self.historyindex = min(self.historyindex, len(self.historylist))


class Redirect:
    """Map self.write to a function"""

    def __init__(self, func: Callable) -> "Redirect":
        self.func = func

    def write(self, line: str) -> None:
        self.func(line)


class pythonConsole(QWidget):
    """A GUI version of code.InteractiveConsole."""

    def __init__(
            self,
            context=locals(),  # context for interpreter
            history: int = 200,  # max lines in history buffer
            blockcount: int = 500,  # max lines in output buffer
    ) -> "pythonConsole":
        super().__init__()
        self.setcontext(context)
        self.buffer = []

        self.content = QGridLayout(self)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(0)

        # Display for output and stderr
        self.outdisplay = QPlainTextEdit(self)
        self.outdisplay.setMaximumBlockCount(blockcount)
        self.outdisplay.setReadOnly(True)
        self.content.addWidget(self.outdisplay, 0, 0, 1, 2)

        # Use color to differentiate input, output and stderr
        self.inpfmt = self.outdisplay.currentCharFormat()
        self.outfmt = QTextCharFormat(self.inpfmt)
        self.outfmt.setForeground(QBrush(QColor(0, 0, 255)))
        self.errfmt = QTextCharFormat(self.inpfmt)
        self.errfmt.setForeground(QBrush(QColor(255, 0, 0)))

        # Display input prompt left of input edit
        self.promptdisp = QLineEdit(self)
        self.promptdisp.setReadOnly(True)
        self.promptdisp.setFixedWidth(15)
        self.promptdisp.setFrame(False)
        self.content.addWidget(self.promptdisp, 1, 0)
        self.setprompt("> ")

        # Enter commands here
        self.inpedit = LineEdit(history=history)
        self.inpedit.newline.connect(self.push)
        self.inpedit.setFrame(False)
        self.content.addWidget(self.inpedit, 1, 1)

    def setcontext(self, context):
        """Set context for interpreter"""
        self.interp = code.InteractiveInterpreter(context)

    def resetbuffer(self) -> None:
        """Reset the input buffer."""
        self.buffer = []

    def setprompt(self, text: str):
        self.prompt = text
        self.promptdisp.setText(text)

    def push(self, line: str) -> None:
        """Execute entered command.  Command may span multiple lines"""
        if line == "clear":
            self.inpedit.clearhistory()
            self.outdisplay.clear()
        else:
            lines = line.split("\n")
            for line in lines:
                if re.match("^[\>\.] ", line):
                    line = line[2:]
                self.writeoutput(self.prompt + line, self.inpfmt)
                self.setprompt(". ")
                self.buffer.append(line)
            # Built a command string from lines in the buffer
            source = "\n".join(self.buffer)
            more = self.interp.runsource(source, "<input>", "exec")
            if not more:
                self.setprompt("> ")
                self.resetbuffer()

    def setfont(self, font: QFont) -> None:
        """Set font for input and display widgets.  Should be monospaced"""
        self.outdisplay.setFont(font)
        self.inpedit.setFont(font)

    def write(self, line: str) -> None:
        """Capture stdout and display in outdisplay"""
        if len(line) != 1 or ord(line[0]) != 10:
            self.writeoutput(line.rstrip(), self.outfmt)

    def errorwrite(self, line: str) -> None:
        """Capture stderr and display in outdisplay"""
        self.writeoutput(line, self.errfmt)

    def writeoutput(self, line: str, fmt: QTextCharFormat = None) -> None:
        """Set text formatting and display line in outdisplay"""
        if fmt is not None:
            self.outdisplay.setCurrentCharFormat(fmt)
        self.outdisplay.appendPlainText(line.rstrip())

    def sizeHint(self):
        return QSize(500, 200)
