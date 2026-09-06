"""Konfiguration laden und Pfade auflösen."""

import json
import math
from pathlib import Path


def load_config(path=None):
    """Lädt config.json (oder gegebenen Pfad) und gibt das dict zurück.

    Pfade werden relativ zum Verzeichnis der Config-Datei aufgelöst.
    Abgeleitete Werte (SLOPE_THRESHOLD_PCT, PD_RATIO usw.) werden ergänzt.
    """
    if path is None:
        path = Path("config/config.json")
    path = Path(path)

    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    # Pfade relativ zur Config-Datei auflösen
    config_dir = path.parent
    paths = cfg["paths"]
    for key in ("data_dir", "vgd", "osm_dir", "wind_pd_150", "wind_pd_100",
                "dgm", "nsg_zip", "powerlines_gpkg", "output_dir"):
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
