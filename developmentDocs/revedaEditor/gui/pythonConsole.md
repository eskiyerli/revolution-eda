# `revedaEditor/gui/pythonConsole.py`

**Module:** `revedaEditor.gui.pythonConsole`

## Purpose

Interactive Python console widget embedded in the main window (stdin/stdout redirection, history).

## Module docstring

Console
Interactive console widget.  Use to add an interactive python interpreter
in a GUI application.

## Classes

- `LineEdit(QLineEdit)` — QLIneEdit with a history buffer for recalling previous lines.
  - `clearhistory()`
  - `event()`
  - `returnkey()`
  - `recall()`
  - `record()`
- `Redirect` — Map self.write to a function
  - `write()`
- `pythonConsole(QWidget)` — A GUI version of code.InteractiveConsole.
  - `setcontext()`
  - `resetbuffer()`
  - `setprompt()`
  - `push()`
  - `setfont()`
  - `write()`
  - `errorwrite()`
  - `writeoutput()`
  - `sizeHint()`

## Used by

- [[reveda|reveda]]
- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
