"""Untergrenze für die Zahl gesammelter Tests (W6.6, docs/rewrite/FORTSCHRITT.md
Punkt 54).

Der Befund: zweimal in Welle 6 ist eine ganze Testdatei stumm verstummt,
ohne dass ``make test`` rot wurde. Am deutlichsten
``tests/test_export_dashboard.py``: nach der ``verify/``->``export/``-
Umbenennung übersprang sie alle 18 Tests, weil ihre Import- oder
Pfadannahme nicht mehr stimmte - 199 statt 217 gesammelte Tests, aber
"199 passed" sieht in der Kurzausgabe genauso grün aus wie "217 passed".
Es gab keine Zusicherung über die gesammelte Zahl selbst, nur über den
Ausgang der einzelnen (weniger gewordenen) Tests.

Dieser Hook macht aus einem stillen Schwund einen lauten Abbruch: fällt die
gesammelte Zahl unter ``MIN_COLLECTED_TESTS``, bricht die Session mit
``pytest.exit()`` hart ab, mitsamt Schwellwert und tatsächlicher Zahl in der
Meldung.
"""
from __future__ import annotations

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent

# Schwellwert. Zum Zeitpunkt dieser Änderung (W6.6) sammelte ein voller Lauf
# über tests/ genau 217 Tests (214 passed + 3 skipped, siehe
# docs/rewrite/FORTSCHRITT.md Punkt 57 für die drei erwarteten Skips).
# MIN_COLLECTED_TESTS stand bewusst etwas darunter (nicht exakt bei 217),
# damit ein einzelner neuer, absichtlich übersprungener oder umbenannter
# Test die Schwelle nicht sofort reißt - aber weit über dem Bug-Zustand von
# 199, den Punkt 54 gefunden hat: jede stille Verstummung einer ganzen
# Testdatei (typischerweise ein zweistelliger Sprung) bleibt damit sicher
# erkennbar. Erhöhen, sobald absichtlich neue Tests dazukommen UND der neue,
# höhere Wert eine Weile stabil gesammelt wird - nicht bei jedem einzelnen
# neuen Testfall einzeln.
#
# W7.1 (Schema 2.2.0, Struktur v4): nach der Integration aller drei Bahnen
# (Zuschnitt/Punkte-Export, sechs angehängte Bänder + Manifest 2.2.0,
# tests/test_export_wka_bestand.py) sammelt ein voller Lauf über tests/
# tatsächlich 238 Tests (235 passed + 3 skipped, siehe test_referenz_tif.py
# für die drei erwarteten Skips - unverändert aus W6.6). Die vorherige
# Schwelle (226) war der konservative Zwischenwert, während Bahn 2 noch
# allein gegen ein widersprüchliches Repo lief (siehe vorheriger
# Kommentartext im Diff dieses Commits) - jetzt auf den tatsächlich
# gesammelten, grünen Stand angehoben.
MIN_COLLECTED_TESTS = 238


def pytest_collection_modifyitems(session, config, items):
    """Bricht einen VOLLEN Lauf über ``tests/`` hart ab, wenn weniger als
    ``MIN_COLLECTED_TESTS`` Tests gesammelt wurden.

    Nur für einen vollen Lauf aktiv - erkannt an den auf der Kommandozeile
    übergebenen Pfaden (``config.args``): steht dort nichts (Default) oder
    genau das ``tests/``-Wurzelverzeichnis, gilt der Lauf als vollständig.
    Ein gezielter Aufruf auf eine Teilmenge (``pytest tests/test_contract.py``,
    ``pytest -k foo``, ein einzelner Node-ID-Aufruf) hat naturgemäß weniger
    Items und darf davon nicht betroffen sein - genau das war die
    Anforderung aus Punkt 54: ``make test`` bekommt eine Untergrenze, ein
    gezielter Einzelaufruf bleibt unangetastet.
    """
    positional = [a for a in config.args if not str(a).startswith("-")]
    if positional:
        try:
            full_run = all(Path(a).resolve() == TESTS_DIR for a in positional)
        except OSError:
            full_run = False
    else:
        full_run = True

    if not full_run:
        return

    if len(items) < MIN_COLLECTED_TESTS:
        pytest.exit(
            f"Punkt 54: nur {len(items)} Tests gesammelt, erwartet "
            f"mindestens {MIN_COLLECTED_TESTS} (voller Lauf über tests/). "
            "Eine Testdatei koennte stumm uebersprungen worden sein - siehe "
            "docs/rewrite/FORTSCHRITT.md Punkt 54.",
            returncode=1,
        )
