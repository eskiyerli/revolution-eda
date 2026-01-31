#    "Commons Clause" License Condition v1.0
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

"""
Editor factory for creating appropriate editor instances based on view type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

from revedaEditor.gui.editorTypes import BaseEditor

if TYPE_CHECKING:
    import revedaEditor.backend.libBackEnd as libb
    import revedaEditor.backend.libraryModelView as lmview


class EditorFactory:
    """Factory for creating editor instances based on view type."""

    _editor_registry: Dict[str, Type[BaseEditor]] = {}

    @classmethod
    def registerEditor(cls, view_type: str,
                       editor_class: Type[BaseEditor]) -> None:
        """Register an editor class for a specific view type."""
        cls._editor_registry[view_type] = editor_class

    @classmethod
    def createEditor(cls, view_type: str, viewItem: 'libb.viewItem',
                     libraryDict: dict,
                     libraryView: 'lmview.BaseDesignLibrariesView') -> BaseEditor:
        """Create appropriate editor based on view type."""
        if view_type not in cls._editor_registry:
            raise ValueError(f"No editor registered for view type: {view_type}")

        editor_class = cls._editor_registry[view_type]
        return editor_class(viewItem, libraryDict, libraryView)

    @classmethod
    def getSupportedViewTypes(cls) -> list[str]:
        """Get list of supported view types."""
        return list(cls._editor_registry.keys())


# Registration function to be called by each editor module
def registerEditors():
    """Register all editor types. Called during module initialization."""
    # Import here to avoid circular imports
    from revedaEditor.gui.schematicEditor import schematicEditor
    from revedaEditor.gui.layoutEditor import layoutEditor
    from revedaEditor.gui.symbolEditor import symbolEditor

    EditorFactory.registerEditor("schematic", schematicEditor)
    EditorFactory.registerEditor("layout", layoutEditor)
    EditorFactory.registerEditor("symbol", symbolEditor)
