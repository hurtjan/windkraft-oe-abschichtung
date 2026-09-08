"""Unit-Tests für pipeline/validate.py (Paket W3.2, docs/rewrite/PLAN.md §6).

Schwerpunkt liegt auf der Ampel-Einstufung selbst: synthetische Zahlen genau
an den Schwellwerten (grün/gelb/rot, beide Bänder-Gruppen, Referenzbänder,
der §13.9-Wächter für unerwartete Bänder) - ein Test, der nur den heutigen
Realwert (die neun bekannten Bänder) festschreibt, würde nichts über die
Grenzfälle aussagen. Daneben: die Nenner-Entscheidung aus dem Moduldocstring
(gesetzte Pixel des Referenzbandes, nicht Gesamtzellzahl) als eigener
Regressionstest, die 4er-Nachbarschaft der Flächenanalyse (dasselbe Muster
wie tests/test_min_area_filter.py) und das Register (Paket-Isolation,
ursache-Erhalt bei erneutem Lauf, erzwungener Platzhalter bei unerwarteten
Bändern).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.band_manifest import (  # noqa: E402
    ROLE_AGGREGAT_KATEGORIE,
    ROLE_BEDINGUNG,
    ROLE_REFERENZ,
    ROLE_UNSCHAERFE,
)

import pipeline.validate as validate_module  # noqa: E402
from pipeline.validate import (  # noqa: E402
    AMPEL_AKZEPTIERT,
    AMPEL_BITGLEICH,
    AMPEL_GELB,
    AMPEL_GRUEN,
    AMPEL_ROT,
    GELB_FLAECHE_HA,
    GELB_FLAECHE_KM2,
    GELB_ANTEIL_PROZENT,
    GRUEN_FLAECHE_HA,
    GRUEN_FLAECHE_KM2,
    GRUEN_ANTEIL_PROZENT,
    REGISTER_COLUMNS,
    URSACHE_PLATZHALTER,
    URSACHE_UNERWARTET,
    BandResult,
    _largest_connected_component_px,
    _load_existing_register,
    _schwerpunkt_bundesland,
    classify,
    measure_bands,
    write_register,
)

CELL_M = 25.0  # 1 Zelle = 625 m²; 1 ha = 16 Zellen; 1 km² = 1600 Zellen


def _result(
    role: str,
    pixel_abs: int = 1,
    anteil_prozent: float = 0.0,
    groesste_flaeche_ha: float = 0.0,
    flaeche_km2: float = 0.0,
    band_name: str = "irgendein_band",
) -> BandResult:
    return BandResult(
        band_nr=1,
        band_name=band_name,
        role=role,
        pixel_abs=pixel_abs,
        gesetzte_pixel_referenz=1000,
        anteil_prozent=anteil_prozent,
        anteil_prozent_kontrolle=0.0,
        groesste_flaeche_ha=groesste_flaeche_ha,
        flaeche_km2=flaeche_km2,
        schwerpunkt_bundesland="Wien",
    )


# ---------------------------------------------------------------------------
# Ampel: bitgleich
# ---------------------------------------------------------------------------

def test_bitgleich_wenn_keine_abweichenden_pixel():
    r = _result(ROLE_BEDINGUNG, pixel_abs=0, anteil_prozent=99, groesste_flaeche_ha=99)
    ampel, unerwartet = classify(r, erlaubte_baender=set())
    assert ampel == AMPEL_BITGLEICH
    assert unerwartet is False


# ---------------------------------------------------------------------------
# Ampel: Bänder 1-26 (bedingung) - anteil UND größte Fläche zusammen
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "anteil,flaeche,erwartet",
    [
        (GRUEN_ANTEIL_PROZENT, GRUEN_FLAECHE_HA, AMPEL_GRUEN),  # beide genau am Gruen-Rand
        (GRUEN_ANTEIL_PROZENT + 1e-6, GRUEN_FLAECHE_HA, AMPEL_GELB),  # anteil knapp drueber
        (GRUEN_ANTEIL_PROZENT, GRUEN_FLAECHE_HA + 1e-6, AMPEL_GELB),  # flaeche knapp drueber
        (GELB_ANTEIL_PROZENT, GELB_FLAECHE_HA, AMPEL_GELB),  # beide genau am Gelb-Rand
        (GELB_ANTEIL_PROZENT + 1e-6, GELB_FLAECHE_HA, AMPEL_ROT),  # anteil ueber Gelb-Rand
        (GELB_ANTEIL_PROZENT, GELB_FLAECHE_HA + 1e-6, AMPEL_ROT),  # flaeche ueber Gelb-Rand
        # anteil fuer sich allein waere gruen, aber die Flaeche sprengt den
        # Gelb-Rand - BEIDE Kennzahlen muessen halten, eine reicht nicht.
        (0.001, 1000.0, AMPEL_ROT),
    ],
)
def test_bedingung_braucht_beide_kennzahlen_unter_schwelle(anteil, flaeche, erwartet):
    r = _result(ROLE_BEDINGUNG, anteil_prozent=anteil, groesste_flaeche_ha=flaeche)
    ampel, unerwartet = classify(r, erlaubte_baender={r.band_name})
    assert ampel == erwartet
    assert unerwartet is False


# ---------------------------------------------------------------------------
# Ampel: Bänder 27-36 (Aggregate/Verfügbarkeit) - absolutes km²-Budget
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "flaeche_km2,erwartet",
    [
        (GRUEN_FLAECHE_KM2, AMPEL_GRUEN),
        (GRUEN_FLAECHE_KM2 + 1e-9, AMPEL_GELB),
        (GELB_FLAECHE_KM2, AMPEL_GELB),
        (GELB_FLAECHE_KM2 + 1e-9, AMPEL_ROT),
    ],
)
@pytest.mark.parametrize("role", [ROLE_AGGREGAT_KATEGORIE, ROLE_UNSCHAERFE])
def test_aggregat_baender_nach_absolutem_km2_budget(role, flaeche_km2, erwartet):
    # anteil_prozent/groesste_flaeche_ha bewusst riesig gesetzt - fuer diese
    # Gruppe zaehlt laut §6 nur die Gesamtflaeche in km², nicht Prozent oder
    # groesste zusammenhaengende Flaeche.
    r = _result(role, anteil_prozent=99.0, groesste_flaeche_ha=99999.0, flaeche_km2=flaeche_km2)
    ampel, unerwartet = classify(r, erlaubte_baender={r.band_name})
    assert ampel == erwartet
    assert unerwartet is False


# ---------------------------------------------------------------------------
# Ampel: Referenzbänder 37/38 - kein Gruen-/Gelb-Korridor
# ---------------------------------------------------------------------------

def test_referenzband_jede_abweichung_ist_rot_auch_minimal():
    r = _result(ROLE_REFERENZ, pixel_abs=1, anteil_prozent=0.0000001, groesste_flaeche_ha=0.0000001)
    ampel, unerwartet = classify(r, erlaubte_baender={r.band_name})
    assert ampel == AMPEL_ROT
    assert unerwartet is False


# ---------------------------------------------------------------------------
# §13.9-Wächter: Bänder außerhalb des erlaubten Wirkungspfads sind ein Fehler
# ---------------------------------------------------------------------------

def test_unerwartetes_band_wird_zu_rot_erzwungen_obwohl_metrik_gruen_waere():
    r = _result(
        ROLE_BEDINGUNG,
        anteil_prozent=GRUEN_ANTEIL_PROZENT,
        groesste_flaeche_ha=GRUEN_FLAECHE_HA,
        band_name="nicht_im_wirkungspfad",
    )
    ampel, unerwartet = classify(r, erlaubte_baender={"ein_anderes_band"})
    assert ampel == AMPEL_ROT
    assert unerwartet is True


def test_band_im_wirkungspfad_wird_nicht_als_unerwartet_markiert():
    r = _result(
        ROLE_BEDINGUNG,
        anteil_prozent=GRUEN_ANTEIL_PROZENT,
        groesste_flaeche_ha=GRUEN_FLAECHE_HA,
        band_name="geography_water_bodies",
    )
    ampel, unerwartet = classify(r, erlaubte_baender={"geography_water_bodies"})
    assert ampel == AMPEL_GRUEN
    assert unerwartet is False


# ---------------------------------------------------------------------------
# Größte zusammenhängende Fläche: 4er-Nachbarschaft, wie min_area_filter()
# (tests/test_min_area_filter.py) - Eckberührung verbindet nicht.
# ---------------------------------------------------------------------------

def test_diagonal_beruehrung_zaehlt_nicht_als_eine_flaeche():
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:13, 10:13] = True  # 9 Zellen
    mask[13:16, 13:16] = True  # 9 Zellen, nur Eckkontakt zum ersten Block
    assert _largest_connected_component_px(mask) == 9


def test_kantenkontakt_verkettet_zu_einer_flaeche():
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:13, 10:13] = True  # 9 Zellen
    mask[13:16, 10:13] = True  # 9 Zellen, gemeinsame Kante
    assert _largest_connected_component_px(mask) == 18


def test_leere_maske_hat_keine_flaeche():
    mask = np.zeros((10, 10), dtype=bool)
    assert _largest_connected_component_px(mask) == 0


# ---------------------------------------------------------------------------
# Schwerpunkt Bundesland
# ---------------------------------------------------------------------------

def test_schwerpunkt_ist_das_bundesland_mit_den_meisten_treffern():
    bl_raster = np.array([[1, 1, 2], [1, 2, 0], [0, 0, 0]], dtype=np.uint8)
    codes = {1: "Wien", 2: "Vorarlberg"}
    diff_mask = np.array([[True, True, True], [True, True, False], [False, False, False]])
    # Code 1 (Wien) trifft 3x, Code 2 (Vorarlberg) trifft 2x.
    assert _schwerpunkt_bundesland(diff_mask, bl_raster, codes) == "Wien"


def test_schwerpunkt_ausserhalb_aller_bundeslaender():
    bl_raster = np.zeros((3, 3), dtype=np.uint8)
    codes = {1: "Wien"}
    diff_mask = np.ones((3, 3), dtype=bool)
    assert _schwerpunkt_bundesland(diff_mask, bl_raster, codes) == "(ausserhalb aller Bundeslaender)"


def test_schwerpunkt_leere_maske_ist_leerer_string():
    bl_raster = np.zeros((3, 3), dtype=np.uint8)
    codes = {1: "Wien"}
    diff_mask = np.zeros((3, 3), dtype=bool)
    assert _schwerpunkt_bundesland(diff_mask, bl_raster, codes) == ""


# ---------------------------------------------------------------------------
# measure_bands(): echte kleine GeoTIFFs, kein Zugriff auf derived/prep/admin
# (Bundesland-Rasterisierung wird gemockt - eigenes Verhalten ist oben schon
# fuer sich getestet).
# ---------------------------------------------------------------------------

def _grid_transform(cells: int = 20) -> Affine:
    return Affine(CELL_M, 0.0, 500_000.0, 0.0, -CELL_M, 400_000.0 + cells * CELL_M)


def _write_tif(path: Path, bands: dict[str, np.ndarray]) -> None:
    names = list(bands.keys())
    shape = next(iter(bands.values())).shape
    profile = {
        "driver": "GTiff",
        "height": shape[0],
        "width": shape[1],
        "count": len(names),
        "dtype": "uint8",
        "crs": "EPSG:31287",
        "transform": _grid_transform(shape[0]),
    }
    with rasterio.open(path, "w", **profile) as dst:
        for i, name in enumerate(names, start=1):
            dst.write(bands[name].astype("uint8"), i)
            dst.set_band_description(i, name)


def test_measure_bands_gesetzte_pixel_nenner_ist_das_referenzband_nicht_die_gesamtzellzahl(tmp_path, monkeypatch):
    # 20x20 = 400 Zellen insgesamt. Referenzband hat nur 100 gesetzte Zellen
    # (25 % der Flaeche); 5 davon weichen im neuen Band ab. §6 verlangt den
    # Anteil an den GESETZTEN Pixeln des Bandes (5/100 = 5 %), nicht an der
    # Gesamtzellzahl (5/400 = 1,25 %) - genau das unterscheidet diesen Test.
    ref = np.zeros((20, 20), dtype=np.uint8)
    ref[0:10, 0:10] = 1  # 100 gesetzte Zellen
    new = ref.copy()
    new[0:1, 0:5] = 0  # 5 Zellen kippen von 1 auf 0

    new_tif = tmp_path / "new.tif"
    ref_tif = tmp_path / "ref.tif"
    _write_tif(new_tif, {"official_settlement_source": new})
    _write_tif(ref_tif, {"official_settlement_source": ref})

    # Monkeypatch ueber das bereits importierte Modulobjekt, nicht ueber den
    # gepunkteten String: tests/test_contract.py tauscht sys.modules['pipeline']
    # fuer test_import_does_not_touch_filesystem() aus (pop + Neuimport von
    # nur 'pipeline.contract'), danach findet pytests string-basiertes
    # monkeypatch.setattr("pipeline.validate...") das Attribut nicht mehr -
    # das Modulobjekt selbst bleibt davon unberuehrt.
    dummy_bl = np.zeros((20, 20), dtype=np.uint8)
    monkeypatch.setattr(
        validate_module,
        "_build_bundesland_code_raster",
        lambda grid: (dummy_bl, {1: "Wien"}),
    )

    [result] = measure_bands(new_tif, ref_tif)
    assert result.pixel_abs == 5
    assert result.gesetzte_pixel_referenz == 100
    assert result.anteil_prozent == pytest.approx(5.0)
    # Kontrollzahl gegen die Gesamtzellzahl - zur Einordnung im Bericht, geht
    # NICHT in die Ampel/das Register ein.
    assert result.anteil_prozent_kontrolle == pytest.approx(5 / 400 * 100)


def test_measure_bands_bitgleiches_band_hat_keine_flaeche_und_keinen_schwerpunkt(tmp_path, monkeypatch):
    arr = np.zeros((10, 10), dtype=np.uint8)
    arr[2:4, 2:4] = 1
    new_tif = tmp_path / "new.tif"
    ref_tif = tmp_path / "ref.tif"
    _write_tif(new_tif, {"official_settlement_source": arr})
    _write_tif(ref_tif, {"official_settlement_source": arr})

    monkeypatch.setattr(
        validate_module,
        "_build_bundesland_code_raster",
        lambda grid: (_ for _ in ()).throw(AssertionError("sollte fuer bitgleiche Baender nicht aufgerufen werden")),
    )

    [result] = measure_bands(new_tif, ref_tif)
    assert result.pixel_abs == 0
    assert result.groesste_flaeche_ha == 0
    assert result.schwerpunkt_bundesland == ""


def test_measure_bands_bricht_bei_unterschiedlichen_bandnamen_ab(tmp_path):
    arr = np.zeros((5, 5), dtype=np.uint8)
    new_tif = tmp_path / "new.tif"
    ref_tif = tmp_path / "ref.tif"
    _write_tif(new_tif, {"band_a": arr})
    _write_tif(ref_tif, {"band_b": arr})
    with pytest.raises(ValueError, match="Bandnamen"):
        measure_bands(new_tif, ref_tif)


def test_measure_bands_bricht_bei_unterschiedlichem_gitter_ab(tmp_path):
    arr5 = np.zeros((5, 5), dtype=np.uint8)
    arr6 = np.zeros((6, 6), dtype=np.uint8)
    new_tif = tmp_path / "new.tif"
    ref_tif = tmp_path / "ref.tif"
    _write_tif(new_tif, {"band_a": arr5})
    _write_tif(ref_tif, {"band_a": arr6})
    with pytest.raises(ValueError, match="Gitter"):
        measure_bands(new_tif, ref_tif)


# ---------------------------------------------------------------------------
# Register: Paket-Isolation, ursache-Erhalt, erzwungener Platzhalter
# ---------------------------------------------------------------------------

def _band(nr: int, name: str, pixel_abs: int = 10) -> BandResult:
    return BandResult(
        band_nr=nr,
        band_name=name,
        role=ROLE_BEDINGUNG,
        pixel_abs=pixel_abs,
        gesetzte_pixel_referenz=1000,
        anteil_prozent=1.0,
        anteil_prozent_kontrolle=0.1,
        groesste_flaeche_ha=50.0,
        flaeche_km2=0.0,
        schwerpunkt_bundesland="Wien",
    )


def test_write_register_schreibt_kopf_und_nur_abweichende_baender(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    results = [_band(1, "band_a", pixel_abs=10), _band(2, "band_b", pixel_abs=0)]
    write_register(path, "W9.9", results, erlaubte_baender={"band_a"})
    rows = _load_existing_register(path)
    assert list(rows.keys()) == [("W9.9", "band_a")]
    header_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert header_line.split("\t") == REGISTER_COLUMNS


def test_write_register_laesst_andere_pakete_unangetastet(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    write_register(path, "W1.0", [_band(1, "band_a")], erlaubte_baender={"band_a"})
    write_register(path, "W2.0", [_band(2, "band_b")], erlaubte_baender={"band_b"})
    rows = _load_existing_register(path)
    assert set(rows.keys()) == {("W1.0", "band_a"), ("W2.0", "band_b")}


def test_write_register_erneuter_lauf_ersetzt_nur_das_eigene_paket(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    write_register(path, "W1.0", [_band(1, "band_a"), _band(2, "band_b")], erlaubte_baender={"band_a", "band_b"})
    # band_b ist im zweiten Lauf nicht mehr abweichend (z. B. nach Korrektur)
    write_register(path, "W1.0", [_band(1, "band_a")], erlaubte_baender={"band_a"})
    rows = _load_existing_register(path)
    assert set(rows.keys()) == {("W1.0", "band_a")}


def test_write_register_bewahrt_von_hand_eingetragene_ursache_bei_wiederholung(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    write_register(path, "W1.0", [_band(1, "band_a")], erlaubte_baender={"band_a"})
    rows = _load_existing_register(path)
    rows[("W1.0", "band_a")][-1] = "Bodensee-Korrektur akzeptiert (Nutzerentscheidung)"
    with path.open("w", encoding="utf-8", newline="") as f:
        import csv

        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(REGISTER_COLUMNS)
        writer.writerows(rows.values())

    # Erneuter Lauf mit identischen Zahlen darf die von Hand gepflegte
    # ursache nicht durch den Platzhalter ueberschreiben.
    write_register(path, "W1.0", [_band(1, "band_a")], erlaubte_baender={"band_a"})
    rows_again = _load_existing_register(path)
    assert rows_again[("W1.0", "band_a")][-1] == "Bodensee-Korrektur akzeptiert (Nutzerentscheidung)"


def test_write_register_unerwartetes_band_bekommt_eigenen_platzhalter(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    write_register(path, "W1.0", [_band(1, "ueberraschung")], erlaubte_baender=set())
    rows = _load_existing_register(path)
    row = rows[("W1.0", "ueberraschung")]
    assert row[-1] == URSACHE_UNERWARTET
    assert row[-2] == AMPEL_ROT  # ampel-Spalte


def test_write_register_frisches_band_bekommt_todo_platzhalter(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    write_register(path, "W1.0", [_band(1, "band_a")], erlaubte_baender={"band_a"})
    rows = _load_existing_register(path)
    assert rows[("W1.0", "band_a")][-1] == URSACHE_PLATZHALTER


# ---------------------------------------------------------------------------
# Nutzerentscheidung vom 08.09.2026 (PLAN.md §6, "Die Referenz hat sich
# geändert"): eine bereits angenommene Abweichung darf den Lauf nicht mehr
# scheitern lassen, eine neue, bislang unbekannte schon - das ist der Bruch,
# den W4.3 gemeldet und dieses Paket (W4-Zusammenführung) behoben hat.
# ---------------------------------------------------------------------------

def _grosse_abweichung(nr: int, name: str) -> BandResult:
    """Ein Band, das nach der Ampel klar Rot waere - grosser Anteil UND
    grosse Flaeche, wie das reale geography_water_bodies (27,58 %,
    33 943 ha) aus docs/rewrite/abweichungen.tsv."""
    return BandResult(
        band_nr=nr,
        band_name=name,
        role=ROLE_BEDINGUNG,
        pixel_abs=543_106,
        gesetzte_pixel_referenz=1_969_000,
        anteil_prozent=27.58,
        anteil_prozent_kontrolle=0.16,
        groesste_flaeche_ha=33_943.44,
        flaeche_km2=0.0,
        schwerpunkt_bundesland="Vorarlberg",
    )


def test_akzeptierte_abweichung_wird_nicht_mehr_rot_eine_neue_zehnte_bleibt_rot(tmp_path):
    path = tmp_path / "abweichungen.tsv"
    erlaubte_baender = {"geography_water_bodies", "voellig_neues_band"}

    # Erster Lauf: die Abweichung ist noch nicht geprueft, die Ampel stuft
    # sie - korrekt - als Rot ein (weit ueber den Gelb-Schwellen).
    erster_lauf = write_register(
        path, "W3.1", [_grosse_abweichung(26, "geography_water_bodies")], erlaubte_baender
    )
    assert erster_lauf[0].ampel == AMPEL_ROT

    # Der Nutzer prueft die Zeile und nimmt sie an - von Hand in die
    # ursache-Spalte eingetragen, wie es die Kopfzeile von
    # docs/rewrite/abweichungen.tsv vorsieht ("ursache wird von der Person
    # eingetragen, die das Paket abschliesst").
    rows = _load_existing_register(path)
    rows[("W3.1", "geography_water_bodies")][-1] = (
        "Bodensee-Relation; Korrektur der neuen Kette, vom Nutzer am "
        "08.09.2026 angenommen (Punkt 33)."
    )
    with path.open("w", encoding="utf-8", newline="") as f:
        import csv

        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(REGISTER_COLUMNS)
        writer.writerows(rows.values())

    # Zweiter Lauf: dieselbe (weiterhin objektiv grosse) Abweichung, PLUS
    # eine bislang voellig unbekannte zehnte Abweichung auf einem anderen
    # Band. Das angenommene Band darf den Lauf nicht mehr scheitern lassen,
    # das neue muss es.
    zweiter_lauf = write_register(
        path,
        "W3.1",
        [
            _grosse_abweichung(26, "geography_water_bodies"),
            _grosse_abweichung(99, "voellig_neues_band"),
        ],
        erlaubte_baender,
    )

    by_name = {r.band_name: r for r in zweiter_lauf}
    assert by_name["geography_water_bodies"].ampel == AMPEL_AKZEPTIERT
    assert by_name["voellig_neues_band"].ampel == AMPEL_ROT

    # Das ist die eigentliche Bedingung des Auftrags: genau die neue,
    # unbekannte Abweichung haelt den Lauf an - die angenommene nicht mehr.
    rot = [r for r in zweiter_lauf if r.ampel == AMPEL_ROT]
    assert [r.band_name for r in rot] == ["voellig_neues_band"]


def test_akzeptierte_abweichung_bleibt_rot_wenn_zugleich_ausserhalb_des_wirkungspfads(tmp_path):
    """Der §13.9-Waechter sticht eine alte 'angenommen'-ursache: wird ein
    Band nachtraeglich aus dem erlaubten Wirkungspfad genommen (z. B. weil
    sich das Manifest geaendert hat), darf eine frueher eingetragene
    Annahme das nicht stillschweigend uebertoenen."""
    path = tmp_path / "abweichungen.tsv"

    write_register(
        path, "W3.1", [_grosse_abweichung(26, "geography_water_bodies")], erlaubte_baender={"geography_water_bodies"}
    )
    rows = _load_existing_register(path)
    rows[("W3.1", "geography_water_bodies")][-1] = "vom Nutzer angenommen (Punkt 33)."
    with path.open("w", encoding="utf-8", newline="") as f:
        import csv

        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(REGISTER_COLUMNS)
        writer.writerows(rows.values())

    # Zweiter Lauf: dasselbe Band, aber das Manifest fuehrt es jetzt NICHT
    # mehr im Wirkungspfad - erlaubte_baender ist leer.
    zweiter_lauf = write_register(
        path, "W3.1", [_grosse_abweichung(26, "geography_water_bodies")], erlaubte_baender=set()
    )
    assert zweiter_lauf[0].ampel == AMPEL_ROT
    assert zweiter_lauf[0].unerwartet is True
