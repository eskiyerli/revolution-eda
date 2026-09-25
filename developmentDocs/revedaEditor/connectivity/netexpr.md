# `revedaEditor\connectivity\netexpr.py`

**Module:** `revedaEditor.connectivity.netexpr`

## Purpose

Net expressions and inherited connections (netSet).

## Functions

- `parseNetExpr()` — Parse `[@name]` / `[@name:default]` -> (name, default).
- `isNetExpr()` — True when *text* parses as a net expression.
- `evalNetExpr()` — Resolve one net expression in a binding context.
- `parseNetSet()` — Parse a netSet value into {exprName: localNetName}.
- `formatNetSet()` — Inverse of parseNetSet's text form, for dialogs.
- `mergeExprDefs()` — Fold expression texts into a {name: default} map.
- `exprNamesFromItems()` — Collect {exprName: default} from live items' `netExpr` attrs.
- `exprNamesFromRecords()` — Collect {exprName: default} from a decoded schematic design array.
- `terminalBinds()` — Identity bindings — resolve `[@name:def]` to `name`.
- `instanceExprNets()` — Binding produced by one instance for each implicit terminal.
