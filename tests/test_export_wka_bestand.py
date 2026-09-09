"""pipeline/export/wka_bestand.py: die vier Zählungen aus dem Auftrag zu
W7.1/Bahn 3 (schnittstelle-manifest-2.2.md §3), verdrahtet.

Referenzwerte laut Auftrag: 1595 Anlagen gesamt, 807 in einer amtlichen
Zone, 788 außerhalb. Eine Abweichung ist laut Auftrag kein Abbruchgrund,
aber dieser Test macht sie sichtbar statt sie stillschweigend durchzulassen
("gehört erklärt" - siehe Berichtstext zu diesem Paket, falls die Zahlen
hier je nicht mehr stimmen).

## Warum dieser Test übersprungen werden kann

``derived/prep/osm/b_layers/windpower.parquet`` (W1.P5) und
``derived/layers/official_wind_zoning.tif`` (W2.4/Bahn 1) sind Ausgaben
anderer Pakete. In einem Worktree, in dem beide noch nicht gelaufen sind,
überspringt sich dieser Test geschlossen - mit einer Begründung, die genau
das sagt (wie ``tests/test_export_dashboard.py``, gleiche Konvention).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract  # noqa: E402
from pipeline.export import wka_bestand  # noqa: E402

_WINDPOWER_PARQUET = contract.PREP["osm"]["b_layers"] / wka_bestand.WINDPOWER_PARQUET_NAME
_OFFICIAL_ZONING_TIF = contract.LAYERS["official_wind_zoning"]

pytestmark = pytest.mark.skipif(
    not (_WINDPOWER_PARQUET.exists() and _OFFICIAL_ZONING_TIF.exists()),
    reason=(
        f"{_WINDPOWER_PARQUET} oder {_OFFICIAL_ZONING_TIF} fehlt - Prep-Stufe "
        "(pipeline/prep/osm.py, W1.P5) bzw. Layer-Stufe (pipeline/layers/geo.py, "
        "W2.4/Bahn 1) noch nicht gelaufen."
    ),
)

# Referenzwerte aus dem Auftrag zu W7.1/Bahn 3 (Stand 2026-09-09).
ERWARTET_GESAMT = 1595
ERWARTET_IN_ZONE = 807
ERWARTET_AUSSERHALB = 788

_ERWARTETE_PROPERTIES = {
    "osm_id",
    "in_zone",
    "hull_id",
    "name",
    "operator",
    "power_kw",
    "start_date",
}


@pytest.fixture(scope="module")
def export_result():
    turbinen = wka_bestand.load_turbines()
    grid = wka_bestand.grid_from_official_wind_zoning()
    return wka_bestand.build_export(turbinen, grid)


def test_gesamtzahl_der_anlagen(export_result):
    gdf, counts = export_result
    assert len(gdf) == counts["gesamt"]
    assert counts["gesamt"] == ERWARTET_GESAMT, (
        f"{counts['gesamt']} Anlagen statt der im Auftrag genannten "
        f"{ERWARTET_GESAMT} - siehe Moduldocstring dieses Tests."
    )


def test_in_zone_und_ausserhalb_ergeben_die_gesamtzahl(export_result):
    gdf, counts = export_result
    assert counts["in_zone_true"] + counts["in_zone_false"] == counts["gesamt"]
    assert counts["in_zone_true"] == ERWARTET_IN_ZONE
    assert counts["in_zone_false"] == ERWARTET_AUSSERHALB


def test_huellenzahl_und_hull_id_nur_ausserhalb_der_zone(export_result):
    gdf, counts = export_result
    in_zone = gdf[gdf["in_zone"]]
    ausserhalb = gdf[~gdf["in_zone"]]

    # §3: "hull_id ... null wenn in_zone".
    assert in_zone["hull_id"].isna().all()

    assert counts["huellen"] > 0
    assert counts["huellen"] <= len(ausserhalb)

    distinct_hulls = set(int(v) for v in ausserhalb["hull_id"].dropna().tolist())
    assert len(distinct_hulls) == counts["huellen"]
    assert distinct_hulls == set(range(1, counts["huellen"] + 1))


def test_properties_entsprechen_wortgetreu_der_schnittstelle_paragraph_3(export_result):
    gdf, _ = export_result
    assert set(gdf.columns) - {"geometry"} == _ERWARTETE_PROPERTIES
    assert gdf.crs is not None and str(gdf.crs).upper() == "EPSG:31287"
    assert (gdf.geometry.geom_type == "Point").all()


def test_hull_id_ist_int_oder_null_kein_float(tmp_path, export_result):
    """Regressions-Test für eine pandas-Falle: eine gemischte int/None-Spalte
    ohne explizites dtype wird von pandas zu float64 hochgestuft (None ->
    NaN, 107 -> 107.0) - das GeoJSON schriebe dann 107.0 statt des laut §3
    geforderten Integers. ``build_export()`` erzwingt pandas' "Int64" statt
    "object" (letzteres schreibt pyogrio als String, siehe Moduldocstring
    von wka_bestand.py)."""
    gdf, _ = export_result
    huellen_werte = gdf["hull_id"].dropna().tolist()
    assert huellen_werte, "keine Anlage außerhalb einer Zone - Test kann nicht prüfen"
    assert all(isinstance(v, int) or float(v).is_integer() for v in huellen_werte)


def test_main_schreibt_ein_gueltiges_geojson_mit_expliziten_crs_member(monkeypatch, tmp_path):
    ziel = tmp_path / "wka_bestand_punkte.geojson"
    monkeypatch.setitem(contract.PRODUCTS, "wka_bestand_punkte_geojson", ziel)

    exit_code = wka_bestand.main([])
    assert exit_code == 0
    assert ziel.exists()

    with open(ziel, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == ERWARTET_GESAMT
    assert "31287" in data["crs"]["properties"]["name"]

    beispiel = data["features"][0]["properties"]
    assert set(beispiel.keys()) == _ERWARTETE_PROPERTIES
