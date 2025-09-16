#    "Commons Clause" License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, "Sell" means practicing any or all of the rights
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

from typing import Callable
from PySide6.QtCore import QRunnable, Slot, Signal, QObject

class workerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = Signal(object)
    error = Signal(tuple)

class startThread(QRunnable):
    """A thread class to execute a given function as a runnable task.

    Attributes:
        fn (Callable): The function to be executed in the thread.
        signals (WorkerSignals): Signal instance to emit results.
    """
    __slots__ = ("fn", "signals")

    def __init__(self, fn: Callable) -> None:
        """Initialize the thread with a function to execute.

        Args:
            fn (Callable): The function to be executed.
        """
        super().__init__()
        self.fn = fn
        self.signals = workerSignals()

    @Slot()
    def run(self) -> None:
        """Execute the stored function in the thread.

        Emits the result through signals when complete or if error occurs.
        """
        try:
            result = self.fn()  # Actually call the function
            self.signals.finished.emit(result if result is not None else "Success")
        except Exception as e:
            print(f"Error executing thread function: {str(e)}")
            self.signals.error.emit((str(e),))
            raise

# from PySide6.QtCore import (
#     QRunnable,
#     Slot,
# )
#
#
# class startThread(QRunnable):
#     __slots__ = ("fn",)
#
#     def __init__(self, fn):
#         super().__init__()
#         self.fn = fn
#
#     @Slot()
#     def run(self) -> None:
#         try:
#             self.fn
#             print(self.fn)
#         except Exception as e:
#             print(e)
