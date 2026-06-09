# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

# Revolution EDA GUI Module
# Initialize editor factory and register all editor types

from revedaEditor.gui.editorFactory import registerEditors

# Register all editor types when module is imported
registerEditors()
