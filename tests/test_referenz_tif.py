"""Vertragstest zur neuen Referenz (Paket W4.3, Teil A3).

## Was hier vertraglich ist

Am **08.09.2026** hat der Nutzer Punkt 33 der Offenen-Punkte-Liste
entschieden: **die Bodensee-Korrektur wird übernommen.** Damit verliert
``run1`` seinen Status als bitgenaues Soll. Neues Soll ist das aus den 33
Checkpoints unter ``build/layers/`` finalisierte GeoTIFF
(``pipeline.contract.PRODUCTS["abschichtung_tif"]``):

* ``sha256`` ``4bdef6ad…6b1a13e``, 124 613 971 Bytes,
* und die Abweichung gegen ``run1`` betrifft **genau neun Bänder** —
  26, 29, 30, 31, 32, 33, 34, 35, 36. Nicht acht, nicht zehn.

``run1`` bleibt bestehen, aber in einer anderen Rolle: **Vergleichsbasis,
nicht mehr Ziel.** Es muss deshalb unverändert ``dc58b011…9e3df1``
tragen — genau das prüft
:func:`test_run1_bleibt_unveraendert_die_vergleichsbasis`. Ein
stillschweigend neu geschriebenes ``run1`` würde jede künftige Messung
gegen eine bewegliche Basis führen, und niemand würde es merken.

Die Neunerliste ist **nicht** aus dem Vergleich abgelesen, sondern stammt
aus dem Manifest: ``geography_water_bodies_wirkungspfad`` ist die transitive
Hülle über ``abgeleitet_von`` und wurde von W3.1 **vor** der Messung
berechnet (PLAN.md §13.9, Regel 8: "vorher genannt, dann gemessen"). Dass
das Manifest genau diese neun Namen führt, prüft bereits
``tests/test_band_manifest.py``
(``test_geography_water_bodies_wirkungspfad_is_the_predicted_nine_bands``)
auf einem synthetischen Manifest. Dieser Test hier schließt den Kreis am
echten Artefakt: er misst die Bänder, die **tatsächlich** abweichen, und
hält sie gegen dieselbe Neunerliste.

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
        tests/test_referenz_tif.py::test_abweichung_gegen_run1_betrifft_genau_neun_baender -v

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
im ``Makefile``). ``build/layers/`` und ``run1`` werden ausschließlich
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
from windkraft.calc.band_manifest import manifest_path_for  # noqa: E402

# ---------------------------------------------------------------------------
# Die Zahlen des Vertrags
# ---------------------------------------------------------------------------

# Neue Referenz, vom Nutzer am 08.09.2026 angenommen (Punkt 33).
REFERENZ_SHA256 = "4bdef6ad5e863692cef0f19cdfe959f04e439e9b17310f2f7a3c067d56b1a13e"
REFERENZ_BYTES = 124_613_971

# Bisheriges Soll, ab 08.09.2026 nur noch Vergleichsbasis - aber als solche
# unveränderlich.
RUN1_SHA256 = "dc58b011af1b461aa21f6416d378bce2a4187e18d674c65060506df5939e3df1"
RUN1_BYTES = 124_685_819

# Genau neun, keines mehr, keines weniger (PLAN.md §13.9). Nummern und Namen
# beide festgehalten: die Nummer allein verschöbe sich still, wenn sich die
# Bandreihenfolge je änderte.
ABWEICHENDE_BANDNUMMERN = frozenset({26, 29, 30, 31, 32, 33, 34, 35, 36})
ABWEICHENDE_BANDNAMEN = frozenset({
    "geography_water_bodies",            # 26 - die Korrektur selbst
    "exclusion_geography",               # 29 - ab hier: Folge über den Wirkungspfad
    "all_exclusions",                    # 30
    "available_after_all_exclusions_raw",  # 31
    "available_cleaned_min_10ha",        # 32
    "available_blur_sigma_100m",         # 33
    "available_blur_sigma_200m",         # 34
    "available_blur_sigma_250m",         # 35
    "available_blur_sigma_300m",         # 36
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
    not RUN1_TIF.exists(),
    reason=(
        f"{RUN1_TIF} fehlt - die run1-Vergleichsbasis liegt im Hauptrepo unter "
        "output/abschichtung_widmung_v2/ und wird von 'make worktree' NICHT in ein "
        "Worktree verlinkt."
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
    not (FINALES_TIF.exists() and RUN1_TIF.exists()),
    reason=f"{FINALES_TIF} oder {RUN1_TIF} fehlt - ohne beide kein Vergleich.",
)
def test_abweichung_gegen_run1_betrifft_genau_neun_baender():
    """Genau neun Bänder weichen ab - nicht acht, nicht zehn.

    Die Zahl ist der eigentliche Vertrag. Ein zehntes abweichendes Band
    hieße, dass die Bodensee-Korrektur weiter wirkt als vorhergesagt (oder
    dass etwas anderes mit hineingeraten ist); ein achtes hieße, dass ein
    Band aus dem Wirkungspfad seine Abweichung verloren hat. Beides ist ein
    Befund, kein Rauschen - PLAN.md §13.9: "Jede andere Abweichung ist ein
    Fehler."
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
    assert len(treffer) == 9, f"{len(treffer)} abweichende Bänder statt neun: {protokoll}"

    # Und dieselbe Neunerliste steht vorab im Manifest des TIFs - vorher
    # genannt, dann gemessen (PLAN.md §13.9, Regel 8).
    manifest_pfad = manifest_path_for(FINALES_TIF)
    if manifest_pfad.exists():
        manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
        assert set(manifest["geography_water_bodies_wirkungspfad"]) == namen, (
            "Der im Manifest vorab genannte Wirkungspfad deckt sich nicht mit den "
            "tatsächlich abweichenden Bändern."
        )


@pytest.mark.skipif(not LANGLAEUFER_AN, reason=LANGLAEUFER_GRUND)
@pytest.mark.skipif(
    not contract.BUILD_LAYERS.is_dir(),
    reason=f"{contract.BUILD_LAYERS} fehlt - 'make layers' zuerst (33 Checkpoints).",
)
def test_finalisierung_aus_checkpoints_reproduziert_die_referenz(tmp_path):
    """Aus denselben 33 Checkpoints entsteht wieder bitgenau dieselbe Referenz.

    Rund 165 s. Schreibt bewusst nach ``tmp_path`` und **nicht** nach
    ``out/abschichtung.tif``: in einem Worktree ist das ein Symlink auf das
    Hauptrepo, und ein Lauf von hier aus träfe alle Verify-Worktrees
    gleichzeitig. ``build/layers/`` wird nur gelesen.

    Der Dateiname des Ziels geht ausschließlich ins Sidecar-Manifest
    (``raster_file``), nicht in das GeoTIFF selbst - der abweichende
    Zielpfad ändert an der Prüfsumme des Rasters deshalb nichts.
    """
    from pipeline import finalize  # noqa: PLC0415  (schwerer Import, nur hier nötig)

    ziel = tmp_path / "abschichtung.tif"
    finalize.main(["--output", str(ziel), "--layer-dir", str(contract.BUILD_LAYERS)])

    assert ziel.exists(), "pipeline.finalize hat kein GeoTIFF geschrieben."
    assert ziel.stat().st_size == REFERENZ_BYTES, (
        f"Frisch finalisiert: {ziel.stat().st_size} Bytes, erwartet {REFERENZ_BYTES}."
    )
    assert _sha256(ziel) == REFERENZ_SHA256, (
        "Die Finalisierung aus denselben Checkpoints ergibt nicht mehr "
        f"{REFERENZ_SHA256}. Entweder ist sie nicht mehr deterministisch, oder die "
        "Checkpoints unter build/layers/ haben sich geändert."
    )
