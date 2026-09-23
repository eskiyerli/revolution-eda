# `revedaEditor/tests/conftest.py`

**Module:** `revedaEditor.tests.conftest`

## Purpose

pytest fixtures: offscreen `QApplication` and a minimal `qtbot` shim (no pytest-qt dependency).

## Module docstring

Shared pytest fixtures for revedaEditor tests.

Provides a minimal `qtbot` shim so tests written against pytest-qt run
without the dependency. Only `addWidget` is supported; it keeps the widget
alive for the duration of the test and enforces offscreen Qt platform.

## Classes

- `_QtBot` — Minimal stand-in for pytest-qt's QtBot fixture.
  - `addWidget()`

## Functions

- `qapp()`
- `qtbot()`
