# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

from typing import Callable

from PySide6.QtCore import QRunnable, Slot, Signal, QObject


class workerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)


class startThread(QRunnable):
    """A thread class to execute a given function as a runnable task."""
    __slots__ = ("fn", "args", "kwargs", "signals")

    def __init__(self, fn: Callable, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = workerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            if result:
                self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit((type(e), e.args, str(e)))
        finally:
            self.signals.finished.emit()
