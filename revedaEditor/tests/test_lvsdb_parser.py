# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

import os
import tempfile

import pytest

from revedaEditor.fileio import importlvsdb as ilvs
from revedaEditor.fileio.importlvsdb import (
    LVSDBParser,
    classifyStatusToken,
    isStatusToken,
    STATUS_MATCH,
    STATUS_MISMATCH,
    STATUS_NOMATCH,
    STATUS_WARNING,
    STATUS_SKIPPED,
    STATUS_ABSENT,
)


# A minimal but complete LVS DB: version (V), description (B), layout (J),
# reference/schematic (H) and xref (Z) sections. Hand-authored from the KLayout
# format reference (no sample fixture ships in the repo). Uses relative
# coordinates for the rectangles and a µ (non-ASCII) cell name to exercise the
# UTF-8 read path. Line endings are substituted per-test for the CRLF/LF cases.
MINIMAL_LVSDB = "\n".join([
    "#%lvsdb-klayout",
    "V(1.0)",
    "B('description')",
    "J(",
    " U(0.001)",
    " L(1 '1/0')",
    " X(invµ",
    "  R((0 0) (100 200))",
    "  N(1 I('VDD') R(1 (0 0) (10 20)))",
    "  N(2 I('VSS') R(1 (30 0) (10 20)))",
    "  D(1 nmos Y(5 5) E(W 1.0) E(L 0.13) T(G 1) T(D 2))",
    " )",
    ")",
    "H(",
    " X(invµ",
    "  N(1 I('VDD'))",
    "  N(2 I('VSS'))",
    "  D(1 nmos I('M0') E(W 1.0) E(L 0.13) T(G 1) T(D 2))",
    " )",
    ")",
    "Z(",
    " X(invµ invµ 1",
    "  Z(N(1 1 1) N(2 2 1) P(1 1 1) D(1 1 1))",
    " )",
    ")",
    "",
])


def _writeLvsdb(content: str, newline: str, encoding: str = "utf-8") -> str:
    """Write *content* to a temp .lvsdb with the given newline/encoding and
    return its path. The caller is responsible for deleting it."""
    body = content.replace("\n", newline)
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".lvsdb", delete=False, encoding=encoding, newline="")
    try:
        handle.write(body)
    finally:
        handle.close()
    return handle.name


def _parse(content: str, newline: str = "\n") -> LVSDBParser:
    path = _writeLvsdb(content, newline)
    try:
        parser = LVSDBParser(path)
        parser.load()
    finally:
        os.unlink(path)
    return parser


# ---------------------------------------------------------------------------
# A1/A2 — status-token classification (the core bug)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "token, expected_tier, is_token, is_hard_mismatch",
    [
        ("0", STATUS_MISMATCH, True, True),    # mismatch -> hard
        ("1", STATUS_MATCH, True, False),      # match
        ("X", STATUS_NOMATCH, True, True),     # nomatch -> hard
        ("W", STATUS_WARNING, True, False),    # warning -> NOT hard
        ("S", STATUS_SKIPPED, True, False),    # skipped -> NOT hard
        (None, STATUS_ABSENT, False, False),   # absent (with both refs present)
    ],
)
def test_status_token_classification(token, expected_tier, is_token,
                                     is_hard_mismatch):
    """Every documented status token maps to the right tier, and only
    '0'/'X' count as hard mismatches when both sides are present."""
    assert classifyStatusToken(token) == expected_tier
    assert isStatusToken(token) is is_token

    # Both sides present so the absent case is NOT a mismatch on its own;
    # this isolates the tier's contribution to the mismatch verdict.
    item = {
        "layout_net": "1",
        "schem_net": "1",
        "status": token,
        "status_tier": expected_tier,
    }
    assert LVSDBParser._is_mismatch(item) is is_hard_mismatch


def test_absent_status_with_missing_side_is_mismatch():
    """An absent [status] is a mismatch only when one side has no counterpart
    (a genuinely unmatched pair)."""
    unmatched = {"layout_net": "1", "schem_net": "", "status_tier": STATUS_ABSENT}
    matched = {"layout_net": "1", "schem_net": "2", "status_tier": STATUS_ABSENT}
    assert LVSDBParser._is_mismatch(unmatched) is True
    assert LVSDBParser._is_mismatch(matched) is False


def test_unknown_token_classifies_as_absent():
    """A non-documented token (e.g. a trailing message element) is treated as
    status-absent rather than guessed into a mismatch tier."""
    assert classifyStatusToken("Z") == STATUS_ABSENT
    assert classifyStatusToken("") == STATUS_ABSENT
    assert isStatusToken("Z") is False


def test_warning_and_skipped_not_counted_as_mismatches_in_crossref():
    """W/S device pairs are surfaced as warning/skipped tiers and never counted
    as device mismatches; 0/X are. Built via a crafted xref so the counting in
    get_all_crossrefs_formatted is exercised directly."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))) )",
        "H( X(top) )",
        "Z(",
        " X(top top 0",
        "  Z(",
        "   D(1 1 X)",   # nomatch  -> hard
        "   D(2 2 X)",   # nomatch  -> hard
        "   D(3 3 W)",   # warning  -> not counted
        "   D(4 4 S)",   # skipped  -> not counted
        "   D(5 5 1)",   # match    -> not counted
        "  )",
        " )",
        ")",
        "",
    ])
    parser = _parse(lvsdb)
    formatted = parser.get_all_crossrefs_formatted()
    assert len(formatted) == 1
    row = formatted[0]
    # Both 'X' (nomatch) device pairs are hard mismatches; W/S/1 are not.
    assert row["device_mismatches"] == 2
    assert row["warning_count"] == 1
    assert row["skipped_count"] == 1
    # Status '0' on the circuit pair means not equivalent.
    assert row["equivalent"] is False
    assert row["status_tier"] == STATUS_MISMATCH


def test_plain_mismatch_device_is_counted():
    """A plain '0' (mismatch) device pair is a hard mismatch and is counted."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))) )",
        "H( X(top) )",
        "Z( X(top top 0 Z(D(1 1 0))) )",
        "",
    ])
    row = _parse(lvsdb).get_all_crossrefs_formatted()[0]
    assert row["device_mismatches"] == 1
    assert row["equivalent"] is False


def test_net_mismatches_counted_without_diagnostics_block():
    """When the optional L(...) diagnostics block is absent, net mismatches
    fall back to raw N(...) pairs with a hard-mismatch status — otherwise a
    failing cell would report 'no mismatches'."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))",
        "   N(1 I('VDD')) N(2 I('VSS')) N(3 I('$5'))) )",
        "H( X(top N(1 I('VDD')) N(2 I('VSS')) N(3 I('VSS')) N(4 I('NET0'))) )",
        "Z( X(top top X",
        "   Z(",
        "    N(1 1 1)",   # match
        "    N(3 4 0)",   # mismatch (no L diagnostics emitted)
        "    N(2 3 0)",   # mismatch
        "    P(1 1 1)",
        "    D(1 1 1)",
        "   )) )",
        "",
    ])
    row = _parse(lvsdb).get_all_crossrefs_formatted()[0]
    assert row["net_mismatches"] == 2
    assert row["equivalent"] is False
    assert row["status_tier"] == STATUS_NOMATCH


def test_internal_net_fallout_suppressed_when_devices_mismatch():
    """Without diagnostics, raw '0' pairs on anonymous '$' layout nets are
    treated as device/property fallout — not net mismatches — when device
    mismatches exist. Named-net fallout is still counted."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))",
        "   N(1 I('VDD')) N(2 I('$7')) N(3 I('$8'))",
        "   D(1 nmos Y(0 0) E(W 1.0))",
        "   D(2 nmos Y(0 0) E(W 1.0))) )",
        "H( X(top N(1 I('VDD')) N(2 I('NET0')) N(3 I('NET1'))",
        "   D(1 nmos I('M0') E(W 1.0)) D(2 nmos I('M1') E(W 2.0))) )",
        "Z( X(top top 0",
        "   Z(",
        "    N(1 1 1)",
        "    N(2 2 0)",   # internal '$7' fallout
        "    N(3 3 0)",   # internal '$8' fallout
        "    D(1 1 X)",    # explicit device nomatch -> hard mismatch
        "    D(2 2 X)",
        "   )) )",
        "",
    ])
    row = _parse(lvsdb).get_all_crossrefs_formatted()[0]
    assert row["device_mismatches"] == 2
    # All mismatched nets are anonymous '$' nets + device mismatches exist.
    assert row["net_mismatches"] == 0


def test_named_net_fallout_counted_when_devices_mismatch():
    """The internal-net suppression must not hide genuine named-net
    mismatches: a mismatched pair on a labeled layout net is counted even
    when device mismatches exist."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))",
        "   N(1 I('VDD')) N(2 I('OUT'))",
        "   D(1 nmos Y(0 0) E(W 1.0))) )",
        "H( X(top N(1 I('VDD')) N(2 I('OUT'))",
        "   D(1 nmos I('M0') E(W 1.0))) )",
        "Z( X(top top 0",
        "   Z(",
        "    N(1 1 1)",
        "    N(2 2 0)",   # named 'OUT' net mismatch
        "    D(1 1 X)",
        "   )) )",
        "",
    ])
    row = _parse(lvsdb).get_all_crossrefs_formatted()[0]
    assert row["device_mismatches"] == 1
    assert row["net_mismatches"] == 1


def test_circuit_status_absent_is_not_equivalent_but_distinguished():
    """When the circuit-pair [status] is omitted, equivalence is False (not a
    confirmed match) and the tier is recorded as absent, not mismatch."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))) )",
        "H( X(top) )",
        # No status token: item[2] is the inner Z(...) list, not a status.
        "Z( X(top top Z(N(1 1 1))) )",
        "",
    ])
    parser = _parse(lvsdb)
    xref = parser.get_crossref("top")
    assert xref is not None
    assert xref["status"] is None
    assert xref["status_tier"] == STATUS_ABSENT
    assert xref["equivalent"] is False
    # The inner mapping was still parsed (status absent must not eat the Z block).
    assert len(xref["mapping"]["nets"]) == 1


# ---------------------------------------------------------------------------
# A4 — encoding and newline handling (cross-platform)
# ---------------------------------------------------------------------------

def test_minimal_lvsdb_parses_end_to_end():
    """A minimal valid .lvsdb parses without error and yields the expected
    nets, device and crossref results."""
    parser = _parse(MINIMAL_LVSDB)

    assert parser.get_all_layout_cells() == ["invµ"]
    assert parser.get_all_schematic_cells() == ["invµ"]

    nets = parser.get_nets("invµ")
    assert [(n["net_id"], n["name"]) for n in nets] == [("1", "VDD"), ("2", "VSS")]
    # Relative-coordinate rect decode: bottom-left + top-right corners.
    assert nets[0]["shapes"][0]["bbox"] == [[0.0, 0.0], [10.0, 20.0]]
    assert nets[1]["shapes"][0]["bbox"] == [[30.0, 0.0], [40.0, 20.0]]

    devices = parser.get_layout_devices("invµ")
    assert len(devices) == 1
    assert devices[0]["type"] == "nmos"
    assert devices[0]["params"] == {"W": 1.0, "L": 0.13}

    xref = parser.get_crossref("invµ")
    assert xref["equivalent"] is True
    assert xref["status_tier"] == STATUS_MATCH

    row = parser.get_all_crossrefs_formatted()[0]
    assert row["net_mismatches"] == 0
    assert row["device_mismatches"] == 0
    assert row["equivalent"] is True


def test_crlf_and_lf_parse_identically():
    """The same minimal .lvsdb with \\r\\n and with \\n must parse identically;
    the tokenizer treats CR/LF uniformly on every OS."""
    lf = _parse(MINIMAL_LVSDB, newline="\n")
    crlf = _parse(MINIMAL_LVSDB, newline="\r\n")

    assert lf.get_all_layout_cells() == crlf.get_all_layout_cells()
    assert lf.get_all_crossrefs_formatted()[0]["equivalent"] == \
        crlf.get_all_crossrefs_formatted()[0]["equivalent"]

    lf_nets = [(n["net_id"], n["name"], n["shapes"][0]["bbox"])
               for n in lf.get_nets("invµ")]
    crlf_nets = [(n["net_id"], n["name"], n["shapes"][0]["bbox"])
                 for n in crlf.get_nets("invµ")]
    assert lf_nets == crlf_nets


def test_utf8_name_parses_and_would_fail_under_cp1252():
    """A non-ASCII (µ) cell name parses correctly with the explicit utf-8 read.

    The file bytes are valid UTF-8 but NOT valid cp1252 for this multibyte
    sequence; decoding as cp1252 (the old Windows platform default) would
    corrupt or raise. We assert the utf-8 path round-trips the name and that
    the bytes are indeed mis-decoded under cp1252, documenting the bug A4 fixes.
    """
    parser = _parse(MINIMAL_LVSDB)
    assert "invµ" in parser.get_all_layout_cells()

    # Prove the raw bytes decode differently under cp1252 vs utf-8.
    path = _writeLvsdb(MINIMAL_LVSDB, newline="\n")
    try:
        raw = open(path, "rb").read()
        assert "invµ".encode("utf-8") in raw
        # 'µ' is U+00B5 -> UTF-8 0xC2 0xB5. Under cp1252 those two bytes decode
        # to 'Â' + 'µ', so the name is corrupted (not equal to the utf-8 name).
        cp1252_text = raw.decode("cp1252")
        assert "invµ" not in cp1252_text
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# A5 — diagnostics: dropped records are counted/logged, not silently empty
# ---------------------------------------------------------------------------

def test_malformed_crossref_record_is_counted(caplog):
    """A structurally malformed circuit-pair is counted as a dropped record and
    logged, rather than silently yielding a clean, empty result."""
    lvsdb = "\n".join([
        "#%lvsdb-klayout",
        "J( U(1.0) X(top R((0 0) (10 10))) )",
        "H( X(top) )",
        # Second X has only one element -> malformed (needs >= 2).
        "Z( X(top top 1 Z(N(1 1 1))) X(onlyone) )",
        "",
    ])
    with caplog.at_level("WARNING"):
        parser = _parse(lvsdb)
    assert parser._dropped_records.get("crossrefs") == 1
    assert any("malformed" in rec.message for rec in caplog.records)


def test_bad_utf8_file_raises_and_logs(caplog):
    """A genuinely non-UTF-8 file raises UnicodeDecodeError (preserving the
    existing caller failure contract) and logs an error."""
    path = _writeLvsdb(MINIMAL_LVSDB, newline="\n", encoding="cp1252")
    # Overwrite with raw invalid-utf-8 bytes.
    with open(path, "wb") as handle:
        handle.write(b"#%lvsdb-klayout\nJ( U(1.0) X(bad\xff\xfe) )\n")
    try:
        parser = LVSDBParser(path)
        with caplog.at_level("ERROR"):
            with pytest.raises(UnicodeDecodeError):
                parser.load()
        assert any("Failed to read LVSDB" in rec.message
                   for rec in caplog.records)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# tokenizer: quoting / empty () / escaped quotes
# ---------------------------------------------------------------------------

def test_tokenizer_handles_quotes_and_empty_parens():
    parser = LVSDBParser("unused")
    tokens = list(parser.tokenize(r"""(A 'quoted val' "dq" () 'esc\'aped')"""))
    assert tokens[0] == "("
    assert "'quoted val'" in tokens
    assert '"dq"' in tokens
    assert tokens.count("(") == 2 and tokens.count(")") == 2
