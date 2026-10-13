"""tests/test_export_viewer.py: Abnahme von W6.7 (Kartenviewer ueber OSM).

Folgt demselben Muster wie tests/test_export_dashboard.py (W4.3): Grep-Test
gegen das echte Manifest (kein Bandname im Quelltext), ein fremdes Manifest
mit anderer Bandzahl/anderen Namen als Haertetest, sowie ein CLI-Rauchtest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

VIEWER_QUELLE = PROJECT_ROOT / "pipeline" / "export" / "viewer.py"

if not VIEWER_QUELLE.is_file():
    pytest.skip(f"{VIEWER_QUELLE} nicht vorhanden.", allow_module_level=True)

from pipeline import contract  # noqa: E402
from pipeline.export import viewer  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402

ECHTES_MANIFEST = contract.PRODUCTS["abschichtung_bands_json"]
ECHTES_RASTER = contract.PRODUCTS["abschichtung_tif"]


def _fremdes_manifest() -> dict:
    return {
        "schema_version": "2.0.0",
        "generated_at": "2026-01-01T00:00:00Z",
        "raster": {
            "crs": "EPSG:31287", "width": 8, "height": 8, "pixel_size_m": 100.0,
            "bounds": [400000, 300000, 400800, 300800], "dtype": "uint8", "nodata": 0,
        },
        "band_count": 3,
        "bands": [
            {"index": 1, "name": "zutat_mehl", "label_de": "Mehl", "description_de": "",
             "category": "Alpha", "value_type": "binary", "rolle": "bedingung",
             "color_rgba": [200, 0, 0, 180], "default_visible": False},
            {"index": 2, "name": "teig", "label_de": "Teig", "description_de": "",
             "category": "Beta", "value_type": "binary", "rolle": "aggregat_gesamt",
             "color_rgba": [0, 200, 0, 180], "default_visible": True},
            {"index": 3, "name": "feuchtigkeit", "label_de": "Feuchtigkeit", "description_de": "",
             "category": "Beta", "value_type": "percent_0_100", "rolle": "unschaerfe",
             "color_rgba": [0, 100, 200, 200], "default_visible": False},
        ],
    }


@pytest.fixture()
def fremdes_manifest() -> dict:
    return _fremdes_manifest()


def _schreibe_mini_tif(pfad: Path, manifest: dict) -> Path:
    import rasterio
    from rasterio.transform import from_bounds

    r = manifest["raster"]
    transform = from_bounds(*r["bounds"], r["width"], r["height"])
    with rasterio.open(
        pfad, "w", driver="GTiff", width=r["width"], height=r["height"],
        count=len(manifest["bands"]), dtype=r["dtype"], crs=r["crs"], transform=transform,
    ) as dst:
        rng = np.random.default_rng(0)
        for band in manifest["bands"]:
            if band["value_type"] == "percent_0_100":
                arr = rng.integers(0, 101, size=(r["height"], r["width"]), dtype="uint8")
            else:
                arr = (rng.random((r["height"], r["width"])) > 0.5).astype("uint8")
            dst.write(arr, band["index"])
            dst.set_band_description(band["index"], band["name"])
    return pfad


@pytest.mark.skipif(not ECHTES_MANIFEST.exists(), reason=f"{ECHTES_MANIFEST} fehlt.")
def test_kein_bandname_der_echten_kette_steht_im_quelltext():
    manifest = json.loads(ECHTES_MANIFEST.read_text(encoding="utf-8"))
    bandnamen = [b["name"] for b in manifest["bands"]]
    # Erst nach der Integration (echtes Manifest neu geschrieben, Schema
    # 2.2.0/W7.1, 44 Bänder; seit 30.09.2026 45 Bänder, Schema 2.3.0) wieder grün - siehe Bericht Bahn 2, W7.1.
    assert len(bandnamen) == 45

    quelltext = VIEWER_QUELLE.read_text(encoding="utf-8")
    treffer = sorted(name for name in bandnamen if name in quelltext)
    assert not treffer, f"{VIEWER_QUELLE.name} enthaelt Bandnamen woertlich: {treffer}"


def test_resampling_fuer_masken_ist_max():
    assert viewer.resampling_for("binary") == Resampling.max


def test_resampling_fuer_prozentbaender_ist_average():
    assert viewer.resampling_for("percent_0_100") == Resampling.average


def test_colorize_maske_ist_volltonfarbe_und_null_ist_durchsichtig():
    werte = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    rgba = viewer.colorize(werte, "binary", [10, 20, 30, 200])
    assert rgba[0, 0, 3] == 0
    assert tuple(rgba[0, 1]) == (10, 20, 30, 200)
    assert tuple(rgba[1, 0]) == (10, 20, 30, 200)
    assert rgba[1, 1, 3] == 0


def test_colorize_prozentband_ist_eine_farbskala():
    werte = np.array([[0, 50], [100, 25]], dtype=np.uint8)
    rgba = viewer.colorize(werte, "percent_0_100", [10, 20, 30, 200])
    assert rgba[0, 0, 3] == 0
    assert rgba[1, 0, 3] == 200
    assert 0 < rgba[0, 1, 3] < rgba[1, 0, 3]
    assert rgba[0, 1, 3] == round(50 / 100 * 200)
    assert tuple(rgba[1, 0, :3]) == (10, 20, 30)


def test_main_laeuft_gegen_ein_fremdes_manifest_unveraendert_durch(tmp_path, fremdes_manifest):
    manifest_pfad = tmp_path / "fremd.bands.json"
    manifest_pfad.write_text(json.dumps(fremdes_manifest, ensure_ascii=False), encoding="utf-8")
    raster_pfad = _schreibe_mini_tif(tmp_path / "fremd.tif", fremdes_manifest)
    out_dir = tmp_path / "dashboard"

    code = viewer.main([
        "--manifest", str(manifest_pfad), "--raster", str(raster_pfad),
        "--out", str(out_dir), "--max-size", "16",
    ])
    assert code == 0

    viewer_manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert viewer_manifest["band_count"] == 3
    alle_layer = [l for g in viewer_manifest["groups"] for l in g["layers"]]
    assert len(alle_layer) == 3
    assert {l["file"] for l in alle_layer} == {
        "layers/01_zutat_mehl.png", "layers/02_teig.png", "layers/03_feuchtigkeit.png",
    }
    gruppen_mit_layern = {g["title"] for g in viewer_manifest["groups"] if g["layers"]}
    assert gruppen_mit_layern == {"Bedingungen", "Gesamt", "Unschärfe"}

    html_text = (out_dir / "index.html").read_text(encoding="utf-8")
    assert html_text.lstrip().startswith("<!doctype html>")

    for l in alle_layer:
        png = out_dir / l["file"]
        assert png.exists()
        assert png.stat().st_size > 0
        assert l["opaque_pixels"] >= 0


def test_main_bricht_bei_bandzahl_mismatch_ab(tmp_path, fremdes_manifest):
    raster_pfad = _schreibe_mini_tif(tmp_path / "fremd.tif", fremdes_manifest)
    fremdes_manifest["bands"].pop()
    manifest_pfad = tmp_path / "fremd.bands.json"
    manifest_pfad.write_text(json.dumps(fremdes_manifest, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Baender"):
        viewer.main(["--manifest", str(manifest_pfad), "--raster", str(raster_pfad), "--out", str(tmp_path / "d")])


def test_main_bricht_bei_fehlendem_manifest_mit_klarer_meldung_ab(tmp_path):
    with pytest.raises(FileNotFoundError, match="fehlt"):
        viewer.main(["--manifest", str(tmp_path / "nicht_da.json"), "--raster", str(tmp_path / "nicht_da.tif")])


@pytest.mark.skipif(not ECHTES_RASTER.exists(), reason=f"{ECHTES_RASTER} fehlt.")
def test_bounding_box_des_echten_rasters_liegt_ueber_oesterreich():
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(ECHTES_RASTER) as src:
        west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)
    assert 7.0 < west < 11.5
    assert 15.0 < east < 20.0
    assert 45.0 < south < 48.0
    assert 47.5 < north < 51.0


def _manifest_mit_themen() -> dict:
    """Bedingungen ueber zwei Kategorien/Familien, absichtlich in 'falscher' Indexreihenfolge."""
    def b(i, cat, fam, stufe):
        return {"index": i, "name": f"b{i}", "label_de": f"B{i}", "description_de": "",
                "category": cat, "familie": fam, "stufe": stufe, "value_type": "binary",
                "rolle": "bedingung", "color_rgba": [1, 2, 3, 100], "default_visible": False}
    return {
        "schema_version": "2.0.0", "generated_at": "2026-01-01T00:00:00Z",
        "raster": {"crs": "EPSG:31287", "width": 8, "height": 8, "pixel_size_m": 100.0,
                   "bounds": [400000, 300000, 400800, 300800], "dtype": "uint8", "nodata": 0},
        "category_order": ["Mensch", "Natur"],
        "stufe_order": ["roh", "quelle", "zone"],
        "familien": [
            {"key": "verkehr", "category": "Mensch"},
            {"key": "leitungen", "category": "Mensch"},
            {"key": "schutz", "category": "Natur"},
        ],
        "kategorien": [
            {"key": "mensch", "category": "Mensch", "label_de": "Mensch-Label"},
            {"key": "natur", "category": "Natur", "label_de": "Natur-Label"},
        ],
        "band_count": 5,
        "bands": [
            b(1, "Natur", "schutz", "zone"),
            b(2, "Mensch", "leitungen", "zone"),
            b(3, "Mensch", "verkehr", "zone"),
            b(4, "Mensch", "verkehr", "roh"),
            b(5, "Unbekannt", "x", "zone"),
        ],
    }


def test_ebenen_folgen_kategorie_familie_stufe_und_haben_unterueberschriften(tmp_path):
    manifest = _manifest_mit_themen()
    manifest_pfad = tmp_path / "t.bands.json"
    manifest_pfad.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    raster_pfad = _schreibe_mini_tif(tmp_path / "t.tif", manifest)
    out_dir = tmp_path / "dashboard"
    assert viewer.main([
        "--manifest", str(manifest_pfad), "--raster", str(raster_pfad),
        "--out", str(out_dir), "--max-size", "16",
    ]) == 0

    vm = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    bed = next(g for g in vm["groups"] if g["title"] == "Bedingungen")
    # Mensch: verkehr (roh 4, zone 3) -> leitungen 2; dann Natur 1; Unbekanntes zuletzt.
    assert [l["index"] for l in bed["layers"]] == [4, 3, 2, 1, 5]
    assert [l["category_label"] for l in bed["layers"]][:4] == ["Mensch-Label"] * 3 + ["Natur-Label"]
    assert all("familie" in l and "stufe" in l for l in bed["layers"])

    html_text = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "multiCategory" in html_text and "subgroup" in html_text


@pytest.mark.skipif(not ECHTES_MANIFEST.exists(), reason=f"{ECHTES_MANIFEST} fehlt.")
def test_sort_layers_echtes_manifest_energieleitungen_neben_verkehr():
    manifest = json.loads(ECHTES_MANIFEST.read_text(encoding="utf-8"))
    layers = [
        {"index": b["index"], "category": b.get("category"), "familie": b.get("familie"), "stufe": b.get("stufe")}
        for b in manifest["bands"] if b.get("rolle") == "bedingung"
    ]
    reihenfolge = [l["index"] for l in viewer.sort_layers(layers, manifest)]
    assert reihenfolge.index(45) == reihenfolge.index(17) + 1
    assert reihenfolge.index(39) < reihenfolge.index(7)
