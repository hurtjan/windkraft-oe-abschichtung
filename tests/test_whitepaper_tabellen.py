"""Tests fuer pipeline/analysis/whitepaper/tabellen.py: deterministische

Markdown-/CSV-Ausgabe fuer feste, handgebaute counts/prov-Eingaben (kein
Zaehlen-Lauf, kein echtes TIF).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.analysis.whitepaper import tabellen, wp_common as wc


def _fixed_counts() -> dict:
    region_cells = {c: 10 for c in wc.REGION_ORDER}
    values = {
        "exclusion_human": 2,
        "nur_mensch": 1,
        "exclusion_nature": 3,
        "nur_natur": 2,
        "exclusion_geography": 1,
        "nur_geografie": 1,
        "all_exclusions": 5,
        "available_cleaned_min_10ha": 4,
        "mensch_natur": 1,
        "mensch_geografie": 1,
        "natur_geografie": 1,
        "alle_drei": 1,
        "frei": 2,
    }
    counters = {k: {c: v for c in wc.REGION_ORDER} for k, v in values.items()}
    at_counts = {k: sum(counters[k].values()) for k in values}
    return {
        "region_cells": region_cells,
        "at_cells": 90,
        "counters": counters,
        "at_counts": at_counts,
        "pixel_area_m2": 100.0,
    }


def _fixed_prov() -> dict:
    return {
        "tif_sha256_short": "deadbeefcafe",
        "reference_area_km2": 12.34,
        "tif_date": "2020-01-01",
    }


def test_build_t1_is_byte_deterministic_across_runs(tmp_path):
    counts, prov = _fixed_counts(), _fixed_prov()
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    tabellen.build_t1(counts, prov, out1)
    tabellen.build_t1(counts, prov, out2)

    for name in ("T1_haupttabelle.md", "T1_haupttabelle.csv"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes()


def test_build_t1_formats_percentages_and_header_correctly(tmp_path):
    counts, prov = _fixed_counts(), _fixed_prov()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    tabellen.build_t1(counts, prov, out_dir)

    md = (out_dir / "T1_haupttabelle.md").read_text(encoding="utf-8")
    assert "Burgenland" in md
    assert "Österreich" in md

    # Mensch: 2/10 Zellen je Region wie AT (18/90) -> 20,0 % ueberall.
    mensch_line = next(line for line in md.splitlines() if line.startswith("| Mensch "))
    cells = [c.strip() for c in mensch_line.strip("|").split("|")]
    assert cells[0] == "Mensch"
    assert all(v == "20,0" for v in cells[1:])

    ausschluss_line = next(line for line in md.splitlines() if line.startswith("| Ausschluss gesamt"))
    cells = [c.strip() for c in ausschluss_line.strip("|").split("|")]
    assert all(v == "50,0" for v in cells[1:])

    eignung_line = next(line for line in md.splitlines() if line.startswith("| Eignung ≥ 10 ha"))
    cells = [c.strip() for c in eignung_line.strip("|").split("|")]
    assert all(v == "40,0" for v in cells[1:])

    csv_text = (out_dir / "T1_haupttabelle.csv").read_text(encoding="utf-8")
    assert csv_text.splitlines()[0].startswith("# Abschichtung, TIF sha256 deadbeefcafe")
    assert "Mensch,20.000000,20.000000,20.000000,20.000000,20.000000,20.000000,20.000000,20.000000,20.000000,20.000000" in csv_text


def test_build_d1_uses_mensch_natur_label_and_not_the_reversed_spelling(tmp_path):
    counts, prov = _fixed_counts(), _fixed_prov()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    tabellen.build_d1(counts, prov, out_dir)

    assert tabellen.D1_CLASS_LABELS["mensch_natur"] == wc.LABEL_MENSCH_NATUR
    assert tabellen.D1_CLASS_LABELS["mensch_geografie"] == wc.LABEL_MENSCH_GEOGRAFIE
    assert tabellen.D1_CLASS_LABELS["natur_geografie"] == wc.LABEL_NATUR_GEOGRAFIE

    md = (out_dir / "D1_exklusiv.md").read_text(encoding="utf-8")
    csv_text = (out_dir / "D1_exklusiv.csv").read_text(encoding="utf-8")
    for text in (md, csv_text):
        assert "Mensch & Natur" in text
        assert "Mensch & Geografie" in text
        assert "Natur & Geografie" in text
        assert "Natur & Mensch" not in text
        assert "Geografie & Mensch" not in text
        assert "Geografie & Natur" not in text
