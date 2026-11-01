# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

# Revolution EDA GUI Module
# Initialize editor factory and register all editor types

from revedaEditor.gui.editorFactory import registerEditors

# Register all editor types when module is imported
registerEditors()
