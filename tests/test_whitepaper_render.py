"""Tests: Zahlenregister, Renderer, Streusiedlungs-Umfang (synthetisch), Tabellen-Registrierung."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.analysis.whitepaper import render, streusiedlung_umfang as su, zahlen as Z


@pytest.fixture(autouse=True)
def _clean():
    Z.reset()
    yield
    Z.reset()


def test_format_de():
    f = render.format_de
    assert f(10852) == "10 852"
    assert f(10852.4, 0) == "10 852"
    assert f(3171.04, 1) == "3 171,0"
    assert f(3.78, 2) == "3,78"
    assert f(28.64, 1, percent=True) == "28,6 %"
    assert f(22.2, 0, percent=True) == "22 %"
    assert f(0.2, 0) == "0"
    assert f(-1234.5, 1) == "-1 234,5"
    assert f(1234.0) == "1 234"


def test_render_placeholders_and_header(tmp_path):
    (tmp_path / "X1.md").write_text("| a |\n|---|\n| 1 |\n\n*Quelle*\n\n", encoding="utf-8")
    reg = {"a": {"wert": 1234567.0, "einheit": "km²"}, "b": {"wert": 12.34, "einheit": "%"},
           "unused": {"wert": 1, "einheit": "x"}}
    text, used = render.render("A {{z:a|0}} B {{z:b|%1}} C {{z:a}}\n{{tab:X1}}\nEnde", reg, tmp_path, "2026-10-13", "abc")
    assert text.splitlines()[0].startswith("<!-- GENERIERT aus paper_vorlage.md durch make whitepaper")
    assert "Stand: 2026-10-13, TIF abc" in text.splitlines()[0]
    assert "A 1 234 567 B 12,3 % C 1 234 567" in text
    assert "| 1 |" in text and "*Quelle*" in text
    assert used == {"a", "b"}


def test_render_unknown_key_is_error(tmp_path):
    with pytest.raises(render.RenderError, match="nope"):
        render.render("{{z:nope}} {{tab:fehlt}}", {}, tmp_path)
    with pytest.raises(render.RenderError, match="fehlt"):
        render.render("{{tab:fehlt}}", {}, tmp_path)


def test_run_missing_template(tmp_path):
    with pytest.raises(SystemExit):
        render.run(tmp_path / "nix.md", tmp_path / "paper.md", {}, tmp_path, "abc")


def test_run_writes_paper_and_reports_unused(tmp_path, capsys):
    v = tmp_path / "paper_vorlage.md"
    v.write_text("Wert {{z:a|1}}", encoding="utf-8")
    render.run(v, tmp_path / "paper.md", {"a": {"wert": 5.55, "einheit": "x"}, "b": {"wert": 1, "einheit": "x"}},
               tmp_path, "abc", "2026-10-13")
    assert (tmp_path / "paper.md").read_text(encoding="utf-8").endswith("Wert 5,5") or \
        (tmp_path / "paper.md").read_text(encoding="utf-8").endswith("Wert 5,6")
    assert "unbenutzte Schluessel: b" in capsys.readouterr().out


def test_registry_register_and_merge(tmp_path):
    Z.register("x_km2", 5.0, "km²", "q1")
    Z.register("x_km2", 5.0, "km²", "q1")  # gleicher Wert ok
    with pytest.raises(ValueError):
        Z.register("x_km2", 6.0, "km²", "q1")
    with pytest.raises(ValueError):
        Z.register("Bad Key", 1, "x", "q")
    Z.register("nan_ignored", float("nan"), "%", "q")
    assert "nan_ignored" not in Z.current()
    p = tmp_path / "zahlen.json"
    p.write_text(json.dumps({"alt": {"wert": 1, "einheit": "x", "quelle": "q", "stand": "old"}}), encoding="utf-8")
    merged = Z.write(p, "sha123456789")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert set(data) == {"alt", "x_km2"} == set(merged)
    assert data["alt"]["stand"] == "old"
    assert data["x_km2"] == {"wert": 5.0, "einheit": "km²", "quelle": "q1", "stand": "sha123456789"}


def test_slug():
    assert Z.slug("Eignung ≥ 10 ha") == "eignung_ge_10_ha"
    assert Z.slug("%") == "pct"
    assert Z.slug("Österreich km²") == "oesterreich_km2"


def _synthetic(n=160):
    z = lambda: np.zeros((n, n), bool)  # noqa: E731
    b = {k: z() for k in ["haeuser_im_gruenen_streusiedlung", "haeuser_im_gruenen", "haeuser_im_gruenen_ferienhaus",
                          "haeuser_im_gruenen_widmung", "haeuser_im_gruenen_noe_pdf", "all_exclusions",
                          "available_after_all_exclusions_raw", "available_cleaned_min_10ha",
                          "exclusion_nature", "exclusion_geography", "rail_main"]}
    # zwei Streusiedlungs-Gruppen (eine diagonal verbunden = 1 Gruppe, 8er-Nachbarschaft)
    b["haeuser_im_gruenen_streusiedlung"][40, 40] = True
    b["haeuser_im_gruenen_streusiedlung"][41, 41] = True
    b["haeuser_im_gruenen_streusiedlung"][120, 120] = True
    cell = 25.0
    zs = su.dilate(b["haeuser_im_gruenen_streusiedlung"], 750.0, cell, 64)
    b["haeuser_im_gruenen"] = zs.copy()
    # Gebiet: Zone S ist alles, was ausgeschlossen ist ... plus ein Streifen "rail" (Zone teils ueberlappt)
    b["rail_main"][:, 30:50] = True
    all_ = zs | b["rail_main"]
    b["all_exclusions"] = all_
    valid = np.ones((n, n), bool)
    b["available_after_all_exclusions_raw"] = valid & ~all_
    b["available_cleaned_min_10ha"] = su.min_area_filter(valid & ~all_, cell, 10.0)
    return b, cell


def test_streusiedlung_synthetic():
    b, cell = _synthetic()
    reg = np.ones((160, 160), np.uint8)
    reg[:, 80:] = 2
    res = su.compute(b, ["rail_main"], cell, reg, ["B", "K"], tile=64)
    assert res["gruppen"] == 2
    km2 = cell * cell / 1e6
    assert res["gruppenflaeche_km2"] == pytest.approx(3 * km2)
    assert res["checks"]["band7_abweichung_zellen"] == 0
    assert res["checks"]["all_exclusions_abweichung_zellen"] == 0
    # marginal = Zone ohne Ueberlapp mit rail
    zs = b["haeuser_im_gruenen"]
    assert res["zone_km2"] == pytest.approx(zs.sum() * km2)
    assert res["nur_km2"] == pytest.approx((zs & ~b["rail_main"]).sum() * km2)
    assert res["nur_km2"] < res["zone_km2"]
    assert res["gewinn_km2"] >= 0
    assert sum(d["zone_km2"] for d in res["land"].values()) == pytest.approx(res["zone_km2"])
    assert sum(d["nur_km2"] for d in res["land"].values()) == pytest.approx(res["nur_km2"])


def test_streusiedlung_selfcheck_fails_on_inconsistent_band():
    b, cell = _synthetic()
    b["all_exclusions"] = b["all_exclusions"].copy()
    b["all_exclusions"][5, 5] = True  # Zelle, die keine Rekonstruktion erklaert
    b["available_after_all_exclusions_raw"][5, 5] = False
    with pytest.raises(su.StreuCheckError):
        su.compute(b, ["rail_main"], cell, tile=64)


def test_streusiedlung_tables_and_register(tmp_path):
    b, cell = _synthetic()
    reg = np.ones((160, 160), np.uint8)
    res = su.compute(b, ["rail_main"], cell, reg, ["ST"], tile=64)
    res.pop("_masks")
    su.build_tables(res, "Quelle X", tmp_path)
    s2 = (tmp_path / "S2_streusiedlung_land.md").read_text(encoding="utf-8")
    assert "| Steiermark |" in s2
    assert "Gruppen" in (tmp_path / "S1_streusiedlung.md").read_text(encoding="utf-8")
    su.register(res)
    assert Z.current()["streu_gruppen"]["wert"] == 2
    assert "streu_land_st_nur_km2" in Z.current()


def test_zahlen_tabellen_from_csv(tmp_path):
    from pipeline.analysis.whitepaper import zahlen_tabellen as zt
    (tmp_path / "K_kernzahlen.csv").write_text(
        '# q\nKennzahl,Wert,Einheit,Anmerkung\nEignung ≥ 10 ha,"3 176,6",km²,AT\nEignung ≥ 10 ha,"3,8",%,AT\n',
        encoding="utf-8")
    (tmp_path / "D2_kriterien.csv").write_text(
        "# q\neinheit,band,name,B,K,N,O,S,ST,T,V,W,AT\n"
        "km2,21,nature_protection_areas,1,2,3,4,5,6,7,8,9,45.5\n"
        "%,21,nature_protection_areas,1,2,3,4,5,6,7,8,9,28.2\n", encoding="utf-8")
    zt.register_k(tmp_path)
    zt._register_long(tmp_path, "D2_kriterien.csv", "d2", "band", "D2")
    reg = Z.current()
    assert reg["k_eignung_ge_10_ha_km2"]["wert"] == 3176.6
    assert reg["k_eignung_ge_10_ha_pct"]["wert"] == 3.8
    assert reg["d2_km2_nature_protection_areas_at"]["wert"] == 45.5
    zt.register_natur_aliase()
    assert reg["natur_amtlich_km2"]["wert"] == 45.5


def test_tab_include_drops_leading_heading(tmp_path):
    (tmp_path / "X2.md").write_text("# L1 — Titel\n\n| a |\n|---|\n| 1 |\n\n*Quelle*\n\nLegende\n", encoding="utf-8")
    text, _ = render.render("Kopf\n{{tab:X2}}\nEnde", {}, tmp_path, "2026-10-13", "abc")
    assert "L1 — Titel" not in text
    assert "Kopf\n| a |" in text and "*Quelle*" in text and "Legende" in text
