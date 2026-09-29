"""Tests fuer pipeline/analysis/whitepaper/wp_common.py: Zahlenformatierung,

Regionenreihenfolge/-codes, Bandaufloesung per Name und die Markdown-/CSV-
Schreiber. Schnell, ohne echtes TIF.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.analysis.whitepaper import wp_common as wc

NBSP = " "


# ---------------------------------------------------------------------------
# Deutsche Zahlenformatierung
# ---------------------------------------------------------------------------

def test_de_num_decimal_comma_and_nbsp_thousands_two_decimals():
    assert wc.de_num(1234567.89, 2) == f"1{NBSP}234{NBSP}567,89"


def test_de_num_one_decimal():
    assert wc.de_num(1234.5, 1) == f"1{NBSP}234,5"


def test_de_num_negative_and_nan():
    assert wc.de_num(-42.0, 1) == "-42,0"
    assert wc.de_num(float("nan"), 1) == "–"


def test_de_num_zero_decimals_has_no_trailing_comma():
    assert wc.de_num(1234, 0) == f"1{NBSP}234"


def test_de_int_thousands_separator():
    assert wc.de_int(1234567) == f"1{NBSP}234{NBSP}567"
    assert wc.de_int(0) == "0"


# ---------------------------------------------------------------------------
# Regionenreihenfolge und -codes
# ---------------------------------------------------------------------------

def test_region_order_is_fixed_b_k_n_o_s_st_t_v_w():
    assert wc.REGION_ORDER == ["B", "K", "N", "O", "S", "ST", "T", "V", "W"]


def test_region_order_at_appends_at():
    assert wc.REGION_ORDER_AT == wc.REGION_ORDER + ["AT"]


def test_full_names_cover_all_codes_including_at():
    assert wc.FULL_NAMES["B"] == "Burgenland"
    assert wc.FULL_NAMES["W"] == "Wien"
    assert wc.FULL_NAMES["AT"] == "Österreich"
    assert set(wc.FULL_NAMES) == set(wc.REGION_ORDER_AT)


def test_state_codes_has_exactly_nine_entries():
    assert len(wc.STATE_CODES) == 9
    assert len(set(wc.STATE_CODES.values())) == 9


def test_label_mensch_natur_is_the_canonical_spelling():
    assert wc.LABEL_MENSCH_NATUR == "Mensch & Natur"


def test_pair_labels_follow_mensch_natur_geografie_order():
    assert wc.LABEL_MENSCH_NATUR == "Mensch & Natur"
    assert wc.LABEL_MENSCH_GEOGRAFIE == "Mensch & Geografie"
    assert wc.LABEL_NATUR_GEOGRAFIE == "Natur & Geografie"


# ---------------------------------------------------------------------------
# Bandaufloesung ausschliesslich per Name
# ---------------------------------------------------------------------------

def _manifest(names):
    return {"bands": [{"name": n, "index": i + 1} for i, n in enumerate(names)]}


def test_band_index_resolves_by_name():
    manifest = _manifest(["all_exclusions", "exclusion_human"])
    assert wc.band_index(manifest, "exclusion_human") == 2
    assert wc.band_index(manifest, "all_exclusions") == 1


def test_band_index_missing_name_raises_clear_error_listing_available():
    manifest = _manifest(["all_exclusions", "exclusion_human"])
    with pytest.raises(KeyError, match="exclusion_nature.*nicht im Manifest"):
        wc.band_index(manifest, "exclusion_nature")
    # Fehlermeldung listet die tatsaechlich vorhandenen Baender auf.
    with pytest.raises(KeyError, match="all_exclusions, exclusion_human"):
        wc.band_index(manifest, "exclusion_nature")


def test_family_member_indices_requires_familie_and_category_match():
    manifest = {
        "bands": [
            {"name": "a", "index": 1, "familie": "verkehr", "category": "Mensch"},
            {"name": "b", "index": 2, "familie": "verkehr", "category": "Natur"},
            {"name": "c", "index": 3, "familie": "luftfahrt", "category": "Mensch"},
        ]
    }
    assert wc.family_member_indices(manifest, "verkehr", "Mensch") == [1]


def test_family_member_indices_raises_if_no_match():
    manifest = {"bands": [{"name": "a", "index": 1, "familie": "verkehr", "category": "Mensch"}]}
    with pytest.raises(KeyError, match="schutzgebiet"):
        wc.family_member_indices(manifest, "schutzgebiet", "Natur")


def test_zone_bands_for_categories_filters_and_sorts_by_index():
    manifest = {
        "bands": [
            {"name": "z3", "index": 3, "stufe": "zone", "category": "Geografie"},
            {"name": "z1", "index": 1, "stufe": "zone", "category": "Mensch"},
            {"name": "not_zone", "index": 2, "stufe": "kategorie", "category": "Mensch"},
        ]
    }
    bands = wc.zone_bands_for_categories(manifest, {"Mensch", "Natur", "Geografie"})
    assert [b["name"] for b in bands] == ["z1", "z3"]


# ---------------------------------------------------------------------------
# Markdown-/CSV-Schreiber: deterministische Ausgabe fuer feste Eingaben
# ---------------------------------------------------------------------------

def test_write_markdown_table_is_byte_deterministic(tmp_path):
    out1 = tmp_path / "a.md"
    out2 = tmp_path / "b.md"
    for out in (out1, out2):
        wc.write_markdown_table(
            out, "Titel", ["Spalte 1", "Spalte 2"],
            [["1,0", "2,0"], ["3,0", "4,0"]],
            source_line="Testquelle",
            intro_lines=["Einleitung."],
        )
    assert out1.read_bytes() == out2.read_bytes()
    text = out1.read_text(encoding="utf-8")
    assert text == (
        "# Titel\n\nEinleitung.\n\n"
        "| Spalte 1 | Spalte 2 |\n|---|---|\n"
        "| 1,0 | 2,0 |\n| 3,0 | 4,0 |\n\n"
        "*Quelle: Testquelle*\n"
    )


def test_write_csv_table_has_comment_lines_and_is_byte_deterministic(tmp_path):
    out1 = tmp_path / "a.csv"
    out2 = tmp_path / "b.csv"
    for out in (out1, out2):
        wc.write_csv_table(
            out, ["k", "v"], [["x", 1], ["y", 2]],
            comment_lines=["Quelle: Test"],
        )
    assert out1.read_bytes() == out2.read_bytes()
    lines = out1.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Quelle: Test"
    assert lines[1] == "k,v"
    assert lines[2] == "x,1"
    assert lines[3] == "y,2"
