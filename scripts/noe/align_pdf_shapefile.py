"""
Alignment-Check: PDF-Karte (Mindestabstandszonen NÖ) georeferenziert
mit Shapefile-Grenzen (Gemeinden, Bezirke, Landesgrenze) darüber.

- PDF GPTS sind im MGI-Datum (EPSG:4312), nicht WGS84
- Affine Warp des PDF-Bildes nach EPSG:31287 (native CRS des Shapefiles)
"""

import argparse
import json
import sys

import fitz
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pyproj import Transformer
from scipy.ndimage import map_coordinates
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.noe.pdf_align import GPTS_LATLON_MINDESTABSTAND  # noqa: E402

DATA = Path("data")
VGD = DATA / "admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp"
PDF_PATH = DATA / "noe_sekrop" / "TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf"
OUT = Path("output/noe")
OUT.mkdir(exist_ok=True)

DEFAULT_OUT_JSON = OUT / "alignment_mindestabstand.json"

CRS = "EPSG:31287"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT_JSON,
        help=f"Zielpfad für alignment_mindestabstand.json (Default: {DEFAULT_OUT_JSON})",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Vorhandene Zieldatei überschreiben. Ohne dieses Flag bricht das "
             "Skript ab, wenn die Zieldatei bereits existiert.",
    )
    return parser.parse_args()


args = parse_args()
if args.out.exists() and not args.overwrite:
    raise SystemExit(
        f"Zieldatei {args.out} existiert bereits — Abbruch (Schutz gegen "
        "versehentliches Überschreiben der derzeit einzigen Kopie). "
        "Mit --overwrite erzwingen."
    )

# --- 1. PDF Georeferenzierung ---
print("Lese PDF Georeferenzierung...")
doc = fitz.open(PDF_PATH)
page = doc[0]

# Viewport BBox in PDF points: [left_x, top_y, right_x, bottom_y]
vp_bbox = [62.39916, 2355.6873, 2928.2005, 28.28232]
page_h = page.rect.height  # 2384.249

# GPTS (lat, lon) in MGI geographic datum (EPSG:4312)
# LPTS order: (0,1)=BL, (0,0)=TL, (1,0)=TR, (1,1)=BR
# LPTS: u=horizontal (0=left,1=right), v=vertical (0=top,1=bottom)
# Quelle: windkraft/noe/pdf_align.py (GPTS_LATLON_MINDESTABSTAND, aus dem
# /GPTS-Eintrag im /Measure-Dictionary des GeoPDFs).
gpts_latlon = GPTS_LATLON_MINDESTABSTAND
lpts = [(0, 1), (0, 0), (1, 0), (1, 1)]

# Transform GPTS: MGI geographic -> EPSG:31287 (both MGI-based, no datum shift)
t = Transformer.from_crs("EPSG:4312", CRS, always_xy=True)
gpts_proj = []
for lat, lon in gpts_latlon:
    e, n = t.transform(lon, lat)
    gpts_proj.append((e, n))

for label, (e, n) in zip(["BL", "TL", "TR", "BR"], gpts_proj):
    print(f"  {label}: easting={e:.0f}, northing={n:.0f}")

# --- 2. PDF rendern, Viewport ausschneiden ---
print("Rendere PDF...")
render_dpi = 200
scale = render_dpi / 72
mat = fitz.Matrix(scale, scale)
pix = page.get_pixmap(matrix=mat)
full_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

# Viewport in image pixel coords (image origin = top-left)
# PDF y goes up from bottom; image y goes down from top
vp_x_min = vp_bbox[0]
vp_x_max = vp_bbox[2]
vp_y_min = min(vp_bbox[1], vp_bbox[3])  # 28.3 (bottom of page in PDF)
vp_y_max = max(vp_bbox[1], vp_bbox[3])  # 2355.7 (top of page in PDF)

px_left = int(vp_x_min * scale)
px_right = int(vp_x_max * scale)
px_top = int((page_h - vp_y_max) * scale)    # PDF top -> image top
px_bottom = int((page_h - vp_y_min) * scale)  # PDF bottom -> image bottom

map_img = full_img[px_top:px_bottom, px_left:px_right]
img_h, img_w = map_img.shape[:2]
print(f"  Kartenausschnitt: {img_w} x {img_h} px")

# --- 3. Affine Transformation: Pixel <-> Projected ---
# LPTS -> pixel: u=horizontal, v=vertical (0=top for v)
pixel_corners = []
for u, v in lpts:
    px = u * img_w
    py = v * img_h
    pixel_corners.append((px, py))

print("  Corner mapping:")
for label, (px, py), (e, n) in zip(["BL","TL","TR","BR"], pixel_corners, gpts_proj):
    print(f"    {label}: pixel({px:.0f},{py:.0f}) -> geo({e:.0f},{n:.0f})")

# Affine fit: [easting, northing] = A @ [px, py, 1]
src = np.array(pixel_corners)
dst = np.array(gpts_proj)
ones = np.ones((4, 1))
src_aug = np.hstack([src, ones])

A_east, _, _, _ = np.linalg.lstsq(src_aug, dst[:, 0], rcond=None)
A_north, _, _, _ = np.linalg.lstsq(src_aug, dst[:, 1], rcond=None)

print("  Affine residuals:")
for i, label in enumerate(["BL", "TL", "TR", "BR"]):
    px, py = pixel_corners[i]
    e_calc = A_east[0] * px + A_east[1] * py + A_east[2]
    n_calc = A_north[0] * px + A_north[1] * py + A_north[2]
    e_true, n_true = gpts_proj[i]
    print(f"    {label}: dE={e_calc - e_true:.1f}m, dN={n_calc - n_true:.1f}m")

# Forward affine matrix (pixel -> geo)
A_fwd = np.array([
    [A_east[0], A_east[1], A_east[2]],
    [A_north[0], A_north[1], A_north[2]],
    [0, 0, 1]
])
A_inv = np.linalg.inv(A_fwd)

# --- 3b. Alignment-JSON exportieren ---
# Schema identisch zu den anderen alignment_<name>.json (siehe
# align_regional_karten.py, dort der Referenz-Writer für dieses Format).
alignment_data = {
    "name": "mindestabstand",
    "title": "Mindestabstandszonen (TeilC 3.2)",
    "pdf_path": str(PDF_PATH),
    "crs": CRS,
    "render_dpi": render_dpi,
    "vp_bbox": vp_bbox,
    "gpts_latlon": [list(p) for p in gpts_latlon],
    "lpts": [list(p) for p in lpts],
    "gpts_proj": [list(g) for g in gpts_proj],
    "img_size": [img_w, img_h],
    "extent": {
        "e_min": min(g[0] for g in gpts_proj),
        "e_max": max(g[0] for g in gpts_proj),
        "n_min": min(g[1] for g in gpts_proj),
        "n_max": max(g[1] for g in gpts_proj),
    },
    "A_fwd": A_fwd.tolist(),
    "A_inv": A_inv.tolist(),
    "pixel_corners": [list(p) for p in pixel_corners],
}
args.out.parent.mkdir(parents=True, exist_ok=True)
with open(args.out, "w", encoding="utf-8") as f:
    json.dump(alignment_data, f, indent=2, ensure_ascii=False)
print(f"Alignment-JSON gespeichert: {args.out}")

# --- 4. Warp image to projected grid ---
print("Warpe Bild in projiziertes CRS...")

e_min = min(g[0] for g in gpts_proj)
e_max = max(g[0] for g in gpts_proj)
n_min = min(g[1] for g in gpts_proj)
n_max = max(g[1] for g in gpts_proj)

target_w = img_w
target_h = img_h

east_grid = np.linspace(e_min, e_max, target_w)
north_grid = np.linspace(n_max, n_min, target_h)  # top (north) to bottom (south)
E, N = np.meshgrid(east_grid, north_grid)

# Inverse: geo -> pixel
px_x = A_inv[0, 0] * E + A_inv[0, 1] * N + A_inv[0, 2]
px_y = A_inv[1, 0] * E + A_inv[1, 1] * N + A_inv[1, 2]

warped = np.zeros((target_h, target_w, 3), dtype=np.uint8)
for c in range(3):
    warped[:, :, c] = map_coordinates(
        map_img[:, :, c].astype(float),
        [px_y.ravel(), px_x.ravel()],
        order=1, mode='constant', cval=255
    ).reshape(target_h, target_w).clip(0, 255).astype(np.uint8)

# --- 5. Shapefile-Grenzen ---
print("Lade Verwaltungsgrenzen...")
vgd = gpd.read_file(VGD)  # EPSG:31287
vgd_noe = vgd[vgd["BL"] == "Niederösterreich"]

gemeinden_noe = vgd_noe.dissolve(by="PG").reset_index()
bezirke_noe = vgd_noe.dissolve(by="PB").reset_index()
land_noe = vgd_noe.dissolve().reset_index()

# --- 6. Karte zeichnen ---
print("Zeichne Alignment-Karte...")
fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)

img_extent = [e_min, e_max, n_min, n_max]
ax.imshow(warped, extent=img_extent, aspect="equal", origin="upper", zorder=0)

gemeinden_noe.boundary.plot(ax=ax, color="cyan", linewidth=0.3, linestyle=":", zorder=1)
bezirke_noe.boundary.plot(ax=ax, color="blue", linewidth=0.8, linestyle="--", zorder=2)
land_noe.boundary.plot(ax=ax, color="magenta", linewidth=2.0, linestyle="-", zorder=3)

noe_bounds = land_noe.total_bounds
pad = 10000
ax.set_xlim(noe_bounds[0] - pad, noe_bounds[2] + pad)
ax.set_ylim(noe_bounds[1] - pad, noe_bounds[3] + pad)

legend_items = [
    mpatches.Patch(facecolor="lightyellow", edgecolor="gray",
                   label="PDF Hintergrund (Mindestabstandszonen)"),
    plt.Line2D([0], [0], color="cyan", linewidth=0.5, linestyle=":",
               label="Gemeindegrenzen (Shapefile)"),
    plt.Line2D([0], [0], color="blue", linewidth=1.0, linestyle="--",
               label="Bezirksgrenzen (Shapefile)"),
    plt.Line2D([0], [0], color="magenta", linewidth=2.5,
               label="Landesgrenze NÖ (Shapefile)"),
]
ax.legend(handles=legend_items, loc="lower left", fontsize=10, framealpha=0.9)

ax.set_title(
    "Alignment-Check: PDF Mindestabstandszonen vs. Shapefile-Grenzen (EPSG:31287)",
    fontsize=14, fontweight="bold", pad=15
)
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")

plt.tight_layout()
# PNG neben die JSON legen (bei --out in ein anderes Verzeichnis landet auch
# der Check-Plot dort, nicht in output/noe/).
outpath = args.out.parent / "alignment_check_pdf_vs_shapefile.png"
fig.savefig(outpath, dpi=200, bbox_inches="tight")
print(f"Karte gespeichert: {outpath}")
plt.close()
