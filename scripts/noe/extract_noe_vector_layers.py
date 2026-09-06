"""Extrahiert Flächen direkt aus den VEKTOR-Pfaden der offiziellen NÖ-Karte
"Mindestabstandszonen" (TeilC 3.2) — ohne Bilderkennung.

Das PDF enthält die Flächen als echte Vektor-Pfade (page.get_drawings()), je
mit einer eindeutigen Füllfarbe. Diese Pfade werden nach Farbe gefiltert, aus
den PDF-Punktkoordinaten rekonstruiert und über die vorhandene Affin-
Georeferenzierung (alignment_mindestabstand.json) nach EPSG:31287 transformiert.

Extrahierte Layer (Füllfarbe laut PDF-Legende):
  * Wohnbaulandflächen            -> grau   (156,156,156)
  * 1200 m zu Wohnbaulandflächen  -> tan    (255,211,127)   "Siedlungs-Abstand"
  * 1200 m zu Bauland-Sondergeb.  -> gold   (205,170,102)

Dazu die drei 750-m-Klassen derselben Karte — sie sind die maßgebliche
Häuser-im-Grünen-Quelle für Niederösterreich, weil RRU_WI_HUELLE keine
Wohnen-im-Grünland-Kategorie kennt (nur `Gho`, 996 Flächen) und nur 8,5 % der
Landesfläche abdeckt:
  * 750 m zu Gebäuden                    -> gelb  (230,230,0)
  * 750 m zu GWR-Objekten                -> rosa  (215,158,158)   amtl. Bewohnt-Signal
  * 750 m zu Grünland-Widmungen          -> grün  (137,205,102)

ACHTUNG: Diese drei Layer sind bereits Objekt **plus** 750 m Puffer. In der
v2-Abschichtung dienen sie nur noch als Kandidatenfilter/Abdeckungsmaske; ins
HiG-Quellband fließen die daraus rekonstruierten QUELLOBJEKTE
(pdf_hig_source_*.geojson, siehe windkraft/noe/pdf_hig_sources.py), die die
Pipeline dann einheitlich mit 750 m puffert.

Aufruf:
    uv run --extra pdf python scripts/noe/extract_noe_vector_layers.py
"""

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF
import geopandas as gpd
import shapely
from shapely.affinity import affine_transform
from shapely.geometry import Polygon

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.noe.pdf_hig_sources import derive_layer_files  # noqa: E402

PDF_PATH = Path("data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf")
ALIGN_PATH = Path("output/noe/alignment_mindestabstand.json")
VGD_PATH = Path("data/admin_boundaries/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp")
OUT_DIR = Path("output/noe")

NOE_BL_KZ = "3"
COLOR_TOL = 0.02              # Toleranz für Farb-Match (Vektorfarben sind exakt)
BEZIER_STEPS = 8             # Sampling-Schritte je Bézier-Kurve
SIMPLIFY_TOL_M = 8.0         # leichte Vereinfachung in Metern (EPSG:31287)

# Layer-Definition: key -> (Füllfarbe RGB 0-1, Dateibasis, ob auflösen/zusammenfassen)
# Die Farbwerte sind die EXAKTEN Vektorfüllfarben aus page.get_drawings(),
# nicht rastergesampelte Näherungen (COLOR_TOL deckt Rundung ab).
LAYERS = {
    "wohnbauland":              ((0.612, 0.612, 0.612), "wohnbauland",               True),
    "siedlungsabstand_1200m":   ((1.000, 0.827, 0.498), "siedlungsabstand_1200m",    True),
    "abstand_sondergebiet_1200m": ((0.804, 0.667, 0.400), "abstand_sondergebiet_1200m", True),
    # 750-m-Klassen (Objekt + Puffer bereits enthalten, siehe Modul-Docstring)
    "pdf_750m_geb":               ((0.90196, 0.90196, 0.00000), "pdf_750m_geb",               True),
    "pdf_750m_gwr":               ((0.84314, 0.61961, 0.61961), "pdf_750m_gwr",               True),
    "pdf_750m_gruenland_widmung": ((0.53726, 0.80392, 0.40000), "pdf_750m_gruenland_widmung", True),
}

# Die drei Klassen, die build_hig_sources.py / die v2-Abschichtung als fertige
# 750-m-Zonen liest (Reihenfolge = Priorität in der Legende).
NOE_PDF_750M_LAYERS = ("pdf_750m_geb", "pdf_750m_gwr", "pdf_750m_gruenland_widmung")


def color_matches(fill, target) -> bool:
    """True, wenn die Füllfarbe (RGB 0-1) der Zielfarbe entspricht."""
    if fill is None or len(fill) != 3:
        return False
    return all(abs(a - b) <= COLOR_TOL for a, b in zip(fill, target))


def _sample_bezier(p0, p1, p2, p3, steps=BEZIER_STEPS):
    """Punkte entlang einer kubischen Bézier-Kurve (ohne Startpunkt)."""
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt**3 * p0.x + 3 * mt**2 * t * p1.x + 3 * mt * t**2 * p2.x + t**3 * p3.x)
        y = (mt**3 * p0.y + 3 * mt**2 * t * p1.y + 3 * mt * t**2 * p2.y + t**3 * p3.y)
        pts.append((x, y))
    return pts


def path_to_rings(items) -> list:
    """Rekonstruiert geschlossene Punktringe aus den PDF-Zeichenbefehlen."""
    rings, ring = [], []

    def flush():
        if len(ring) >= 3:
            rings.append(ring.copy())
        ring.clear()

    def last():
        return ring[-1] if ring else None

    for it in items:
        op = it[0]
        if op == "l":          # Linie p1->p2
            p1, p2 = it[1], it[2]
            if not ring:
                ring.append((p1.x, p1.y))
            elif abs(last()[0] - p1.x) > 1e-3 or abs(last()[1] - p1.y) > 1e-3:
                flush(); ring.append((p1.x, p1.y))
            ring.append((p2.x, p2.y))
        elif op == "c":        # kubische Bézier p1..p4
            p1, p2, p3, p4 = it[1], it[2], it[3], it[4]
            if not ring:
                ring.append((p1.x, p1.y))
            elif abs(last()[0] - p1.x) > 1e-3 or abs(last()[1] - p1.y) > 1e-3:
                flush(); ring.append((p1.x, p1.y))
            ring.extend(_sample_bezier(p1, p2, p3, p4))
        elif op == "re":       # Rechteck als eigener Ring
            flush()
            r = it[1]
            rings.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
        elif op == "qu":       # Quad als eigener Ring
            flush()
            q = it[1]
            rings.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y),
                          (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
    flush()
    return rings


def load_pixel_transform(align: dict):
    """Liefert (pdf->cropped-pixel)-Parameter und (cropped-pixel->geo)-Affine."""
    scale = align["render_dpi"] / 72.0
    vp = align["vp_bbox"]
    # Crop-Offsets identisch zur Georeferenzierung
    px_left = int(vp[0] * scale)
    # py_top: PDF-Oberkante des Crops; page_h kommt aus dem PDF
    return scale, px_left, vp


def pixel_to_geo_params(align: dict) -> list:
    import numpy as np
    src = np.array(align["pixel_corners"], dtype=float)
    dst = np.array(align["gpts_proj"], dtype=float)
    src_aug = np.hstack([src, np.ones((len(src), 1))])
    a_east, *_ = np.linalg.lstsq(src_aug, dst[:, 0], rcond=None)
    a_north, *_ = np.linalg.lstsq(src_aug, dst[:, 1], rcond=None)
    return [a_east[0], a_east[1], a_north[0], a_north[1], a_east[2], a_north[2]]


def rings_to_evenodd(rings, scale, px_left, px_top):
    """Even-odd-Fläche eines Pfades: symmetrische Differenz aller Ringe.

    Die Karte verwendet die even-odd Fill-Rule -> innere Ringe sind Löcher
    (Donut). XOR der Ring-Polygone bildet das exakt ab (gefüllt = ungerade
    Überdeckung), statt Löcher fälschlich zu füllen.
    """
    ring_polys = []
    for ring in rings:
        pix = [(x * scale - px_left, y * scale - px_top) for x, y in ring]
        p = Polygon(pix)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty and p.area > 0:
            ring_polys.append(p)
    if not ring_polys:
        return None
    geom = ring_polys[0]
    for p in ring_polys[1:]:
        try:
            geom = geom.symmetric_difference(p)
        except shapely.errors.GEOSException:
            geom = shapely.union_all([geom, p], grid_size=0.01)
    return geom


def extract_polys_by_color(page, page_h, scale, px_left, px_top, target_color, geo_params):
    """Alle Pfade der Zielfarbe -> Liste georeferenzierter shapely-Polygone (even-odd)."""
    polys = []
    for d in page.get_drawings():
        if not color_matches(d.get("fill"), target_color):
            continue
        geom = rings_to_evenodd(path_to_rings(d["items"]), scale, px_left, px_top)
        if geom is None or geom.is_empty:
            continue
        polys.append(affine_transform(geom, geo_params))
    return polys


def _polygonal(geom):
    """Nur die polygonalen Teile einer (ggf. gemischten) Geometrie."""
    if geom is None or geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [geom]
    if gt == "MultiPolygon":
        return list(geom.geoms)
    if gt == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_polygonal(g))
        return out
    return []


def robust_union(polys, grid=0.05):
    """Topologie-robuste Vereinigung: erst make_valid, dann batchweise union_all."""
    clean = []
    for g in polys:
        gv = shapely.make_valid(g) if not g.is_valid else g
        clean.extend(_polygonal(gv))
    if not clean:
        return None
    try:
        return shapely.union_all(clean, grid_size=grid)
    except shapely.errors.GEOSException:
        acc, batch = None, 2000
        for i in range(0, len(clean), batch):
            part = shapely.union_all(clean[i:i + batch], grid_size=grid)
            acc = part if acc is None else shapely.union_all([acc, part], grid_size=grid)
        return acc


def export_layer(key, polys, dissolve, crs, noe_geom):
    """Validiert, clippt auf NÖ, vereinfacht und schreibt GeoJSON (31287 + WGS84)."""
    if not polys:
        print(f"  [{key}] keine Pfade gefunden!")
        return
    if dissolve:
        merged = robust_union(polys)
        geoms = _polygonal(merged)
    else:
        geoms = polys
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)
    gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]

    gdf = gdf[gdf.intersects(noe_geom)].copy()
    gdf["geometry"] = gdf.geometry.intersection(noe_geom)
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOL_M, preserve_topology=True)
    gdf = gdf[gdf.geometry.area > 0].reset_index(drop=True)
    gdf["area_ha"] = (gdf.geometry.area / 1e4).round(2)

    base = LAYERS[key][1]
    gdf.to_file(OUT_DIR / f"{base}.geojson", driver="GeoJSON")
    gdf.to_crs("EPSG:4326").to_file(OUT_DIR / f"{base}_wgs84.geojson", driver="GeoJSON")
    print(f"  [{key}] {len(gdf)} Flächen, {gdf.geometry.area.sum()/1e6:.1f} km² "
          f"-> {base}.geojson (+_wgs84)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    align = json.loads(ALIGN_PATH.read_text())
    crs = align["crs"]
    scale, px_left, vp = load_pixel_transform(align)

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    page_h = page.rect.height
    px_top = int((page_h - max(vp[1], vp[3])) * scale)
    print(f"PDF: {len(page.get_drawings())} Vektorpfade, page {page.rect.width:.0f}x{page_h:.0f} pt, "
          f"Crop-Offset px=({px_left},{px_top})")

    geo_params = pixel_to_geo_params(align)

    print("Lade NÖ-Grenze ...")
    vgd = gpd.read_file(VGD_PATH).to_crs(crs)
    noe_geom = vgd[vgd["BL_KZ"] == NOE_BL_KZ].dissolve().geometry.iloc[0]

    for key, (color, _base, dissolve) in LAYERS.items():
        print(f"Extrahiere '{key}' (Füllfarbe {tuple(round(c*255) for c in color)}) ...")
        polys = extract_polys_by_color(page, page_h, scale, px_left, px_top, color, geo_params)
        raw_km2 = sum(p.area for p in polys) / 1e6
        print(f"  {len(polys)} Pfad-Geometrien, Roh-Summe {raw_km2:.1f} km² (vor Auflösung/Clip)")
        export_layer(key, polys, dissolve, crs, noe_geom)
    doc.close()
    # Die Quellobjekte hinter den 750-m-Zonen gleich mitrekonstruieren, damit
    # Zonen und Quellen nie aus verschiedenen Extraktionsläufen stammen.
    print("Rekonstruiere HiG-Quellobjekte aus den 750-m-Zonen ...")
    derive_layer_files(OUT_DIR)
    print("Fertig.")


if __name__ == "__main__":
    main()
