"""Traegt die Werte der bestehenden Tabellen (K, T1, D1-D3, L1) ins Zahlenregister ein.

Liest die von ``tabellen.py`` / ``landnutzung.py`` geschriebenen CSVs (Quelle
bleibt TIF + Manifest) und schluesselt jede Zelle:

  k_<kennzahl>_<einheit>                K_kernzahlen (Anzeigewerte, gerundet)
  t1_<groesse>_<region>                 T1_haupttabelle (% bzw. km², roh)
  d1_<einheit>_<klasse>_<region>        D1_exklusiv
  d2_<einheit>_<name>_<region>          D2_kriterien
  d3_<einheit>_<key>_<region>           D3_eignung
  l1_<region>_<feld>                    L1_landnutzung
  natur_*                               Aliase fuer die Natur-Zahlen (Abschnitt 3.2.1)
Region ist klein (b k n o s st t v w at).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from . import wp_common as wc
from . import zahlen as Z

_EINHEIT = {"km2": "km²", "%": "%"}
_NAME_TO_CODE = {name: code for name, code in wc.STATE_CODES.items()}
_NAME_TO_CODE["Österreich"] = "AT"


def _rows(path: Path) -> list[list[str]]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    return list(csv.reader(lines))


def _de_float(s: str) -> float:
    return float(re.sub(r"[\s  ]", "", s).replace(",", "."))


def _fl(s: str) -> float | None:
    s = s.strip()
    return float(s) if s not in ("", "nan") else None


def register_k(tab_dir: Path) -> None:
    rows = _rows(Path(tab_dir) / "K_kernzahlen.csv")
    for kenn, wert, einheit, _anm in rows[1:]:
        key = f"k_{Z.slug(kenn)}_{Z.slug(einheit)}"
        Z.register(key, _de_float(wert), einheit, "K_kernzahlen (angezeigte Rundung)")


def register_t1(tab_dir: Path) -> None:
    rows = _rows(Path(tab_dir) / "T1_haupttabelle.csv")
    head = rows[0]
    codes = [_NAME_TO_CODE[h] for h in head[1:]]
    for r in rows[1:]:
        label = r[0]
        einheit = "km²" if "km²" in label else "%"
        for code, v in zip(codes, r[1:], strict=True):
            f = _fl(v)
            if f is not None:
                Z.register(f"t1_{Z.slug(label)}_{code.lower()}", f, einheit, "T1_haupttabelle")


def _register_long(tab_dir: Path, fname: str, prefix: str, keycol: str, tabname: str) -> None:
    rows = _rows(Path(tab_dir) / fname)
    head = rows[0]
    ki = head.index(keycol)
    cols = [(i, h) for i, h in enumerate(head) if h in wc.REGION_ORDER_AT]
    for r in rows[1:]:
        einheit = _EINHEIT[r[0]]
        base = r[ki] if prefix != "d2" else r[head.index("name")]
        for i, h in cols:
            f = _fl(r[i])
            if f is not None:
                Z.register(f"{prefix}_{r[0].replace('%', 'pct')}_{Z.slug(base)}_{h.lower()}", f, einheit, tabname)


def register_d(tab_dir: Path) -> None:
    _register_long(tab_dir, "D1_exklusiv.csv", "d1", "klasse_key", "D1_exklusiv")
    _register_long(tab_dir, "D2_kriterien.csv", "d2", "band", "D2_kriterien")
    _register_long(tab_dir, "D3_eignung.csv", "d3", "key", "D3_eignung")


def register_l1(tab_dir: Path) -> None:
    rows = _rows(Path(tab_dir) / "L1_landnutzung.csv")
    head = rows[0]
    for r in rows[1:]:
        code = r[0].lower()
        for h, v in zip(head[2:], r[2:], strict=True):
            f = _fl(v)
            if f is not None:
                Z.register(f"l1_{code}_{h}", f, "km²" if h.endswith("km2") else "%", "L1_landnutzung")


def register_natur_aliase() -> None:
    """Natur-Zahlen fuer Abschnitt 3.2.1 (aus D2/T1; Zellmittelpunkt-Bezugsflaeche)."""
    reg = Z.current()
    for alias, src, text in (
        ("natur_amtlich_km2", "d2_km2_nature_protection_areas_at", "amtliche Schutzgebiete (Band 21)"),
        ("natur_amtlich_pct", "d2_pct_nature_protection_areas_at", "amtliche Schutzgebiete (Band 21)"),
        ("natur_osm_km2", "d2_km2_osm_nature_protection_areas_at", "OSM-Schutzgebiete (Band 22, nur Information)"),
        ("natur_osm_pct", "d2_pct_osm_nature_protection_areas_at", "OSM-Schutzgebiete (Band 22, nur Information)"),
        ("natur_ausschluss_km2", "d2_km2_exclusion_nature_at", "Ausschluss Natur (Band 28)"),
        ("natur_ausschluss_pct", "d2_pct_exclusion_nature_at", "Ausschluss Natur (Band 28)"),
        ("natur_nur_natur_pct", "d1_pct_nur_natur_at", "nur Natur (D1)"),
    ):
        if src in reg:
            Z.register(alias, reg[src]["wert"], reg[src]["einheit"], f"{text}; = {src}")


def run(tab_dir: Path) -> int:
    n0 = len(Z.current())
    register_k(tab_dir)
    register_t1(tab_dir)
    register_d(tab_dir)
    register_l1(tab_dir)
    register_natur_aliase()
    n = len(Z.current()) - n0
    print(f"[zahlen_tabellen] {n} Schluessel aus K/T1/D1-D3/L1 registriert")
    return n
