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

"""Net expressions and inherited connections (netSet).

A *net expression* is a ``[@name]`` or ``[@name:default]`` string carried by:

- ``scn``/``scp`` record ``nx`` fields (net segment / schematic pin),
- symbol ``pin`` record ``nx`` fields (inherited-connection pins),
- live items via their ``netExpr`` attribute.

Evaluation happens inside ``connectivity.resolve`` — the single evaluation
point — with a *binding map* (``netSet``) supplied by the caller:

- ``binds[name]`` wins when present (an ancestor instance's netSet
  override, or an identity binding for a subcircuit terminal);
- otherwise the expression's ``default`` is used when declared;
- otherwise the bare ``name`` (connect-by-name in the local context).

A *netSet* is a per-instance override map ``{exprName: localNetName}``,
persisted as the ``nst`` field on ``sys`` records. During hierarchical
netlisting each distinct expression name used inside a cell becomes an
implicit subcircuit terminal; the instance line supplies the netSet
override, or the expression default, or the bare name.

This module is Qt-free so GUI scenes, headless record checks, netlisters
and aiTerminal design ops share identical semantics.
"""

from __future__ import annotations

import json
import re
from typing import Iterable, Optional

# [@name] or [@name:default] — whole-string match. The name is an
# identifier with an optional <n> or <n:m> bus suffix (so the ':' inside
# bus notation is not mistaken for the default separator); defaults are
# arbitrary net names including globals (vdd!).
_NETEXPR_RE = re.compile(
    r"^\s*\[@\s*([A-Za-z_][\w.]*(?:<\d+(?::\d+)?>)?)\s*"
    r"(?::\s*(.*?)\s*)?\]\s*$")


def parseNetExpr(text) -> Optional[tuple[str, str]]:
    """Parse ``[@name]`` / ``[@name:default]`` -> (name, default).

    Returns None when *text* is not a well-formed net expression. A missing
    default yields ``""``.
    """
    if not isinstance(text, str):
        return None
    match = _NETEXPR_RE.match(text)
    if match is None:
        return None
    return match.group(1), match.group(2) or ""


def isNetExpr(text) -> bool:
    """True when *text* parses as a net expression."""
    return parseNetExpr(text) is not None


def evalNetExpr(expr: str, binds: Optional[dict] = None) -> Optional[str]:
    """Resolve one net expression in a binding context.

    ``binds`` maps expression name -> local net name (netSet overrides or
    identity bindings for subcircuit terminals). Unbound names fall back to
    the expression default, then to the bare name. Returns None for
    malformed expressions.
    """
    parsed = parseNetExpr(expr)
    if parsed is None:
        return None
    name, default = parsed
    bound = (binds or {}).get(name)
    return bound or default or name


def parseNetSet(value) -> dict[str, str]:
    """Parse a netSet value into {exprName: localNetName}.

    Accepts the persisted ``nst`` forms: a dict (JSON object on ``sys``
    records) or a text encoding ``"vdd=AVDD;avss=AVSS"`` (commas also
    accepted) used by property dialogs. Anything else returns {}.
    """
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if str(k)}
    if not isinstance(value, str) or not value.strip():
        return {}
    text = value.strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except ValueError:
            return {}
        return parseNetSet(parsed)
    result: dict[str, str] = {}
    for pair in re.split(r"[;,]", text):
        pair = pair.strip()
        if not pair:
            continue
        name, sep, net = pair.partition("=")
        if sep and name.strip():
            result[name.strip()] = net.strip()
    return result


def formatNetSet(netSet: dict) -> str:
    """Inverse of parseNetSet's text form, for dialogs."""
    return ",".join(f"{name}={net}" for name, net in
                    sorted((netSet or {}).items()))


def mergeExprDefs(into: dict[str, str], exprTexts: Iterable[str],
                  problems: Optional[list] = None) -> dict[str, str]:
    """Fold expression texts into a {name: default} map.

    Conflicting defaults for the same name and malformed expressions are
    appended to *problems* (human-readable strings); the first default
    seen wins so output stays deterministic.
    """
    for text in exprTexts:
        if not text:
            continue
        parsed = parseNetExpr(text)
        if parsed is None:
            if problems is not None:
                problems.append(f"Malformed net expression {text!r}")
            continue
        name, default = parsed
        if name in into:
            if default and into[name] and into[name] != default:
                if problems is not None:
                    problems.append(
                        f"Net expression '{name}' has conflicting "
                        f"defaults '{into[name]}' and '{default}'")
        else:
            into[name] = default
    return into


def exprNamesFromItems(items: Iterable) -> tuple[dict[str, str], list[str]]:
    """Collect {exprName: default} from live items' ``netExpr`` attrs.

    Duck-typed: any object with a ``netExpr`` attribute contributes —
    nets, schematic pins, and symbol pins alike. Symbol instances are
    expanded to their pins so per-pin expressions are seen at this level.
    """
    defs: dict[str, str] = {}
    problems: list[str] = []
    texts = []
    for item in items:
        expr = getattr(item, "netExpr", "")
        if expr:
            texts.append(expr)
        pins = getattr(item, "pins", None)
        if pins:
            texts.extend(pin.netExpr for pin in pins.values()
                         if getattr(pin, "netExpr", ""))
    mergeExprDefs(defs, texts, problems)
    return defs, problems


def exprNamesFromRecords(records: Iterable[dict],
                         pinLocator=None) -> tuple[dict[str, str], list[str]]:
    """Collect {exprName: default} from a decoded schematic design array.

    Reads ``nx`` on ``scn``/``scp`` records and per-pin expressions exposed
    by *pinLocator* (``"pinExprs"`` metadata, as produced by
    ``loadJSON.makeSymbolPinLocator``) for ``sys`` records.
    """
    defs: dict[str, str] = {}
    problems: list[str] = []
    texts: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        recType = record.get("type")
        if recType in ("scn", "scp"):
            texts.append(record.get("nx", "") or "")
        elif recType == "sys" and pinLocator is not None:
            pinMap = pinLocator(record.get("lib", ""), record.get("cell", ""),
                                record.get("view", "symbol")) or {}
            texts.extend((pinMap.get("pinExprs") or {}).values())
    mergeExprDefs(defs, texts, problems)
    return defs, problems


def terminalBinds(exprNames: Iterable[str]) -> dict[str, str]:
    """Identity bindings — resolve ``[@name:def]`` to ``name``.

    Used when collecting a subcircuit definition: each expression name is
    an implicit terminal bound at instantiation, so the internal net is
    literally ``name``.
    """
    return {name: name for name in exprNames}


def instanceExprNets(netSet, exprDefs: dict[str, str]) -> dict[str, str]:
    """Binding produced by one instance for each implicit terminal.

    Returns {exprName: parentNetName}: the instance's netSet override when
    present, else the expression default, else the bare name.
    """
    binds = parseNetSet(netSet)
    return {name: binds.get(name) or default or name
            for name, default in exprDefs.items()}
