"""Leichter Test der Huellen-Auswahl in beispielkarten (synthetisch)."""
from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import box

from pipeline.analysis.whitepaper import beispielkarten as bk


def _gdf(rows):
    return gpd.GeoDataFrame(
        {"label": [r[0] for r in rows], "ist_streusiedlung": [r[1] for r in rows]},
        geometry=[r[2] for r in rows], crs=31287)


def test_select_hull_picks_streusiedlung_containing_point():
    g = _gdf([(1, 0, box(0, 0, 10, 10)), (2, 1, box(0, 0, 10, 10)), (3, 1, box(20, 20, 30, 30))])
    assert int(bk.select_hull(g, (5, 5))["label"]) == 2


def test_select_hull_fails_if_none():
    g = _gdf([(1, 0, box(0, 0, 10, 10)), (3, 1, box(20, 20, 30, 30))])
    with pytest.raises(bk.HullSelectionError):
        bk.select_hull(g, (5, 5))


def test_select_hull_fails_if_multiple():
    g = _gdf([(1, 1, box(0, 0, 10, 10)), (2, 1, box(4, 4, 14, 14))])
    with pytest.raises(bk.HullSelectionError):
        bk.select_hull(g, (5, 5))


def test_register_numbers_prefix(tmp_path):
    (tmp_path / "tabellen").mkdir()
    (tmp_path / "tabellen" / bk.JSON_NAME).write_text(
        '{"n_hausnummern":21,"hausnummer_min":19,"hausnummer_max":50,"n_bauflaechen":48,'
        '"n_bauflaechen_ns41":43,"n_bauflaechen_ns83":5,"n_wohn":48,"n_bev_gebaeude":48,'
        '"abstand_wohnbauland_m":1391.0,"abstand_siedlungspuffer_m":400.0,"flaeche_ha":11.75,'
        '"gemeinde":"Mortantsch","gkz":"61730"}')
    got = {}
    bk.register_numbers(lambda k, w, e, q: got.__setitem__(k, w), tmp_path)
    assert got["beispiel_haselbach.gkz"] == "61730" and all(k.startswith("beispiel_haselbach.") for k in got)


def test_window_bbox_uses_all_edges_and_warp_in_3857():
    import numpy as np
    from rasterio.transform import Affine

    # Rotierende Abbildung: Ecken allein ergaeben eine zu kleine Bbox.
    ang = np.radians(10)

    def fn(x, y):
        return x * np.cos(ang) - y * np.sin(ang), x * np.sin(ang) + y * np.cos(ang)

    tr = Affine(25, 0, 0, 0, -25, 1000)
    bb = bk.window_bbox_3857(tr, 40, 40, fn)
    cx, cy = fn(np.array([0, 1000, 0, 1000.]), np.array([0, 0, 1000, 1000.]))
    assert bb[0] == pytest.approx(min(cx), abs=1) and bb[2] == pytest.approx(max(cx), abs=1)
    assert bb[1] == pytest.approx(min(cy), abs=1) and bb[3] == pytest.approx(max(cy), abs=1)


def test_warp_to_3857_shape_and_content():
    import numpy as np
    from pyproj import Transformer
    from rasterio.transform import Affine

    x, y = Transformer.from_crs(4326, 31287, always_xy=True).transform(16.5, 48.1)
    tr = Affine(25, 0, x, 0, -25, y)
    m = np.ones((20, 20), bool)
    x3, y3 = Transformer.from_crs(31287, 3857, always_xy=True).transform(x + 250, y - 250)
    dst = Affine(37.4, 0, x3 - 200, 0, -37.4, y3 + 200)
    out = bk.warp_to_3857(m, tr, dst, (10, 10))
    assert out.shape == (10, 10) and out.any()
