"""Tests fuer pipeline/analysis/flaechenbilanz.py.

Zwei Ebenen, wie im Rest von tests/ ueblich (siehe test_flaechenanteile.py):

* Ein billiger Vertragstest gegen die bereits geschriebene TSV
  (``docs/flaechenbilanz.tsv``) - liest nur die Datei, braucht kein TIF.
  Der Pfad ist per Env-Var ``FLAECHENBILANZ_TSV`` ueberschreibbar, weil
  ``docs/flaechenbilanz.tsv`` zum Zeitpunkt dieses Commits noch nicht im
  Repo liegt (das Ziel ``bilanz`` wurde noch nicht produktiv gelaufen) -
  ohne die Variable wird auf den Default-Pfad geschaut und bei Fehlen mit
  Begruendung uebersprungen, kein rotes Ergebnis fuer ein fehlendes
  Artefakt (gleiches Muster wie tests/test_referenz_tif.py).
* Eine winzige synthetische 3x3-Rasterprobe (kein Zugriff auf echte
  Repo-Daten), die compute_bilanz()/write_tsv() direkt aufruft - schnell,
  deckt Zaehlung, fehlende Baender und Formatierung ab.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from affine import Affine
from shapely.geometry import box

# Projekt-Root relativ zu dieser Datei (<repo>/tests/); dort liegt auch
# tests/test_referenz_tif.py, dessen REFERENZ_SHA256 unten importiert wird.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
REPO_TESTS_DIR = PROJECT_ROOT / "tests"
if str(REPO_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_TESTS_DIR))

from pipeline.analysis import flaechenanteile as fa  # noqa: E402

try:
    # Normalfall, sobald diese Datei (und flaechenbilanz.py) im Repo liegen.
    from pipeline.analysis import flaechenbilanz as flb  # noqa: E402
except ImportError:
    # Vor der Graduierung: flaechenbilanz.py existiert nur im
    # Scratch-Spiegelverzeichnis neben dieser Testdatei (gleiche relative
    # Lage tests/../pipeline/analysis/), nicht im echten Repo-Package -
    # per Dateipfad geladen, damit dieselbe Testdatei nachher unveraendert
    # weiterlaeuft.
    _flb_path = Path(__file__).resolve().parents[1] / "pipeline" / "analysis" / "flaechenbilanz.py"
    _spec = importlib.util.spec_from_file_location("flaechenbilanz_unter_test", _flb_path)
    flb = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = flb
    _spec.loader.exec_module(flb)

# Referenz-sha256 des aktuellen Repo-Stands importiert aus test_referenz_tif.py
# (Modul liegt im selben tests/-Verzeichnis, kein eigenes Package -> pytest
# fuegt tests/ ohnehin zu sys.path hinzu; der Insert oben oben ist nur die
# Absicherung fuer einen direkten Einzelaufruf dieser Datei).
from test_referenz_tif import REFERENZ_SHA256  # noqa: E402

TSV_PATH = Path(os.environ.get("FLAECHENBILANZ_TSV", str(PROJECT_ROOT / "docs" / "flaechenbilanz.tsv")))

AREA_KEYS = [key for key, _bands, _fn in flb.AREA_KENNZAHLEN]
ALL_KEYS = flb.ALL_KENNZAHLEN_ORDER
EXKLUSIV_KEYS = [
    "exklusiv.nur_mensch", "exklusiv.nur_natur", "exklusiv.nur_geografie",
    "exklusiv.mensch_natur", "exklusiv.mensch_geografie", "exklusiv.natur_geografie",
    "exklusiv.alle_drei",
]


def _parse_tsv(path: Path):
    """(comment_kv: dict, fehlt_lines: list[str], rows: dict[(key,region)] -> dict)"""
    comment_kv: dict[str, str] = {}
    fehlt_lines: list[str] = []
    rows: dict[tuple[str, str], dict[str, str]] = {}
    header = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if body.startswith("fehlt:"):
                fehlt_lines.append(body)
            elif "=" in body:
                k, _, v = body.partition("=")
                comment_kv[k.strip()] = v.strip()
            continue
        cols = line.split("\t")
        if header is None:
            header = cols
            assert header == ["kennzahl", "region", "zellen", "km2", "prozent", "anzahl"]
            continue
        rec = dict(zip(header, cols))
        rows[(rec["kennzahl"], rec["region"])] = rec
    assert header is not None, f"{path}: keine Kopfzeile gefunden"
    return comment_kv, fehlt_lines, rows


# ---------------------------------------------------------------------------
# Vertragstests gegen die (mutmasslich noch nicht vorhandene) docs/flaechenbilanz.tsv
# ---------------------------------------------------------------------------

pytestmark_skip_reason = (
    f"{TSV_PATH} fehlt - 'make bilanz' (bzw. das flaechenbilanz-Modul direkt) "
    "zuerst laufen lassen, oder FLAECHENBILANZ_TSV auf eine vorhandene Probe-TSV "
    "zeigen lassen. Ein fehlendes Artefakt ist kein gebrochener Vertrag."
)


@pytest.fixture(scope="module")
def bilanz_tsv():
    if not TSV_PATH.is_file():
        pytest.skip(pytestmark_skip_reason)
    return _parse_tsv(TSV_PATH)


def test_tif_sha256_matches_referenz_tif_contract(bilanz_tsv):
    """Erwartungsgemaess rot, bis die TSV auf der neuen Referenz erzeugt wurde:
    die Probe-TSV in diesem Auftrag ist auf dem Backup-TIF
    (sha256 58caa8ff...) gerechnet, der Repo-Vertrag (tests/test_referenz_tif.py)
    steht noch auf c1809c4c... . Das ist kein Bug dieses Tests, sondern genau
    die im Auftrag angekuendigte, noch ausstehende Aktualisierung."""
    comment_kv, _fehlt, _rows = bilanz_tsv
    assert comment_kv["tif_sha256"] == REFERENZ_SHA256


def test_alle_kennzahlen_x_regionen_vorhanden(bilanz_tsv):
    _comment_kv, _fehlt, rows = bilanz_tsv
    missing_combos = [
        (key, region) for key in ALL_KEYS for region in flb.REGION_ORDER
        if (key, region) not in rows
    ]
    assert not missing_combos, f"Fehlende kennzahl x region Kombinationen: {missing_combos[:10]}..."


def test_at_ist_summe_der_neun_laender_je_flaechenzeile(bilanz_tsv):
    _comment_kv, _fehlt, rows = bilanz_tsv
    for key in AREA_KEYS:
        at_cell = rows[(key, "AT")]["zellen"]
        if at_cell == "":
            continue  # Kennzahl fehlt (Band nicht vorhanden) - nichts zu pruefen
        at_val = int(at_cell)
        summe = sum(int(rows[(key, code)]["zellen"]) for code in fa.STATE_CODES.values())
        assert at_val == summe, f"{key}: AT={at_val} != Summe(9 Laender)={summe}"


def test_exklusiv_plus_frei_roh_ergibt_regionstotal(bilanz_tsv):
    _comment_kv, _fehlt, rows = bilanz_tsv
    for region in list(fa.STATE_CODES.values()) + ["AT"]:
        ausschluss = rows[("ergebnis.ausschluss_gesamt", region)]["zellen"]
        frei_roh = rows[("ergebnis.frei_roh", region)]["zellen"]
        if ausschluss == "" or frei_roh == "":
            continue
        exklusiv_summe = sum(int(rows[(k, region)]["zellen"]) for k in EXKLUSIV_KEYS)
        assert exklusiv_summe == int(ausschluss), (
            f"{region}: Summe der 7 exklusiv-Klassen ({exklusiv_summe}) != "
            f"ergebnis.ausschluss_gesamt ({ausschluss})"
        )
        total = int(ausschluss) + int(frei_roh)
        assert exklusiv_summe + int(frei_roh) == total  # tautologisch, dokumentiert die Beziehung


def test_kleinflaechen_gleich_frei_roh_minus_eignung(bilanz_tsv):
    _comment_kv, _fehlt, rows = bilanz_tsv
    for region in list(fa.STATE_CODES.values()) + ["AT"]:
        frei_roh = rows[("ergebnis.frei_roh", region)]["zellen"]
        eignung = rows[("ergebnis.eignung_10ha", region)]["zellen"]
        klein = rows[("ergebnis.kleinflaechen", region)]["zellen"]
        if "" in (frei_roh, eignung, klein):
            continue
        assert int(klein) == int(frei_roh) - int(eignung), (
            f"{region}: kleinflaechen={klein} != frei_roh({frei_roh}) - eignung_10ha({eignung})"
        )


# ---------------------------------------------------------------------------
# Reine Formatierungs-Unit-Tests, ohne jedes Raster
# ---------------------------------------------------------------------------

def test_fmt_km2_und_pct():
    assert flb._fmt_km2(1600) == "1.00"  # 1600 * 625 m^2 = 1 km^2
    assert flb._fmt_km2(0) == "0.00"
    assert flb._fmt_pct(25, 200) == "12.500"
    assert flb._fmt_pct(0, 0) == ""  # Region ohne Zellen: leer, keine Division durch 0


# ---------------------------------------------------------------------------
# Winzige synthetische Rasterprobe: 3x3, ein Pixel je Bundesland (wie
# tests/test_flaechenanteile.py::_inputs), nur 6 der ~40 Baender vorhanden -
# uebt damit auch den "Band fehlt" - Pfad aus, wie er auf den aelteren
# 38-/54-Band-TIFs vorkommen wird.
# ---------------------------------------------------------------------------

def _make_regions_gpkg(tmp_path: Path) -> Path:
    names = list(fa.STATE_CODES)
    geoms = [box(x, 2 - y, x + 1, 3 - y) for y in range(3) for x in range(3)]
    path = tmp_path / "bundesland_masken.gpkg"
    gpd.GeoDataFrame({"BL": names}, geometry=geoms, crs=fa.TARGET_CRS).to_file(path, driver="GPKG")
    return path


def _make_synthetic_tif(tmp_path: Path):
    # Zellzuordnung (Affine(1,0,0,0,-1,3), row=y, col=x - siehe _make_regions_gpkg):
    # B=[0,0] K=[0,1] N=[0,2] / O=[1,0] S=[1,1] ST=[1,2] / T=[2,0] V=[2,1] W=[2,2]
    H = np.array([[1, 0, 0], [1, 1, 0], [1, 0, 0]], dtype="uint8")
    N = np.array([[0, 1, 0], [1, 0, 1], [1, 0, 0]], dtype="uint8")
    G = np.array([[0, 0, 1], [0, 1, 1], [1, 0, 0]], dtype="uint8")
    ALL = ((H | N | G) != 0).astype("uint8")
    RAW = (ALL == 0).astype("uint8")
    TENHA = np.zeros((3, 3), dtype="uint8")
    TENHA[2, 1] = 1  # V: einzige Eignungszelle

    bands = {
        "exclusion_human": H,
        "exclusion_nature": N,
        "exclusion_geography": G,
        "all_exclusions": ALL,
        "available_after_all_exclusions_raw": RAW,
        "available_cleaned_min_10ha": TENHA,
    }
    tif_path = tmp_path / "mini.tif"
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=3, width=3, count=len(bands),
        dtype="uint8", crs=fa.TARGET_CRS, transform=Affine(1, 0, 0, 0, -1, 3), nodata=0,
    ) as dst:
        for i, (name, arr) in enumerate(bands.items(), start=1):
            dst.write(arr, i)
            dst.set_band_description(i, name)
    return tif_path


def _make_wka_geojson(tmp_path: Path) -> Path:
    features = [
        {"type": "Feature",
         "properties": {"in_zone": False, "hull_id": 7},
         "geometry": {"type": "Point", "coordinates": [0.5, 2.5]}},  # B
        {"type": "Feature",
         "properties": {"in_zone": False, "hull_id": 7},
         "geometry": {"type": "Point", "coordinates": [0.6, 2.4]}},  # B, gleicher Park
        {"type": "Feature",
         "properties": {"in_zone": True, "hull_id": None},
         "geometry": {"type": "Point", "coordinates": [1.5, 2.5]}},  # K
    ]
    path = tmp_path / "wka.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return path


def test_synthetische_probe_zaehlt_richtig_und_markiert_fehlende_baender(tmp_path):
    regions_path = _make_regions_gpkg(tmp_path)
    tif_path = _make_synthetic_tif(tmp_path)
    wka_path = _make_wka_geojson(tmp_path)

    data = flb.compute_bilanz(tif_path, bands_json=None, wka_path=wka_path, regions_path=regions_path)

    assert data["band_count"] == 6
    assert data["schema"] == "unknown"  # kein Sidecar-Manifest, kein BAND_SCHEMA-Tag
    assert len(data["tif_sha256"]) == 64

    missing_keys = {key for key, _m in data["missing_report"]}
    assert "kriterium.mensch.siedlung" in missing_keys
    assert "referenz.amtliche_zonen" in missing_keys
    assert "kriterium.mensch.verkehr" in missing_keys
    # 37 Flaechen-Kennzahlen insgesamt, nur die 14 auf den 6 vorhandenen
    # Baendern (ergebnis x4, kategorie x3, exklusiv x7) sind rechenbar.
    assert len(data["counters"]) == 14
    assert len(missing_keys) == len(flb.AREA_KENNZAHLEN) - 14

    c = data["counters"]
    assert c["ergebnis.ausschluss_gesamt"] == {
        "B": 1, "K": 1, "N": 1, "O": 1, "S": 1, "ST": 1, "T": 1, "V": 0, "W": 0,
    }
    assert c["ergebnis.frei_roh"] == {
        "B": 0, "K": 0, "N": 0, "O": 0, "S": 0, "ST": 0, "T": 0, "V": 1, "W": 1,
    }
    assert c["ergebnis.eignung_10ha"]["V"] == 1
    assert sum(c["ergebnis.eignung_10ha"].values()) == 1
    assert c["exklusiv.nur_mensch"]["B"] == 1
    assert c["exklusiv.nur_natur"]["K"] == 1
    assert c["exklusiv.nur_geografie"]["N"] == 1
    assert c["exklusiv.mensch_natur"]["O"] == 1
    assert c["exklusiv.mensch_geografie"]["S"] == 1
    assert c["exklusiv.natur_geografie"]["ST"] == 1
    assert c["exklusiv.alle_drei"]["T"] == 1
    assert sum(c["kategorie.mensch"].values()) == 4
    assert sum(c["kategorie.natur"].values()) == 4
    assert sum(c["kategorie.geografie"].values()) == 4
    assert data["region_cells"] == {code: 1 for code in fa.STATE_CODES.values()}
    assert data["at_cells"] == 9

    wka = data["wka_counts"]
    assert wka["B"] == {"anlagen": 2, "in_zonen": 0, "ausserhalb": 2, "parks": 1}
    assert wka["K"] == {"anlagen": 1, "in_zonen": 1, "ausserhalb": 0, "parks": 0}
    assert wka["AT"] == {"anlagen": 3, "in_zonen": 1, "ausserhalb": 2, "parks": 1}

    out_path = tmp_path / "out.tsv"
    flb.write_tsv(data, out_path)
    comment_kv, fehlt_lines, rows = _parse_tsv(out_path)
    assert comment_kv["schema"] == "unknown"
    assert comment_kv["band_count"] == "6"
    assert any(l.startswith("fehlt: kriterium.mensch.siedlung") for l in fehlt_lines)

    # fehlende Kennzahl: alle Wertspalten leer, aber die Zeile existiert
    row = rows[("kriterium.mensch.siedlung", "B")]
    assert row["zellen"] == row["km2"] == row["prozent"] == row["anzahl"] == ""

    # vorhandene Flaechenzeile: exakte Formatierung
    row = rows[("ergebnis.ausschluss_gesamt", "B")]
    assert row["zellen"] == "1"
    assert row["km2"] == "0.00"  # 1 Zelle * 625 m^2 = 0.000625 km^2, auf 2 Dezimalen
    assert row["prozent"] == "100.000"

    row_at = rows[("ergebnis.ausschluss_gesamt", "AT")]
    assert row_at["zellen"] == "7"
    assert row_at["prozent"] == f"{7/9*100:.3f}"

    # Zaehl-Kennzahl: nur anzahl gefuellt, Flaechenspalten leer
    row_wka = rows[("referenz.wka.parks", "AT")]
    assert row_wka["zellen"] == row_wka["km2"] == row_wka["prozent"] == ""
    assert row_wka["anzahl"] == "1"


def test_zweiter_lauf_ist_bytegleich(tmp_path):
    regions_path = _make_regions_gpkg(tmp_path)
    tif_path = _make_synthetic_tif(tmp_path)
    wka_path = _make_wka_geojson(tmp_path)

    data1 = flb.compute_bilanz(tif_path, bands_json=None, wka_path=wka_path, regions_path=regions_path)
    data2 = flb.compute_bilanz(tif_path, bands_json=None, wka_path=wka_path, regions_path=regions_path)
    out1, out2 = tmp_path / "a.tsv", tmp_path / "b.tsv"
    flb.write_tsv(data1, out1)
    flb.write_tsv(data2, out2)
    assert out1.read_bytes() == out2.read_bytes()
