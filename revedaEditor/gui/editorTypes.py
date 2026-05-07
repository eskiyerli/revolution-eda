# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#

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
