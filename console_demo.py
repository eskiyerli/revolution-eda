# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Live demo for the embedded Python console in reveda's main window.

Run inside the console's `>` prompt:
    exec(open("console_demo.py").read())
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

mw = next(w for w in QApplication.topLevelWidgets()
          if isinstance(w, MainWindow))
console = mw.centralW.console
say = lambda t="": console.writeoutput(t, console.outfmt)  # blue text

# -- 1. Introspection: what is the app holding right now? --------------------
say("=" * 52)
say("  Revolution EDA — scripted from its own console")
say("=" * 52)

say(f"Libraries loaded : {len(mw.libraryDict)}")
for name in sorted(mw.libraryDict)[:8]:
    say(f"    · {name}")

views = list(mw.openViews.values())
say(f"Open editors     : {len(views)}")
for w in views:
    say(f"    · {w.__class__.__name__:16s} {w.windowTitle()}")

pluginsObj = getattr(mw.app, "pluginsObj", None)
if pluginsObj:
    names = sorted(getattr(pluginsObj, "plugins", {}) or {})
    say(f"Plugins loaded   : {len(names)}")
    for name in names:
        say(f"    · {name}")

# -- 2. Drive the GUI: animated title + window wiggle, all non-blocking ------
origTitle, origGeom = mw.windowTitle(), mw.geometry()
spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
state = {"i": 0}

def tick():
    i = state["i"]
    mw.setWindowTitle(
        f"{spinner[i % len(spinner)]} Python is driving this window…")
    mw.move(origGeom.x() + (4, 0, -4, 0)[i % 4], origGeom.y())
    state["i"] += 1
    if i >= 39:  # ~3 s at 75 ms
        timer.stop()
        mw.setWindowTitle(origTitle)
        mw.setGeometry(origGeom)
        say("Done — GUI stayed responsive the whole time.")
        mw.libraryBrowserClick()  # pop the Library Browser as a finale

timer = QTimer(mw)
timer.timeout.connect(tick)
timer.start(75)
say("Animating the main window…")
