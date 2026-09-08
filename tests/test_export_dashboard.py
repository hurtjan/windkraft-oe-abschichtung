"""pipeline/export/dashboard.py: die Abnahmebedingung von W4.1, verdrahtet.

W4.1s Abnahme lautet: "Liest ausschließlich das Manifest; keine Bandnamen im
Code. Läuft gegen ein Manifest mit geänderter Bandzahl ohne Anpassung."
(``docs/rewrite/PLAN.md`` §7). W4.1 hat beides von Hand belegt und dabei
selbst einen Treffer gefunden — einen Bandnamen in einem Docstring-Beispiel,
den es danach umformuliert hat. Ein Handbeleg findet so etwas **einmal**;
das ist der Unterschied zwischen einem Nachweis und einer Zusicherung.
``tests/`` gehört W4.3, also steht die Zusicherung hier.

## Warum dieses Modul dem Test nicht gehört

``pipeline/export/dashboard.py`` gehört W4.1, nicht W4.3 (PLAN.md §8,
Regel 1: ein Pfad, ein Besitzer). Diese Datei **liest** es — als Quelltext
für den Grep-Test und als Importziel für alles Übrige — und ändert daran
nichts.

## Erst nach dem Zusammenführen der Welle 4 grün

W4.1 liegt zum Zeitpunkt dieses Pakets auf Zweig ``4.1`` (Commit
``68ab19c``) und ist im Worktree von W4.3 nicht vorhanden. Solange
``pipeline/export/dashboard.py`` fehlt, überspringt sich dieses Modul
geschlossen — mit einer Begründung, die genau das sagt. Nach dem Merge der
Welle 4 laufen die Tests ohne weiteres Zutun an.

Bewusst **kein** Umbau, der sie auch ohne das Modul grün macht: ein Test,
der ohne sein Prüfobjekt besteht, prüft nichts. Und bewusst **kein**
hart fehlschlagender Platzhalter: das machte jedes ``make test`` in jedem
anderen Worktree der Welle 4 rot, ohne dass dort irgendetwas kaputt wäre.
Fehlt das Modul, ist die Aussage "nicht geprüft" — genau das, was ein Skip
bedeutet. Ist es da, wird geprüft.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DASHBOARD_QUELLE = PROJECT_ROOT / "pipeline" / "export" / "dashboard.py"

if not DASHBOARD_QUELLE.is_file():
    pytest.skip(
        f"{DASHBOARD_QUELLE} nicht vorhanden - das Modul gehoert W4.1 (Zweig 4.1, "
        "Commit 68ab19c) und erreicht diesen Zweig erst mit dem Zusammenfuehren der "
        "Welle 4. Diese Tests werden dort ohne weiteres Zutun gruen.",
        allow_module_level=True,
    )

from pipeline import contract  # noqa: E402
from pipeline.export import dashboard  # noqa: E402

ECHTES_MANIFEST = contract.PRODUCTS["abschichtung_bands_json"]


# ---------------------------------------------------------------------------
# Ein synthetisches Manifest: andere Bandzahl, andere Namen, andere Rollen.
# Genau der Härtetest aus W4.1s Abnahme - hier als Fixture, damit jeder Test
# darunter mit seiner eigenen, unversehrten Kopie arbeitet.
# ---------------------------------------------------------------------------

def _fremdes_manifest() -> dict:
    """Fünf Bänder, kein einziger Name aus der echten Kette.

    Absichtlich in einer anderen Sprache/Domäne benannt: fiele dem Modul
    irgendwo ein echter Bandname aus der Abschichtung heraus, wäre er hier
    unauflösbar und der Bericht bräche - statt still das Falsche zu tun.
    """
    return {
        "schema_version": "2.0.0",
        "generated_at": "2026-01-01T00:00:00Z",
        "pipeline": "irgendwas_anderes",
        "band_schema": "fremd-5",
        "raster_file": "fremd.tif",
        "band_count": 5,
        "raster": {
            "crs": "EPSG:3857",
            "width": 10,
            "height": 10,
            "pixel_size_m": 1.0,
            "dtype": "uint8",
            "nodata": 0,
        },
        "category_order": ["Alpha", "Beta"],
        "bands": [
            {"index": 1, "name": "zutat_mehl", "label_de": "Mehl", "category": "Alpha",
             "rolle": "bedingung", "puffer_m": None, "puffer_hinweis": None,
             "quelle": ["speisekammer"], "abgeleitet_von": []},
            {"index": 2, "name": "zutat_wasser", "label_de": "Wasser", "category": "Alpha",
             "rolle": "bedingung", "puffer_m": 3.5, "puffer_hinweis": None,
             "quelle": ["speisekammer"], "abgeleitet_von": []},
            {"index": 3, "name": "teig", "label_de": "Teig", "category": "Beta",
             "rolle": "aggregat_gesamt", "puffer_m": None, "puffer_hinweis": None,
             "quelle": [], "abgeleitet_von": ["zutat_mehl", "zutat_wasser"]},
            {"index": 4, "name": "brot", "label_de": "Brot", "category": "Beta",
             "rolle": "verfuegbarkeit_bereinigt", "puffer_m": None,
             "puffer_hinweis": "Kein Puffer, nur Hitze.",
             "quelle": [], "abgeleitet_von": ["teig"]},
            {"index": 5, "name": "krumen", "label_de": "Krumen", "category": "Gamma",
             "rolle": "referenz", "puffer_m": None, "puffer_hinweis": None,
             "quelle": [], "abgeleitet_von": ["brot"]},
        ],
        "parameters": {"OFENTEMPERATUR_C": "230"},
        "sources": {"speisekammer": {"pfad": "x/y.zip", "stand": "01.01.2026", "rolle": "Zutaten"}},
        "caveats": [{"id": "ofen_ungleichmaessig", "severity": "methodisch",
                     "affects": {"bands": [4, 5]}, "text_de": "Der Ofen heizt hinten staerker."}],
        "zutat_mehl_wirkungspfad": ["zutat_mehl", "teig", "brot", "krumen"],
    }


@pytest.fixture()
def fremdes_manifest() -> dict:
    return _fremdes_manifest()


# ---------------------------------------------------------------------------
# 1. Der Grep-Test: kein Bandname der echten Kette steht im Quelltext.
#    (Vorschlag 1 aus W4.1s Übergabe - die wichtigste, weil sie eine
#    Abnahmebedingung prüft, die sonst nur als Behauptung existiert.)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not ECHTES_MANIFEST.exists(),
    reason=(
        f"{ECHTES_MANIFEST} fehlt - ohne das echte Manifest gibt es keine Liste "
        "echter Bandnamen, gegen die zu greppen waere. 'make finalize' zuerst."
    ),
)
def test_kein_bandname_der_echten_kette_steht_im_quelltext():
    """Die Abnahmebedingung von W4.1, mechanisch geprüft.

    Die Namen kommen aus dem **echten** Manifest, nicht aus einer Liste in
    dieser Datei: sonst wäre genau die zweite, von Hand synchron zu
    haltende Bandliste entstanden, die dieses ganze Modul vermeiden soll
    (PLAN.md §13.6).

    Geprüft wird auf die Namen der **heutigen** 38 Bänder. Der
    Moduldocstring von ``dashboard.py`` nennt bewusst mehrere Bandnamen der
    alten 63-Band-Kette (``power_380_400kv`` und andere) als Beispiel für
    genau den Fehler, den es nicht wiederholt - die sind kein Verstoß,
    stehen in keinem heutigen Manifest und werden hier deshalb auch nicht
    gefunden.
    """
    manifest = json.loads(ECHTES_MANIFEST.read_text(encoding="utf-8"))
    bandnamen = [b["name"] for b in manifest["bands"]]
    assert len(bandnamen) == 38, "Unerwartete Bandzahl im echten Manifest."

    quelltext = DASHBOARD_QUELLE.read_text(encoding="utf-8")
    treffer = sorted(name for name in bandnamen if name in quelltext)

    assert not treffer, (
        f"{DASHBOARD_QUELLE.relative_to(PROJECT_ROOT)} enthaelt {len(treffer)} Bandnamen "
        f"woertlich im Quelltext: {treffer}. W4.1s Abnahme verlangt 'keine Bandnamen im "
        "Code' - eine Bandliste, die in Code UND Manifest lebt, laeuft auseinander, ohne "
        "dass es auffaellt (PLAN.md Paragraph 13.6). Auch ein Docstring-Beispiel zaehlt: "
        "es wird beim naechsten Schema-Wechsel genauso falsch wie Code."
    )


# ---------------------------------------------------------------------------
# 2. build_report() gegen ein fremdes Manifest (Vorschlag 2).
# ---------------------------------------------------------------------------

def test_build_report_laeuft_gegen_ein_fremdes_manifest_unveraendert_durch(fremdes_manifest):
    """Andere Bandzahl, andere Namen, andere Kategorien - derselbe Code.

    Das ist der Härtetest, den W4.1 einmalig von Hand gefahren hat. Wäre
    irgendwo ein Bandname oder die Zahl 38 verdrahtet, bräche hier etwas.
    """
    report = dashboard.build_report(fremdes_manifest, raster_path=None)

    assert report["validation"]["ok"], report["validation"]["problems"]
    assert report["source_manifest"]["band_count"] == 5
    assert [b["name"] for b in report["bands"]] == [
        "zutat_mehl", "zutat_wasser", "teig", "brot", "krumen"
    ]
    # Gruppierung läuft über rolle - Schema-Vokabular, kein Bandwissen.
    assert report["role_counts"] == {
        "bedingung": 2,
        "aggregat_gesamt": 1,
        "verfuegbarkeit_bereinigt": 1,
        "referenz": 1,
    }
    # category_order aus dem Manifest wird respektiert, und eine Kategorie,
    # die dort NICHT steht ("Gamma"), geht trotzdem nicht verloren.
    assert report["category_order"] == ["Alpha", "Beta"]
    assert [b["name"] for b in report["categories"]["Gamma"]] == ["krumen"]
    # Der Wirkungspfad wird über das Namenssuffix gefunden, nicht über einen
    # konkreten Bandnamen - hier heißt er anders als in der echten Kette.
    assert report["impact_paths"] == {
        "zutat_mehl_wirkungspfad": ["zutat_mehl", "teig", "brot", "krumen"]
    }
    assert report["raster_check"]["checked"] is False


def test_build_report_ist_ohne_raster_vollstaendig(fremdes_manifest):
    """Der Manifest-Teil steht für sich - ``raster_path=None`` ist kein
    halber Bericht, sondern ein vollständiger ohne Raster-Abgleich."""
    report = dashboard.build_report(fremdes_manifest, raster_path=None)
    for schluessel in ("validation", "roles", "categories", "sources", "caveats",
                       "impact_paths", "bands", "raster_meta"):
        assert schluessel in report, f"{schluessel} fehlt im Bericht"


# ---------------------------------------------------------------------------
# 3. Die beiden Prüffunktionen gegen kaputte Manifeste (Vorschlag 3).
#    Direkt aufgerufen statt über build_report: so sagt ein Fehlschlag,
#    WELCHE der beiden Prüfungen ausgefallen ist, statt nur "irgendeine".
# ---------------------------------------------------------------------------

def test_shape_pruefung_findet_band_count_mismatch(fremdes_manifest):
    fremdes_manifest["band_count"] = 4  # bands[] hat weiterhin 5
    probleme = dashboard._validate_manifest_shape(fremdes_manifest)
    assert any("band_count" in p for p in probleme), probleme


def test_shape_pruefung_findet_luecke_in_den_indizes(fremdes_manifest):
    fremdes_manifest["bands"][2]["index"] = 99
    probleme = dashboard._validate_manifest_shape(fremdes_manifest)
    assert any("index" in p for p in probleme), probleme


def test_shape_pruefung_findet_doppelten_bandnamen(fremdes_manifest):
    fremdes_manifest["bands"][1]["name"] = "zutat_mehl"
    probleme = dashboard._validate_manifest_shape(fremdes_manifest)
    assert any("Duplikate" in p for p in probleme), probleme


def test_referenzpruefung_findet_haengenden_abgeleitet_von_verweis(fremdes_manifest):
    fremdes_manifest["bands"][3]["abgeleitet_von"] = ["gibt_es_nicht"]
    probleme = dashboard._validate_references(fremdes_manifest)
    assert any("gibt_es_nicht" in p for p in probleme), probleme


def test_referenzpruefung_findet_unbekannten_quellen_schluessel(fremdes_manifest):
    fremdes_manifest["bands"][0]["quelle"] = ["nirgendwo"]
    probleme = dashboard._validate_references(fremdes_manifest)
    assert any("nirgendwo" in p for p in probleme), probleme


def test_referenzpruefung_findet_unbekannten_caveat_index(fremdes_manifest):
    fremdes_manifest["caveats"][0]["affects"]["bands"] = [4, 77]
    probleme = dashboard._validate_references(fremdes_manifest)
    assert any("77" in p for p in probleme), probleme


def test_referenzpruefung_findet_haengenden_wirkungspfad_eintrag(fremdes_manifest):
    fremdes_manifest["zutat_mehl_wirkungspfad"] = ["zutat_mehl", "phantomband"]
    probleme = dashboard._validate_references(fremdes_manifest)
    assert any("phantomband" in p for p in probleme), probleme


def test_ein_kaputtes_manifest_macht_den_bericht_nicht_ok(fremdes_manifest):
    """Und dasselbe noch einmal über die öffentliche Oberfläche: die
    Probleme der beiden Prüfungen landen tatsächlich im Bericht, statt
    unterwegs verloren zu gehen."""
    fremdes_manifest["band_count"] = 4
    fremdes_manifest["bands"][3]["abgeleitet_von"] = ["gibt_es_nicht"]
    report = dashboard.build_report(fremdes_manifest, raster_path=None)
    assert report["validation"]["ok"] is False
    assert len(report["validation"]["problems"]) >= 2


# ---------------------------------------------------------------------------
# 4. cross_check_raster gegen ein winziges GeoTIFF (Vorschlag 4).
# ---------------------------------------------------------------------------

def _schreibe_mini_tif(pfad: Path, bandnamen: list[str]) -> Path:
    import numpy as np  # noqa: PLC0415
    import rasterio  # noqa: PLC0415
    from rasterio.transform import from_origin  # noqa: PLC0415

    with rasterio.open(
        pfad, "w", driver="GTiff", width=2, height=2, count=len(bandnamen),
        dtype="uint8", crs="EPSG:3857", transform=from_origin(0, 2, 1, 1),
    ) as dst:
        for i, name in enumerate(bandnamen, start=1):
            dst.write(np.zeros((2, 2), dtype="uint8"), i)
            dst.set_band_description(i, name)
    return pfad


def test_cross_check_raster_ist_zufrieden_bei_gleicher_reihenfolge(tmp_path, fremdes_manifest):
    tif = _schreibe_mini_tif(
        tmp_path / "gleich.tif", [b["name"] for b in fremdes_manifest["bands"]]
    )
    ergebnis = dashboard.cross_check_raster(fremdes_manifest, tif)
    assert ergebnis["checked"] is True
    assert ergebnis["band_count_match"] is True
    assert ergebnis["names_match"] is True
    assert ergebnis["mismatches"] == []


def test_cross_check_raster_findet_vertauschte_baender(tmp_path, fremdes_manifest):
    """Genau die Falle aus docs/HANDOFF.md: gleiche Bandzahl, gleiche Namen,
    aber zwei davon vertauscht. Positionsbasiertes Lesen bekäme still das
    falsche Band - der Kopf-Abgleich sieht es."""
    namen = [b["name"] for b in fremdes_manifest["bands"]]
    namen[0], namen[1] = namen[1], namen[0]
    tif = _schreibe_mini_tif(tmp_path / "vertauscht.tif", namen)

    ergebnis = dashboard.cross_check_raster(fremdes_manifest, tif)
    assert ergebnis["checked"] is True
    assert ergebnis["band_count_match"] is True, "Bandzahl stimmt - nur die Reihenfolge nicht."
    assert ergebnis["names_match"] is False
    assert {m["index"] for m in ergebnis["mismatches"]} == {1, 2}


def test_cross_check_raster_findet_abweichende_bandzahl(tmp_path, fremdes_manifest):
    tif = _schreibe_mini_tif(tmp_path / "zu_wenig.tif", ["zutat_mehl", "zutat_wasser"])
    ergebnis = dashboard.cross_check_raster(fremdes_manifest, tif)
    assert ergebnis["band_count_match"] is False
    assert ergebnis["raster_band_count"] == 2
    assert ergebnis["manifest_band_count"] == 5
    assert ergebnis["names_match"] is False


def test_cross_check_raster_meldet_fehlende_datei_statt_zu_brechen(tmp_path, fremdes_manifest):
    ergebnis = dashboard.cross_check_raster(fremdes_manifest, tmp_path / "gibt_es_nicht.tif")
    assert ergebnis["checked"] is False
    assert "nicht gefunden" in ergebnis["reason"]


# ---------------------------------------------------------------------------
# 5. CLI-Rauchtest (Vorschlag 5).
# ---------------------------------------------------------------------------

def test_cli_schreibt_json_und_html_und_endet_mit_null(tmp_path, fremdes_manifest):
    """``main()`` von Anfang bis Ende, ohne Raster und ohne die echten
    Produktpfade anzufassen: eigenes ``--manifest``, eigenes ``--out``."""
    manifest_pfad = tmp_path / "fremd.bands.json"
    manifest_pfad.write_text(json.dumps(fremdes_manifest, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "dashboard"

    code = dashboard.main(
        ["--manifest", str(manifest_pfad), "--out", str(out_dir), "--skip-raster"]
    )

    assert code == 0
    bericht = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert bericht["validation"]["ok"] is True
    assert bericht["source_manifest"]["band_count"] == 5
    html_text = (out_dir / "index.html").read_text(encoding="utf-8")
    assert html_text.lstrip().startswith("<!DOCTYPE html>")
    assert "zutat_mehl" in html_text, "Die Bandnamen aus dem Manifest fehlen im HTML."


def test_cli_meldet_ein_kaputtes_manifest_mit_exit_code_1(tmp_path, fremdes_manifest):
    """Das Werkzeug bewertet und meldet - ein inkonsistentes Manifest darf
    nicht mit Exit 0 durchrutschen."""
    fremdes_manifest["band_count"] = 4
    manifest_pfad = tmp_path / "kaputt.bands.json"
    manifest_pfad.write_text(json.dumps(fremdes_manifest, ensure_ascii=False), encoding="utf-8")

    code = dashboard.main(
        ["--manifest", str(manifest_pfad), "--out", str(tmp_path / "d"), "--skip-raster"]
    )
    assert code == 1


def test_cli_bricht_bei_fehlendem_manifest_mit_klarer_meldung_ab(tmp_path):
    with pytest.raises(FileNotFoundError, match="fehlt"):
        dashboard.main(["--manifest", str(tmp_path / "nicht_da.json"), "--skip-raster"])
