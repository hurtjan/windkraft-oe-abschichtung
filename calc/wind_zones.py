"""Amtliche Windkraft-Zonen je Bundesland — Positivzonen.

Single source of truth for the polygons behind the reference band
``official_wind_zoning`` (Positivzonen). Both Abschichtung pipelines
(``scripts/main/create_osm_wka_distance_zones.py`` and
``calc/abschichtung_common.py``) load through :func:`load_wind_zones`,
so a new Bundesland only has to be registered in :data:`WIND_ZONE_SOURCES`.

Das Band ist ein reines Referenz-Overlay — es schränkt die berechnete
verfügbare Fläche NICHT ein. Die Rechtswirkung steht je Quelle in
``WindZoneSource.regime``:

``exclusive``
    Positivzone; Windkraft ist nur innerhalb zulässig (Stmk SAPRO Wind, Sbg
    Sachprogramm Wind, Bgld Eignungszonen-Verordnung).
``accelerated``
    Positivzone; beschleunigt die Genehmigung, verbietet das Außerhalb nicht
    (Kärnten RED-III-Windkraftbeschleunigungszonen).

Eine frühere Ausschlusszonen-Registrierung (Negativband
``official_wind_exclusion_zoning``, ``load_wind_exclusion_zones()``,
``WIND_EXCLUSION_ZONE_SOURCES``, Regime ``forbidden``) ist in W1.5 entfernt
worden: das Band existiert im 38-Band-Schema nicht, und die Ladefunktion
hatte keinen Aufrufer (siehe ``docs/rewrite/FORTSCHRITT.md``, Eintrag W1.5).
Der einzige verbliebene Eintrag, ``BgldAus``, filterte dieselbe Datei wie
die Positivzone ``Bgld`` (``data/zonen/WK_Eignungszonen.zip``) nur auf die
andere Attributgruppe — die Positivzone und die Datei bleiben unverändert.

Die NÖ-Zonierung wird nicht hier, sondern über ``--official-zoning-geojson``
geladen und ins Positivband vereinigt.

TODO: Für Band 37 werden fünf kleine amtliche Windzonen-Quellen gebraucht -
data/zonen/zonierung_noe.json, data/zonen/luca_zonen/*, data/zonen/WK_Eignungszonen.zip,
data/zonen/RED_III_Windkraftbeschleunigungszone.zip (zusammen < 2 MB) - die alle
unter dem gitignorten data/-Baum liegen und daher lokal fehlen können (siehe
_resolve_path()). Zu klären: sollen diese fünf Dateien per .gitignore-
Ausnahme fürs öffentliche Repo eingecheckt werden, damit Band 37 reproduzierbar
ist? Vorher muss die Lizenzlage geprüft werden: data.gv.at-Quellen (NÖ) sind
meist CC-BY, aber die Land-GIS-Exporte Bgld/Ktn/Stmk/Sbg sind bislang
ungeprüft.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

TARGET_CRS = "EPSG:31287"

REGIME_EXCLUSIVE = "exclusive"
REGIME_ACCELERATED = "accelerated"


@dataclass(frozen=True)
class WindZoneSource:
    """One official zone dataset.

    ``key``           short id; also the shapefile stem inside the zone directory
    ``source_path``   .zip (zipped shapefile), .shp/.geojson, or ``None`` -> ``<dir>/<key>.shp``
    ``filter_field``  attribute column to filter on; ``None`` -> keep all features
    ``keep_prefixes`` keep only features whose ``filter_field`` starts with one of these
    ``note``          caveat shown in --list-rules (e.g. georeferencing accuracy)
    """

    key: str
    bundesland: str
    regime: str
    label: str
    source_path: str | None = None
    filter_field: str | None = None
    keep_prefixes: tuple[str, ...] = ()
    note: str = ""


# Positivzonen -> Band official_wind_zoning.
# Order is cosmetic (log output only); the masks are OR-combined.
WIND_ZONE_SOURCES = (
    WindZoneSource(
        key="Stmk",
        bundesland="Steiermark",
        regime=REGIME_EXCLUSIVE,
        label="Vorrang-/Eignungszonen (SAPRO Wind)",
    ),
    WindZoneSource(
        key="Sbg",
        bundesland="Salzburg",
        regime=REGIME_EXCLUSIVE,
        label="Vorrangzonen (Sachprogramm Windkraft)",
    ),
    WindZoneSource(
        key="Bgld",
        bundesland="Burgenland",
        regime=REGIME_EXCLUSIVE,
        label="Eignungszonen gem. Verordnung",
        # source_path ist hier hartkodiert und NICHT per CLI überschreibbar
        # (anders als --official-zoning-geojson). Liegt unter dem gitignorten
        # data/-Baum, also nicht im Repo. Fehlt die Datei lokal, überspringt
        # _resolve_path() (~Zeile 157-170) diese Quelle still (nur [warn]-Log,
        # kein Abbruch) - Band 37 (official_wind_zoning) wird dadurch unbemerkt
        # unvollständig, ohne dass der Lauf das meldet.
        source_path="data/zonen/WK_Eignungszonen.zip",
        # Die Datei enthält Eignungs- UND Ausschlusszonen im selben Layer.
        # Ohne Filter landeten die Ausschlusszonen im Windzonen-Band.
        filter_field="Status",
        keep_prefixes=("Eignungszone",),
    ),
    WindZoneSource(
        key="RED3",
        bundesland="Kärnten",
        regime=REGIME_ACCELERATED,
        label="RED-III-Windkraftbeschleunigungszonen",
        # Ebenfalls hartkodiert, nicht per CLI überschreibbar, unter dem
        # gitignorten data/-Baum; fehlt die Datei, überspringt _resolve_path()
        # (~Zeile 157-170) sie still - gleiches Risiko für Band 37 wie beim
        # Bgld-Eintrag oben.
        source_path="data/zonen/RED_III_Windkraftbeschleunigungszone.zip",
    ),
)


def _inner_shapefile(zip_path: Path) -> str | None:
    """Name of the single .shp inside a zipped shapefile, or None."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    except (zipfile.BadZipFile, OSError) as exc:
        print(f"[warn]  wind zone zip unreadable: {zip_path} ({exc})", flush=True)
        return None
    if not names:
        print(f"[warn]  wind zone zip contains no .shp: {zip_path}", flush=True)
        return None
    return names[0]


def _resolve_path(source: WindZoneSource, zone_dir: Path) -> str | None:
    """Resolve a registry entry to a path geopandas can open, or None.

    ``source_path`` may be a zipped shapefile (.zip), a plain vector file
    (.shp/.geojson/...), or ``None`` for ``<zone_dir>/<key>.shp``.
    """
    path = Path(source.source_path) if source.source_path else zone_dir / f"{source.key}.shp"
    if not path.exists():
        print(f"[warn]  wind zone source missing: {path}", flush=True)
        return None
    if path.suffix.lower() != ".zip":
        return str(path)
    inner = _inner_shapefile(path)
    return f"zip://{path}!{inner}" if inner else None


def _apply_filter(gdf: gpd.GeoDataFrame, source: WindZoneSource) -> gpd.GeoDataFrame:
    """Keep only the features that actually are wind zones.

    Raises on a missing filter column: silently skipping the filter would mix
    Ausschlusszonen into the wind zone band, which is worse than a hard failure.
    """
    if not source.filter_field:
        return gdf
    if not source.keep_prefixes:
        raise ValueError(f"wind zone source '{source.key}' sets filter_field but no keep_prefixes")
    if source.filter_field not in gdf.columns:
        raise KeyError(
            f"wind zone source '{source.key}' expects attribute "
            f"'{source.filter_field}' (available: {sorted(gdf.columns)})"
        )
    values = gdf[source.filter_field].astype("string").fillna("")
    keep = values.str.startswith(source.keep_prefixes)
    return gdf[keep.fillna(False)]


def _clip_to_bundesland(
    gdf: gpd.GeoDataFrame,
    source: WindZoneSource,
    bl_boundaries: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Clip a source to the Bundesland whose authority issued it.

    Necessary because some datasets are delivered with the full analysis extent
    rather than the legal extent: the OÖ Windkraft-Masterplan reaches ~960 km²
    into Salzburg/Steiermark/NÖ in large blobs, and the PDF-derived Stmk 2026
    zones bleed ~8 km² across the Kärnten border. A Landesverordnung has no
    effect outside its Bundesland, so attributing that area would be wrong.
    """
    match = bl_boundaries[bl_boundaries["BL"] == source.bundesland]
    if match.empty:
        print(f"[warn]  no boundary for '{source.bundesland}', zone source '{source.key}' left unclipped", flush=True)
        return gdf
    clipped = gpd.clip(gdf, match.geometry.union_all())
    dropped = (gdf.area.sum() - clipped.area.sum()) / 1e6
    if dropped > 0.5:
        print(f"[info]  zone source '{source.key}': {dropped:.1f} km² outside {source.bundesland} clipped away", flush=True)
    return clipped


def _clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop empty/null geometries and repair invalid ones without mutating input."""
    out = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    if out.empty:
        return out
    invalid = ~out.geometry.is_valid
    if invalid.any():
        out.loc[invalid, "geometry"] = out.geometry[invalid].buffer(0)
    return out[out.geometry.notnull() & ~out.geometry.is_empty]


def load_zones(
    sources: tuple[WindZoneSource, ...],
    zone_dir: str | Path,
    enabled: bool = True,
    bl_boundaries: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame | None:
    """Load and merge a registry of official zones into one GeoDataFrame.

    ``zone_dir`` only applies to sources without an own ``source_path``.
    ``bl_boundaries`` (a GeoDataFrame with a ``BL`` column) clips every source to
    its issuing Bundesland; pass ``None`` to keep the raw delivered extent.
    Returns ``None`` when disabled or when no source could be read.
    """
    if not enabled:
        return None
    zdir = Path(zone_dir)
    frames: list[gpd.GeoDataFrame] = []
    for source in sources:
        path = _resolve_path(source, zdir)
        if path is None:
            continue
        gdf = _clean_geometries(_apply_filter(gpd.read_file(path), source).to_crs(TARGET_CRS))
        if bl_boundaries is not None and not gdf.empty:
            gdf = _clean_geometries(_clip_to_bundesland(gdf, source, bl_boundaries))
        if gdf.empty:
            print(f"[warn]  wind zone source '{source.key}' has no usable features", flush=True)
            continue
        print(
            f"[info]  wind zones {source.bundesland} ({source.key}, {source.regime}): "
            f"n={len(gdf)}, {gdf.area.sum() / 1e6:.1f} km²",
            flush=True,
        )
        frames.append(gdf[["geometry"]])
    if not frames:
        print("[warn]  zones enabled but no source could be loaded", flush=True)
        return None
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=TARGET_CRS)


def load_wind_zones(
    zone_dir: str | Path,
    enabled: bool = True,
    bl_boundaries: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame | None:
    """Positivzonen for the band ``official_wind_zoning``."""
    return load_zones(WIND_ZONE_SOURCES, zone_dir, enabled, bl_boundaries)


def describe_sources(sources: tuple[WindZoneSource, ...] = WIND_ZONE_SOURCES) -> str:
    """One line per registered source, for --list-rules output."""
    return "\n".join(
        f"  {s.key:12s} {s.bundesland:17s} {s.regime:12s} {s.label}  "
        f"[{s.source_path or f'<zone-dir>/{s.key}.shp'}]" + (f"\n{'':14s}-> {s.note}" if s.note else "")
        for s in sources
    )
