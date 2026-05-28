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
    import revedaEditor.backend.lib_back_end as libb
    import revedaEditor.backend.library_model_view as lmview
    from revedaEditor.gui.editor_views import EditorView
    from revedaEditor.scenes.editor_scene import EditorScene

# Forward declarations to avoid circular imports
EditorWindow = Union['SchematicEditor', 'LayoutEditor', 'SymbolEditor']


class EditorContainer(Protocol):
    scene: EditorScene  # Base class that all scenes inherit from
    view: EditorView  # Base class that all views inherit from
    EditorWindow: EditorWindow


class BaseEditor(Protocol):
    """Protocol defining the interface all editors must implement."""

    @property
    def centralW(self) -> EditorContainer: ...

    @property
    def ViewItem(self) -> libb.ViewItem: ...

    @property
    def libraryDict(self) -> dict: ...

    @property
    def libraryView(self) -> lmview.BaseDesignLibrariesView: ...

    def checkSaveCell(self) -> None: ...

    def saveCell(self) -> None: ...

    def show(self) -> None: ...
