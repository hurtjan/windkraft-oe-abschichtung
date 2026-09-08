"""Äquivalenztest: distance_engine.py (NEU) gegen kataster_layers.py (ALT).

Dieser Test importiert die unveränderte Originaldatei aus dem Alt-Repo
`windkraft_ö_karten` direkt über ihren absoluten Pfad. Er ist das
Verifikationsartefakt der Migration von `fft_circle_dilation` und `ns_kind`
nach `windkraft/calc/distance_engine.py` - KEIN dauerhafter Unittest. Sobald
das Alt-Repo nicht mehr existiert (oder die Datei dort geändert wird), wird er
bedeutungslos und darf entfernt werden.

## Der Alt-Repo-Pfad, und was W4.3 daran repariert hat

Der Pfad stand hier als nacktes Literal, und `_load_old_module()` lief beim
**Import** des Moduls. Auf jeder Maschine ohne dieses Alt-Repo - und in jedem
Wegwerf-Worktree, dessen Nachbarverzeichnis anders heißt - brach damit nicht
dieser eine Test ab, sondern die **Sammelphase von `make test`** mit einem
`FileNotFoundError`: ein Kollektionsfehler, kein Testergebnis. Ein Test, der
ein Verifikationsartefakt für eine abgeschlossene Migration ist, darf die
gesamte Testsuite einer fremden Maschine nicht unbenutzbar machen.

Zwei Änderungen, beide ohne Wirkung auf das, was der Test misst:

1. Der Pfad ist über `ABSCHICHTUNG_ALTREPO` überschreibbar (dasselbe Muster
   wie `ABSCHICHTUNG_ROOT` in `pipeline/contract.py`); das bisherige Literal
   bleibt der Default, damit sich auf dieser Maschine nichts ändert.
2. Fehlt die Alt-Datei, überspringt sich das Modul sauber selbst
   (`pytest.skip(..., allow_module_level=True)`) mit einer Begründung, die
   den erwarteten Pfad nennt - statt die Sammelphase abzubrechen.

`sys.dont_write_bytecode = True` steht weiterhin vor dem Laden der Alt-Datei:
das Alt-Repo gilt als read-only, und ein `__pycache__` dort hinein wäre ein
Schreibzugriff.
"""
import os
import sys

sys.dont_write_bytecode = True

import importlib.util
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.distance_engine import fft_circle_dilation as fft_circle_dilation_new  # noqa: E402
from windkraft.calc.distance_engine import ns_kind as ns_kind_new  # noqa: E402

OLD_REPO_ROOT = os.environ.get(
    "ABSCHICHTUNG_ALTREPO", "/Users/jhurt/Documents/windkraft_ö_karten"
)
OLD_MODULE_PATH = OLD_REPO_ROOT + "/windkraft/calc/kataster_layers.py"

if not Path(OLD_MODULE_PATH).is_file():
    pytest.skip(
        f"Alt-Repo-Datei {OLD_MODULE_PATH} nicht vorhanden - dieser Aequivalenztest "
        "vergleicht gegen das unveraenderte Original aus windkraft_ö_karten und ist "
        "ohne dieses Repo gegenstandslos. Anderer Ort: ABSCHICHTUNG_ALTREPO setzen.",
        allow_module_level=True,
    )


def _load_old_module():
    """Lädt kataster_layers.py direkt aus dem unveränderten Alt-Repo.

    Das Alt-Repo-Root wird nur für die Dauer dieses Imports auf sys.path
    gelegt (try/finally), damit die eigenen `windkraft.*`-Imports der Alt-Datei
    (terrain, siedlung_method, util/admin, config) aufloesen. Zusaetzlich wird
    der sys.modules-Cache um jeden bereits vorhandenen "windkraft"-Eintrag
    (aus dem NEUEN Repo, s.o. bereits importiert) fuer die Dauer des Ladens
    verdraengt und danach wiederhergestellt - sonst wuerde Python die
    Alt-Importe faelschlich gegen das schon gecachte NEUE windkraft-Paket
    aufloesen (gleicher Paketname, unterschiedlicher Ort auf der Platte).
    """
    saved_modules = {
        name: mod
        for name, mod in sys.modules.items()
        if name == "windkraft" or name.startswith("windkraft.")
    }
    for name in list(saved_modules):
        del sys.modules[name]

    sys.path.insert(0, OLD_REPO_ROOT)
    try:
        spec = importlib.util.spec_from_file_location("old_kataster_layers", OLD_MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        # dataclasses._is_type() looks up cls.__module__ in sys.modules while
        # resolving type hints, so the module must be registered before exec.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(OLD_REPO_ROOT)
        sys.modules.pop("old_kataster_layers", None)
        for name in list(sys.modules):
            if name == "windkraft" or name.startswith("windkraft."):
                del sys.modules[name]
        sys.modules.update(saved_modules)


_OLD_MODULE = _load_old_module()
fft_circle_dilation_old = _OLD_MODULE.fft_circle_dilation
ns_kind_old = _OLD_MODULE.ns_kind


# ---------------------------------------------------------------------------
# fft_circle_dilation
# ---------------------------------------------------------------------------

CELL_M = 1.0
TILE_SIZE = 8  # willkuerlich gewaehlte, aber realistische interne Kachelgroesse


def _compare_dilation(base: np.ndarray, buffer_m: float, tile_size: int = TILE_SIZE, label: str = "test") -> None:
    old = fft_circle_dilation_old(base.copy(), buffer_m, CELL_M, tile_size, label)
    new = fft_circle_dilation_new(base.copy(), buffer_m, CELL_M, tile_size, label)
    assert old.dtype == new.dtype
    assert old.shape == new.shape
    assert np.array_equal(old, new), (
        f"Mismatch: {int(np.count_nonzero(old != new))} von {old.size} Pixeln "
        f"unterschiedlich (buffer_m={buffer_m}, tile_size={tile_size})"
    )


@pytest.mark.parametrize("buffer_m", [3.0, 12.0])
def test_dilation_radius_smaller_and_larger_than_tile_size(buffer_m):
    # TILE_SIZE=8: buffer_m=3 (radius_px=3 < 8) und buffer_m=12 (radius_px=12 > 8)
    rng = np.random.default_rng(1234)
    base = rng.random((24, 24)) < 0.05
    _compare_dilation(base, buffer_m)


def test_dilation_object_exactly_on_tile_boundary():
    base = np.zeros((24, 24), dtype=bool)
    # TILE_SIZE=8 -> Kachelgrenzen bei x=8,16 und y=8,16
    base[8, 8] = True
    _compare_dilation(base, buffer_m=4.0)


def test_dilation_object_at_raster_edge():
    base = np.zeros((16, 16), dtype=bool)
    base[0, 0] = True
    base[0, 15] = True
    base[15, 0] = True
    base[15, 15] = True
    _compare_dilation(base, buffer_m=5.0)


def test_dilation_empty_input():
    base = np.zeros((20, 20), dtype=bool)
    _compare_dilation(base, buffer_m=6.0)


def test_dilation_radius_zero():
    base = np.zeros((20, 20), dtype=bool)
    base[10, 10] = True
    base[5, 3] = True
    _compare_dilation(base, buffer_m=0.0)


def test_dilation_single_isolated_pixel():
    base = np.zeros((20, 20), dtype=bool)
    base[9, 11] = True
    _compare_dilation(base, buffer_m=4.0)


def test_dilation_fully_filled_mask():
    base = np.ones((20, 20), dtype=bool)
    _compare_dilation(base, buffer_m=6.0)


def test_dilation_random_mask_various_shapes():
    rng = np.random.default_rng(42)
    for shape in [(17, 23), (32, 32), (9, 40)]:
        base = rng.random(shape) < 0.1
        _compare_dilation(base, buffer_m=7.0)


# ---------------------------------------------------------------------------
# ns_kind
# ---------------------------------------------------------------------------

NS_KIND_CASES = [
    (None, None),
    (None, "Baufläche"),
    ("41", None),
    ("041", None),
    ("FIG041", None),
    (41, None),
    (41.0, None),
    ("66", None),
    ("52", None),
    ("71", None),
    ("FIG052", None),
    ("99", None),
    (None, "Baufläche"),
    (None, "Bauflaeche"),
    (None, "Garten"),
    ("99", "Baufläche"),
    ("99", "Bauflaeche"),
    ("99", "Garten"),
    ("99", "garten (Zwischenhaus)"),
    ("", ""),
    ("  41  ", None),
    ("abc", None),
    ("abc", "unbekannt"),
    (None, None),
]


@pytest.mark.parametrize("ns,category", NS_KIND_CASES)
def test_ns_kind_equivalence(ns, category):
    assert ns_kind_old(ns, category) == ns_kind_new(ns, category)
