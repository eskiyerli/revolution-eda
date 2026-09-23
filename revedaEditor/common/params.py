# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""Typed instance-parameter model (CDF-lite).

One semantic model for symbol parameter definitions, consumed by the GUI
(instance properties dialog, place-with-form), the JSON load path, the
record-level diagnostics in ``connectivity.diagnostics``, and the symbol
importers. The module is deliberately Qt-free so headless paths
(aiTerminal design ops, importers, batch tooling) share identical
semantics.

Persistence
-----------
Parameter definitions live in the symbol's attribute list as a reserved
attribute ``paramDefs`` whose definition is a JSON-encoded ordered list::

    {"type": "attr", "nam": "paramDefs",
     "def": '[{"name": "r", "type": "float", "default": "1k", ...}]'}

Older files simply lack the attribute (no parameters); older readers see
an opaque attribute they ignore. Instance values are unchanged: they stay
in ``sys.ld`` as ``labelName: [value, visible]`` and are *validated*
against the matching ``ParamDef`` at load and edit time.

Each ``ParamDef`` declares:

    name      parameter name; matches instance label ``@<name>``
    type      "float" | "int" | "string" | "boolean" | "choice"
    default   literal default, may embed ``pPar("name")`` sibling refs
    minimum   optional numeric lower bound (quantiphy-parseable)
    maximum   optional numeric upper bound (quantiphy-parseable)
    choices   allowed values for type "choice"
    display   False hides the parameter from the instance edit form
    parse     True: numeric values may use quantiphy suffixes ("1k", "2u")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Mapping, Optional

from quantiphy import Quantity

PARAMDEFS_ATTR = "paramDefs"

PARAM_TYPES = ("float", "int", "string", "boolean", "choice")

_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}

_PPAR_RE = re.compile(r'''pPar\(\s*["']([^"']+)["']\s*\)''')

# Bound for iterative pPar resolution (pPar chains and cycles).
_PPAR_MAX_DEPTH = 8


@dataclass(frozen=True)
class ParamDef:
    """Typed parameter definition declared on a symbol."""

    name: str
    type: str = "string"
    default: str = ""
    minimum: str = ""
    maximum: str = ""
    choices: tuple = ()
    display: bool = True
    parse: bool = True

    def toDict(self) -> dict:
        result = {"name": self.name, "type": self.type}
        if self.default != "":
            result["default"] = self.default
        if self.minimum != "":
            result["min"] = self.minimum
        if self.maximum != "":
            result["max"] = self.maximum
        if self.choices:
            result["choices"] = list(self.choices)
        if not self.display:
            result["display"] = False
        if not self.parse:
            result["parse"] = False
        return result


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def paramDefsFromJson(text: str) -> tuple[list[ParamDef], list[str]]:
    """Parse the ``paramDefs`` attribute payload.

    Returns ``(paramDefs, errors)``; malformed input yields an empty list
    plus human-readable errors, never raises."""
    defs: list[ParamDef] = []
    errors: list[str] = []
    if text is None or str(text).strip() == "":
        return defs, errors
    try:
        rawList = json.loads(str(text))
    except (json.JSONDecodeError, TypeError) as e:
        return [], [f"paramDefs attribute is not valid JSON: {e}"]
    if not isinstance(rawList, list):
        return [], ["paramDefs attribute must be a JSON list"]
    for index, entry in enumerate(rawList):
        if not isinstance(entry, dict):
            errors.append(f"paramDefs[{index}] is not an object")
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            errors.append(f"paramDefs[{index}] has no 'name'")
            continue
        ptype = str(entry.get("type", "string")).strip().lower()
        if ptype not in PARAM_TYPES:
            errors.append(
                f"paramDefs[{index}] '{name}' has unknown type "
                f"'{ptype}' (expected one of {PARAM_TYPES})")
            ptype = "string"
        choices = entry.get("choices", ())
        if isinstance(choices, str):
            choices = [c.strip() for c in choices.split(",") if c.strip()]
        defs.append(ParamDef(
            name=name,
            type=ptype,
            default=str(entry.get("default", "")),
            minimum=str(entry.get("min", "")),
            maximum=str(entry.get("max", "")),
            choices=tuple(str(c) for c in choices),
            display=bool(entry.get("display", True)),
            parse=bool(entry.get("parse", True))))
    errors.extend(validateParamDefs(defs))
    return defs, errors


def paramDefsToJson(paramDefs: list[ParamDef]) -> str:
    """Serialise paramDefs to the ``paramDefs`` attribute payload."""
    return json.dumps([pd.toDict() for pd in paramDefs],
                      separators=(",", ":"))


def paramDefsFromSymattrs(symattrs: Optional[Mapping]) -> list[ParamDef]:
    """Extract ParamDefs from a symbol attribute dict (``symattrs``)."""
    if not symattrs:
        return []
    defs, _errors = paramDefsFromJson(symattrs.get(PARAMDEFS_ATTR, ""))
    return defs


def paramDefLabelBindings(paramDefs: list[ParamDef], labelNames) -> tuple[
        list[tuple[ParamDef, str]], list[str]]:
    """Match typed parameter definitions to persistent label carriers.

    Parameter values persist in schematic ``sys.ld`` under existing symbol
    label names, not in a separate parameter dictionary. A definition is
    therefore usable by editable-instance UIs only when the symbol exposes
    an NLP label named ``@<name>`` (preferred) or the legacy bare ``<name>``
    form. Returns bindings in ParamDef declaration order plus definition
    names with no carrier.
    """
    names = set(labelNames.keys() if isinstance(labelNames, Mapping)
                else labelNames)
    bindings = []
    missing = []
    for pdef in paramDefs:
        labelName = next(
            (candidate for candidate in (f"@{pdef.name}", pdef.name)
             if candidate in names),
            None,
        )
        if labelName is None:
            missing.append(pdef.name)
        else:
            bindings.append((pdef, labelName))
    return bindings, missing


def validateParamDefs(paramDefs: list[ParamDef]) -> list[str]:
    """Structural checks on a paramDefs list (duplicates, range sanity)."""
    errors: list[str] = []
    seen: set[str] = set()
    for pd in paramDefs:
        if pd.name in seen:
            errors.append(f"Duplicate parameter name '{pd.name}'")
        seen.add(pd.name)
        if pd.type == "choice" and not pd.choices:
            errors.append(
                f"Choice parameter '{pd.name}' declares no choices")
        low = _parseNumber(pd.minimum, pd) if pd.minimum else None
        high = _parseNumber(pd.maximum, pd) if pd.maximum else None
        if pd.minimum and low is None:
            errors.append(
                f"Parameter '{pd.name}' has unparseable min "
                f"'{pd.minimum}'")
        if pd.maximum and high is None:
            errors.append(
                f"Parameter '{pd.name}' has unparseable max "
                f"'{pd.maximum}'")
        if low is not None and high is not None and low > high:
            errors.append(
                f"Parameter '{pd.name}' min {pd.minimum} > max "
                f"{pd.maximum}")
        if pd.default and not _PPAR_RE.search(pd.default):
            defErrors = _validateScalar(pd, pd.default)
            errors.extend(
                f"Parameter '{pd.name}' default: {e}"
                for e in defErrors)
    return errors


# ---------------------------------------------------------------------------
# Value validation / normalisation
# ---------------------------------------------------------------------------


def _parseNumber(raw: str, pdef: ParamDef) -> Optional[float]:
    """Parse a numeric value, honouring the def's quantiphy flag."""
    text = str(raw).strip()
    if text == "":
        return None
    if pdef.parse:
        try:
            return float(Quantity(text))
        except (ValueError, TypeError):
            return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _validateScalar(pdef: ParamDef, raw: str) -> list[str]:
    """Type checks for a single value (no range or pPar handling)."""
    text = str(raw).strip()
    match pdef.type:
        case "float":
            if _parseNumber(text, pdef) is None:
                return [f"'{text}' is not a number"]
        case "int":
            value = _parseNumber(text, pdef)
            if value is None:
                return [f"'{text}' is not a number"]
            if int(value) != value:
                return [f"'{text}' is not an integer"]
        case "boolean":
            if text.lower() not in _BOOL_TRUE | _BOOL_FALSE:
                return [f"'{text}' is not a boolean"]
        case "choice":
            if text not in pdef.choices:
                return [f"'{text}' is not one of {list(pdef.choices)}"]
        case _:
            pass
    return []


def validateValue(pdef: ParamDef, raw: str,
                  siblings: Optional[Mapping] = None) -> list[str]:
    """Validate an instance value against its ParamDef.

    Empty values are valid (the default applies). ``pPar("name")``
    references inside the value are resolved against ``siblings``
    (a name -> value mapping; ``@``-prefixed keys are also consulted)
    before checking the result against type and range."""
    text = str(raw).strip()
    if text == "":
        return []
    text = resolveRefs(text, siblings)
    errors = _validateScalar(pdef, text)
    if errors:
        return errors
    if pdef.type in ("float", "int"):
        value = _parseNumber(text, pdef)
        if value is not None:
            low = (_parseNumber(pdef.minimum, pdef)
                   if pdef.minimum else None)
            high = (_parseNumber(pdef.maximum, pdef)
                    if pdef.maximum else None)
            if low is not None and value < low:
                errors.append(
                    f"'{text}' below minimum '{pdef.minimum}'")
            if high is not None and value > high:
                errors.append(
                    f"'{text}' above maximum '{pdef.maximum}'")
    return errors


def normalizeValue(pdef: ParamDef, raw: str) -> str:
    """Canonical string form of a valid value (booleans lower-cased)."""
    text = str(raw).strip()
    if pdef.type == "boolean":
        return "true" if text.lower() in _BOOL_TRUE else "false"
    return text


# ---------------------------------------------------------------------------
# Defaults and pPar("name") sibling references
# ---------------------------------------------------------------------------


def _siblingLookup(siblings: Optional[Mapping], name: str) -> Optional[str]:
    """Find ``name`` in a label/value mapping, tolerating ``@`` keys.

    Values may be raw strings, label objects (``labelValue``), or
    ``[value, visible]`` pairs (``sys.ld`` record shape)."""
    if not siblings:
        return None
    value = siblings.get(name, siblings.get(f"@{name}"))
    if value is None:
        return None
    value = getattr(value, "labelValue", value)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value)


def resolveRefs(text: str, siblings: Optional[Mapping] = None) -> str:
    """Substitute ``pPar("name")`` references with sibling values.

    Mirrors the PyLabel convention: the parent is the instance holding
    the label, so a sibling lookup reads the instance's other parameter
    values. Unresolvable references are left literal so downstream tools
    can still see the intent."""
    if not text or "pPar" not in text:
        return text

    def repl(match):
        value = _siblingLookup(siblings, match.group(1))
        return value if value not in (None, "") else match.group(0)

    resolved = text
    for _ in range(_PPAR_MAX_DEPTH):
        newText = _PPAR_RE.sub(repl, resolved)
        if newText == resolved or "pPar" not in newText:
            return newText
        resolved = newText
    return resolved


def resolveDefault(pdef: ParamDef,
                   siblings: Optional[Mapping] = None) -> str:
    """The parameter's effective default with pPar references resolved."""
    return resolveRefs(str(pdef.default), siblings)


def effectiveValue(pdef: ParamDef, raw: str,
                   siblings: Optional[Mapping] = None) -> str:
    """Value after applying the default when ``raw`` is empty."""
    text = str(raw).strip()
    if text:
        return resolveRefs(text, siblings)
    return resolveDefault(pdef, siblings)


def applyDefaults(paramDefs: list[ParamDef],
                  labelValues: Mapping) -> dict:
    """Fill empty parameter values with resolved defaults.

    ``labelValues`` maps label names (``@name`` or bare ``name``) to raw
    value strings. Definitions are resolved iteratively so a visible default
    may reference a hidden or later sibling through ``pPar("name")``. Returns
    ``{@name: value}`` covering only parameters that gained a non-empty
    effective value; values already present are passed through with references
    resolved.
    """
    result: dict = {}
    workingValues = dict(labelValues or {})
    for _ in range(_PPAR_MAX_DEPTH):
        changed = False
        for pdef in paramDefs:
            raw = _siblingLookup(workingValues, pdef.name) or ""
            value = effectiveValue(pdef, raw, workingValues)
            if value == "":
                continue
            key = f"@{pdef.name}"
            if workingValues.get(key) != value:
                workingValues[key] = value
                changed = True
            result[key] = value
        if not changed:
            break
    return result


def inferType(value: str) -> str:
    """Best-effort ParamDef type for an imported default value."""
    text = str(value).strip()
    if text.lower() in ("true", "false", "yes", "no", "on", "off"):
        return "boolean"
    try:
        int(text)
        return "int"
    except (ValueError, TypeError):
        pass
    try:
        float(Quantity(text))
        return "float"
    except (ValueError, TypeError):
        return "string"


def validateInstanceValues(paramDefs: list[ParamDef],
                           labelValues: Mapping,
                           owner: str = "") -> list[str]:
    """Validate a label value mapping against paramDefs.

    ``labelValues`` may map ``@name``/``name`` to raw strings, label
    objects, or ``[value, visible]`` pairs (``sys.ld`` record shape).
    Returns human-readable error strings; missing values are skipped
    (defaults apply)."""
    errors: list[str] = []
    for pdef in paramDefs:
        raw = _siblingLookup(labelValues, pdef.name)
        if raw in (None, ""):
            continue
        for err in validateValue(pdef, raw, labelValues):
            prefix = f"{owner}: " if owner else ""
            errors.append(f"{prefix}parameter '{pdef.name}': {err}")
    return errors
