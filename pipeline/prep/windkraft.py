"""Prepare the authoritative Austrian wind-turbine inventory.

``data/windkraft/windkraft_standorte_at.geojson`` is an RFC 7946 GeoJSON.
It deliberately has no legacy GeoJSON ``crs`` member; its longitude/latitude
coordinates are therefore assigned CRS84 / EPSG:4326 explicitly here before
they are projected to the project CRS, EPSG:31287.  This module is the one
and only positive turbine source for both the Band-38 builder and the point
export.  OSM's ``windpower`` layer is intentionally outside this data flow:
it remains a negative safeguard in ``pipeline.layers.osm`` so turbine-tagged
objects cannot become generic buildings.

The delivered source has no properties.  The derived Parquet therefore holds
only an opaque, deterministic ``wka_id`` and the Point geometry. Exact raw
coordinate duplicates are collapsed while preserving a stable ID derived from
the full source coordinate pair.  The raw GeoJSON is never changed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd

from pipeline import contract, fingerprint, runtime

SOURCE_CRS = "EPSG:4326"
TARGET_CRS = "EPSG:31287"
TARGET_EPSG = 31287
OUTPUT_FILENAME = "standorte.parquet"
ID_COLUMN = "wka_id"
EXPECTED_RAW_FEATURES = 1_388
EXPECTED_UNIQUE_COORDINATES = 1_386


def output_path() -> Path:
    """The sole prepared-input path shared by the two WKA consumers."""
    return contract.PREP["windkraft"] / OUTPUT_FILENAME


def _raw_features(path: Path) -> list[dict]:
    """Read and validate the RFC 7946 FeatureCollection without mutating it."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"WKA source is not a GeoJSON FeatureCollection: {path}")
    if "crs" in data:
        raise ValueError(
            "WKA source unexpectedly declares a GeoJSON crs member; update the "
            "explicit CRS decision instead of silently overriding it."
        )
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("WKA source has no feature list")
    return features


def _coordinate_pair(feature: dict, index: int) -> tuple[float, float]:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "Point":
        raise ValueError(
            f"WKA feature {index} must be a Point, got {geometry.get('type')!r}"
        )
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError(f"WKA Point {index} has no two-dimensional coordinates")
    lon, lat = coordinates[:2]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise ValueError(f"WKA Point {index} has non-numeric coordinates")
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(f"WKA Point {index} is outside WGS84 coordinate bounds: {coordinates!r}")
    return float(lon), float(lat)


def _stable_id(lon: float, lat: float) -> str:
    """Opaque, source-neutral ID stable across input feature ordering."""
    source_key = f"{lon:.15g},{lat:.15g}"
    digest = hashlib.sha256(source_key.encode("ascii")).hexdigest()[:16]
    return f"wka_at_{digest}"


def normalize(path: Path | None = None) -> gpd.GeoDataFrame:
    """Validate raw Points, deduplicate exact coordinates, and reproject once."""
    source = path or contract.RAW["windkraft"]["standorte"]
    features = _raw_features(source)
    coordinates = [_coordinate_pair(feature, index) for index, feature in enumerate(features)]
    unique_coordinates = list(dict.fromkeys(coordinates))
    ids = [_stable_id(lon, lat) for lon, lat in unique_coordinates]
    if len(ids) != len(set(ids)):
        raise ValueError("stable WKA IDs collided; increase the digest length")

    gdf = gpd.GeoDataFrame(
        {ID_COLUMN: ids},
        geometry=gpd.points_from_xy(
            [lon for lon, _ in unique_coordinates],
            [lat for _, lat in unique_coordinates],
        ),
        # Explicitly assign RFC 7946 WGS84 rather than relying on a reader
        # default for a GeoJSON file without a crs member.
        crs=SOURCE_CRS,
    ).to_crs(TARGET_CRS)
    if not (gdf.geometry.geom_type == "Point").all():
        raise ValueError("WKA prep produced non-Point geometry")
    return gdf


def run(force: bool = False) -> Path:
    source = contract.RAW["windkraft"]["standorte"]
    out_dir = contract.PREP["windkraft"]
    out_path = output_path()
    inputs = [source, Path(__file__)]
    runtime.ensure_dir(out_dir)

    if not force and out_path.exists() and fingerprint.matches(out_dir, inputs):
        print(f"[skip]  prep-windkraft: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_path

    prepared = normalize(source)
    prepared.to_parquet(out_path, index=False)
    fingerprint.write(out_dir, inputs)

    raw_count = len(_raw_features(source))
    deduplicated = raw_count - len(prepared)
    print(
        f"[done]  prep-windkraft: {raw_count:,} RFC-7946 Points (EPSG:4326) -> "
        f"{len(prepared):,} eindeutige Punkte (EPSG:31287), "
        f"{deduplicated:,} exakte Duplikate entfernt -> {out_path}",
        flush=True,
    )
    return out_path


def load_prepared() -> gpd.GeoDataFrame:
    """Load the authoritative normalized turbines; fail closed if absent."""
    path = output_path()
    if not path.exists():
        raise SystemExit(
            f"[fehler] {path} fehlt - pipeline/prep/windkraft.py noch nicht gelaufen "
            "('make prep-windkraft')."
        )
    gdf = gpd.read_parquet(path)
    if ID_COLUMN not in gdf.columns:
        raise ValueError(f"prepared WKA inventory lacks {ID_COLUMN!r}: {path}")
    if gdf.crs is None or gdf.crs.to_epsg() != TARGET_EPSG:
        raise ValueError(f"prepared WKA inventory has CRS {gdf.crs!r}, expected {TARGET_CRS}: {path}")
    if not (gdf.geometry.geom_type == "Point").all():
        raise ValueError(f"prepared WKA inventory contains non-Point geometries: {path}")
    if gdf[ID_COLUMN].duplicated().any():
        raise ValueError(f"prepared WKA inventory contains duplicate {ID_COLUMN} values: {path}")
    return gdf


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
