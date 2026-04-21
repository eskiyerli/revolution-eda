
# LVS Netlisting Implementation
## Summary

I have successfully implemented LVS netlisting functionality to the schematic editor. Here's what was added:

### Changes Made:

1. **Added LVS mode parameter to [xyceNetlist](cci:2://file:///c:/Users/eskiye50/OneDrive%20-%20Revolution%20Semiconductor/Projects/design_software/revolution-eda/revedaEditor/gui/schematicEditor.py:611:0-1039:44) constructor**
   - Added `lvsMode: bool = False` parameter
   - Stored as `self._lvsMode` instance variable

2. **Added `lvsNetlistLine` attribute to symbol creation**
   - Added `symenc.symbolAttribute("lvsNetlistLine", "X@instName %pinOrder @cellName")` to the default symbol attributes

3. **Modified [processElementSymbol](cci:1://file:///c:/Users/eskiye50/OneDrive%20-%20Revolution%20Semiconductor/Projects/design_software/revolution-eda/revedaEditor/gui/schematicEditor.py:771:4-785:91) method**
   - Added logic to check for `lvsIgnore` attribute when in LVS mode
   - When `lvsIgnore="1"` and in LVS mode, the symbol is excluded from netlisting
   - In normal mode, continues to check `NetlistIgnore` attribute and `netlistIgnore` flag

4. **Modified [createXyceSymbolLine](cci:1://file:///c:/Users/eskiye50/OneDrive%20-%20Revolution%20Semiconductor/Projects/design_software/revolution-eda/revedaEditor/gui/schematicEditor.py:956:4-958:69) method**
   - Uses `lvsNetlistLine` when `self._lvsMode` is `True`
   - Uses `SpiceNetlistLine` when in normal mode

5. **Updated [__repr__](cci:1://file:///c:/Users/eskiye50/OneDrive%20-%20Revolution%20Semiconductor/Projects/design_software/revolution-eda/revedaEditor/gui/schematicEditor.py:642:4-643:143) method**
   - Added LVS mode to the string representation for debugging

### How to Use:

To enable LVS netlisting, create the [xyceNetlist](cci:2://file:///c:/Users/eskiye50/OneDrive%20-%20Revolution%20Semiconductor/Projects/design_software/revolution-eda/revedaEditor/gui/schematicEditor.py:611:0-1039:44) instance with `lvsMode=True`:

```python
netlister = xyceNetlist(schematic, filePath, useConfig=False, topSubckt=False, lvsMode=True)
```

When in LVS mode:
- Symbols with `lvsIgnore="1"` attribute will be excluded from netlisting
- Netlist lines will use the `lvsNetlistLine` attribute instead of `SpiceNetlistLine`

The implementation maintains backward compatibility - existing code will continue to work normally when `lvsMode=False` (the default).