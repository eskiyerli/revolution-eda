# `revedaEditor/connectivity/netexpr.py`

**Module:** `revedaEditor.connectivity.netexpr`

## Purpose

Net-expression / inherited-connection (`netSet`) parsing and evaluation — `<*N>` replication, global nets, expression terminals.

## Module docstring

Net expressions and inherited connections (netSet).

A *net expression* is a `[@name]` or `[@name:default]` string carried by:

- `scn`/`scp` record `nx` fields (net segment / schematic pin),
- symbol `pin` record `nx` fields (inherited-connection pins),
- live items via their `netExpr` attribute.

Evaluation happens inside `connectivity.resolve` — the single evaluation
point — with a *binding map* (`netSet`) supplied by the caller:

- `binds[name]` wins when present (an ancestor instance's netSet
  override, or an identity binding for a subcircuit terminal);
- otherwise the expression's `default` is used when declared;
- otherwise the bare `name` (connect-by-name in the local context).

A *netSet* is a per-instance override map `{exprName: localNetName}`,
persisted as the `nst` field on `sys` records. During hierarchical
netlisting each distinct expression name used inside a cell becomes an
implicit subcircuit terminal; the instance line supplies the netSet
override, or the expression default, or the bare name.

This module is Qt-free so GUI scenes, headless record checks, netlisters
and aiTerminal design ops share identical semantics.

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
