"""Vertragstest zur neuen Referenz (Paket W4.3, Teil A3; Bandliste seit
W5.P3 auf zwei überlagerte Ursachen umgeschrieben).

## Zweiter Wechsel (W5.P2, 08.09.2026, Punkt 34) - Bandliste nachgezogen (W5.P3)

Adresslose DKM-Großflächen über ``HIG_MAX_FOOTPRINT_M2`` entfallen jetzt
als Kandidat (Nutzerentscheidung). ``REFERENZ_SHA256``/``REFERENZ_BYTES``
unten sind auf den daraus finalisierten Stand gezogen. W5.P2 hatte diesen
Wechsel selbst gemeldet, aber die Neunerliste
(``ABWEICHENDE_BANDNUMMERN``/``-NAMEN``) und den zugehörigen Langläufer
bewusst nicht mitgezogen (Regel 4) - der Lauf schlug seitdem fehl, weil
real 18 Bänder von ``run1`` abweichen, nicht neun. W5.P3 zieht das jetzt
nach: zwei Ursachen liegen inzwischen übereinander, und (Stand W5.P2/W5.P3)
war nur eine davon - die Bodensee-Korrektur - in
``geography_water_bodies_wirkungspfad`` vorab genannt. **Seit W5.P5** hat
auch die zweite Ursache ihr eigenes Manifestfeld
(``dkm_geoparquet_wirkungspfad``) - der folgende Abschnitt beschreibt noch
den Stand VOR W5.P5, die Tests unten prüfen nur den bis dahin geltenden
Teil des Vertrags (``geography_water_bodies_wirkungspfad``) unverändert
weiter; siehe ``tests/test_band_manifest.py`` für die DKM-Gegenprobe.

## Was hier vertraglich ist (Stand W5.P2/W5.P3)

Am **08.09.2026** hat der Nutzer Punkt 33 der Offenen-Punkte-Liste
entschieden: **die Bodensee-Korrektur wird übernommen.** Damit verliert
``run1`` seinen Status als bitgenaues Soll. Am selben Tag hat er außerdem
Punkt 34 entschieden: adresslose DKM-Großflächen über 10 000 m² entfallen
als Kandidat. Neues Soll ist das aus den 33 Checkpoints unter
``derived/layers/`` finalisierte GeoTIFF nach BEIDEN Entscheidungen
(``pipeline.contract.PRODUCTS["abschichtung_tif"]``):

* ``sha256`` ``fb57c41d…232c30``, 124 597 421 Bytes,
* und die Abweichung gegen ``run1`` betrifft **genau 18 Bänder** — 5, 7,
  8, 9, 10, 11, 12, 13, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36. Nicht 17,
  nicht 19.

Diese 18 zerfallen in drei Gruppen (siehe
``docs/rewrite/abweichungen.tsv``, Spalte ``ursache``, Paket ``W5.P2``):

* **Nur Bodensee** (2 Bänder, von W5.P2 unverändert übernommen): 26, 29.
* **Nur die adresslosen DKM-Großflächen** (9 Bänder, W5.P2 allein): 5, 7,
  8, 9, 10, 11, 12, 13, 27.
* **Beide Ursachen überlagert** (7 Bänder): 30, 31, 32, 33, 34, 35, 36.

``run1`` bleibt bestehen, aber in einer anderen Rolle: **Vergleichsbasis,
nicht mehr Ziel.** Es muss deshalb unverändert ``dc58b011…9e3df1``
tragen — genau das prüft
:func:`test_run1_bleibt_unveraendert_die_vergleichsbasis`. Ein
stillschweigend neu geschriebenes ``run1`` würde jede künftige Messung
gegen eine bewegliche Basis führen, und niemand würde es merken.

Die neun Bodensee-Bänder (26, 29-36, Gruppen "Nur Bodensee" und "Beide"
oben) sind **nicht** aus dem Vergleich abgelesen, sondern stammen aus dem
Manifest: ``geography_water_bodies_wirkungspfad`` ist die transitive Hülle
über ``abgeleitet_von`` und wurde von W3.1 **vor** der Messung berechnet
(PLAN.md §13.9, Regel 8: "vorher genannt, dann gemessen"). Dass das
Manifest genau diese neun Namen führt, prüft bereits
``tests/test_band_manifest.py``
(``test_geography_water_bodies_wirkungspfad_is_the_predicted_nine_bands``)
auf einem synthetischen Manifest - unverändert, denn diese neun sind vom
Punkt-34-Wechsel nicht berührt. Die übrigen neun Bänder (Gruppe "Nur die
adresslosen DKM-Großflächen") haben **keine** entsprechende Vorab-Liste im
Manifestschema; ihre Vorab-Nennung stand stattdessen im Messbericht zu
W5.P2 (docs/rewrite/FORTSCHRITT.md, Punkt 34). Dieser Test hier schließt
den Kreis am echten Artefakt: er misst die Bänder, die **tatsächlich**
abweichen, hält sie gegen die volle 18er-Liste und prüft für die
Bodensee-Teilmenge zusätzlich die Deckung mit dem Manifest.

## Warum drei der vier Tests nicht in `make test` laufen

``make test`` soll in Sekunden ein Urteil liefern. Zwei der Zusicherungen
hier kosten deutlich mehr:

* Der bandweise Vergleich liest zwei 38-Band-Raster à 336 038 001 Zellen
  vollständig ein — rund 25 GB Ein-/Ausgabe, Minuten statt Sekunden.
* Die Finalisierung aus den Checkpoints dauert rund **165 s** (gemessen von
  W3.1: 164 s) und braucht mehrere GB Arbeitsspeicher.

Beide sind deshalb hinter ein Env-Var-Gate gelegt und melden sich sonst als
übersprungen — mit einer Begründung, die sagt, wie man sie bekommt. Sie
sind **absichtlich** auszuführen, nicht beiläufig::

    # nur die beiden Langläufer, gezielt:
    ABSCHICHTUNG_VERTRAGSTEST=1 uv run pytest tests/test_referenz_tif.py -v

    # oder ein einzelner davon:
    ABSCHICHTUNG_VERTRAGSTEST=1 uv run pytest \\
        tests/test_referenz_tif.py::test_abweichung_gegen_run1_betrifft_genau_achtzehn_baender -v

    ABSCHICHTUNG_VERTRAGSTEST=1 uv run pytest \\
        tests/test_referenz_tif.py::test_finalisierung_aus_checkpoints_reproduziert_die_referenz -v

    # und die ganze Suite inklusive der Langläufer:
    ABSCHICHTUNG_VERTRAGSTEST=1 make test

Die beiden **billigen** Tests (zwei ``sha256`` über je rund 124 MB, unter
einer Sekunde) laufen in ``make test`` mit, sobald die Artefakte da sind.
Fehlt ein Artefakt — frischer Checkout ohne Kettenlauf, oder ein Worktree,
in das ``make worktree`` ``run1`` nicht hineinverlinkt —, überspringen sie
sich mit Angabe des fehlenden Pfads, statt rot zu werden: ein fehlendes
Artefakt ist kein gebrochener Vertrag.

## Was dieser Test nicht anfasst

Nichts Geteiltes. Die Finalisierung schreibt in ein ``tmp_path`` des Tests,
**nie** nach ``out/abschichtung.tif`` — in einem Worktree ist das ein
Symlink auf das Hauptrepo, und ein Schreibzugriff dorthin träfe alle
Verify-Worktrees gleichzeitig (siehe die Warnungen des ``worktree``-Ziels
im ``Makefile``). ``derived/layers/`` und ``run1`` werden ausschließlich
gelesen.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract  # noqa: E402
# Der run1-Pfad wird gelesen, nicht kopiert (PLAN.md §8, Regel 2): er ist in
# pipeline/validate.py verankert, das ihn als Vergleichsbasis besitzt.
from pipeline.validate import REFERENCE_TIF as RUN1_TIF  # noqa: E402
from calc.band_manifest import manifest_path_for  # noqa: E402

# ---------------------------------------------------------------------------
# Die Zahlen des Vertrags
# ---------------------------------------------------------------------------

# Dritter Wechsel (W7.1, Neuzuschnitt "Layer-Struktur v4", 09.09.2026):
# Hüllen-Zuschnitt gegen official_wind_zoning (Band 38) plus sechs
# angehängte Bänder 39-44 (Schema 2.2.0, clean-44-…) heben die Bandzahl von
# 38 auf 44 - allein dadurch ändert sich Dateigröße und Hash, auch ohne
# Pixeländerung an den ersten 38 Bändern. Vorheriger Wert (Punkt 34,
# W5.P2, 08.09.2026): sha256 fb57c41d…232c30, 124 597 421 Bytes - bleibt
# als historischer Zeuge in docs/rewrite/FORTSCHRITT.md/PLAN.md
# dokumentiert.
#
# Vierter Wechsel (W7.5, Personenseilbahnen enger gefasst, 09.09.2026):
# PEOPLE_CARRYING_AERIALWAY_TYPES (calc/abschichtung_common.py) auf
# gondola/cable_car/chair_lift/mixed_lift eingeengt - Nutzerentscheidung
# 09.09.2026, angenommen; siehe docs/rewrite/abweichungen.tsv, Paket W7.5,
# und cableway_typ_wirkungspfad im Manifest (calc/band_manifest.py). Datei
# wird KLEINER (weniger Pufferfläche => mehr Bytes an gleichen Werten,
# tatsächlich minimal kleiner durch die TIFF-Kompression), nicht größer.
# Vorheriger Wert (W7.1, 09.09.2026 vormittags):
# sha256 a905c056…ab5c9f, 152 669 124 Bytes - bleibt ebenso als
# historischer Zeuge dokumentiert.
REFERENZ_SHA256 = "99d522239dc499b833cab3080c810b9568ac3078a66b81a470e37228b55a96ac"
REFERENZ_BYTES = 152_656_278

# Bisheriges Soll, ab 08.09.2026 nur noch Vergleichsbasis - aber als solche
# unveränderlich.
RUN1_SHA256 = "dc58b011af1b461aa21f6416d378bce2a4187e18d674c65060506df5939e3df1"
RUN1_BYTES = 124_685_819

# Genau 18, keines mehr, keines weniger - zwei überlagerte Ursachen seit
# Punkt 34/W5.P2 (PLAN.md §13.9 fuer die Bodensee-Teilmenge; die adresslosen
# DKM-Grossflaechen sind eine zweite, unabhaengige Ursache - bis W5.P5 ohne
# eigenes Manifestfeld, seither in dkm_geoparquet_wirkungspfad). Nummern
# und Namen beide festgehalten: die Nummer allein
# verschoebe sich still, wenn sich die Bandreihenfolge je aenderte. Herkunft
# je Band steht in docs/rewrite/abweichungen.tsv, Paket W5.P2, Spalte
# ursache.
ABWEICHENDE_BANDNUMMERN = frozenset({5, 7, 8, 9, 10, 11, 12, 13, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36})
ABWEICHENDE_BANDNAMEN = frozenset({
    "haeuser_im_gruenen_streusiedlung",  # 5  - nur adresslose DKM-Grossflaechen
    "haeuser_im_gruenen",                # 7  - nur adresslose DKM-Grossflaechen
    "nonresidential_hulls_source",       # 8  - nur adresslose DKM-Grossflaechen
    "nonresidential_hulls_buffer",       # 9  - nur adresslose DKM-Grossflaechen
    "cableway_buildings_source",         # 10 - nur adresslose DKM-Grossflaechen
    "cableway_buildings_buffer",         # 11 - nur adresslose DKM-Grossflaechen
    "general_buildings_source",          # 12 - nur adresslose DKM-Grossflaechen
    "general_buildings_buffer",          # 13 - nur adresslose DKM-Grossflaechen
    "geography_water_bodies",            # 26 - nur Bodensee, unveraendert von W5.P2
    "exclusion_human",                   # 27 - nur adresslose DKM-Grossflaechen
    "exclusion_geography",               # 29 - nur Bodensee, unveraendert von W5.P2
    "all_exclusions",                    # 30 - beide Ursachen ueberlagert
    "available_after_all_exclusions_raw",  # 31 - beide Ursachen ueberlagert
    "available_cleaned_min_10ha",        # 32 - beide Ursachen ueberlagert
    "available_blur_sigma_100m",         # 33 - beide Ursachen ueberlagert
    "available_blur_sigma_200m",         # 34 - beide Ursachen ueberlagert
    "available_blur_sigma_250m",         # 35 - beide Ursachen ueberlagert
    "available_blur_sigma_300m",         # 36 - beide Ursachen ueberlagert
})

# Die Teilmenge, die aus geography_water_bodies transitiv gespeist wird
# (PLAN.md §13.9) - unveraendert 9 Baender, vom Punkt-34-Wechsel nicht
# beruehrt. Das Manifest kennt nur diese Teilmenge vorab, nicht die volle
# 18er-Liste.
BODENSEE_BANDNAMEN = frozenset({
    "geography_water_bodies",
    "exclusion_geography",
    "all_exclusions",
    "available_after_all_exclusions_raw",
    "available_cleaned_min_10ha",
    "available_blur_sigma_100m",
    "available_blur_sigma_200m",
    "available_blur_sigma_250m",
    "available_blur_sigma_300m",
})

FINALES_TIF = contract.PRODUCTS["abschichtung_tif"]

LANGLAEUFER_GATE = "ABSCHICHTUNG_VERTRAGSTEST"
LANGLAEUFER_AN = os.environ.get(LANGLAEUFER_GATE) == "1"
LANGLAEUFER_GRUND = (
    f"Langläufer - nur mit {LANGLAEUFER_GATE}=1. Der bandweise Vergleich liest "
    "zwei 38-Band-Raster vollständig (rund 25 GB I/O), die Finalisierung dauert "
    "rund 165 s. Siehe Moduldocstring für die genauen Aufrufe."
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _abweichende_baender(neu: Path, referenz: Path) -> list[tuple[int, str, int]]:
    """(Bandnummer, Bandname, abweichende Zellen) je Band mit Abweichung.

    Bandweise gelesen, nicht als Block: ein 38-Band-uint8-Raster mit
    336 038 001 Zellen je Band wäre am Stück rund 12 GB im Speicher.
    """
    treffer: list[tuple[int, str, int]] = []
    with rasterio.open(neu) as a_src, rasterio.open(referenz) as b_src:
        assert a_src.count == b_src.count, (
            f"Bandzahl weicht ab: {neu} hat {a_src.count}, {referenz} hat {b_src.count} - "
            "ein bandweiser Vergleich wäre bedeutungslos."
        )
        assert a_src.descriptions == b_src.descriptions, (
            "Bandnamen/-reihenfolge weichen ab - kein bandweiser Vergleich möglich."
        )
        for nr, name in enumerate(a_src.descriptions, start=1):
            diff = int((a_src.read(nr) != b_src.read(nr)).sum())
            if diff:
                treffer.append((nr, name, diff))
    return treffer


# ---------------------------------------------------------------------------
# Billig: zwei Prüfsummen. Laufen in `make test` mit.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not FINALES_TIF.exists(),
    reason=(
        f"{FINALES_TIF} fehlt - 'make -f make/finalize/finalize.mk finalize' bzw. "
        "'uv run python -m pipeline.finalize' zuerst laufen lassen. Ein fehlendes "
        "Artefakt ist kein gebrochener Vertrag."
    ),
)
def test_finalisiertes_tif_hat_die_neue_referenz_sha256():
    """Das finalisierte TIF ist bitgenau die am 08.09.2026 angenommene Referenz."""
    assert FINALES_TIF.stat().st_size == REFERENZ_BYTES, (
        f"{FINALES_TIF} hat {FINALES_TIF.stat().st_size} Bytes, erwartet {REFERENZ_BYTES}."
    )
    assert _sha256(FINALES_TIF) == REFERENZ_SHA256, (
        f"{FINALES_TIF} hat nicht die vereinbarte Referenz-sha256 {REFERENZ_SHA256}. "
        "Entweder hat sich die Kette geändert (dann gehört das gemessen, begründet und "
        "in docs/rewrite/abweichungen.tsv eingetragen), oder die Datei stammt aus einem "
        "anderen Lauf."
    )


@pytest.mark.skipif(
    RUN1_TIF is None or not RUN1_TIF.exists(),
    reason=(
        f"run1 nicht aufloesbar ({RUN1_TIF}) - seit W6.1 liegt die run1-"
        "Vergleichsbasis nicht mehr im Repo, sondern (falls vorhanden) im Archiv "
        "unter ~/Documents/master_windkraft/archiv/run1.tif und muss über "
        "ABSCHICHTUNG_RUN1 aufgeloest werden (siehe pipeline/contract.py:RUN1_TIF). "
        "Ein fehlendes/nicht gesetztes run1 ist kein gebrochener Vertrag."
    ),
)
def test_run1_bleibt_unveraendert_die_vergleichsbasis():
    """run1 ist ab 08.09.2026 nicht mehr Ziel - aber weiterhin unveränderlich.

    PLAN.md §6 ("Vergleichsbasis") misst jede künftige Abweichung gegen
    genau diese Datei. Würde sie neu geschrieben, verschöbe sich die Basis
    still mit, und keine der Zahlen in ``docs/rewrite/abweichungen.tsv``
    wäre danach noch nachvollziehbar. ``pipeline/validate.py`` sagt es
    ausdrücklich zu: "es überschreibt nie ``run1`` selbst".
    """
    assert RUN1_TIF.stat().st_size == RUN1_BYTES
    assert _sha256(RUN1_TIF) == RUN1_SHA256, (
        f"{RUN1_TIF} ist nicht mehr {RUN1_SHA256} - die Vergleichsbasis wurde "
        "überschrieben. Jede Messung gegen run1 ist damit ungültig, bis geklärt ist, "
        "was sie ersetzt hat."
    )


# ---------------------------------------------------------------------------
# Langläufer: nur mit ABSCHICHTUNG_VERTRAGSTEST=1
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LANGLAEUFER_AN, reason=LANGLAEUFER_GRUND)
@pytest.mark.skipif(
    not FINALES_TIF.exists() or RUN1_TIF is None or not RUN1_TIF.exists(),
    reason=(
        f"{FINALES_TIF} oder run1 ({RUN1_TIF}) fehlt - ohne beide kein Vergleich. "
        "run1 seit W6.1 nur ueber ABSCHICHTUNG_RUN1 aufloesbar (siehe oben)."
    ),
)
def test_abweichung_gegen_run1_betrifft_genau_achtzehn_baender():
    """Genau 18 Bänder weichen ab - nicht 17, nicht 19.

    Die Zahl ist der eigentliche Vertrag, und seit Punkt 34/W5.P2 setzt sie
    sich aus zwei überlagerten Ursachen zusammen (siehe Moduldocstring):
    neun Bänder allein aus der Bodensee-Korrektur (Punkt 33) oder aus deren
    Überlagerung mit Punkt 34, und neun weitere allein aus dem Wegfall der
    adresslosen DKM-Großflächen (Punkt 34). Ein 19. abweichendes Band hieße,
    dass eine der beiden Korrekturen weiter wirkt als vorhergesagt (oder
    dass etwas anderes mit hineingeraten ist); ein 17. hieße, dass ein Band
    seine Abweichung verloren hat. Beides ist ein Befund, kein Rauschen.
    """
    treffer = _abweichende_baender(FINALES_TIF, RUN1_TIF)
    nummern = {nr for nr, _name, _diff in treffer}
    namen = {name for _nr, name, _diff in treffer}

    protokoll = ", ".join(f"{nr} {name} ({diff} Zellen)" for nr, name, diff in treffer)
    assert nummern == set(ABWEICHENDE_BANDNUMMERN), (
        f"Abweichende Bänder: {sorted(nummern)}, erwartet {sorted(ABWEICHENDE_BANDNUMMERN)}. "
        f"Gemessen: {protokoll}"
    )
    assert namen == set(ABWEICHENDE_BANDNAMEN), (
        f"Abweichende Bandnamen: {sorted(namen)}, erwartet {sorted(ABWEICHENDE_BANDNAMEN)}."
    )
    assert len(treffer) == 18, f"{len(treffer)} abweichende Bänder statt 18: {protokoll}"

    # Die Bodensee-Teilmenge (9 Bänder) steht vorab im Manifest des TIFs -
    # vorher genannt, dann gemessen (PLAN.md §13.9, Regel 8). Geprüft wird
    # hier bewusst nur dieses eine, ursprüngliche Feld
    # (geography_water_bodies_wirkungspfad) unveraendert weiter - seit
    # W5.P5 kennt das Manifest zusätzlich dkm_geoparquet_wirkungspfad fuer
    # die anderen neun Bänder (adresslose DKM-Großflächen, Punkt 34); dessen
    # exakte Namensmenge nagelt tests/test_band_manifest.py fest
    # (test_dkm_geoparquet_wirkungspfad_is_the_predicted_sixteen_bands), auf
    # einem synthetischen Manifest, nicht hier am echten Artefakt. Der
    # Wasserpfad allein bleibt eine ECHTE TEILMENGE der 18 tatsächlich
    # abweichenden Bänder, keine Gleichheit - das war schon vor W5.P5 so und
    # ist unveraendert richtig.
    manifest_pfad = manifest_path_for(FINALES_TIF)
    if manifest_pfad.exists():
        manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
        wirkungspfad = set(manifest["geography_water_bodies_wirkungspfad"])
        assert wirkungspfad == BODENSEE_BANDNAMEN, (
            f"Bodensee-Wirkungspfad im Manifest: {sorted(wirkungspfad)}, "
            f"erwartet {sorted(BODENSEE_BANDNAMEN)}."
        )
        assert wirkungspfad <= namen, (
            "Der im Manifest vorab genannte Bodensee-Wirkungspfad ist keine Teilmenge "
            "der tatsächlich abweichenden Bänder mehr."
        )
        unerklaert = namen - wirkungspfad - ABWEICHENDE_BANDNAMEN
        assert not unerklaert, (
            f"Abweichende Bänder ohne Erklärung (weder Bodensee-Wirkungspfad noch "
            f"die bekannte DKM-Großflächen-Liste): {sorted(unerklaert)}."
        )


@pytest.mark.skipif(not LANGLAEUFER_AN, reason=LANGLAEUFER_GRUND)
@pytest.mark.skipif(
    not contract.DERIVED_LAYERS.is_dir(),
    reason=f"{contract.DERIVED_LAYERS} fehlt - 'make layers' zuerst (33 Checkpoints).",
)
def test_finalisierung_aus_checkpoints_reproduziert_die_referenz(tmp_path):
    """Aus denselben 33 Checkpoints entsteht wieder bitgenau dieselbe Referenz.

    Rund 165 s. Schreibt bewusst nach ``tmp_path`` und **nicht** nach
    ``out/abschichtung.tif``: in einem Worktree ist das ein Symlink auf das
    Hauptrepo, und ein Lauf von hier aus träfe alle Verify-Worktrees
    gleichzeitig. ``derived/layers/`` wird nur gelesen.

    Der Dateiname des Ziels geht ausschließlich ins Sidecar-Manifest
    (``raster_file``), nicht in das GeoTIFF selbst - der abweichende
    Zielpfad ändert an der Prüfsumme des Rasters deshalb nichts.
    """
    from pipeline import finalize  # noqa: PLC0415  (schwerer Import, nur hier nötig)

    ziel = tmp_path / "abschichtung.tif"
    finalize.main(["--output", str(ziel), "--layer-dir", str(contract.DERIVED_LAYERS)])

    assert ziel.exists(), "pipeline.finalize hat kein GeoTIFF geschrieben."
    assert ziel.stat().st_size == REFERENZ_BYTES, (
        f"Frisch finalisiert: {ziel.stat().st_size} Bytes, erwartet {REFERENZ_BYTES}."
    )
    assert _sha256(ziel) == REFERENZ_SHA256, (
        "Die Finalisierung aus denselben Checkpoints ergibt nicht mehr "
        f"{REFERENZ_SHA256}. Entweder ist sie nicht mehr deterministisch, oder die "
        "Checkpoints unter derived/layers/ haben sich geändert."
    )
