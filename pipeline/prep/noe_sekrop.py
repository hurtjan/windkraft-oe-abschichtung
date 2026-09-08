"""Prep: NÖ-SekROP-PDF, zwei Stufen (Paket W1.P9, docs/rewrite/PLAN.md §7, §4).

Ungewöhnlichster Rohpfad der Kette: die Rohquelle ist kein GIS-Datensatz,
sondern ein GeoPDF (``contract.RAW["noe_sekrop"]["pdf"]``, 16,6 MB, TeilC
3.2 "Mindestabstandszonen" des NÖ SekROP). Die Kartenobjekte stecken darin
als echte Vektor-Pfade (``page.get_drawings()``), nicht als Rasterbild -
Bilderkennung ist nicht nötig, nur Farbfilterung und Georeferenzierung.

Zwei Stufen, wie ``contract.PREP["noe_sekrop"]`` es vorgibt (Alignment vor
Vektorisierung, PLAN.md §4):

- ``run_align()`` -> ``contract.PREP["noe_sekrop"]["a_align"]``: liest nur
  die vier georeferenzierten Eckpunkte (``/GPTS`` des GeoPDFs, hier als
  Konstante übernommen - siehe ``calc/noe/pdf_align.py``) und die
  Seitenhöhe, transformiert MGI (EPSG:4312) nach EPSG:31287 und passt eine
  affine Pixel<->Geo-Transformation. Schreibt ``alignment_mindestabstand.json``.
- ``run_vectorize()`` -> ``contract.PREP["noe_sekrop"]["b_vectorize"]``:
  liest die Alignment-Datei von Stufe a (harte Vorbedingung), filtert die
  PDF-Vektorpfade nach den sechs amtlichen Füllfarben, rekonstruiert
  geschlossene Ringe (inkl. Bézier-Sampling), löst sie even-odd auf,
  vereinigt gleichfarbige Pfade, clippt auf NÖ und vereinfacht leicht.
  Schreibt sechs GeoJSON-Layer (+ WGS84-Variante je Layer).

Verschoben, unverändert in der Verarbeitungslogik (Regel 4 - Farbschwellen,
Toleranzen, Bézier-Sampling, Vereinfachungstoleranz sind willkürlich, aber
sie sind die Grundlage des bestehenden Ergebnisses, deshalb angeschrieben,
nicht angefasst), aus ``scripts/noe/align_pdf_shapefile.py`` und
``scripts/noe/extract_noe_vector_layers.py``. Zwei bewusste Abweichungen,
keine der beiden ändert eine Ausgabedatei:

1. Stufe a rendert das PDF nicht mehr als Bild und zeichnet keinen
   Diagnose-Plot (``alignment_check_pdf_vs_shapefile.png``) mehr. Die Karte
   diente nur der visuellen Kontrolle durch eine Person, kein Codepfad las
   sie (repoweite Suche, siehe Bericht zu W1.P9) - und die eigentliche
   Alignment-JSON (``pixel_corners``/``A_fwd``/``A_inv``) hängt ohnehin nur
   an ``page.rect.height`` und der festen Viewport-BBox, nicht am
   gerenderten Pixelinhalt. Das Rendern bei 200 DPI war der teuerste Teil
   des alten Alignment-Skripts (~19 s von ~19 s Gesamtlaufzeit) und ist
   jetzt weg.
2. Stufe b ruft ``page.get_drawings()`` einmal statt sechsmal auf (einmal
   je Farbschicht im alten Skript) - dieselbe Pfadliste wird nur einmal
   geparst und für alle sechs Farben wiederverwendet. Deterministische
   Cache-Optimierung, keine Änderung an Ergebnis, Schwelle oder Toleranz.

Was diese Stufe bewusst NICHT mehr erzeugt: die drei
``pdf_hig_source_*.geojson``-Dateien (rekonstruierte SekROP-Quellobjekte
über ``calc/noe/pdf_hig_sources.py:derive_layer_files()``, Erosion um
750-50 m). Repoweite Vorwärts-/Rückwärtssuche (siehe Bericht zu W1.P9)
bestätigt: seit Paket W1.6 (``calc/hig_source_masks.py``,
Funktion ``noe_pdf_source_mask()`` entfernt) liest diese Dateien niemand
mehr - weder ein Band im 38-Band-Schema noch ``pipeline/contract.py:
LAYER_NAMES`` noch irgendein anderes Skript. ``calc/noe/
pdf_hig_sources.py`` wurde deshalb mit diesem Paket gelöscht, nicht
mitverschoben - eine Sackgasse eine Ebene über der, die W1.6 beseitigt
hat. Der einzige echte Abnehmer dieser Domäne ist ``noe_pdf_750m_zones``
(über ``calc/hig_source_masks.py:noe_pdf_mask()``, liest exakt
die drei ``pdf_750m_*.geojson`` unten) - dieser Pfad bleibt unverändert
erhalten und wird von diesem Paket nicht angefasst (Abgrenzung laut
Auftrag: Konsumenten von ``noe_pdf_750m_zones`` ändert diese Welle nicht).

Die drei übrigen Layer (``wohnbauland``, ``siedlungsabstand_1200m``,
``abstand_sondergebiet_1200m``) haben im heutigen Code ebenfalls keinen
Codeleser (``docs/dataflow/nodes.tsv`` markiert sie separat, unabhängig
von W1.6, als ``dead_end,unused``) - das ist aber ein eigener, hier nicht
beauftragter Befund (siehe Bericht zu W1.P9) und wird deshalb weiter
unverändert miterzeugt, wie die Abnahme in PLAN.md §7 es verlangt
("erzeugte GeoJSON deckungsgleich mit den bestehenden").
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF
import geopandas as gpd
import numpy as np
import shapely
from pyproj import Transformer
from shapely.affinity import affine_transform
from shapely.geometry import Polygon

from pipeline import contract, fingerprint, runtime
from calc.noe.pdf_align import GPTS_LATLON_MINDESTABSTAND

PDF_PATH = contract.RAW["noe_sekrop"]["pdf"]
VGD_PATH = contract.RAW["admin"]["vgd"]

ALIGN_DIR = contract.PREP["noe_sekrop"]["a_align"]
VECTORIZE_DIR = contract.PREP["noe_sekrop"]["b_vectorize"]

ALIGNMENT_FILENAME = "alignment_mindestabstand.json"

# Zaehlt zum Fingerabdruck beider Stufen mit (W6.4, Punkt 45): eine
# Aenderung an dieser Datei soll den jeweiligen Selbst-Ueberspringer
# aufheben, nicht nur eine Aenderung an data/. Konservativ - nur die eigene
# Quelldatei, nicht die Importe (siehe pipeline/fingerprint.py).
MODULE_PATH = Path(__file__)

# --- Stufe a: Alignment-Konstanten -----------------------------------------
# Unverändert aus scripts/noe/align_pdf_shapefile.py. VP_BBOX ist die feste
# Viewport-BBox der Kartenseite in PDF-Punkten, LPTS die Eckpunkt-Reihenfolge
# (u=horizontal 0=links/1=rechts, v=vertikal 0=oben/1=unten), beide passend
# zu GPTS_LATLON_MINDESTABSTAND (calc/noe/pdf_align.py, aus dem
# /GPTS-Eintrag des GeoPDFs).
VP_BBOX = [62.39916, 2355.6873, 2928.2005, 28.28232]
LPTS = [(0, 1), (0, 0), (1, 0), (1, 1)]
CRS = "EPSG:31287"
RENDER_DPI = 200

# --- Stufe b: Vektorisierungs-Konstanten ------------------------------------
# Unverändert aus scripts/noe/extract_noe_vector_layers.py (Regel 4 - siehe
# Moduldokstring).
NOE_BL_KZ = "3"
COLOR_TOL = 0.02              # Toleranz für Farb-Match (Vektorfarben sind exakt)
BEZIER_STEPS = 8              # Sampling-Schritte je Bézier-Kurve
SIMPLIFY_TOL_M = 8.0          # leichte Vereinfachung in Metern (EPSG:31287)

# Layer-Definition: key -> (Füllfarbe RGB 0-1, Dateibasis, ob auflösen/zusammenfassen).
# Die Farbwerte sind die EXAKTEN Vektorfüllfarben aus page.get_drawings(),
# nicht rastergesampelte Näherungen (COLOR_TOL deckt Rundung ab).
LAYERS = {
    "wohnbauland":                 ((0.612, 0.612, 0.612), "wohnbauland",               True),
    "siedlungsabstand_1200m":      ((1.000, 0.827, 0.498), "siedlungsabstand_1200m",    True),
    "abstand_sondergebiet_1200m":  ((0.804, 0.667, 0.400), "abstand_sondergebiet_1200m", True),
    # 750-m-Klassen (Objekt + Puffer bereits enthalten) - die einzigen drei
    # mit echtem Abnehmer, siehe Moduldokstring.
    "pdf_750m_geb":                ((0.90196, 0.90196, 0.00000), "pdf_750m_geb",               True),
    "pdf_750m_gwr":                ((0.84314, 0.61961, 0.61961), "pdf_750m_gwr",               True),
    "pdf_750m_gruenland_widmung":  ((0.53726, 0.80392, 0.40000), "pdf_750m_gruenland_widmung", True),
}


def _shapefile_sidecars(shp_path: Path) -> list[Path]:
    """Alle Begleitdateien eines Shapefiles (.shp/.shx/.dbf/.prj/.cpg/...).

    Wie ``pipeline/prep/admin.py:_shapefile_sidecars`` - eigene Kopie, weil
    kein Prep-Paket sich eine Datei mit einem anderen teilt (PLAN.md §7).
    """
    return sorted(p for p in shp_path.parent.glob(shp_path.stem + ".*") if p.is_file())


# ---------------------------------------------------------------------------
# Stufe a: Alignment
# ---------------------------------------------------------------------------


def run_align(force: bool = False) -> Path:
    """Georeferenziert die Kartenseite: vier GPTS-Eckpunkte (MGI) ->
    EPSG:31287, affine Pixel<->Geo-Transformation. Schreibt
    ``alignment_mindestabstand.json`` nach ``contract.PREP["noe_sekrop"]
    ["a_align"]``.

    Rendert das PDF absichtlich NICHT als Bild (siehe Moduldokstring,
    Abweichung 1) - die Zahlen unten hängen nur an ``page.rect.height``
    und der festen Viewport-BBox.

    Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    (run_extract/run_layers): ein wiederholter `make all` ohne
    Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf.
    """
    runtime.ensure_dir(ALIGN_DIR)

    out_path = ALIGN_DIR / ALIGNMENT_FILENAME
    if not force and out_path.exists() and fingerprint.matches(ALIGN_DIR, [PDF_PATH, MODULE_PATH]):
        print(
            f"[skip]  prep-noe-sekrop a_align: Fingerabdruck unveraendert -> {out_path}",
            flush=True,
        )
        return out_path

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    page_h = page.rect.height
    doc.close()

    # MGI geographisch (EPSG:4312) -> EPSG:31287, beide MGI-basiert, kein Datum-Shift.
    transformer = Transformer.from_crs("EPSG:4312", CRS, always_xy=True)
    gpts_proj = [transformer.transform(lon, lat) for lat, lon in GPTS_LATLON_MINDESTABSTAND]

    scale = RENDER_DPI / 72.0
    vp_x_min, vp_x_max = VP_BBOX[0], VP_BBOX[2]
    vp_y_min = min(VP_BBOX[1], VP_BBOX[3])
    vp_y_max = max(VP_BBOX[1], VP_BBOX[3])
    px_left = int(vp_x_min * scale)
    px_right = int(vp_x_max * scale)
    px_top = int((page_h - vp_y_max) * scale)
    px_bottom = int((page_h - vp_y_min) * scale)
    img_w = px_right - px_left
    img_h = px_bottom - px_top

    # LPTS -> Pixel: u=horizontal, v=vertikal (0=oben).
    pixel_corners = [(u * img_w, v * img_h) for u, v in LPTS]

    src = np.array(pixel_corners, dtype=float)
    dst = np.array(gpts_proj, dtype=float)
    src_aug = np.hstack([src, np.ones((len(src), 1))])
    a_east, *_ = np.linalg.lstsq(src_aug, dst[:, 0], rcond=None)
    a_north, *_ = np.linalg.lstsq(src_aug, dst[:, 1], rcond=None)

    a_fwd = np.array([
        [a_east[0], a_east[1], a_east[2]],
        [a_north[0], a_north[1], a_north[2]],
        [0.0, 0.0, 1.0],
    ])
    a_inv = np.linalg.inv(a_fwd)

    alignment_data = {
        "name": "mindestabstand",
        "title": "Mindestabstandszonen (TeilC 3.2)",
        "pdf_path": str(PDF_PATH),
        "crs": CRS,
        "render_dpi": RENDER_DPI,
        "vp_bbox": VP_BBOX,
        "gpts_latlon": [list(p) for p in GPTS_LATLON_MINDESTABSTAND],
        "lpts": [list(p) for p in LPTS],
        "gpts_proj": [list(g) for g in gpts_proj],
        "img_size": [img_w, img_h],
        "extent": {
            "e_min": min(g[0] for g in gpts_proj),
            "e_max": max(g[0] for g in gpts_proj),
            "n_min": min(g[1] for g in gpts_proj),
            "n_max": max(g[1] for g in gpts_proj),
        },
        "A_fwd": a_fwd.tolist(),
        "A_inv": a_inv.tolist(),
        "pixel_corners": [list(p) for p in pixel_corners],
    }

    out_path.write_text(
        json.dumps(alignment_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fingerprint.write(ALIGN_DIR, [PDF_PATH, MODULE_PATH])
    print(
        f"[done]  prep-noe-sekrop a_align: Kartenausschnitt {img_w}x{img_h} px -> {out_path}",
        flush=True,
    )
    return out_path


# ---------------------------------------------------------------------------
# Stufe b: Vektorisierung
# ---------------------------------------------------------------------------


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


def pixel_to_geo_params(align: dict) -> list:
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


def extract_polys_by_color(drawings, scale, px_left, px_top, target_color, geo_params):
    """Alle Pfade der Zielfarbe -> Liste georeferenzierter shapely-Polygone (even-odd).

    ``drawings`` ist die (einmal geparste, siehe run_vectorize) Liste aus
    ``page.get_drawings()`` - im alten Skript wurde sie je Farbe neu
    geparst (Abweichung 2, siehe Moduldokstring).
    """
    polys = []
    for d in drawings:
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


def export_layer(out_dir, key, polys, dissolve, crs, noe_geom):
    """Validiert, clippt auf NÖ, vereinfacht und schreibt GeoJSON (31287 + WGS84)."""
    if not polys:
        print(f"  [{key}] keine Pfade gefunden!")
        return None
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
    out_path = out_dir / f"{base}.geojson"
    gdf.to_file(out_path, driver="GeoJSON")
    gdf.to_crs("EPSG:4326").to_file(out_dir / f"{base}_wgs84.geojson", driver="GeoJSON")
    print(
        f"  [{key}] {len(gdf)} Flächen, {gdf.geometry.area.sum()/1e6:.1f} km² "
        f"-> {base}.geojson (+_wgs84)"
    )
    return out_path


def _load_align(align: dict | None) -> dict:
    if align is not None:
        return align
    path = ALIGN_DIR / ALIGNMENT_FILENAME
    if not path.exists():
        raise SystemExit(
            f"Stufe a (a_align) ist noch nicht gelaufen - {path} fehlt. Harte "
            "Vorbedingung (docs/rewrite/PLAN.md §4): erst `make prep-noe-sekrop-a`, "
            "dann diese Stufe."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def run_vectorize(align: dict | None = None, force: bool = False) -> Path:
    """Filtert die PDF-Vektorpfade nach Farbe, rekonstruiert Geometrie,
    clippt auf NÖ und schreibt sechs GeoJSON-Layer nach
    ``contract.PREP["noe_sekrop"]["b_vectorize"]``.

    ``align`` optional vorgegeben (z. B. von ``run()`` direkt aus Stufe a
    durchgereicht) - ohne Vorgabe wird das Ergebnis von Stufe a von der
    Platte gelesen (harte Vorbedingung, siehe ``_load_align``), damit die
    Stufe auch unabhängig aufrufbar bleibt.

    Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    (run_extract/run_layers): ein wiederholter `make all` ohne
    Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf. Der
    Fingerabdruck deckt neben PDF und NÖ-Grenze auch das Alignment-Ergebnis
    von Stufe a ab (``ALIGN_DIR / ALIGNMENT_FILENAME``) - eine geaenderte
    Stufe-a-Ausgabe hebt den Ueberspringer hier also mit auf, obwohl sie
    nicht unter ``data/`` liegt.
    """
    runtime.ensure_dir(VECTORIZE_DIR)

    vectorize_inputs = [
        PDF_PATH, VGD_PATH, *_shapefile_sidecars(VGD_PATH), ALIGN_DIR / ALIGNMENT_FILENAME,
        MODULE_PATH,
    ]
    output_paths = []
    for _key, (_color, base, _dissolve) in LAYERS.items():
        output_paths.append(VECTORIZE_DIR / f"{base}.geojson")
        output_paths.append(VECTORIZE_DIR / f"{base}_wgs84.geojson")

    if (
        not force
        and all(p.exists() for p in output_paths)
        and fingerprint.matches(VECTORIZE_DIR, vectorize_inputs)
    ):
        print(
            f"[skip]  prep-noe-sekrop b_vectorize: Fingerabdruck unveraendert -> {VECTORIZE_DIR}",
            flush=True,
        )
        return VECTORIZE_DIR

    align = _load_align(align)
    crs = align["crs"]
    scale = align["render_dpi"] / 72.0
    vp = align["vp_bbox"]
    px_left = int(vp[0] * scale)

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    page_h = page.rect.height
    px_top = int((page_h - max(vp[1], vp[3])) * scale)
    drawings = page.get_drawings()
    print(
        f"PDF: {len(drawings)} Vektorpfade, page {page.rect.width:.0f}x{page_h:.0f} pt, "
        f"Crop-Offset px=({px_left},{px_top})",
        flush=True,
    )

    geo_params = pixel_to_geo_params(align)

    print("Lade NÖ-Grenze ...", flush=True)
    vgd = gpd.read_file(VGD_PATH).to_crs(crs)
    noe_geom = vgd[vgd["BL_KZ"] == NOE_BL_KZ].dissolve().geometry.iloc[0]

    written = []
    for key, (color, _base, dissolve) in LAYERS.items():
        print(f"Extrahiere '{key}' (Füllfarbe {tuple(round(c*255) for c in color)}) ...", flush=True)
        polys = extract_polys_by_color(drawings, scale, px_left, px_top, color, geo_params)
        raw_km2 = sum(p.area for p in polys) / 1e6
        print(f"  {len(polys)} Pfad-Geometrien, Roh-Summe {raw_km2:.1f} km² (vor Auflösung/Clip)")
        out_path = export_layer(VECTORIZE_DIR, key, polys, dissolve, crs, noe_geom)
        if out_path is not None:
            written.append(out_path)
    doc.close()

    fingerprint.write(VECTORIZE_DIR, vectorize_inputs)
    print(
        f"[done]  prep-noe-sekrop b_vectorize: {len(written)} Layer -> {VECTORIZE_DIR}",
        flush=True,
    )
    return VECTORIZE_DIR


def run(force: bool = False) -> tuple[Path, Path]:
    """Beide Stufen nacheinander (Stufe b liest das Alignment direkt aus dem
    Rückgabewert von Stufe a, nicht erneut von der Platte - beide laufen
    hier im selben Prozess)."""
    run_align(force=force)
    align = json.loads((ALIGN_DIR / ALIGNMENT_FILENAME).read_text(encoding="utf-8"))
    run_vectorize(align, force=force)
    return ALIGN_DIR, VECTORIZE_DIR


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
