# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

"""Qt-free VACASK netlist formatting primitives.

This module is the single implementation of VACASK instance-line and
deck-level formatting.  It is consumed by:

- :class:`revedaEditor.netlisting.vacaskNetlist.vacaskNetlist` — the
  interactive netlister, which adapts ``schematicSymbol`` items into
  :class:`InstanceIR` and delegates;
- plugins (designPilot) and headless callers, which build
  :class:`InstanceIR` records directly from connectivity data — no
  schematic editor required.

Everything here is pure data in / text out: no Qt imports, no library
model access.  Directory-dependent work (include-file resolution and
``model``-definition scanning) takes explicit base paths.
"""

from __future__ import annotations

import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# Constants shared with the interactive netlister
# ---------------------------------------------------------------------------

# Strip dangling parameter assignments (e.g. `` w =`` or ``w=@w``) left
# after token substitution.  ``$`` is allowed as a parameter-name prefix so
# VACASK system parameters such as ``$mfactor`` are cleaned up as well.
PARAM_RE = re.compile(r'\s+\$?\w+\s*=\s*@\w+|\s+\$?\w+\s*=(?=\s|$)')

# Leftover substitution tokens after cleanup.
LEFTOVER_TOKEN_RE = re.compile(r'[@%]\w+')

# ``<``/``>`` are VACASK operators — bus-tap names need quoting.
_NEEDS_QUOTE_RE = re.compile(r'[<>]')

# Regexes for scanning included files for ``model`` statements so locally
# generated model lines can be suppressed when an included file already
# defines the same model name.
MODEL_STMT_RE = re.compile(r'^\s*\.?model\s+([^\s(=]+)', re.IGNORECASE)
INCLUDE_STMT_RE = re.compile(r'^\s*\.?include\s+"([^"]+)"', re.IGNORECASE)
# ``section=``/``lang=`` options are searched in the text following the
# quoted filename so they are recognised in either order
# (``include "f" lang=ngspice section=tt``).
INCLUDE_SECTION_RE = re.compile(
    r'\bsection\s*=\s*"?([\w.\-]+)"?', re.IGNORECASE)
# ``lang=`` marks a foreign-format (SPICE/Spectre) include: those are
# handed to the bundled foreign parser, which registers SPICE ``.model``
# names with an ``m_`` prefix — scanning them as native ``model``
# statements would collect names VACASK never defines.
FOREIGN_INCLUDE_RE = re.compile(r'\blang\s*=', re.IGNORECASE)
SECTION_RE = re.compile(r'^\s*section\s+([^\s=]+)', re.IGNORECASE)
ENDSECTION_RE = re.compile(r'^\s*endsection\b', re.IGNORECASE)
MAX_INCLUDE_DEPTH = 8

# VACASK's numeric lexer accepts ``<number><SI prefix><optional unit>``
# (``1mV``, ``1MHz``, ``100uA``) but rejects a bare unit with no SI
# prefix (``1V``, ``1Hz``, ``1A``) — the suffix letters turn into an
# identifier and the parse dies with "unexpected identifier, expecting =".
# ``meg``/``mil`` must precede ``m`` for the longest-prefix match.
_SI_PREFIXES = ("meg", "mil", "m", "u", "n", "p", "f", "a",
                "k", "K", "M", "x", "X", "G", "T")
_NUM_UNIT_RE = re.compile(
    r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-zA-Z_]+)\s*$")


def vacask_literal(value) -> str:
    """Normalize a numeric literal for the VACASK lexer.

    ``1.2V`` → ``1.2`` (bare unit dropped), ``1MHz`` → ``1M`` (prefix kept,
    unit dropped), everything else passes through.  Non-matching strings
    (expressions, names) are returned unchanged.
    """
    text = str(value).strip()
    match = _NUM_UNIT_RE.match(text)
    if not match:
        return text
    number, suffix = match.groups()
    for prefix in _SI_PREFIXES:
        if suffix.startswith(prefix):
            return f"{number}{prefix}"
    return number


# ---------------------------------------------------------------------------
# Identifier / array helpers
# ---------------------------------------------------------------------------

def quote_id(name: str) -> str:
    """Quote an identifier with single quotes if it contains ``<`` or ``>``.

    VACASK treats ``<`` and ``>`` as operators, so net/instance names that
    use angle-bracket bus notation must be wrapped in single quotes to form
    a valid quoted identifier.  Plain identifiers are returned unchanged.

    Any embedded single quotes in *name* are escaped as ``''`` per VACASK
    quoted-identifier rules.
    """
    if '<' in name or '>' in name:
        return "'" + name.replace("'", "''") + "'"
    return name


def parse_array_notation(name: str) -> tuple[str, tuple[int, int]]:
    """Parse ``'name<0:5>'``/``'name<0>'`` into ``(base, (start, end))``.

    Scalar names return ``(name, (-1, -1))``.
    """
    if '<' not in name or '>' not in name:
        return name, (-1, -1)
    base_name = name.split('<')[0]
    index_range = name.split('<')[1].split('>')[0]
    if ':' not in index_range:
        single = int(index_range)
        return base_name, (single, single)
    start, end = map(int, index_range.split(':'))
    return base_name, (start, end)


def expand_pin_names(pin_names: Iterable[str]) -> str:
    """Expand pin-name array notation into quoted pins (``a<0:1>`` → ``a<0> a<1>``)."""
    out: list[str] = []
    for pin_name in pin_names:
        base, pair = parse_array_notation(pin_name)
        if pair[0] == pair[1] == -1:
            out.append(quote_id(base))
        else:
            step = 1 if pair[1] >= pair[0] else -1
            for i in range(pair[0], pair[1] + step, step):
                out.append(quote_id(f'{base}<{i}>'))
    return ' '.join(out)


def model_name(model_line: str) -> str:
    """Model name declared by a ``model`` statement line (second token)."""
    tokens = model_line.split()
    return tokens[1] if len(tokens) > 1 else model_line.strip()


def nlp_label_default(definition: str) -> str:
    """Default value of an NLP ``[@name:format:default]`` definition, or ""."""
    text = str(definition or "")
    if not text.startswith("[@"):
        return ""
    end = text.find("]")
    if end == -1:
        return ""
    parts = text[1:end].split(":")
    if len(parts) < 3:
        return ""
    default = parts[2].strip()
    if "=" in default:
        default = default.split("=", 1)[1].strip()
    return default


def resolve_label_values(label_defs: dict[str, str],
                         instance_values: dict[str, str],
                         stored_values: dict[str, str] | None = None,
                         typed_defaults: dict[str, str] | None = None,
                         ) -> dict[str, str]:
    """Resolve ``{@label: effective_value}`` for one instance.

    ``label_defs`` maps label name (with ``@``) to its NLP definition
    string.  Precedence: explicit ``instance_values`` (``@``-tolerant,
    case-insensitive) → ``stored_values`` (values persisted on the symbol
    instance) → typed ``paramDefs`` defaults (already resolved, e.g. via
    ``params.applyDefaults``) → NLP definition default.
    """
    inst = {str(k).lstrip("@").lower(): str(v)
            for k, v in (instance_values or {}).items()}
    stored = {str(k).lstrip("@").lower(): str(v)
              for k, v in (stored_values or {}).items()}
    defaults = {str(k).lstrip("@").lower(): str(v)
                for k, v in (typed_defaults or {}).items()}
    out: dict[str, str] = {}
    for name, definition in (label_defs or {}).items():
        bare = str(name).lstrip("@")
        if not bare:
            continue
        value = inst.get(bare.lower())
        if value is None or value == "":
            value = stored.get(bare.lower())
        if value is None or value == "":
            value = defaults.get(bare.lower())
        if value is None or value == "":
            value = nlp_label_default(definition)
        out[f"@{bare}"] = str(value) if value is not None else ""
    return out


# ---------------------------------------------------------------------------
# Instance intermediate representation
# ---------------------------------------------------------------------------

@dataclass
class InstanceIR:
    """Everything needed to format one instance's netlist line(s).

    - ``name``: instance name (may carry array notation ``I5<0:3>``).
    - ``attrs``: symbol attributes (``VacaskNetlistLine`` template,
      ``pinOrder``, ``lvsPinOrder``, ``modelName``, …).
    - ``labels``: ``{labelName_with_@: resolved_value}`` — callers resolve
      instance overrides + typed/legacy defaults before constructing this
      (see :func:`resolve_label_values`).
    - ``pinNets``: ordered ``(pinName, netName)`` pairs in the instance's
      *netlist* pin order (already resolved by the caller).
    - ``exprNets``: resolved implicit-terminal nets appended after the
      pin nets (net-expression terminals of a subcircuit instance).
    """
    name: str
    attrs: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)
    pinNets: list = field(default_factory=list)   # [(pinName, netName)]
    exprNets: list = field(default_factory=list)


class _GlobalTracker:
    """Collect ``ground``/``global`` directives while stripping ``!``."""

    def __init__(self):
        self.groundNets: set[str] = set()
        self.globalNets: set[str] = set()

    def process(self, net_name: str) -> str:
        """Strip trailing ``!`` from global nets; register directives."""
        if "gnd!" in net_name:
            self.groundNets.add("gnd")
            return net_name.replace("gnd!", "gnd")
        if net_name.endswith("!"):
            global_name = net_name[:-1]
            self.globalNets.add(global_name)
            return global_name
        return net_name


def format_instance_lines(
        ir: InstanceIR,
        line_key: str,
        globals_tracker: _GlobalTracker | None = None,
        warn: Callable[[str], None] | None = None,
        strict_tokens: bool = False) -> list[str]:
    """Format one instance into VACASK line(s).

    Mirrors the interactive netlister's ``_createNetlistLine``: array
    notation (vector preservation when every pin net is an equal-sized
    vector), single-pass whole-token substitution, ``_PARAM_RE`` cleanup,
    ``{}`` brace stripping, and ``!``-global processing.

    ``warn`` receives a message for recoverable anomalies (missing
    template, net-width mismatch).  ``strict_tokens`` additionally reports
    unresolved ``@x``/``%x`` tokens left in the final line — headless
    callers should treat them as errors; the interactive path historically
    leaves them for downstream handling.
    """
    tracker = globals_tracker or _GlobalTracker()

    def _warn(msg: str) -> None:
        if warn is not None:
            warn(msg)

    attrs = ir.attrs or {}
    template = str(attrs.get(line_key, "") or "")
    if not template.strip():
        _warn(f"{ir.name}: symbol has no {line_key} attribute")
        return []

    # The interactive netlister bails when no @instName label exists —
    # without it the template's instance token cannot be substituted.
    if not any(str(k).lstrip("@").lower() == "instname"
               for k in (ir.labels or {})):
        _warn(f"{ir.name}: instance has no @instName label")
        return []

    base_inst_name, array_tuple = parse_array_notation(ir.name)
    array_step = -1 if array_tuple[0] > array_tuple[1] else 1
    array_size = abs(array_tuple[0] - array_tuple[1]) + 1

    # Single-pass token substitution over the template. Only whole
    # "@name"/"%name" tokens match, so "@w" never substitutes inside
    # "@wfeed"; unresolved tokens are left for PARAM_RE cleanup.
    token_map = {f"%{k}": v for k, v in attrs.items()}
    token_map.update({k: v for k, v in (ir.labels or {}).items()})
    inst_name_token = next(
        (k for k in token_map if k.lower() == "@instname"), "@instName")
    token_pattern = re.compile("(?:" + "|".join(sorted(
        (re.escape(tok)
         for tok in (*token_map, inst_name_token, "%pinOrder",
                     "%lvsPinOrder")),
        key=len, reverse=True)) + r")(?!\w)")

    def _create_line(instance_name: str, nets_list: str,
                     lvs_nets_list: str) -> str:
        def _sub(match):
            token = match.group(0)
            if token == inst_name_token:
                return instance_name
            if token == "%pinOrder":
                return nets_list
            if token == "%lvsPinOrder":
                return lvs_nets_list
            return token_map.get(token, token)
        return token_pattern.sub(_sub, template.strip())

    def _process_line(line: str) -> str:
        line = PARAM_RE.sub('', line)
        line = line.replace('{', '').replace('}', '')
        return line

    def _expand_net(net_name: str) -> list[str]:
        base, pair = parse_array_notation(net_name)
        if pair[0] == pair[1] == -1:
            return [quote_id(base)]
        step = 1 if pair[1] >= pair[0] else -1
        return [quote_id(f'{base}<{i}>')
                for i in range(pair[0], pair[1] + step, step)]

    def _vector_info(net_name: str):
        base, pair = parse_array_notation(net_name)
        return (base, None if pair[0] == pair[1] == -1 else pair)

    # Process net names: strip ! from global nets and track them.
    pin_nets = [tracker.process(net) for _pin, net in ir.pinNets]
    expr_nets = [quote_id(tracker.process(net)) for net in ir.exprNets]

    net_vector_infos = [_vector_info(n) for n in pin_nets]

    # 'lvsPinOrder' reorders the same pin nets for the LVS line when the
    # extracted terminal order differs from pinOrder.
    pin_by_name = dict(ir.pinNets)
    lvs_pin_order = attrs.get("lvsPinOrder")
    lvs_pin_nets = pin_nets
    if lvs_pin_order:
        lvs_pin_nets = [
            tracker.process(pin_by_name[p])
            for p in (tok.strip() for tok in str(lvs_pin_order).split(","))
            if p in pin_by_name]
    lvs_vector_infos = [_vector_info(n) for n in lvs_pin_nets]

    # Preserve vector notation only when every net is a scalar-free vector
    # of exactly the instance's dimension.
    can_use_vector = array_size > 1
    if can_use_vector:
        for _base, pair in net_vector_infos:
            if pair is None or abs(pair[0] - pair[1]) + 1 != array_size:
                can_use_vector = False
                break

    lines: list[str] = []
    if can_use_vector:
        vector_nets = " ".join([
            quote_id(f"{base}<{pair[0]}:{pair[1]}>") if pair else base
            for base, pair in net_vector_infos] + expr_nets)
        vector_lvs = " ".join([
            quote_id(f"{base}<{pair[0]}:{pair[1]}>") if pair else base
            for base, pair in lvs_vector_infos] + expr_nets)
        vector_name = quote_id(
            f"{base_inst_name}<{array_tuple[0]}:{array_tuple[1]}>")
        lines.append(_process_line(
            _create_line(vector_name, vector_nets, vector_lvs)))
    else:
        expanded = [_expand_net(n) for n in pin_nets]
        expanded_lvs = [_expand_net(n) for n in lvs_pin_nets]

        def _select(nets_list, index):
            picked = []
            for nets in nets_list:
                if len(nets) == array_size:
                    picked.append(nets[index])
                elif len(nets) == 1:
                    picked.append(nets[0])
                else:
                    _warn(
                        f"net connection width mismatch for {ir.name}: "
                        f"expected 1 or {array_size}, got {len(nets)}. "
                        "Falling back to element 0.")
                    picked.append(nets[0])
            return picked

        if array_size == 1:
            flat_nets = " ".join(
                [nets[0] for nets in expanded] + expr_nets)
            flat_lvs = " ".join(
                [nets[0] for nets in expanded_lvs] + expr_nets)
            lines.append(_process_line(
                _create_line(base_inst_name, flat_nets, flat_lvs)))
        else:
            for j, i in enumerate(
                    range(array_tuple[0], array_tuple[1] + array_step,
                          array_step)):
                nets = " ".join(_select(expanded, j) + expr_nets)
                lvs = " ".join(_select(expanded_lvs, j) + expr_nets)
                lines.append(_process_line(_create_line(
                    quote_id(f"{base_inst_name}<{i}>"), nets, lvs)))

    if strict_tokens:
        bad = [ln for ln in lines if LEFTOVER_TOKEN_RE.search(ln)]
        if bad:
            _warn(f"{ir.name}: unresolved token(s) "
                  f"{sorted(set(LEFTOVER_TOKEN_RE.findall(' '.join(bad))))}")
            return []
    return lines


# ---------------------------------------------------------------------------
# Include-file model scanning and deck collection
# ---------------------------------------------------------------------------

def resolve_include_file(name: str, *bases: pathlib.Path
                         ) -> pathlib.Path | None:
    """Resolve an ``include`` file name to a readable local path.

    Relative names are tried against *bases*, then the current working
    directory, then the directories on ``SIM_INCLUDE_PATH``.
    """
    path = pathlib.Path(name)
    if path.is_absolute():
        return path if path.is_file() else None
    search = [*bases, pathlib.Path.cwd()]
    search.extend(
        pathlib.Path(entry)
        for entry in os.environ.get("SIM_INCLUDE_PATH", "").split(
            os.pathsep)
        if entry)
    for base in search:
        candidate = base / path
        if candidate.is_file():
            return candidate
    return None


def scan_include_file(path: pathlib.Path, requested_sections: frozenset,
                      model_names: set, visited: set, depth: int = 0,
                      *extra_bases: pathlib.Path) -> None:
    """Collect ``model`` names defined in *path* into *model_names*.

    ``section``/``endsection`` blocks count only when named by
    *requested_sections*; nested ``include`` directives are followed up to
    ``MAX_INCLUDE_DEPTH``; ``lang=`` foreign includes are skipped.
    """
    if depth > MAX_INCLUDE_DEPTH:
        return
    try:
        resolved = path.resolve()
    except OSError:
        return
    key = (resolved, requested_sections)
    if key in visited or not resolved.is_file():
        return
    visited.add(key)
    try:
        lines = resolved.read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    active_section: str | None = None
    for raw in lines:
        line = raw.split("//", 1)[0]
        if not line.strip() or line.lstrip().startswith(("*", "#")):
            continue
        section_match = SECTION_RE.match(line)
        if section_match:
            active_section = section_match.group(1)
            continue
        if ENDSECTION_RE.match(line):
            if (active_section is not None
                    and active_section in requested_sections):
                # A section= include reads only the first matching
                # section — VACASK returns to the including file.
                break
            active_section = None
            continue
        if active_section is None:
            if requested_sections:
                continue
        elif active_section not in requested_sections:
            continue
        model_match = MODEL_STMT_RE.match(line)
        if model_match:
            model_names.add(model_match.group(1))
            continue
        include_match = INCLUDE_STMT_RE.match(line)
        if include_match:
            tail = line[include_match.end():]
            if FOREIGN_INCLUDE_RE.search(tail):
                continue
            nested = resolve_include_file(
                include_match.group(1), resolved.parent, *extra_bases)
            if nested is not None:
                section_opt = INCLUDE_SECTION_RE.search(tail)
                nested_sections = (frozenset({section_opt.group(1)})
                                   if section_opt else frozenset())
                scan_include_file(nested, nested_sections, model_names,
                                  visited, depth + 1, *extra_bases)


class DeckCollector:
    """Directive accumulator for one VACASK deck.

    Collects ground/global nets, library includes (with ``section=``
    options), file includes, OSDI/custom ``load`` lines and ``model``
    lines; deduplicates models on their declared name and suppresses
    models already defined inside a resolvable include file.
    """

    def __init__(self, globals_tracker: _GlobalTracker | None = None):
        self.globals = globals_tracker or _GlobalTracker()
        self.includeLibLines: set[str] = set()
        self.includeLines: set[str] = set()
        self.vahdlLines: set[str] = set()
        self.osdiLoadLines: set[str] = set()
        self.loadLines: set[str] = set()
        self.modelLines: set[str] = set()
        self._model_defs: dict[str, str] = {}
        self._include_file_paths: set[pathlib.Path] = set()

    # -- net directives ---------------------------------------------------
    def process_global_net(self, net_name: str) -> str:
        return self.globals.process(net_name)

    # -- attr-driven directives ---------------------------------------------
    def collect_symbol_directives(self, attrs: dict,
                                  cell_dir: pathlib.Path | None = None,
                                  skip_load_file: bool = False,
                                  base_dirs: tuple = ()) -> None:
        """Collect model/load/include directives from symbol attributes.

        ``VacaskIncludeLib`` → ``include`` (+ section option, plus model
        scan registration); ``VacaskModelLine`` → ``model`` (only when no
        include-lib); ``VacaskIncludeFile`` → ``include`` resolved against
        *cell_dir*; ``VacaskLoadFile`` → bare filename to ``osdiLoadLines``
        or path to ``loadLines``.
        """
        attrs = attrs or {}
        include_lib = str(attrs.get("VacaskIncludeLib", "") or "")
        if include_lib:
            include_lib = include_lib.strip().replace("\\", "/")
            self.includeLibLines.add(f'include "{include_lib}"')
            lib_file = include_lib
            section_opt = INCLUDE_SECTION_RE.search(include_lib)
            if section_opt:
                lib_file = include_lib[:section_opt.start()].strip()
            lib_path = resolve_include_file(lib_file, *base_dirs)
            if lib_path is not None:
                self._include_file_paths.add(lib_path)
        if not include_lib:
            model_line = str(attrs.get("VacaskModelLine", "") or "")
            if model_line:
                self.add_model_line(model_line.strip())
        include_file = str(attrs.get("VacaskIncludeFile", "") or "")
        if include_file and cell_dir is not None:
            path = pathlib.Path(cell_dir) / include_file.strip().replace(
                "\\", "/")
            self.add_include_file(path)
        if not skip_load_file:
            load_file = str(attrs.get("VacaskLoadFile", "") or "")
            if load_file:
                load_file = load_file.strip().replace("\\", "/")
                if "/" in load_file:
                    self.loadLines.add(f'load "{load_file}"')
                else:
                    self.osdiLoadLines.add(f'load "{load_file}"')

    # -- explicit registrations ---------------------------------------------
    def add_model_line(self, model_line: str,
                       warn: Callable[[str], None] | None = None) -> None:
        """Register a ``model`` statement, deduplicating on the model name."""
        for raw in model_line.splitlines():
            normalized = " ".join(raw.split())
            if not normalized:
                continue
            name = model_name(normalized)
            previous = self._model_defs.get(name)
            if previous is not None:
                if previous != normalized and warn is not None:
                    warn(f"Duplicate model definition for '{name}' "
                         f"ignored: '{normalized}' (keeping '{previous}')")
                continue
            self._model_defs[name] = normalized
            self.modelLines.add(normalized)

    def add_include_file(self, file_path: pathlib.Path) -> None:
        """Register an ``include`` directive for a local file (canonicalised)."""
        resolved = file_path.resolve()
        self.includeLines.add(f'include "{resolved.as_posix()}"')
        self._include_file_paths.add(resolved)

    def suppress_include_defined_models(
            self, info: Callable[[str], None] | None = None,
            base_dirs: tuple = ()) -> None:
        """Drop model lines whose model is already defined in an include."""
        if not self.modelLines or not self._include_file_paths:
            return
        include_model_names: set[str] = set()
        visited: set[tuple[pathlib.Path, frozenset]] = set()
        for path in self._include_file_paths:
            scan_include_file(path, frozenset(), include_model_names,
                              visited, 0, *base_dirs)
        if not include_model_names:
            return
        suppressed = {line for line in self.modelLines
                      if model_name(line) in include_model_names}
        for line in sorted(suppressed):
            if info is not None:
                info(f"Model '{model_name(line)}' is already defined in an "
                     f"included file — dropping local model line '{line}'")
            self._model_defs.pop(model_name(line), None)
        self.modelLines -= suppressed


def render_netlist(header_text: str, body_lines: list[str],
                   collector: DeckCollector,
                   subckt_defs: list[str] | None = None) -> str:
    """Assemble a complete VACASK netlist string.

    Order matches the interactive netlister: header, ``global``, ``ground``,
    include-library lines, OSDI + custom ``load`` lines, ``model`` lines,
    the instance body, ``subckt`` definitions, then trailing file
    includes/Verilog-A lines.
    """
    parts: list[str] = [header_text]
    global_nets = " ".join(
        sorted(quote_id(n) for n in collector.globals.globalNets))
    if global_nets:
        parts.append(f"global {global_nets}\n\n")
    ground_nets = " ".join(
        sorted(quote_id(n) for n in collector.globals.groundNets))
    parts.append(f"ground 0 {ground_nets}\n\n" if ground_nets
                 else "ground 0\n\n")
    for line in sorted(collector.includeLibLines):
        parts.append(f"{line}\n")
    if collector.includeLibLines:
        parts.append("\n")
    for line in sorted(collector.osdiLoadLines):
        parts.append(f"{line}\n")
    for line in sorted(collector.loadLines):
        parts.append(f"{line}\n")
    if collector.osdiLoadLines or collector.loadLines:
        parts.append("\n")
    for line in sorted(collector.modelLines):
        parts.append(f"{line}\n")
    if collector.modelLines:
        parts.append("\n")
    parts.extend(body_lines)
    if subckt_defs:
        parts.append("\n// Subcircuit Definitions\n")
        parts.extend(subckt_defs)
    for line in collector.includeLines:
        parts.append(f"{line}\n")
    for line in collector.vahdlLines:
        parts.append(f"{line}\n")
    return "".join(parts)
