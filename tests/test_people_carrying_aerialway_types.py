"""Regressionstest für Paket W7.5 (docs/rewrite/PLAN.md, Nutzerentscheidung
vom 09.09.2026): Personenseilbahnen sind genau vier OSM-``aerialway``-Typen
- ``gondola``, ``cable_car``, ``chair_lift``, ``mixed_lift`` - und diese
Liste ist an genau einer Stelle definiert
(``calc.abschichtung_common.PEOPLE_CARRYING_AERIALWAY_TYPES``), von der alle
drei Verbraucher (Band 10 ``cableway_buildings_source``, Band 17
``cableway_people_150m``, Band 42 ``sources_human``) lesen, statt sie je
eigene lokal zu duplizieren.

Kein Aufbau echter Raster/Vektor-Fixtures hier (die drei Funktionen brauchen
umfangreiche Ein-/Ausgaben, siehe pipeline/layers/osm.py und geo.py) -
dieser Test prüft den Vertrag auf zwei Arten, die ohne solche Fixtures
auskommen: den Inhalt der Konstante selbst, und dass die drei Verbraucher-
Module dieselbe Konstante importieren statt eine eigene Liste zu führen.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.abschichtung_common import PEOPLE_CARRYING_AERIALWAY_TYPES  # noqa: E402

# Explizit ausgeschlossen laut Nutzerentscheidung vom 09.09.2026 - keine
# Schlepplifte, kein magic_carpet, nichts aus goods/zip_line/explosive/
# avalanche/pylon/station/yes/proposed/abandoned/deflection_roller.
AUSGESCHLOSSENE_TYPEN = frozenset({
    "drag_lift", "t-bar", "j-bar", "platter", "rope_tow",
    "magic_carpet",
    "goods", "zip_line", "explosive", "avalanche", "pylon", "station",
    "yes", "proposed", "abandoned", "deflection_roller",
})


def test_genau_vier_personenseilbahn_typen():
    assert PEOPLE_CARRYING_AERIALWAY_TYPES == {"gondola", "cable_car", "chair_lift", "mixed_lift"}


def test_schlepplifte_und_sonstiges_bleiben_ausgeschlossen():
    assert PEOPLE_CARRYING_AERIALWAY_TYPES.isdisjoint(AUSGESCHLOSSENE_TYPEN)


def test_alle_drei_verbraucher_importieren_dieselbe_konstante_statt_sie_zu_duplizieren():
    """Statischer Vertragstest statt teurer Fixtures (siehe Moduldocstring):
    jede der drei Verbraucher-Dateien muss PEOPLE_CARRYING_AERIALWAY_TYPES
    aus calc.abschichtung_common importieren. Ein Fund einer eigenen,
    lokal hartkodierten Menge mit denselben vier Namen waere genau der
    zweite-Wahrheit-Fehler, den dieses Paket beheben sollte - dieser Test
    kann das nicht lückenlos ausschließen, stellt aber sicher, dass
    zumindest der Import nirgends fehlt bzw. entfernt wurde.
    """
    verbraucher = [
        PROJECT_ROOT / "pipeline" / "layers" / "osm.py",
        PROJECT_ROOT / "pipeline" / "layers" / "geo.py",
    ]
    for pfad in verbraucher:
        text = pfad.read_text(encoding="utf-8")
        assert "PEOPLE_CARRYING_AERIALWAY_TYPES" in text, f"{pfad} referenziert die Konstante nicht (mehr)"


def test_konstante_kommt_im_code_genau_einmal_als_definition_vor():
    """§ Auftrag: 'kommt im Code genau einmal vor'. calc/abschichtung_common.py
    ist die einzige Definitionsstelle - anderswo darf der Name nur als Import
    oder Verwendung auftauchen, nie als ``PEOPLE_CARRYING_AERIALWAY_TYPES =``.
    """
    dieser_test = Path(__file__).resolve()
    treffer = []
    for pfad in PROJECT_ROOT.rglob("*.py"):
        if any(teil in pfad.parts for teil in (".venv", "venv", "site-packages")):
            continue
        if pfad.resolve() == dieser_test:
            continue  # enthaelt das gesuchte Muster nur als String-Literal
        text = pfad.read_text(encoding="utf-8")
        if "PEOPLE_CARRYING_AERIALWAY_TYPES = {" in text or "PEOPLE_CARRYING_AERIALWAY_TYPES={" in text:
            treffer.append(pfad)
    assert treffer == [PROJECT_ROOT / "calc" / "abschichtung_common.py"]
