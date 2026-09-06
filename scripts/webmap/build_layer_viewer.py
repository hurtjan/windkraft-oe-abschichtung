#!/usr/bin/env python3
"""Build the current main Leaflet Abschichtungsprozess viewer.

Input is ``output/abschichtung/osm_wka_distance_zones.tif`` by default.
Creates one transparent PNG overlay per GeoTIFF band plus an index.html with
checkboxes to toggle layers on/off. By default, PNGs keep the full projected
raster resolution; the default --max-size 2000 creates a practical web preview.
Use --max-size 0 to keep full projected raster resolution.

If the simplified export (``--simplified-input``, default
``output/abschichtung/simplified_150w.tif``) exists, it is rendered into a
second layer group in the same viewer.

Layers are grouped in the panel by category (Mensch / Natur / Geografie /
Total & Ergebnis / Amtliche Zonen), with each category's aggregate band shown
as its bold "Σ total" row.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import array_bounds
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from PIL import Image


from windkraft.viz.band_metadata import (
    BLUR_SIGMA_COLORS,
    CATEGORY_ORDER,
    CATEGORY_TOTALS,
    CLEANED_ZONE_COLOR,
    DEFAULT_COLORS,
    DEFAULT_VISIBLE,
    FALLBACK_COLOR,
    GEO_PREFIXES,
    GEO_WIND_COLOR,
    HUMAN_PREFIXES,
    NATURE_PREFIXES,
    RESULT_PREFIXES,
    VARIANT_SUFFIXES,
    categorize_layer,
    layer_color,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build clickable Leaflet viewer for OSM WKA distance-zone GeoTIFF layers.")
    p.add_argument("--input", default="output/abschichtung/osm_wka_distance_zones.tif")
    p.add_argument("--simplified-input", default="output/abschichtung/simplified_150w.tif")
    p.add_argument("--no-simplified", action="store_true", help="Do not add the simplified export as a second layer group")
    p.add_argument("--output", default="output/abschichtung/viewer")
    p.add_argument(
        "--max-size",
        type=int,
        default=2000,
        help="Maximum width/height of each overlay PNG; default 2000 creates a practical web preview; 0 keeps full projected raster resolution",
    )
    return p.parse_args()


def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)


def overlay_size(width: int, height: int, max_size: int) -> tuple[int, int]:
    if max_size <= 0:
        return width, height
    scale = min(1.0, float(max_size) / max(width, height))
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def render_group(
    src_path: Path,
    layer_dir: Path,
    file_prefix: str,
    title: str,
    default_visible: set[str],
    max_size: int,
) -> tuple[dict, tuple[float, float, float, float], list[int], str]:
    layer_dir.mkdir(parents=True, exist_ok=True)
    for old_png in layer_dir.glob("*.png"):
        old_png.unlink()

    with rasterio.open(src_path) as src:
        dst_crs = "EPSG:3857"
        full_transform, full_w, full_h = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        out_w, out_h = overlay_size(full_w, full_h, max_size)
        scale_x = full_w / out_w
        scale_y = full_h / out_h
        dst_transform = full_transform * full_transform.scale(scale_x, scale_y)
        bounds_3857 = array_bounds(out_h, out_w, dst_transform)
        bounds = transform_bounds("EPSG:3857", "EPSG:4326", *bounds_3857, densify_pts=21)
        layers = []
        for band in range(1, src.count + 1):
            name = src.descriptions[band - 1] or f"band_{band}"
            color = layer_color(name)
            category, is_total = categorize_layer(name)
            arr = np.zeros((out_h, out_w), dtype=np.uint8)
            reproject(
                source=rasterio.band(src, band),
                destination=arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
                src_nodata=src.nodata,
                dst_nodata=0,
            )
            mask = arr > 0
            rgba = np.zeros((out_h, out_w, 4), dtype=np.uint8)
            rgba[mask] = np.array(color, dtype=np.uint8)
            filename = f"{band:02d}_{safe_name(name)}.png"
            Image.fromarray(rgba, mode="RGBA").save(layer_dir / filename, compress_level=1)
            layers.append({
                "band": band,
                "name": name,
                "file": f"{file_prefix}/{filename}",
                "color": color,
                "category": category,
                "is_total": is_total,
                "pixels": int(mask.sum()),
                "default_visible": name in default_visible,
            })
            print(f"wrote {file_prefix}/{filename}: {int(mask.sum())} active pixels")

    group = {
        "id": safe_name(file_prefix),
        "title": title,
        "source": str(src_path),
        "layers": layers,
    }
    return group, bounds, [out_w, out_h], dst_crs


def write_html(out_dir: Path, manifest: dict) -> None:
    html = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OSM WKA Distance Layers</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map { height: 100%; margin: 0; }
    /* Panel als Flex-Spalte: Kopf (Titel/Buttons/Opacity) steht fest, NUR die
       Layerliste scrollt. Genau EIN Scroll-Container - ein zweiter (frueher:
       #panel selbst) laesst beim Scrollen erst die Liste, dann das Panel und
       dann die Karte wandern. overscroll-behavior stoppt das Weiterketten. */
    #panel {
      position: absolute; z-index: 1000; top: 10px; right: 10px;
      max-height: calc(100vh - 20px); width: 390px; box-sizing: border-box;
      display: flex; flex-direction: column; overflow: hidden;
      background: rgba(255,255,255,0.94); border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0,0,0,.25); padding: 10px 12px;
      font: 13px/1.35 system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }
    #panel h2 { font-size: 16px; margin: 0 0 8px; }
    /* Kopfzeilen nie zusammenquetschen; die Liste zusaetzlich hart auf die
       Viewport-Hoehe deckeln - Fallback fuer Browser, in denen max-height am
       Flex-Container die Kinder nicht begrenzt (sonst: Panel abgeschnitten
       und nirgends scrollbar). */
    #panel > :not(#layers) { flex: 0 0 auto; }
    #layers { flex: 1 1 auto; min-height: 0; max-height: calc(100vh - 280px); overflow-y: scroll; overscroll-behavior: contain; border-top: 1px solid #ddd; padding-top: 6px; }
    /* macOS blendet Overlay-Scrollbalken aus - dauerhaft sichtbarer Balken,
       damit man der Liste die Scrollbarkeit ansieht. */
    #layers::-webkit-scrollbar { width: 10px; }
    #layers::-webkit-scrollbar-thumb { background: #c0c0c0; border-radius: 5px; }
    #layers::-webkit-scrollbar-track { background: #f0f0f0; border-radius: 5px; }
    .group { margin: 8px 0 12px; }
    .group h3 { font-size: 14px; margin: 8px 0 4px; }
    .group h4 { font-size: 12px; margin: 10px 0 2px; color: #444; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid #eee; }
    .group-source { color: #666; font-size: 11px; margin-bottom: 4px; word-break: break-word; }
    .layer-row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
    .layer-row.total label { font-weight: 700; }
    .swatch { width: 14px; height: 14px; border: 1px solid #777; flex: 0 0 14px; }
    .layer-row label { flex: 1; word-break: break-word; }
    .small { color: #555; font-size: 12px; margin: 6px 0; }
    input[type=range] { width: 100%; }
    button { margin: 2px 4px 6px 0; }
  </style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h2>OSM WKA GeoTIFF layers</h2>
  <div class="small">Toggle individual GeoTIFF bands. Enthält die vollständige Abschichtung und, falls vorhanden, die vereinfachte 300-W/m²-Version.</div>
  <div class="small"><b id="layer-count"></b> Layer verfügbar. Liste scrollen, um alle Layer zu sehen.</div>
  <button id="none">none</button><button id="all">all</button><button id="finals">finals</button>
  <div class="small">Opacity</div>
  <input id="opacity" type="range" min="0" max="1" step="0.05" value="0.75" />
  <div id="layers"></div>
</div>
<script>
const manifest = __MANIFEST__;
const map = L.map('map');
window._wkaMap = map; // Zugriff für Screenshot-/Automatisierungs-Skripte
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
const bounds = [[manifest.bounds_wgs84[1], manifest.bounds_wgs84[0]], [manifest.bounds_wgs84[3], manifest.bounds_wgs84[2]]];
map.fitBounds(bounds);
const overlays = {};
const allLayers = [];
const layerDiv = document.getElementById('layers');
const opacity = document.getElementById('opacity');
function rgbaCss(c) { return `rgba(${c[0]},${c[1]},${c[2]},${(c[3]||255)/255})`; }
const categoryOrder = manifest.category_order || ['Sonstige'];
for (const group of manifest.groups) {
  const groupEl = document.createElement('div'); groupEl.className = 'group';
  const title = document.createElement('h3'); title.textContent = group.title;
  const source = document.createElement('div'); source.className = 'group-source'; source.textContent = group.source;
  groupEl.appendChild(title); groupEl.appendChild(source);
  for (const cat of categoryOrder) {
    const catLayers = group.layers.filter(l => (l.category || 'Sonstige') === cat);
    if (!catLayers.length) continue;
    const catTitle = document.createElement('h4'); catTitle.textContent = cat; groupEl.appendChild(catTitle);
    const ordered = [...catLayers.filter(l => !l.is_total), ...catLayers.filter(l => l.is_total)];
    for (const layer of ordered) {
      const key = `${group.id}:${layer.name}`;
      const ov = L.imageOverlay(layer.file, bounds, {opacity: Number(opacity.value), interactive: false});
      overlays[key] = ov;
      allLayers.push({...layer, groupId: group.id, key});
      if (layer.default_visible) ov.addTo(map);
      const row = document.createElement('div');
      row.className = layer.is_total ? 'layer-row total' : 'layer-row';
      row.dataset.layerKey = key;
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = !!layer.default_visible;
      cb.onchange = () => cb.checked ? ov.addTo(map) : map.removeLayer(ov);
      const sw = document.createElement('span'); sw.className = 'swatch'; sw.style.background = rgbaCss(layer.color);
      const lab = document.createElement('label');
      lab.textContent = layer.is_total ? `${layer.band}. Σ ${layer.name}` : `${layer.band}. ${layer.name}`;
      row.appendChild(cb); row.appendChild(sw); row.appendChild(lab); groupEl.appendChild(row);
    }
  }
  layerDiv.appendChild(groupEl);
}
document.getElementById('layer-count').textContent = allLayers.length;
opacity.oninput = () => Object.values(overlays).forEach(o => o.setOpacity(Number(opacity.value)));
document.getElementById('none').onclick = () => document.querySelectorAll('#layers input').forEach(cb => { if (cb.checked) cb.click(); });
document.getElementById('all').onclick = () => document.querySelectorAll('#layers input').forEach(cb => { if (!cb.checked) cb.click(); });
document.getElementById('finals').onclick = () => {
  const finals = new Set(manifest.final_layer_names);
  document.querySelectorAll('#layers .layer-row').forEach(row => {
    const layer = allLayers.find(l => l.key === row.dataset.layerKey); const cb = row.querySelector('input');
    const want = finals.has(layer.name); if (cb.checked !== want) cb.click();
  });
};
</script>
</body>
</html>'''
    (out_dir / "index.html").write_text(html.replace("__MANIFEST__", json.dumps(manifest)), encoding="utf-8")


def simplified_group_title(path: Path) -> str:
    """Panel title for the simplified group, derived from the file's threshold tag."""
    try:
        with rasterio.open(path) as src:
            thr = src.tags().get("WIND_THRESHOLD_W_M2")
        if thr:
            return f"Vereinfachte {int(float(thr))}-W/m²-Version"
    except Exception as exc:
        print(f"warning: could not read WIND_THRESHOLD_W_M2 tag from {path}: {exc}")
    return "Vereinfachte Version"


def main() -> None:
    args = parse_args()
    src_path = Path(args.input)
    simplified_path = Path(args.simplified_input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in (out_dir / "manifest.json", out_dir / "index.html"):
        if stale.exists():
            stale.unlink()

    main_group, bounds, preview_size, preview_crs = render_group(
        src_path=src_path,
        layer_dir=out_dir / "layers",
        file_prefix="layers",
        title="Vollständige Abschichtung",
        default_visible=DEFAULT_VISIBLE,
        max_size=args.max_size,
    )
    groups = [main_group]

    if not args.no_simplified:
        if simplified_path.exists():
            simplified_group, simplified_bounds, simplified_size, simplified_crs = render_group(
                src_path=simplified_path,
                layer_dir=out_dir / "simplified_layers",
                file_prefix="simplified_layers",
                title=simplified_group_title(simplified_path),
                default_visible=SIMPLIFIED_DEFAULT_VISIBLE,
                max_size=args.max_size,
            )
            if list(map(round, simplified_bounds)) != list(map(round, bounds)):
                print("warning: simplified bounds differ from main bounds; using main map bounds")
            if simplified_size != preview_size or simplified_crs != preview_crs:
                print("warning: simplified preview grid differs from main preview grid")
            groups.append(simplified_group)
        else:
            print(f"simplified input not found, skipping: {simplified_path}")

    manifest = {
        "source": str(src_path),
        "bounds_wgs84": list(bounds),
        "preview_size": preview_size,
        "preview_crs": preview_crs,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "category_order": CATEGORY_ORDER,
        "groups": groups,
        "layers": groups[0]["layers"],  # backwards-compatible for old consumers of manifest.json
        "final_layer_names": sorted(FINAL_LAYER_NAMES),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_html(out_dir, manifest)
    print(f"Viewer written to {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
