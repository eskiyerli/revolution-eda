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
"""
Type definitions and protocols for editor modules to minimize type errors.
"""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, Union

if TYPE_CHECKING:
    import revedaEditor.backend.libBackEnd as libb
    import revedaEditor.backend.libraryModelView as lmview
    from revedaEditor.gui.editorViews import editorView
    from revedaEditor.scenes.editorScene import editorScene

# Forward declarations to avoid circular imports
EditorWindow = Union['schematicEditor', 'layoutEditor', 'symbolEditor']


class EditorContainer(Protocol):
    scene: editorScene  # Base class that all scenes inherit from
    view: editorView  # Base class that all views inherit from
    editorWindow: EditorWindow


class BaseEditor(Protocol):
    """Protocol defining the interface all editors must implement."""

    @property
    def centralW(self) -> EditorContainer: ...

    @property
    def viewItem(self) -> libb.viewItem: ...

    @property
    def libraryDict(self) -> dict: ...

    @property
    def libraryView(self) -> lmview.BaseDesignLibrariesView: ...

    def checkSaveCell(self) -> None: ...

    def saveCell(self) -> None: ...

    def show(self) -> None: ...
