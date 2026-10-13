"""Tests fuer N1_natur_ebenen (synthetisches GeoPackage) und OSM-ausserhalb-amtlich (synthetisches TIF)."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_whitepaper_zaehlen import TRANSFORM, _write_boundaries  # noqa: E402

from pipeline.analysis.whitepaper import natur_ebenen, weitere_zahlen, wp_common as wc  # noqa: E402
from pipeline.analysis.whitepaper import zahlen as Z  # noqa: E402


def _gdf():
    sq = box(0, 0, 1, 1)
    rows = [("NP_AT_2024", None, sq)] * 3
    rows += [("S_AT_2024", k, sq) for k in ["RG", "RG", "ÖSG", "SGNOG", "XYZ"]]
    rows += [("NDKM_AT_2024", None, g) for g in [sq, sq, Point(0, 0), Point(1, 1)]]
    return gpd.GeoDataFrame({"layer": [r[0] for r in rows], "KAT_SUB": [r[1] for r in rows]},
                            geometry=[r[2] for r in rows], crs=31287)


def test_count_layers_filter_and_points():
    g = _gdf()
    g = g[~g.KAT_SUB.isin(["SGNOG", "XYZ"])]          # prep liefert nur gefilterte S-Zeilen
    e = natur_ebenen.count_layers(g)
    assert [x["layer"] for x in e] == ["NP_AT_2024", "S_AT_2024", "NDKM_AT_2024"]
    assert [x["n"] for x in e] == [3, 3, 4]
    assert e[1]["subs"] == [("RG", 2), ("ÖSG", 1)]
    assert e[2]["n_points"] == 2 and e[0]["n_points"] is None


def test_build_rows_names_and_code_fallback():
    entries = [{"layer": "S_AT_2024", "n": 3, "n_points": None, "subs": [("RG", 2), ("QQ", 1)]},
               {"layer": "NDKM_AT_2024", "n": 1500, "n_points": 7, "subs": []}]
    rows = natur_ebenen.build_rows(entries)
    assert rows[0][:2] == ["Umweltbundesamt [7]", "Sonstige Schutzgebiete (nur verordnete Kategorien)"]
    assert rows[1] == ["", "davon Ruhegebiet", "2"]
    assert rows[2][1] == "davon QQ"                  # fehlender Name -> Code
    assert "Flächen und Punkte" in rows[3][1] and "7 Punkte" in rows[3][2]


def test_run_writes_files_and_registers(tmp_path):
    pq = tmp_path / "schutzgebiete.parquet"
    g = _gdf()
    g[~g.KAT_SUB.isin(["SGNOG", "XYZ", "ÖSG"])].to_parquet(pq)
    Z.reset()
    natur_ebenen.run(tmp_path / "out", pq)
    md = (tmp_path / "out/tabellen/N1_natur_ebenen.md").read_text(encoding="utf-8")
    assert md.startswith("| Quelle |") and "Nationalparks | 3" in md and "davon Ruhegebiet | 2" in md
    assert (tmp_path / "out/tabellen/N1_natur_ebenen.csv").is_file()
    assert "N1_natur_ebenen" in (tmp_path / "out/tabellen/HERKUNFT.md").read_text(encoding="utf-8")
    reg = Z.current()
    assert reg["uba_n_np"]["wert"] == 3 and reg["uba_n_s"]["wert"] == 2 and reg["uba_n_s_rg"]["wert"] == 2
    Z.reset()


def test_osm_ausserhalb_amtlich(tmp_path):
    amt = np.zeros((3, 3), "uint8"); amt[0, 0] = 1; amt[0, 1] = 1
    osm = np.zeros((3, 3), "uint8"); osm[0, 1] = 1; osm[1, 1] = 1; osm[2, 2] = 1
    tif = tmp_path / "t.tif"
    with rasterio.open(tif, "w", driver="GTiff", height=3, width=3, count=2, dtype="uint8",
                       crs=wc.TARGET_CRS, transform=TRANSFORM) as ds:
        ds.write(amt, 1); ds.write(osm, 2)
    manifest = {"raster": {"pixel_size_m": 1000},
                "bands": [{"index": 1, "name": "nature_protection_areas"},
                          {"index": 2, "name": "osm_nature_protection_areas"}]}
    grenzen = _write_boundaries(tmp_path)
    n, km2 = weitere_zahlen.osm_ausserhalb_amtlich(tif, manifest, grenzen)
    assert n == 2 and km2 == 2.0                      # (1,1) und (2,2); (0,1) ist amtlich
