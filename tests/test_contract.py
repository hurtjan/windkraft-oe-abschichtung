"""pipeline/contract.py: der Pfadvertrag muss beim Import nichts prüfen, jeder
RAW-Pfad muss auf eine tatsächlich vorhandene Datei zeigen, die vier
Abschnitte (RAW/PREP/LAYERS/PRODUCTS) müssen überschneidungsfrei sein, die
Layernamen müssen mit denen der Kette übereinstimmen, und
``windkraft.config.load_config()`` muss trotz der Umstellung auf den
Vertrag dieselben ``paths``-Werte wie vor W0.2 liefern.

Siehe docs/rewrite/PLAN.md §8 (Regel 2: "Der Vertrag wird gelesen, nicht
kopiert") und §11.1 (Klassifikation der config.json-Pfade).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pipeline.contract as contract  # noqa: E402
from windkraft.config import load_config  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Import ist seiteneffektfrei
# ---------------------------------------------------------------------------

def test_import_does_not_touch_filesystem(tmp_path, monkeypatch):
    """Ein frischer Import muss auch dann gelingen, wenn ABSCHICHTUNG_ROOT auf
    ein nicht existierendes Verzeichnis zeigt - das ist nur möglich, wenn der
    Import keine Datei öffnet, prüft oder anlegt, sondern rein deklariert."""
    fake_root = tmp_path / "does-not-exist"
    monkeypatch.setenv("ABSCHICHTUNG_ROOT", str(fake_root))
    for mod_name in ("pipeline.contract", "pipeline"):
        sys.modules.pop(mod_name, None)
    try:
        import pipeline.contract as fresh  # noqa: PLC0415

        assert fresh.ROOT == fake_root.resolve()
        assert fresh.RAW["admin"]["vgd"].name == "VGD_50_generalisiert.shp"
        # Keine der beiden Aussagen setzt voraus, dass fake_root existiert -
        # genau das beweist, dass hier nur konstruiert, nicht geprüft wurde.
    finally:
        for mod_name in ("pipeline.contract", "pipeline"):
            sys.modules.pop(mod_name, None)
        import pipeline.contract  # noqa: F401, PLC0415  (mit echter ROOT neu laden)


def _iter_leaf_paths(section) -> list[Path]:
    out = []
    for value in section.values():
        if isinstance(value, dict):
            out.extend(_iter_leaf_paths(value))
        else:
            out.append(value)
    return out


# ---------------------------------------------------------------------------
# 2. Jeder RAW-Pfad existiert tatsächlich
# ---------------------------------------------------------------------------

RAW_PATHS = _iter_leaf_paths(contract.RAW)


@pytest.mark.parametrize(
    "path",
    RAW_PATHS,
    ids=[str(p.relative_to(contract.ROOT)) for p in RAW_PATHS],
)
def test_raw_path_exists(path):
    assert path.exists(), f"RAW-Pfad existiert nicht: {path}"


def test_raw_is_not_empty():
    # Schützt gegen eine leere Struktur, die die Parametrisierung oben
    # stillschweigend zu null Tests verkürzen würde.
    assert len(RAW_PATHS) == 31


# ---------------------------------------------------------------------------
# 2b. LEGACY_TOT und LEGACY_ENTFAELLT: überschneidungsfrei zu RAW, und die
#     Existenz muss genau zum Namen passen - "entfaellt" existiert
#     (wird heute gelesen), "tot" existiert nicht (nie existiert).
# ---------------------------------------------------------------------------

def test_raw_and_legacy_do_not_overlap():
    raw = set(RAW_PATHS)
    tot = set(contract.LEGACY_TOT.values())
    entfaellt = set(contract.LEGACY_ENTFAELLT.values())
    assert not (raw & tot), f"RAW und LEGACY_TOT überschneiden sich: {raw & tot}"
    assert not (raw & entfaellt), f"RAW und LEGACY_ENTFAELLT überschneiden sich: {raw & entfaellt}"
    assert not (tot & entfaellt), (
        f"LEGACY_TOT und LEGACY_ENTFAELLT überschneiden sich: {tot & entfaellt}"
    )


@pytest.mark.parametrize(
    "path",
    list(contract.LEGACY_ENTFAELLT.values()),
    ids=list(contract.LEGACY_ENTFAELLT.keys()),
)
def test_legacy_entfaellt_path_exists(path):
    # Diese Pfade werden heute noch tatsächlich gelesen (siehe Kommentar je
    # Eintrag, welches Welle-1-Paket sie entfernt) - bis dahin gilt für sie
    # dieselbe Zusicherung wie für RAW.
    assert path.exists(), f"LEGACY_ENTFAELLT-Pfad existiert nicht: {path}"


def test_legacy_entfaellt_is_currently_empty():
    """Companion zu test_legacy_entfaellt_path_exists (W1.4): Seit W1.2 ist
    LEGACY_ENTFAELLT leer (der einzige Eintrag, "powerlines_gpkg", ist mit
    der gelöschten Datei entfallen - siehe Kommentar in contract.py und
    Bericht zu W1.2). Ein leeres parametrize(...) erzeugt in pytest keinen
    bestandenen, sondern einen einzigen übersprungenen Testfall ("NOTSET")
    - der prüft dann nichts mehr, er dokumentiert nur die leere Liste.

    contract.py hält LEGACY_ENTFAELLT bewusst als Register für künftige
    Welle-1-Funde offen (§13.1), statt die Sektion ganz zu entfernen - die
    Parametrisierung oben deckt solche künftigen Einträge automatisch ab,
    ohne dass dieser Testcode sich ändern müsste. Aber "bleibt als
    Vorbereitung stehen" darf nicht heißen "prüft bis dahin gar nichts":
    dieser Test läuft immer (keine Parametrisierung) und hält aktiv fest,
    dass die Liste leer ist. Wird sie befüllt, schlägt genau diese Zeile
    fehl - ein bewusster Anstoß, das neu Gefundene zu sichten, statt dass
    es beiläufig durchrutscht.
    """
    assert contract.LEGACY_ENTFAELLT == {}, (
        "LEGACY_ENTFAELLT ist nicht mehr leer - test_legacy_entfaellt_path_exists "
        "deckt die neuen Einträge automatisch ab (Parametrisierung), aber diese "
        "Zusicherung hier ist jetzt überholt und muss bewusst aktualisiert werden."
    )


@pytest.mark.parametrize(
    "path",
    list(contract.LEGACY_TOT.values()),
    ids=list(contract.LEGACY_TOT.keys()),
)
def test_legacy_tot_path_does_not_exist(path):
    # Diese Pfade haben nie existiert - der Codezweig, der sie läse, ist
    # unerreichbar. Existierten sie doch, wäre die Klassifikation falsch.
    assert not path.exists(), f"LEGACY_TOT-Pfad existiert (sollte er nicht): {path}"


# ---------------------------------------------------------------------------
# 3. Kein Pfad bricht aus der Wurzel aus
# ---------------------------------------------------------------------------

def _all_declared_paths():
    paths = list(RAW_PATHS)
    paths.extend(contract.LEGACY_TOT.values())
    paths.extend(contract.LEGACY_ENTFAELLT.values())
    paths.extend(_iter_leaf_paths(contract.PREP))
    paths.extend(contract.LAYERS.values())
    paths.extend(contract.PRODUCTS.values())
    return paths


def test_all_paths_are_absolute_and_within_root():
    for path in _all_declared_paths():
        assert path.is_absolute(), f"Pfad ist nicht absolut: {path}"
        assert contract.ROOT in path.parents or path == contract.ROOT, (
            f"Pfad liegt außerhalb der Wurzel {contract.ROOT}: {path}"
        )
        # Kein rechnerischer Ausbruch über ".." - der aufgelöste Pfad muss mit
        # der Wurzel als Präfix beginnen.
        assert os.path.commonpath([str(contract.ROOT), str(path)]) == str(contract.ROOT)


# ---------------------------------------------------------------------------
# 4. RAW/PREP/LAYERS/PRODUCTS sind überschneidungsfrei und liegen im
#    richtigen Bereich (build/ bzw. out/)
# ---------------------------------------------------------------------------

def test_sections_do_not_overlap():
    raw = set(RAW_PATHS) | set(contract.LEGACY_TOT.values()) | set(contract.LEGACY_ENTFAELLT.values())
    prep = set(_iter_leaf_paths(contract.PREP))
    layers = set(contract.LAYERS.values())
    products = set(contract.PRODUCTS.values())

    sections = {"RAW": raw, "PREP": prep, "LAYERS": layers, "PRODUCTS": products}
    names = list(sections)
    for i, name_a in enumerate(names):
        for name_b in names[i + 1:]:
            overlap = sections[name_a] & sections[name_b]
            assert not overlap, f"{name_a} und {name_b} überschneiden sich: {overlap}"


def test_prep_and_layers_live_under_build():
    for path in _iter_leaf_paths(contract.PREP):
        assert contract.BUILD in path.parents, f"PREP-Pfad nicht unter build/: {path}"
    for path in contract.LAYERS.values():
        assert contract.BUILD in path.parents, f"LAYERS-Pfad nicht unter build/: {path}"


def test_products_live_under_out():
    for path in contract.PRODUCTS.values():
        assert contract.OUT in path.parents, f"PRODUCTS-Pfad nicht unter out/: {path}"
    assert len(contract.PRODUCTS) == 4


def test_raw_lives_under_data():
    for path in RAW_PATHS:
        assert contract.DATA in path.parents, f"RAW-Pfad nicht unter data/: {path}"


# ---------------------------------------------------------------------------
# 5. Layernamen sind eindeutig und decken sich mit der Kette
# ---------------------------------------------------------------------------

def _load_module_from_path(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_layer_names_are_unique():
    assert len(contract.LAYER_NAMES) == len(set(contract.LAYER_NAMES))
    assert len(contract.LAYER_NAMES) == 33


def test_layer_names_match_the_chain():
    """Vergleicht pipeline.contract.LAYER_NAMES gegen die tatsächlichen
    Namenslisten in den drei Skripten, die die Checkpoint-Layer schreiben
    bzw. voraussetzen (02/03/04 der widmung_v2-Kette)."""
    m02 = _load_module_from_path("_test_contract_w02", "scripts/widmung_v2/02_build_hig_sources.py")
    m03 = _load_module_from_path("_test_contract_w03", "scripts/widmung_v2/03_build_osm_layers.py")
    m04 = _load_module_from_path("_test_contract_w04", "scripts/widmung_v2/04_create_distance_zones.py")

    from_chain = set()
    from_chain.update(m02.SOURCE_LAYER_NAMES)
    from_chain.update(m03.OSM_LAYER_NAMES)
    from_chain.update(m03.INFRA_LAYER_NAMES)
    from_chain.update(m03.AIRPORT_LAYER_NAMES)
    from_chain.update(m04.HIG_FAMILY_SOURCE_BANDS)
    from_chain.update(m04.BUFFER_BANDS)
    from_chain.update(m04.NATURE_BANDS)
    from_chain.update(m04.GEOGRAPHY_BANDS)
    from_chain.update(m04.WATER_BANDS)
    from_chain.update(m04.OFFICIAL_ZONING_BANDS)
    from_chain.add(m04.WKA_BESTAND_BAND)

    assert from_chain == set(contract.LAYER_NAMES)


@pytest.mark.skipif(
    not (PROJECT_ROOT / "output" / "abschichtung_widmung_v2" / "distance_layers").is_dir(),
    reason="Checkpoint-Verzeichnis aus einem früheren Kettenlauf nicht vorhanden",
)
def test_layer_names_match_existing_checkpoints():
    layer_dir = PROJECT_ROOT / "output" / "abschichtung_widmung_v2" / "distance_layers"
    on_disk = {p.stem for p in layer_dir.glob("*.tif")}
    assert on_disk == set(contract.LAYER_NAMES)


def test_layers_derive_path_from_name():
    for name in contract.LAYER_NAMES:
        assert contract.LAYERS[name] == contract.BUILD_LAYERS / f"{name}.tif"


# ---------------------------------------------------------------------------
# 6. load_config()["paths"] liefert dieselben Werte wie vor W0.2
# ---------------------------------------------------------------------------

# Wörtlich der Stand vor der Umstellung (siehe git-Historie von config.json /
# windkraft/config.py) - bewusst hier als Konstante festgehalten, damit dieser
# Test trägt, auch wenn config.json und windkraft/config.py künftig
# gemeinsam driften.
EXPECTED_PATHS_BEFORE_W02 = {
    "data_dir": "data",
    "vgd": "data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp",
    "osm_dir": "data/osm/austria-260328-free.shp",
    "wind_pd_150": "data/gelaende/AUT_power-density_150m.tif",
    "wind_pd_100": "data/gelaende/AUT_power-density_100m.tif",
    "dgm": "data/gelaende/DGM_R25.tif",
    "nsg_zip": "data/natur/SG_AT_2024_v_April_Stand_3_April_2024.zip",
    "nsg_gpkg": "SG_AT_2024_v_April.gpkg",
    "nsg_layers": ["NP_AT_2024", "NSG_AT_2024", "ESG_AT_2024", "RAMSAR_AT_2024"],
    # powerlines_gpkg stand hier bis Paket W1.2 ("data/osm_power_lines.gpkg").
    # Mit der Datei ist auch pipeline.contract.LEGACY_ENTFAELLT["powerlines_gpkg"]
    # entfernt worden (siehe Bericht zu W1.2) - cfg["paths"] trägt den
    # Schlüssel seither nicht mehr, ein Vergleich hier wäre ein KeyError.
    "output_dir": "output",
}


def test_load_config_paths_unchanged():
    cfg = load_config()
    for key, expected in EXPECTED_PATHS_BEFORE_W02.items():
        got = cfg["paths"][key]
        assert got == expected, f"paths[{key!r}] geändert: {got!r} != {expected!r}"
        assert type(got) is type(expected), (
            f"paths[{key!r}] hat den Typ gewechselt: {type(got)} != {type(expected)}"
        )
