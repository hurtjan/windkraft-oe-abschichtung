"""Beispielkarten fuer das White Paper: Abb. 3 (Streusiedlung Haselbach bei Weiz).

Illustrationsabbildung; nutzt neben dem TIF Kataster, Adressregister und
OSM-Kacheln (Ausnahme von der TIF-Regel, Entscheidung Jan offen).

Ausgabe:
- ``<out_root>/abb/abb3_streusiedlung_haselbach.png``
- ``<out_root>/tabellen/beispiel_haselbach.json`` (alle Zahlen der Abbildung)

Die Streusiedlungs-Huelle wird nicht ueber eine Label-ID gewaehlt (Labels
aendern sich zwischen Laeufen), sondern ueber einen festen Punkt (EPSG:31287)
in Gemeinde GKZ 61730 (``select_hull``). OSM-Kacheln liegen in
``derived/work/whitepaper/osm_tiles/`` (gitignored), damit der Build offline laeuft.
Kataster-/Adress-Ausschnitte werden in ``derived/work/whitepaper/beispiel_haselbach/``
zwischengespeichert.

Importe aus ``calc.*`` erfolgen bewusst lazy (nur diese Abbildung braucht sie).
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import contract
from pipeline.runtime import read_vector

from . import wp_common as wc

REPO = Path(__file__).resolve().parents[3]
FIG_NAME = "abb3_streusiedlung_haselbach.png"
JSON_NAME = "beispiel_haselbach.json"
KEY_PREFIX = "beispiel_haselbach."

# Fester Punkt (EPSG:31287) innerhalb der Haselbach-Huelle, Gemeinde Mortantsch.
HULL_POINT = (569120.3, 371927.7)
HULL_GKZ = "61730"
UA = "abschichtung-methoden-figure/1.0 (research, low volume; Abschichtung white paper)"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_CREDIT = "© OpenStreetMap-Mitwirkende (ODbL)"



class HullSelectionError(RuntimeError):
    pass


def select_hull(gdf, point_xy: tuple[float, float]):
    """Waehlt die Streusiedlungs-Huelle (``ist_streusiedlung`` == 1), die
    ``point_xy`` enthaelt. Genau ein Treffer, sonst ``HullSelectionError``."""
    from shapely.geometry import Point

    pt = Point(*point_xy)
    cand = gdf[gdf["ist_streusiedlung"].astype(int) == 1]
    hit = cand[cand.geometry.contains(pt)]
    if len(hit) == 0:
        raise HullSelectionError(f"keine Streusiedlungs-Huelle enthaelt den Punkt {point_xy}")
    if len(hit) > 1:
        raise HullSelectionError(
            f"{len(hit)} Streusiedlungs-Huellen enthalten den Punkt {point_xy} (Labels {list(hit.get('label', hit.index))})")
    return hit.iloc[0]


# --------------------------------------------------------------------------
# Tiles
# --------------------------------------------------------------------------

def _tile_xy(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def _tile_bounds3857(x, y, z):
    s = 40075016.6856 / 2 ** z
    x0 = -20037508.3428 + x * s
    y1 = 20037508.3428 - y * s
    return x0, y1 - s, x0 + s, y1


def _fetch_tile(tiles_dir: Path, z, x, y):
    from PIL import Image

    p = tiles_dir / f"{z}_{x}_{y}.png"
    if not p.exists():
        req = urllib.request.Request(TILE_URL.format(z=z, x=x, y=y), headers={"User-Agent": UA})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(0.2)  # hoeflich zum Tile-Server
    return Image.open(p).convert("RGB")


# --------------------------------------------------------------------------
# Datenbeschaffung (mit Cache)
# --------------------------------------------------------------------------

def _load_dkm(repo: Path, cache: Path, hull_geom, bundesland: str):
    import geopandas as gpd
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    import shapely
    from shapely.geometry import box

    if cache.exists():
        return gpd.read_file(cache)
    bbox = box(*hull_geom.buffer(450).bounds)
    f = pq.ParquetFile(contract.PREP_FILES["kataster"]["at_dkm_gst_nfl"])
    names = f.schema_arrow.names
    bl_idx = names.index("bundesland")
    rows = []
    for i in range(f.metadata.num_row_groups):
        st = f.metadata.row_group(i).column(bl_idx).statistics
        if st is not None and st.has_min_max and st.min == st.max and st.min != bundesland:
            continue
        t = f.read_row_group(i, columns=["ns", "ns_category", "ns_label", "geometry"])
        m = pc.or_(pc.is_in(t["ns_category"], value_set=pa.array(["Baufläche", "Garten"])),
                   pc.is_in(t["ns"], value_set=pa.array(["41", "66", "83", "52", "71"])))
        t = t.filter(m)
        if not t.num_rows:
            continue
        geoms = shapely.from_wkb(t["geometry"].to_numpy(zero_copy_only=False))
        hit = shapely.intersects(geoms, bbox)
        if hit.any():
            d = t.drop(["geometry"]).to_pandas()[hit]
            d["geometry"] = geoms[hit]
            rows.append(d)
    dk = gpd.GeoDataFrame(pd.concat(rows), geometry="geometry", crs=31287)
    cache.parent.mkdir(parents=True, exist_ok=True)
    dk.to_file(cache, driver="GPKG")
    return dk


def _load_bev(repo: Path, cache_dir: Path, bb):
    ca, cg = cache_dir / "adressen_bbox.csv", cache_dir / "gebaeude_bbox.csv"
    if ca.exists() and cg.exists():
        return pd.read_csv(ca, dtype={"HNR_ADR_ZUSAMMEN": str}), pd.read_csv(cg, dtype={"EIGENSCHAFT": str})
    xmin, ymin, xmax, ymax = bb
    adr = read_vector(contract.PREP_FILES["adressen"]["adressen"])
    if "HNR_ADR_ZUSAMMEN" not in adr.columns:
        raise RuntimeError(
            "prep-Produkt adressen_31287.parquet hat keine Hausnummer (HNR_ADR_ZUSAMMEN); "
            "die Beispielkarte Haselbach braucht sie als Beschriftung - Spalte in prep ergaenzen.")
    adr = pd.DataFrame(adr.drop(columns="geometry"))
    geb = pd.DataFrame(read_vector(contract.PREP_FILES["adressen"]["gebaeude"]).drop(columns="geometry"))
    geb = geb.rename(columns={"eigenschaft": "EIGENSCHAFT"})

    def _in_box(d):
        return d[(d.x > xmin) & (d.x < xmax) & (d.y > ymin) & (d.y < ymax)]

    adr = _in_box(adr)[["HNR_ADR_ZUSAMMEN", "x", "y"]]
    geb = _in_box(geb)[["x", "y", "EIGENSCHAFT"]]
    cache_dir.mkdir(parents=True, exist_ok=True)
    adr.to_csv(ca, index=False)
    geb.to_csv(cg, index=False)
    return adr, geb


def _hnr_num(h: str) -> int:
    d = "".join(c for c in str(h) if c.isdigit())
    return int(d) if d else -1


# --------------------------------------------------------------------------
# Zahlen
# --------------------------------------------------------------------------

def compute_numbers(hull, bau, gar, adr, geb, settle_pts_tree, b2_poly, gemeinde: dict) -> dict:
    """Zaehlt Mitglieds-Baufl., Adressen, Gaerten, Wohnanteil und Abstaende."""
    from scipy.spatial import cKDTree
    from shapely.geometry import Point
    from shapely.ops import nearest_points

    from calc.bev_register import RESIDENTIAL_EIGENSCHAFTEN

    hg = hull.geometry
    cen = np.column_stack([bau["cx"], bau["cy"]])
    inside = np.array([hg.contains(Point(x, y)) for x, y in cen])
    mem = bau[inside].copy()
    mem["d_wid"] = settle_pts_tree.query(mem[["cx", "cy"]].to_numpy())[0]
    mem = mem[mem.d_wid > 500]
    c = mem[["cx", "cy"]].to_numpy()
    at = cKDTree(adr[["x", "y"]].to_numpy())
    d, ix = at.query(c, distance_upper_bound=100)
    has_a = ix < len(adr)
    pts = sorted(set(ix[has_a]))
    sel_adr = adr.iloc[pts]
    gt = cKDTree(gar[["cx", "cy"]].to_numpy())
    _, ig = gt.query(c, distance_upper_bound=150)
    gb = cKDTree(geb[["x", "y"]].to_numpy())
    _, ib = gb.query(c, distance_upper_bound=100)
    has_b = ib < len(geb)
    eig = geb.iloc[ib[has_b]].EIGENSCHAFT.tolist()
    hb = np.array(hg.exterior.coords) if hg.geom_type == "Polygon" else np.vstack(
        [np.array(p.exterior.coords) for p in hg.geoms])
    d_wohn = float(settle_pts_tree.query(hb)[0].min()) - 12.5
    pa, pb = nearest_points(hg, b2_poly)
    hn = sel_adr.HNR_ADR_ZUSAMMEN.astype(str).tolist()
    nums = [_hnr_num(h) for h in hn]
    split = mem.ns.astype(str).str.replace(r"\.0$", "", regex=True).value_counts().to_dict()
    return {
        "gemeinde": gemeinde.get("PG"), "gkz": gemeinde.get("GKZ"), "bundesland": gemeinde.get("BL"),
        "hull_label": int(hull["label"]),  # nur Information, nicht zur Auswahl benutzt
        "n_hausnummern": len(hn), "hausnummern": hn,
        "hausnummer_min": min(nums), "hausnummer_max": max(nums),
        "n_bauflaechen": int(len(mem)), "n_bauflaechen_ns41": int(split.get("41", 0)),
        "n_bauflaechen_ns83": int(split.get("83", 0)),
        "n_bauflaechen_mit_adresse_100m": int(has_a.sum()),
        "n_garten_150m": int((ig < len(gar)).sum()),
        "n_bev_gebaeude": int(has_b.sum()),
        "n_wohn": int(sum(e in RESIDENTIAL_EIGENSCHAFTEN for e in eig)),
        "abstand_wohnbauland_m": round(d_wohn, 0),
        "abstand_siedlungspuffer_m": round(float(pa.distance(pb)), 0),
        "flaeche_ha": round(float(hg.area) / 1e4, 2),
        "address_point_xy": sel_adr[["x", "y"]].round(1).values.tolist(),
    }


# --------------------------------------------------------------------------
# Abbildung + Lauf
# --------------------------------------------------------------------------

def run_haselbach(out_root: Path, tif: Path | None = None, manifest_path: Path | None = None,
        repo: Path | None = None) -> Path:
    t0 = time.time()
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    import shapely
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, PathPatch
    from matplotlib.path import Path as MPath
    from pyproj import Transformer
    from rasterio import features
    from rasterio.windows import from_bounds
    from scipy.spatial import cKDTree
    from shapely.geometry import Point, box, shape
    from shapely.ops import nearest_points, transform as sh_transform, unary_union

    from calc.distance_engine import fft_circle_dilation, ns_kind

    repo = Path(repo) if repo else REPO
    tif = Path(tif) if tif else repo / "out/abschichtung.tif"
    manifest_path = Path(manifest_path) if manifest_path else repo / "out/abschichtung.bands.json"
    out_root = Path(out_root)
    (out_root / "abb").mkdir(parents=True, exist_ok=True)
    (out_root / "tabellen").mkdir(parents=True, exist_ok=True)
    cache_dir = repo / "derived/work/whitepaper/beispiel_haselbach"
    tiles_dir = repo / "derived/work/whitepaper/osm_tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    t_to3857 = Transformer.from_crs(31287, 3857, always_xy=True).transform
    t_to4326 = Transformer.from_crs(31287, 4326, always_xy=True).transform

    # --- Huelle robust waehlen
    g = gpd.read_file(repo / "derived/layers/hig_huellen.gpkg", layer="hig_huellen")
    hull = select_hull(g, HULL_POINT)
    hg = hull.geometry
    cen = hg.centroid
    gem = read_vector(contract.PREP_FILES["admin"]["gemeinden"])
    gem = gem.to_crs(31287) if gem.crs else gem
    gj = gem[gem.contains(Point(*HULL_POINT))]
    if len(gj) != 1 or str(gj.iloc[0]["GKZ"]) != HULL_GKZ:
        raise HullSelectionError(f"Punkt liegt nicht in genau einer Gemeinde mit GKZ {HULL_GKZ}: "
                                 f"{gj['GKZ'].tolist() if len(gj) else 'keine'}")
    gemeinde = {c: str(gj.iloc[0][c]) for c in gj.columns if c != "geometry"}
    lon, lat = t_to4326(cen.x, cen.y)

    # --- Daten
    dk = _load_dkm(repo, cache_dir / "dkm_bbox.gpkg", hg, str(hull["bundesland"]))
    dk = dk.copy()
    dk["cx"] = dk.geometry.centroid.x
    dk["cy"] = dk.geometry.centroid.y
    dk["kind"] = [ns_kind(a, b) for a, b in zip(dk.ns, dk.ns_category)]
    bau = dk[dk.kind == "building"].copy()
    gar = dk[dk.kind == "garden"].copy()
    bb = hg.buffer(600).bounds
    adr, geb = _load_bev(repo, cache_dir, bb)

    # --- Raster
    mm = wc.load_manifest(manifest_path)
    i_wohn = wc.band_index(mm, "official_settlement_source")
    i_puffer = wc.band_index(mm, "settlement_buffer")
    i_hull = wc.band_index(mm, "haeuser_im_gruenen_streusiedlung")
    ds = rasterio.open(tif)
    R = 3600
    win = from_bounds(cen.x - R, cen.y - R, cen.x + R, cen.y + R, ds.transform).round_offsets().round_lengths()
    wt = ds.window_transform(win)

    def rd(i):
        return ds.read(i, window=win, boundless=True, fill_value=0).astype(bool)

    def vec(m):
        return unary_union([shape(s) for s, v in features.shapes(m.astype("uint8"), mask=m, transform=wt)])

    b1, b2, b5 = rd(i_wohn), rd(i_puffer), rd(i_hull)
    zS = fft_circle_dilation(b5, 750.0, 25.0, 2048, "zoneS_local").astype(bool)
    zoneS_poly, b1_poly, b2_poly = vec(zS), vec(b1), vec(b2)
    rr_, cc_ = np.nonzero(b1)
    xs_, ys_ = wt * (cc_ + 0.5, rr_ + 0.5)
    stree = cKDTree(np.column_stack([xs_, ys_]))

    N = compute_numbers(hull, bau, gar, adr, geb, stree, b2_poly, gemeinde)
    N.update({"punkt_31287": list(HULL_POINT), "centroid_wgs84": [round(lon, 6), round(lat, 6)],
              "tif": tif.name, "adressregister": contract.PREP_FILES["adressen"]["adressen"].name})
    (out_root / "tabellen" / JSON_NAME).write_text(json.dumps(N, indent=1, ensure_ascii=False), encoding="utf-8")

    # --- Zeichnen
    from PIL import Image

    def to3857(geom):
        return sh_transform(t_to3857, geom)

    def draw(ax, geom, **kw):
        geom = to3857(geom)
        for p in shapely.get_parts(geom):
            if p.geom_type != "Polygon":
                continue
            if kw.get("fill"):
                ax.add_patch(PathPatch(MPath.make_compound_path(*[MPath(np.asarray(r.coords)) for r in [p.exterior, *p.interiors]]),
                                       facecolor=kw["fill"], edgecolor=kw.get("ec", "none"), lw=kw.get("lw", 1),
                                       alpha=kw.get("alpha", 1), zorder=kw.get("z", 2), ls=kw.get("ls", "-")))
            else:
                for ring in [p.exterior, *p.interiors]:
                    xs, ys = ring.xy
                    ax.plot(xs, ys, color=kw["ec"], lw=kw.get("lw", 1), ls=kw.get("ls", "-"), zorder=kw.get("z", 2))

    def basemap(ax, bbx, z):
        to_ll = Transformer.from_crs(3857, 4326, always_xy=True).transform
        lo0, la0 = to_ll(bbx[0], bbx[1])
        lo1, la1 = to_ll(bbx[2], bbx[3])
        x0, y1 = _tile_xy(lo0, la0, z)
        x1, y0 = _tile_xy(lo1, la1, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                t = _tile_bounds3857(x, y, z)
                ax.imshow(np.asarray(_fetch_tile(tiles_dir, z, x, y)), extent=(t[0], t[2], t[1], t[3]),
                          origin="upper", zorder=0, interpolation="bilinear")
        ax.set_xlim(bbx[0], bbx[2])
        ax.set_ylim(bbx[1], bbx[3])
        ax.set_aspect("equal")

    half = 380
    fig = plt.figure(figsize=(1600 / 150, 800 / 150), dpi=150)
    axL = fig.add_axes([0.01, 0.17, 0.46, 0.72])
    axR = fig.add_axes([0.52, 0.17, 0.46, 0.72])
    cx, cy = to3857(cen).x, to3857(cen).y
    k = 1 / math.cos(math.radians(lat))
    hL, hR = half * k, 2300 * k
    basemap(axL, (cx - hL, cy - hL, cx + hL, cy + hL), 17)

    _c = bau.geometry.centroid
    bau["in_hull"] = [hg.contains(c) for c in _c]
    bau["d_wid"] = stree.query(np.column_stack([_c.x, _c.y]))[0]
    bau["cand"] = bau.in_hull & (bau.d_wid > 500)
    for geom in gar.geometry:
        draw(axL, geom, fill="#7fc97f", ec="#2e7d32", alpha=0.25, lw=0.5, z=2)
    draw(axL, hg, fill="#ff7f00", ec="#d95f00", alpha=0.22, lw=1.8, z=3)
    for geom, cand in zip(bau.geometry, bau.cand):
        draw(axL, geom, ec="#0b3c91" if cand else "#8a8a8a", lw=1.3 if cand else 0.9, ls="-" if cand else "--", z=4)
    adr_v = adr[(adr.x > cen.x - half - 60) & (adr.x < cen.x + half + 60) & (adr.y > cen.y - half - 60) & (adr.y < cen.y + half + 60)].reset_index(drop=True)
    ax_xy = np.array([to3857(Point(x, y)).coords[0] for x, y in zip(adr_v.x, adr_v.y)])
    cnt_xy = np.array(N["address_point_xy"])
    is_cnt = np.array([np.min(np.hypot(cnt_xy[:, 0] - x, cnt_xy[:, 1] - y)) < 1.0 for x, y in zip(adr_v.x, adr_v.y)])
    axL.scatter(ax_xy[~is_cnt, 0], ax_xy[~is_cnt, 1], s=20, c="#9e9e9e", edgecolor="white", lw=0.6, zorder=6)
    axL.scatter(ax_xy[is_cnt, 0], ax_xy[is_cnt, 1], s=30, c="#c2185b", edgecolor="white", lw=0.8, zorder=7)
    axL.figure.canvas.draw()
    placed = []
    cands = [(5, 6), (5, -12), (-18, 6), (-18, -12), (8, 16), (8, -22), (-22, 16), (-22, -22)]
    for i in list(np.argsort(~is_cnt)):
        px, py = ax_xy[i]
        t = adr_v.HNR_ADR_ZUSAMMEN.iloc[i]
        if not (cx - hL < px < cx + hL and cy - hL < py < cy + hL):
            continue
        d0 = axL.transData.transform((px, py))
        for off in cands:
            pos = (d0[0] + off[0] * 150 / 72, d0[1] + off[1] * 150 / 72)
            if all(np.hypot(pos[0] - q[0], pos[1] - q[1]) > 24 for q in placed):
                break
        placed.append(pos)
        col = "#880e4f" if is_cnt[i] else "#757575"
        axL.annotate(str(t), (px, py), xytext=off, textcoords="offset points", fontsize=7.5, fontweight="bold",
                     color=col, zorder=8,
                     arrowprops=dict(arrowstyle="-", color=col, lw=0.6, shrinkA=0, shrinkB=2) if abs(off[0]) > 10 or abs(off[1]) > 10 else None,
                     bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8))
    gname = gemeinde.get("PG", "")
    info_txt = "\n".join([
        f"{N['n_hausnummern']} Adressen (Haselbach bei Weiz {N['hausnummer_min']}–{N['hausnummer_max']})",
        f"{N['n_bauflaechen']} Bauflächen ({N['n_bauflaechen_ns41']} Gebäude, {N['n_bauflaechen_ns83']} Nebenflächen),",
        f"davon {N['n_bauflaechen_mit_adresse_100m']} mit Adresse ≤ 100 m",
        "→ zählt als Streusiedlung (≥ 5)",
        f"Wohnanteil {round(100 * N['n_wohn'] / max(N['n_bev_gebaeude'], 1))} % ({N['n_wohn']} von {N['n_bev_gebaeude']} BEV-Gebäuden)",
        f"{N['n_garten_150m']} Gärten ≤ 150 m · Fläche {N['flaeche_ha']:.1f} ha"])
    axL.text(cx + hL * 0.96, cy - hL * 0.96, info_txt, ha="right", va="bottom", fontsize=7, zorder=9, linespacing=1.35,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#555", alpha=0.93))
    axL.text(cx, cy + hL * 0.93, "Streusiedlung (Gruppe)", ha="center", fontsize=9, fontweight="bold", color="#8a3b00",
             bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#d95f00", alpha=0.9), zorder=8)
    axL.set_title("Nahausschnitt (ca. 760 × 760 m)\nStreusiedlung Haselbach bei Weiz", fontsize=9, pad=3)

    basemap(axR, (cx - hR, cy - hR, cx + hR, cy + hR), 14)
    near = g[g.intersects(box(cen.x - 2500, cen.y - 2500, cen.x + 2500, cen.y + 2500)) & (g.index != hull.name)]

    def cls(r):
        if r.klasse == "bewohnt":
            return "bewohnt_streu" if r.ist_streusiedlung else "bewohnt"
        return "unbewohnt" if r.klasse == "unbewohnt" else "industrie"

    sty = {"bewohnt_streu": ("#ffb74d", "#e65100"), "bewohnt": ("#4fc3f7", "#0277bd"),
           "unbewohnt": ("#bdbdbd", "#616161"), "industrie": ("#ce93d8", "#6a1b9a")}
    draw(axR, b2_poly, fill="#5e35b1", ec="#311b92", alpha=0.18, lw=0.0, z=2)
    draw(axR, b2_poly, ec="#311b92", lw=1.6, ls="--", z=4)
    draw(axR, b1_poly, fill="#311b92", ec="#1a0f5c", alpha=0.75, lw=0.5, z=3)
    for _, r in near.iterrows():
        fc, ec = sty[cls(r)]
        draw(axR, r.geometry, fill=fc, ec=ec, alpha=0.65, lw=0.8, z=3)
    extra = to3857(zoneS_poly.difference(b2_poly).buffer(0))
    for p_ in shapely.get_parts(extra):
        if p_.geom_type != "Polygon" or p_.area < 1:
            continue
        axR.add_patch(PathPatch(MPath.make_compound_path(*[MPath(np.asarray(r.coords)) for r in [p_.exterior, *p_.interiors]]),
                                facecolor="none", edgecolor="#c62828", hatch="////", lw=0, alpha=0.55, zorder=3.5))
    draw(axR, zoneS_poly, ec="#c62828", lw=1.8, z=4)
    draw(axR, hg, fill="#ff6f00", ec="#bf360c", alpha=0.9, lw=1.5, z=5)
    pa, pb = nearest_points(hg, b2_poly)
    qa, qb = to3857(pa), to3857(pb)
    axR.annotate("", qb.coords[0], xytext=qa.coords[0], arrowprops=dict(arrowstyle="<->", color="k", lw=1.3, shrinkA=0, shrinkB=0), zorder=9)
    axR.text((qa.x + qb.x) / 2, (qa.y + qb.y) / 2, f" {round(pa.distance(pb), -1):.0f} m ", fontsize=8, fontweight="bold",
             ha="center", va="center", zorder=10, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="k", lw=0.6))
    axR.annotate("untersuchte\nStreusiedlung", (cx, cy), xytext=(cx + 350 * k, cy + 800 * k), fontsize=8, fontweight="bold",
                 color="#8a3b00", zorder=8, arrowprops=dict(arrowstyle="-", color="#8a3b00"),
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#bf360c", alpha=0.9))
    sx0, sy0 = cx - hR + 0.06 * 2 * hR, cy - hR + 0.05 * 2 * hR
    axR.plot([sx0, sx0 + 500 * k], [sy0, sy0], color="k", lw=4, zorder=9, solid_capstyle="butt")
    axR.text(sx0 + 250 * k, sy0 + 45 * k, "500 m", ha="center", fontsize=8, fontweight="bold", zorder=9,
             bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.8))
    lx, ly = cx - hL + 0.05 * 2 * hL, cy - hL + 0.05 * 2 * hL
    axL.plot([lx, lx + 100 * k], [ly] * 2, color="k", lw=4, zorder=9, solid_capstyle="butt")
    axL.text(lx + 50 * k, ly + 12 * k, "100 m", ha="center", fontsize=8, fontweight="bold", zorder=9,
             bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.8))
    axR.set_title(f"Umgebung (ca. 4,6 × 4,6 km): Siedlungspuffer und 750-m-Zone\nHaselbach bei Weiz, Gemeinde {gname} (Stmk.)", fontsize=9, pad=3)
    for a in (axL, axR):
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_color("#555")
    hand = [Patch(fc="#ff7f00", ec="#d95f00", alpha=0.4, label="Streusiedlung (Gruppe, Hülle)"),
            Line2D([], [], color="#0b3c91", lw=1.5, label="DKM-Baufläche"),
            Patch(fc="#7fc97f", ec="#2e7d32", alpha=0.4, label="DKM-Garten"),
            Line2D([], [], marker="o", color="w", mfc="#c2185b", mec="white", ms=7, label="BEV-Adresse (zählt für die Gruppe)"),
            Line2D([], [], marker="o", color="w", mfc="#9e9e9e", mec="white", ms=6, label="BEV-Adresse (zählt nicht)"),
            Line2D([], [], color="#8a8a8a", lw=1, ls="--", label="Baufläche, nicht Kandidat (≤ 500 m am Wohnbauland)"),
            Line2D([], [], color="#c62828", lw=2, label="750-m-Zone der Streusiedlungen"),
            Patch(fc="#311b92", ec="#1a0f5c", alpha=0.75, label="Wohnbauland (Widmung)"),
            Patch(fc="#5e35b1", ec="#311b92", alpha=0.3, ls="--", label="Siedlungspuffer 1.000 m"),
            Patch(fc="none", ec="#c62828", hatch="////", lw=0, label="750-m-Zone außerhalb des Siedlungspuffers"),
            Patch(fc=sty["bewohnt_streu"][0], ec=sty["bewohnt_streu"][1], alpha=0.65, label="andere Streusiedlung"),
            Patch(fc=sty["bewohnt"][0], ec=sty["bewohnt"][1], alpha=0.65, label="bewohnte Einzellage"),
            Patch(fc=sty["unbewohnt"][0], ec=sty["unbewohnt"][1], alpha=0.65, label="unbewohnt"),
            Patch(fc=sty["industrie"][0], ec=sty["industrie"][1], alpha=0.65, label="industriegebietartig")]
    fig.legend(handles=hand, loc="lower center", ncol=5, fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.035),
               columnspacing=1.2, handlelength=1.6)
    fig.text(0.5, 0.012, f"Karte: {OSM_CREDIT} · Adressen: BEV Adressregister, Stichtag 01.10.2025 · Bauflächen: BEV DKM · "
             "Wohnbauland: Flächenwidmung Land Steiermark · Klassifikation: Abschichtung",
             ha="center", fontsize=7, color="#333")
    out = out_root / "abb" / FIG_NAME
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[beispielkarten] {out} {Image.open(out).size} in {time.time() - t0:.1f} s")
    return out


def window_bbox_3857(tr, h: int, w: int, transform_fn, n: int = 400):
    """3857-Bbox eines Rasterfensters aus allen vier Kanten (Meridiankonvergenz
    zwischen 31287 und 3857 beachten, nicht nur zwei Ecken)."""
    l, r, t = tr.c, tr.c + w * tr.a, tr.f
    b = tr.f + h * tr.e
    u = np.linspace(0, 1, n)
    X = np.concatenate([l + u * (r - l), l + u * (r - l), np.full_like(u, l), np.full_like(u, r)])
    Y = np.concatenate([np.full_like(u, b), np.full_like(u, t), b + u * (t - b), b + u * (t - b)])
    Xe, Ye = transform_fn(X, Y)
    return float(Xe.min()), float(Ye.min()), float(Xe.max()), float(Ye.max())


def warp_to_3857(mask, src_transform, dst_transform, shape):
    """Nearest-Reprojektion einer Bool-Maske (EPSG:31287) auf ein 3857-Gitter."""
    from rasterio.crs import CRS
    from rasterio.warp import Resampling, reproject

    out = np.zeros(shape, np.uint8)
    reproject(source=mask.astype(np.uint8), destination=out, src_transform=src_transform,
              src_crs=CRS.from_epsg(31287), dst_transform=dst_transform, dst_crs=CRS.from_epsg(3857),
              resampling=Resampling.nearest)
    return out > 0


def run_schwechat(out_root: Path, tif: Path | None = None, manifest_path: Path | None = None,
                  repo: Path | None = None) -> Path:
    """Abb. 4: Flughafenareal Wien-Schwechat und An-/Abflugkorridore auf OSM.

    Zeigt keine Zahlen (nur 2-km-Massstab), daher keine Registrierung.
    """
    t0 = time.time()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Patch
    from rasterio.transform import Affine
    from rasterio.windows import from_bounds
    from pyproj import Transformer

    repo = Path(repo) if repo else REPO
    tif = Path(tif) if tif else repo / "out/abschichtung.tif"
    manifest_path = Path(manifest_path) if manifest_path else repo / "out/abschichtung.bands.json"
    out_root = Path(out_root)
    (out_root / "abb").mkdir(parents=True, exist_ok=True)
    tiles_dir = repo / "derived/work/whitepaper/osm_tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    mm = wc.load_manifest(manifest_path)
    iA = wc.band_index(mm, "airport_area_major")
    iC = wc.band_index(mm, "airport_runway_corridor_5km")
    t3 = Transformer.from_crs(31287, 3857, always_xy=True).transform
    x, y = Transformer.from_crs(4326, 31287, always_xy=True).transform(16.559, 48.105)
    w, h = 11000, 8000
    with rasterio.open(tif) as s:
        win = from_bounds(x - w, y - h, x + w, y + h, s.transform).round_offsets().round_lengths()
        A = s.read(iA, window=win) > 0
        C = s.read(iC, window=win) > 0
        tr = s.window_transform(win)
    H, Wd = A.shape
    bx = window_bbox_3857(tr, H, Wd, t3)
    PX = 25 / math.cos(math.radians(48.1))
    X0, Y1 = bx[0], bx[3]
    W2 = int(math.ceil((bx[2] - X0) / PX))
    H2 = int(math.ceil((Y1 - bx[1]) / PX))
    dst_tr = Affine(PX, 0, X0, 0, -PX, Y1)
    A2 = warp_to_3857(A, tr, dst_tr, (H2, W2))
    C2 = warp_to_3857(C, tr, dst_tr, (H2, W2))
    X1, Y0 = X0 + W2 * PX, Y1 - H2 * PX
    ext = [X0, X1, Y0, Y1]
    xc = X0 + (np.arange(W2) + .5) * PX
    yc = Y1 - (np.arange(H2) + .5) * PX
    k = PX / 25
    FW = 6.0
    fig = plt.figure(figsize=(FW, FW * (Y1 - Y0) / (X1 - X0)), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True).transform
    lo0, la0 = to_ll(X0, Y0)
    lo1, la1 = to_ll(X1, Y1)
    tx0, ty1 = _tile_xy(lo0, la0, 12)
    tx1, ty0 = _tile_xy(lo1, la1, 12)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            t = _tile_bounds3857(tx, ty, 12)
            ax.imshow(np.asarray(_fetch_tile(tiles_dir, 12, tx, ty)), extent=(t[0], t[2], t[1], t[3]),
                      origin="upper", zorder=0, interpolation="bilinear")
    ca, cc = "#c0392b", "#2e6fb7"
    for m, c, al, z in ((C2, cc, .38, 2), (A2, ca, .6, 3)):
        img = np.zeros((H2, W2, 4))
        img[m] = to_rgba(c, al)
        ax.imshow(img, extent=ext, interpolation="nearest", zorder=z)
        ax.contour(xc, yc, m.astype(float), [.5], colors=c, linewidths=.7, zorder=z + .5)
    ax.set_xlim(X0, X1)
    ax.set_ylim(Y0, Y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    x0, y0 = X0 + 1000 * k, Y0 + 2000 * k
    ax.add_patch(plt.Rectangle((x0 - 500 * k, y0 - 700 * k), 3100 * k, 1700 * k, fc="w", alpha=.8, zorder=5, ec="none"))
    ax.plot([x0, x0 + 2000 * k], [y0, y0], "k", lw=2.5, zorder=6)
    ax.text(x0 + 1000 * k, y0 + 250 * k, "2 km", ha="center", fontsize=8, zorder=6)
    ax.annotate("N", xy=(X1 - 900 * k, Y1 - 300 * k), xytext=(X1 - 900 * k, Y1 - 2000 * k), ha="center",
                fontsize=10, fontweight="bold", zorder=6, arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.legend(handles=[Patch(fc=ca, ec=ca, alpha=.7, label="Flughafenareal"),
                       Patch(fc=cc, alpha=.6, ec=cc, label="An- und Abflugkorridor")],
              loc="lower right", fontsize=8, framealpha=.92).set_zorder(7)
    ax.text(X0 + 150 * k, Y0 + 100 * k, f"Karte: {OSM_CREDIT}", ha="left", va="bottom", fontsize=5.5,
            zorder=6, bbox=dict(fc="w", alpha=.7, ec="none", pad=1))
    out = out_root / "abb" / "abb4_schwechat_korridore.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[beispielkarten] {out} in {time.time() - t0:.1f} s")
    return out


def run(out_root: Path, tif: Path | None = None, manifest_path: Path | None = None,
        repo: Path | None = None) -> Path:
    """Erzeugt Abb. 3 und Abb. 4; gibt den Pfad von Abb. 3 zurueck."""
    p3 = run_haselbach(out_root, tif, manifest_path, repo)
    run_schwechat(out_root, tif, manifest_path, repo)
    return p3



def register_numbers(register, out_root: Path | None = None) -> None:
    """Registriert die Zahlen aus ``beispiel_haselbach.json``.

    ``register(key, wert, einheit, quelle)``; Schluessel mit Praefix ``beispiel_haselbach.``.
    """
    root = Path(out_root) if out_root else REPO / "docs/whitepaper"
    N = json.loads((root / "tabellen" / JSON_NAME).read_text(encoding="utf-8"))
    q = ("Illustrationsabbildung Abb. 3: TIF (Baender Wohnbauland, Siedlungspuffer, Streusiedlungs-Huellen), "
         "BEV-Kataster DKM, BEV-Adressregister")
    items = [
        ("n_hausnummern", N["n_hausnummern"], "Adressen"),
        ("hausnummer_min", N["hausnummer_min"], ""),
        ("hausnummer_max", N["hausnummer_max"], ""),
        ("n_bauflaechen", N["n_bauflaechen"], "Bauflaechen"),
        ("n_bauflaechen_ns41", N["n_bauflaechen_ns41"], "Bauflaechen"),
        ("n_bauflaechen_ns83", N["n_bauflaechen_ns83"], "Bauflaechen"),
        ("n_wohn", N["n_wohn"], "Gebaeude"),
        ("n_bev_gebaeude", N["n_bev_gebaeude"], "Gebaeude"),
        ("abstand_wohnbauland_m", N["abstand_wohnbauland_m"], "m"),
        ("abstand_siedlungspuffer_m", N["abstand_siedlungspuffer_m"], "m"),
        ("flaeche_ha", N["flaeche_ha"], "ha"),
        ("gemeinde", N["gemeinde"], ""),
        ("gkz", N["gkz"], ""),
    ]
    for key, wert, einheit in items:
        register(KEY_PREFIX + key, wert, einheit, q)
    # Wohnanteil in Prozent (wie streu_gewinn_pct: 0..100, Formatierung `%` haengt " %" an)
    register(KEY_PREFIX + "wohnanteil_pct", N["n_wohn"] / N["n_bauflaechen"] * 100.0, "%",
             q + "; = n_wohn / n_bauflaechen")


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs/whitepaper")
