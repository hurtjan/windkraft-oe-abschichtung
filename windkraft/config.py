"""Konfiguration laden und Pfade auflösen."""

import json
import math
import os
from pathlib import Path

from pipeline import contract


def load_config(path=None):
    """Lädt config.json (oder gegebenen Pfad) und gibt das dict zurück.

    Pfade werden relativ zum Verzeichnis der Config-Datei aufgelöst.
    Abgeleitete Werte (SLOPE_THRESHOLD_PCT, PD_RATIO usw.) werden ergänzt.
    """
    if path is None:
        path = Path("config.json")
    path = Path(path)

    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    config_dir = path.parent
    paths = cfg["paths"]

    # Die fünf tatsächlich gelesenen Pfade (siehe docs/rewrite/PLAN.md §11.1,
    # Klasse F; bis Paket W1.2 waren es sechs - powerlines_gpkg ist mit dem
    # Codeeintrag entfallen, siehe pipeline/contract.py:LEGACY_ENTFAELLT und
    # den Bericht zu W1.2) plus den einen toten (Klasse U, wind_pd_100)
    # kommen jetzt ausschließlich aus dem Pfadvertrag - config.json führt sie
    # nicht mehr als eigenes Literal. Zwei Quellen für denselben Pfad waren
    # genau die Doppelung, die diesen Umbau nötig gemacht hat (PLAN.md §8,
    # Regel 2). Gleiche Darstellung wie zuvor (relativ zum
    # Config-Verzeichnis), damit sich am Konsumentenverhalten - überall
    # ``Path(cfg["paths"][...])`` - nichts ändert, nur die Quelle ist neu.
    contract_paths = {
        "vgd": contract.RAW["admin"]["vgd"],
        "osm_dir": contract.LEGACY_TOT["osm_dir"],
        "wind_pd_150": contract.RAW["gelaende"]["wind_pd_150"],
        "wind_pd_100": contract.LEGACY_TOT["wind_pd_100"],
        "dgm": contract.RAW["gelaende"]["dgm"],
        "nsg_zip": contract.RAW["natur"]["nsg_zip"],
    }
    for key, abs_path in contract_paths.items():
        paths[key] = os.path.relpath(abs_path, start=config_dir)

    # data_dir/output_dir bleiben JSON-Literale: kein Konsument (siehe
    # PLAN.md §11.1) und kein Teil des Vertrags - output_dir ist der
    # bestehende output/-Baum, nicht das künftige out/ aus
    # pipeline.contract.PRODUCTS.
    for key in ("data_dir", "output_dir"):
        paths[key] = str(config_dir / paths[key])

    # Abgeleitete Wind-Parameter
    wcfg = cfg["wind"]
    alpha = wcfg["shear_alpha"]
    heights = wcfg["pd_data_heights_m"]
    pd_min_h = wcfg["pd_min_height_m"]
    cfg["_derived"] = {
        "pd_ratio_150_130": (heights[1] / pd_min_h) ** (3 * alpha),
        "power_density_min_150": wcfg["pd_min"] * (heights[1] / pd_min_h) ** (3 * alpha),
        "slope_threshold_pct": math.tan(math.radians(cfg["exclusion"]["slope_max_deg"])) * 100,
        "turbine_density": 1000.0 / cfg["turbine"]["specific_area_m2_per_kw"],
    }

    # Elevation-Bänder als Tupel
    cfg["terrain_correction"]["elevation_bands"] = [
        tuple(b) for b in cfg["terrain_correction"]["elevation_bands"]
    ]

    # Studie-Referenz als Tupel
    sref = cfg.get("study_reference", {})
    studie = {}
    for bl, vals in sref.get("by_bundesland", {}).items():
        studie[bl] = tuple(vals)
    cfg["_studie"] = studie
    cfg["_studie_fläche"] = sref.get("total_area_km2", 0)
    cfg["_studie_mw"] = sref.get("total_mw", 0)

    # Major-Airport-IDs als Set
    cfg["buffers"]["_major_airport_ids"] = set(
        cfg["buffers"].get("major_airport_osm_ids", [])
    )

    return cfg
