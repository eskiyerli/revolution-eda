"""Shared pytest fixtures for revedaEditor tests.

Provides a minimal ``qtbot`` shim so tests written against pytest-qt run
without the dependency. Only ``addWidget`` is supported; it keeps the widget
alive for the duration of the test and enforces offscreen Qt platform.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


class _QtBot:
    """Minimal stand-in for pytest-qt's QtBot fixture."""

    def __init__(self):
        self._widgets = []

    def addWidget(self, widget):
        self._widgets.append(widget)
        return widget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp):
    return _QtBot()
