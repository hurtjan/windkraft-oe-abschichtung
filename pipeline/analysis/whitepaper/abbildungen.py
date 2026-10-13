"""Erzeugt alle White-Paper-Abbildungen (PNG 300 dpi, teils zusaetzlich SVG) aus dem Cache.

Liest ausschliesslich den von ``zaehlen.py`` geschriebenen Cache und die
Bundeslandgrenzen-Rohquelle (fuer die Grenzlinien). Wiederverwendet Farben,
Klasseneinteilung und die Downsampling-Regel aus
``whitepaper/abb_entwurf/_make_figures.py`` / ``_plot_figures.py``
(kopiert, nicht importiert). Schreibt ausschliesslich nach
``docs/whitepaper/abb/``.

Die Kartenabbildungen (``abb1_v1_5klassen``, ``abb1_v2_8klassen``,
``abb1_v3_kleinkarten``, ``abb_methoden_uebersicht``) werden nur als PNG geschrieben; ``abb2_balken`` und
``abbD_wasserfall`` weiterhin als PNG+SVG.
"""
from __future__ import annotations

from pipeline import contract as _contract

import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.legend_handler as mlh
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from . import wp_common as wc

CM = 1 / 2.54

def hex_to_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i: i + 2], 16) / 255.0 for i in (0, 2, 4)])


# Aktuelle (unfreigegebene) Standardpalette, bleibt Default bis Jan eine Variante waehlt.
_PALETTE_AKTUELL = {
    "mensch": "#f46d43",
    "natur": "#006d2c",
    "geografie": "#807dba",
    # Kombinationsklassen: eigene Farbtoene (rot+gruen -> gelb, rot+violett -> magenta,
    # gruen+violett -> cyan), CVD-validiert (protan/deutan Delta E >= 9.5).
    "mensch_natur": "#fed976",
    "mensch_geografie": "#e7298a",
    "natur_geografie": "#41b6c4",
    "alle_drei": "#3a3a3a",
    "small_area": "#c6dbef",
    "eignung": "#084594",
    "outside": "#ffffff",
    "mehrfach": "#bdbdbd",
    "excluded_grey": "#e6e6e6",
    "gesamt": "#999999",
}


def _blend(hexes: list[str], dunkler: float) -> str:
    """Mittelwert der sRGB-Werte, um den Faktor ``dunkler`` (0..1) abgedunkelt, als Hex."""
    m = np.mean([hex_to_rgb(h) for h in hexes], axis=0) * (1.0 - dunkler)
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in np.clip(m, 0, 1))


def _variant(mensch: str, natur: str, geografie: str, eignung: str = "#08519c",
             small_area: str = "#9ecae1") -> dict[str, str]:
    """Vollstaendige Palette aus den Basisfarben.

    Mensch = orange/rot, Natur = gruen, Geografie = grau, Eignung = blau. Die
    Kombinationsklassen haben keine eigenen Farbtoene: Balkendiagramm = diagonale
    Streifen der beteiligten Basisfarben (siehe ``_draw_stripes``); in der
    100-m-Karte (V2, Streifen nicht darstellbar) Mischton der Basisfarben, leicht
    abgedunkelt (zwei Klassen 12 %, alle drei 55 %).
    """
    return {
        "mensch": mensch, "natur": natur, "geografie": geografie,
        "mensch_natur": _blend([mensch, natur], 0.12),
        "mensch_geografie": _blend([mensch, geografie], 0.12),
        "natur_geografie": _blend([natur, geografie], 0.12),
        "alle_drei": _blend([mensch, natur, geografie], 0.55),
        "small_area": small_area, "eignung": eignung,
        "outside": "#ffffff", "mehrfach": "#3d3d3d", "excluded_grey": "#e6e6e6",
        "gesamt": "#3d3d3d",
    }


# Farbvarianten fuer die Vorschau. Grau liegt jeweils klar neben Rot/Gruen in der
# Helligkeit, Rot/Gruen trennen sich ueber die Helligkeit (CVD-Validator, siehe Bericht).
PALETTE_VARIANTS: dict[str, dict[str, str]] = {
    "aktuell": _PALETTE_AKTUELL,
    # A: rotorange / dunkelgruen / mittelgrau
    "A": _variant("#e8743b", "#00692f", "#8f8f8f"),
    # B: Bernstein-Orange / dunkelgruen / mittelgrau
    "B": _variant("#f28e2b", "#1b7837", "#8c8c8c"),
    # C: Rot / hellgruen / dunkelgrau (Helligkeitsachse umgekehrt)
    "C": _variant("#d7301f", "#7fbf7b", "#707070"),
}
DEFAULT_PALETTE = "B"

PALETTE: dict[str, str] = dict(PALETTE_VARIANTS[DEFAULT_PALETTE])


def set_palette(name: str) -> None:
    """Schaltet ``PALETTE`` (in place, alle Zeichenfunktionen lesen das Modul-Dict) um."""
    if name not in PALETTE_VARIANTS:
        raise KeyError(f"unbekannte Palette {name!r}; verfuegbar: {sorted(PALETTE_VARIANTS)}")
    PALETTE.clear()
    PALETTE.update(PALETTE_VARIANTS[name])


FULL_NAMES = wc.FULL_NAMES

SAVE_KWARGS = dict(metadata={"Date": None, "Software": None})


def _savefig(fig, out_path_png: Path, out_path_svg: Path | None = None) -> None:
    """Schreibt PNG (immer) und optional SVG.

    Die abb1_*-Kartenabbildungen werden nur als PNG geschrieben (``out_path_svg=None``),
    abb2_balken und abbD_wasserfall weiterhin als PNG+SVG.
    """
    matplotlib.rcParams["svg.hashsalt"] = wc.MPL_SVG_HASHSALT
    fig.savefig(out_path_png, dpi=300, metadata={"Software": None})
    print(f"[abb] {out_path_png}")
    if out_path_svg is not None:
        fig.savefig(out_path_svg, metadata={"Date": None, "Creator": None})
        print(f"[abb] {out_path_svg}")


def de1(x: float) -> str:
    return wc.de_num(x, 1)


def load_cache(cache_dir: Path):
    npz = np.load(Path(cache_dir) / "downsampled.npz")
    counts = json.loads((Path(cache_dir) / "counts.json").read_text(encoding="utf-8"))
    prov = json.loads((Path(cache_dir) / "provenance.json").read_text(encoding="utf-8"))
    return npz, counts, prov


def load_borders(grenzen_path: Path) -> gpd.GeoDataFrame:
    regions = wc.load_bundeslaender(grenzen_path)
    return gpd.GeoDataFrame(
        {"code": [c for c, _n, _g in regions], "name": [n for _c, n, _g in regions]},
        geometry=[g for _c, _n, g in regions], crs=wc.TARGET_CRS,
    )


def build_rgb(class_ds: np.ndarray, lut: dict[int, np.ndarray]) -> np.ndarray:
    lut_arr = np.zeros((10, 3), dtype=np.float64)
    for k, v in lut.items():
        lut_arr[k] = v
    return lut_arr[class_ds]


def region_pct(counts: dict, key: str) -> dict[str, float]:
    at_cells = counts["at_cells"]
    return {"AT": counts["at_counts"][key] / at_cells * 100.0}


def at_pct(counts: dict, key: str) -> float:
    return counts["at_counts"][key] / counts["at_cells"] * 100.0


FOOTNOTE_MAIN = (
    "Kartendarstellung auf 100 m aggregiert (4×4 Zellen à 25 m): jede 100-m-Zelle "
    "erhält die häufigste Klasse unter ihren innerhalb Österreichs liegenden "
    "25-m-Zellen; Ausnahme: Eignung setzt sich durch, sobald mindestens 4 von 16 Zellen "
    "Eignung sind (damit kleine geeignete Flächen sichtbar bleiben)."
)


def make_map_figure(rgb_image, borders_gdf, bounds, title, legend_patches, footnote,
                     source_line, out_dir: Path, stem: str, legend_ncol=3):
    left, bottom, right, top = bounds
    fig = plt.figure(figsize=(16 * CM, 12.6 * CM), dpi=300)
    ax_map = fig.add_axes([0.02, 0.28, 0.96, 0.66])
    ax_map.imshow(rgb_image, extent=(left, right, bottom, top), origin="upper", interpolation="nearest")
    borders_gdf.boundary.plot(ax=ax_map, color="#333333", linewidth=0.4, zorder=3)
    ax_map.set_xlim(left, right)
    ax_map.set_ylim(bottom, top)
    ax_map.set_aspect("equal")
    ax_map.axis("off")
    ax_map.set_title(title, fontsize=9, pad=3)

    ax_leg = fig.add_axes([0.0, 0.10, 1.0, 0.16])
    ax_leg.axis("off")
    ax_leg.legend(handles=legend_patches, loc="center", ncol=legend_ncol, fontsize=6.3,
                  frameon=False, handlelength=1.4, handleheight=1.1, columnspacing=1.2)

    fig.text(0.02, 0.045, footnote, fontsize=5.3, va="bottom", color="#333333", wrap=True)
    fig.text(0.02, 0.012, source_line, fontsize=5.3, va="bottom", color="#333333")

    _savefig(fig, out_dir / f"{stem}.png")
    plt.close(fig)


def fig_v1(npz, counts, prov, borders, out_dir: Path):
    class_ds = npz["class_ds"]
    lut = {
        0: hex_to_rgb(PALETTE["outside"]),
        1: hex_to_rgb(PALETTE["mensch"]),
        2: hex_to_rgb(PALETTE["natur"]),
        3: hex_to_rgb(PALETTE["geografie"]),
        4: hex_to_rgb(PALETTE["mehrfach"]),
        5: hex_to_rgb(PALETTE["mehrfach"]),
        6: hex_to_rgb(PALETTE["mehrfach"]),
        7: hex_to_rgb(PALETTE["mehrfach"]),
        8: hex_to_rgb(PALETTE["small_area"]),
        9: hex_to_rgb(PALETTE["eignung"]),
    }
    rgb = build_rgb(class_ds, lut)

    mehrfach_pct = sum(at_pct(counts, k) for k in
                        ("mensch_natur", "mensch_geografie", "natur_geografie", "alle_drei"))
    small_pct = at_pct(counts, "kleinflaechen")
    eign_pct = at_pct(counts, "available_cleaned_min_10ha")

    legend_items = [
        ("nur Mensch", PALETTE["mensch"], at_pct(counts, "nur_mensch")),
        ("nur Natur", PALETTE["natur"], at_pct(counts, "nur_natur")),
        ("nur Geografie", PALETTE["geografie"], at_pct(counts, "nur_geografie")),
        ("mehrfach ausgeschlossen", PALETTE["mehrfach"], mehrfach_pct),
        ("Kleinfläche < 10 ha", PALETTE["small_area"], small_pct),
        ("Eignung ≥ 10 ha", PALETTE["eignung"], eign_pct),
    ]
    patches = [mpatches.Patch(facecolor=c, edgecolor="#333333", linewidth=0.3,
                               label=f"{lbl} ({de1(p)} % AT)") for lbl, c, p in legend_items]

    make_map_figure(
        rgb, borders, npz["bounds"],
        title="Ausschluss und Eignung in Österreich, 5 Klassen",
        legend_patches=patches, footnote=FOOTNOTE_MAIN,
        source_line=prov["figure_source_line"], out_dir=out_dir, stem="abb1_v1_5klassen",
        legend_ncol=3,
    )


def fig_v2(npz, counts, prov, borders, out_dir: Path):
    class_ds = npz["class_ds"]
    mn = hex_to_rgb(PALETTE["mensch_natur"])
    mg = hex_to_rgb(PALETTE["mensch_geografie"])
    ng = hex_to_rgb(PALETTE["natur_geografie"])
    lut = {
        0: hex_to_rgb(PALETTE["outside"]),
        1: hex_to_rgb(PALETTE["mensch"]),
        2: hex_to_rgb(PALETTE["natur"]),
        3: hex_to_rgb(PALETTE["geografie"]),
        4: mn, 5: mg, 6: ng,
        7: hex_to_rgb(PALETTE["alle_drei"]),
        8: hex_to_rgb(PALETTE["small_area"]),
        9: hex_to_rgb(PALETTE["eignung"]),
    }
    rgb = build_rgb(class_ds, lut)

    legend_items = [
        ("nur Mensch", hex_to_rgb(PALETTE["mensch"]), at_pct(counts, "nur_mensch")),
        ("nur Natur", hex_to_rgb(PALETTE["natur"]), at_pct(counts, "nur_natur")),
        ("nur Geografie", hex_to_rgb(PALETTE["geografie"]), at_pct(counts, "nur_geografie")),
        (wc.LABEL_MENSCH_NATUR, mn, at_pct(counts, "mensch_natur")),
        (wc.LABEL_MENSCH_GEOGRAFIE, mg, at_pct(counts, "mensch_geografie")),
        (wc.LABEL_NATUR_GEOGRAFIE, ng, at_pct(counts, "natur_geografie")),
        ("alle drei", hex_to_rgb(PALETTE["alle_drei"]), at_pct(counts, "alle_drei")),
        ("Kleinfläche < 10 ha", hex_to_rgb(PALETTE["small_area"]), at_pct(counts, "kleinflaechen")),
        ("Eignung ≥ 10 ha", hex_to_rgb(PALETTE["eignung"]), at_pct(counts, "available_cleaned_min_10ha")),
    ]
    patches = [mpatches.Patch(facecolor=c, edgecolor="#333333", linewidth=0.3,
                               label=f"{lbl} ({de1(p)} % AT)") for lbl, c, p in legend_items]

    make_map_figure(
        rgb, borders, npz["bounds"],
        title="Ausschluss und Eignung in Österreich, 8 Klassen",
        legend_patches=patches, footnote=FOOTNOTE_MAIN,
        source_line=prov["figure_source_line"], out_dir=out_dir, stem="abb1_v2_8klassen",
        legend_ncol=3,
    )


def fig_v3(npz, prov, borders, out_dir: Path):
    """Redesign: drei kleine Kategorie-Panels oben in einer Reihe, ein grosses

    Eignungs-Panel darunter ueber die volle Breite (bessere Sichtbarkeit der
    Eignungsflaeche gegenueber der 2x2-Vorlage). Uebrige Flaeche hellgrau.
    """
    _kleinkarten(npz, prov, borders, out_dir, stem="abb1_v3_kleinkarten",
                 rest_color=PALETTE["excluded_grey"],
                 suptitle="Mensch, Natur, Geografie und Eignung im Vergleich",
                 big_title="Eignung ≥ 10 ha", rest_label="übrige Fläche")


def fig_methoden_uebersicht(npz, prov, borders, out_dir: Path):
    """Uebersicht fuer das Methodendokument: wie V3, aber uebrige Flaeche weiss."""
    _kleinkarten(npz, prov, borders, out_dir, stem="abb_methoden_uebersicht",
                 rest_color=PALETTE["outside"],
                 suptitle="Ausschlussflächen und Eignung in Österreich",
                 big_title="Eignung ≥ 10 ha", rest_label=None)


def _kleinkarten(npz, prov, borders, out_dir: Path, stem: str, rest_color: str,
                 suptitle: str, big_title: str, rest_label: str | None):
    H_ds, N_ds, G_ds, class_ds = npz["H_ds"], npz["N_ds"], npz["G_ds"], npz["class_ds"]
    bounds = npz["bounds"]
    left, bottom, right, top = bounds

    white = hex_to_rgb(PALETTE["outside"])

    def band_rgb(mask, color):
        out = np.tile(white, (*mask.shape, 1))
        out[mask] = hex_to_rgb(color)
        return out

    eign_grey = hex_to_rgb(rest_color)
    eign_blue = hex_to_rgb(PALETTE["eignung"])
    eign_rgb = np.tile(white, (*class_ds.shape, 1))
    eign_rgb[(class_ds >= 1) & (class_ds <= 8)] = eign_grey
    eign_rgb[class_ds == 9] = eign_blue

    small_panels = [
        ("Mensch", band_rgb(H_ds, PALETTE["mensch"])),
        ("Natur", band_rgb(N_ds, PALETTE["natur"])),
        ("Geografie", band_rgb(G_ds, PALETTE["geografie"])),
    ]

    fig = plt.figure(figsize=(16 * CM, 18 * CM), dpi=300)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 2.0], hspace=0.14, wspace=0.04,
                           left=0.02, right=0.98, top=0.93, bottom=0.14)

    for col, (title, rgb) in enumerate(small_panels):
        ax = fig.add_subplot(gs[0, col])
        ax.imshow(rgb, extent=(left, right, bottom, top), origin="upper", interpolation="nearest")
        borders.boundary.plot(ax=ax, color="#333333", linewidth=0.3, zorder=3)
        ax.set_xlim(left, right)
        ax.set_ylim(bottom, top)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=8, pad=2)

    ax_big = fig.add_subplot(gs[1, :])
    ax_big.imshow(eign_rgb, extent=(left, right, bottom, top), origin="upper", interpolation="nearest")
    borders.boundary.plot(ax=ax_big, color="#333333", linewidth=0.45, zorder=3)
    ax_big.set_xlim(left, right)
    ax_big.set_ylim(bottom, top)
    ax_big.set_aspect("equal")
    ax_big.axis("off")
    ax_big.set_title(big_title, fontsize=9, pad=3)

    fig.suptitle(suptitle, fontsize=10, y=0.985)

    legend_items = [
        ("Mensch", PALETTE["mensch"]), ("Natur", PALETTE["natur"]), ("Geografie", PALETTE["geografie"]),
        ("Eignung ≥ 10 ha", PALETTE["eignung"]),
    ]
    if rest_label is not None:
        legend_items.append((rest_label, rest_color))
    patches = [mpatches.Patch(facecolor=c, edgecolor="#333333", linewidth=0.3, label=lbl)
               for lbl, c in legend_items]
    fig.legend(handles=patches, loc="lower center", ncol=len(patches) if len(patches) <= 4 else 3,
               fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, 0.075))

    footnote = (
        "Kartendarstellung auf 100 m aggregiert (4×4 Zellen à 25 m): Panels Mensch/Natur/"
        "Geografie zeigen die volle Ausdehnung der jeweiligen Ausschlussschicht (Mehrheitsregel: "
        "aktiv ab 8 von 16 Zellen); Panel Eignung wie bei den Hauptkarten (Eignung setzt sich ab "
        "4 von 16 Zellen durch)."
    )
    fig.text(0.02, 0.045, footnote, fontsize=5.3, va="bottom", color="#333333", wrap=True)
    fig.text(0.02, 0.015, prov["figure_source_line"], fontsize=5.3, va="bottom", color="#333333")

    _savefig(fig, out_dir / f"{stem}.png")
    plt.close(fig)


# --- Diagonale Streifen fuer Kombinationsklassen (Balkendiagramm) -------------------------
STRIPE_WIDTH_IN = 0.035   # Breite eines Einzelstreifens in Zoll (0,9 mm; ~2,5 pt)


def _stripe_polys(w: float, h: float, ncol: int, width: float):
    """Parallelogramme (je Farbe eine Liste) fuer Streifen '/' in einem Rechteck w x h.

    Koordinaten relativ zur linken unteren Ecke, y nach oben, 45 Grad. Streifen
    ``k`` (Laufvariable u = x - y) hat Farbindex ``k % ncol``; der erste Streifen
    (Farbe 0) beginnt an der linken unteren Ecke.
    """
    out: list[list[list[tuple[float, float]]]] = [[] for _ in range(ncol)]
    k_min = int(np.floor(-h / width)) - 1
    k_max = int(np.ceil(w / width)) + 1
    for k in range(k_min, k_max + 1):
        u0, u1 = k * width, (k + 1) * width
        out[k % ncol].append([(u0, 0.0), (u1, 0.0), (u1 + h, h), (u0 + h, h)])
    return out


class StripePatch(mpatches.Patch):
    """Legenden-Proxy fuer eine gestreifte Klasse (``colors`` = Hex-Liste)."""

    def __init__(self, colors: list[str], label: str):
        super().__init__(facecolor=colors[0], edgecolor="none", label=label)
        self.stripe_colors = list(colors)


class HandlerStripes(mlh.HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        cols = orig_handle.stripe_colors
        base = mpatches.Rectangle((-xdescent, -ydescent), width, height, facecolor=cols[0],
                                  edgecolor="none", linewidth=0, transform=trans)
        arts = [base]
        # Streifenbreite in Punkten (trans der Legende arbeitet in Punkten)
        for ci, polys in enumerate(_stripe_polys(width, height, len(cols), STRIPE_WIDTH_IN * 72.0)):
            if ci == 0:
                continue
            for poly in polys:
                pts = [(-xdescent + x, -ydescent + y) for x, y in poly]
                pa = mpatches.Polygon(pts, closed=True, facecolor=cols[ci], edgecolor="none",
                                      linewidth=0, transform=trans)
                pa.set_clip_path(base)
                arts.append(pa)
        return arts


def _draw_stripes(ax, fig, x0: float, x1: float, y0: float, y1: float, colors: list[str]) -> None:
    """Zeichnet in das Datenrechteck (x0..x1, y0..y1) diagonale Streifen der ``colors``.

    Geometrie in Zoll (``fig.dpi_scale_trans``), damit der Winkel (45 Grad) und die
    Streifenbreite unabhaengig von Achsenskalierung und Ausgabe-dpi (PNG/SVG) sind.
    Muss nach dem endgueltigen Layout (subplots_adjust, Achsengrenzen) aufgerufen werden.
    """
    to_in = ax.transData + fig.dpi_scale_trans.inverted()
    (ax_, ay_), (bx_, by_) = to_in.transform([(x0, y0), (x1, y1)])
    left, right = min(ax_, bx_), max(ax_, bx_)
    bottom, top = min(ay_, by_), max(ay_, by_)
    w, h = right - left, top - bottom
    clip = mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transData,
                              facecolor="none", edgecolor="none")
    ax.add_patch(mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=colors[0],
                                    edgecolor="none", linewidth=0))
    for ci, polys in enumerate(_stripe_polys(w, h, len(colors), STRIPE_WIDTH_IN)):
        if ci == 0:
            continue
        for poly in polys:
            pts = [(left + x, bottom + y) for x, y in poly]
            pa = mpatches.Polygon(pts, closed=True, facecolor=colors[ci], edgecolor="none",
                                  linewidth=0, transform=fig.dpi_scale_trans)
            ax.add_patch(pa)
            pa.set_clip_path(clip)


def fig_bars(counts, prov, out_dir: Path):
    """Gestapelte Balken je Bundesland.

    Basisklassen (nur Mensch/Natur/Geografie) einfarbig, Kombinationsklassen als
    diagonale Streifen der beteiligten Basisfarben (keine eigenen Farben).
    """
    pm, pn, pg = PALETTE["mensch"], PALETTE["natur"], PALETTE["geografie"]
    # (Schluessel, Beschriftung, Farbliste; mehr als eine Farbe = Streifen)
    order_names = [
        ("nur_mensch", "nur Mensch", [pm]),
        ("mensch_geografie", wc.LABEL_MENSCH_GEOGRAFIE, [pm, pg]),
        ("nur_geografie", "nur Geografie", [pg]),
        ("natur_geografie", wc.LABEL_NATUR_GEOGRAFIE, [pn, pg]),
        ("nur_natur", "nur Natur", [pn]),
        ("mensch_natur", wc.LABEL_MENSCH_NATUR, [pm, pn]),
        ("alle_drei", "alle drei", [pm, pn, pg]),
        ("kleinflaechen", "Kleinflächen < 10 ha", [PALETTE["small_area"]]),
        ("available_cleaned_min_10ha", "Eignung ≥ 10 ha", [PALETTE["eignung"]]),
    ]

    def row_values(code: str):
        region_cells = counts["region_cells"]
        counters = counts["counters"]
        at_cells = counts["at_cells"]
        at_counts = counts["at_counts"]
        vals = []
        for key, _lbl, _c in order_names:
            if code == "AT":
                vals.append(at_counts[key] / at_cells * 100.0)
            else:
                vals.append(counters[key][code] / region_cells[code] * 100.0)
        eign = vals[-1]
        return vals, eign

    bl_codes = list(wc.REGION_ORDER)
    bl_sorted = sorted(bl_codes, key=lambda c: row_values(c)[1], reverse=True)
    rows = [("AT", "Österreich", True)] + [(c, FULL_NAMES[c], False) for c in bl_sorted]

    fig, ax = plt.subplots(figsize=(16 * CM, 14 * CM), dpi=300)
    bar_h = 0.72
    segments = []  # (x0, x1, y0, y1, Farben) -> nach dem Layout gezeichnet
    y_positions, labels, bold_flags = [], [], []
    y = 0
    for code, name, is_at in rows:
        y_positions.append(y)
        labels.append(name)
        bold_flags.append(is_at)
        vals, eign_pct = row_values(code)
        left = 0.0
        for (_key, _lbl, cols), v in zip(order_names, vals):
            segments.append((left, left + v, y - bar_h / 2, y + bar_h / 2, cols))
            left += v
        ax.text(101.5, y, de1(eign_pct), va="center", ha="left", fontsize=6.5)
        y += 1
        if is_at:
            y += 1

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=7.5)
    for tick, bold in zip(ax.get_yticklabels(), bold_flags):
        if bold:
            tick.set_fontweight("bold")

    ax.set_xlim(0, 112)
    ax.set_ylim(y - 1 + 0.5 + 0.0, -0.5)  # invertiert (oben = Oesterreich)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100 %"], fontsize=7)
    ax.axvline(100, color="#999999", linewidth=0.5, linestyle=":")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)

    ax.set_title("Ausschluss und Eignung je Bundesland", fontsize=9, pad=8)
    fig.subplots_adjust(left=0.16, right=0.94, top=0.92, bottom=0.20)  # Layout vor den Streifen

    for x0, x1, y0, y1, cols in segments:
        if len(cols) == 1:
            ax.add_patch(mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=cols[0],
                                            edgecolor="none", linewidth=0))
        else:
            _draw_stripes(ax, fig, x0, x1, y0, y1, cols)

    handles = [StripePatch(cols, lbl) if len(cols) > 1
               else mpatches.Patch(facecolor=cols[0], edgecolor="none", label=lbl)
               for _k, lbl, cols in order_names]
    fig.legend(handles=handles, handler_map={StripePatch: HandlerStripes()}, loc="lower center",
               ncol=3, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, 0.02),
               handlelength=2.6, handleheight=1.3)

    fig.text(0.99, 0.965, "Eignung % rechts an jedem Balken", fontsize=5.5, ha="right", color="#333333")
    fig.text(0.02, 0.145, prov["figure_source_line"], fontsize=5.5, va="bottom", color="#333333")

    _savefig(fig, out_dir / "abb2_balken.png", out_dir / "abb2_balken.svg")
    plt.close(fig)


def fig_waterfall(counts, prov, out_dir: Path):
    at_cells = counts["at_cells"]
    at_counts = counts["at_counts"]
    nur_geografie_at = at_counts["nur_geografie"]
    frei_at = at_counts["frei"]
    union_hn_at = at_cells - nur_geografie_at - frei_at

    stages = [
        ("Gesamtfläche", 100.0),
        ("nach Mensch", 100.0 - at_counts["exclusion_human"] / at_cells * 100.0),
        ("nach Natur", 100.0 - union_hn_at / at_cells * 100.0),
        ("nach Geografie", frei_at / at_cells * 100.0),
        ("Eignung (≥ 10 ha)", at_counts["available_cleaned_min_10ha"] / at_cells * 100.0),
    ]

    fig, ax = plt.subplots(figsize=(16 * CM, 9 * CM), dpi=300)
    xs = list(range(len(stages)))
    vals = [v for _l, v in stages]
    colors = [PALETTE["gesamt"], PALETTE["mensch"], PALETTE["natur"], PALETTE["geografie"], PALETTE["eignung"]]
    ax.bar(xs, vals, color=colors, width=0.6)
    for x, v in zip(xs, vals):
        ax.text(x, v + 1.5, de1(v), ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(xs)
    ax.set_xticklabels([l for l, _v in stages], fontsize=7.5)
    ax.set_ylim(0, 110)
    ax.set_ylabel("% der Bezugsfläche Österreich", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Von der Gesamtfläche zur Eignungsfläche (Österreich)", fontsize=9, pad=8)

    fig.text(0.02, 0.02, prov["figure_source_line"], fontsize=5.5, va="bottom", color="#333333")
    fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.16)
    _savefig(fig, out_dir / "abbD_wasserfall.png", out_dir / "abbD_wasserfall.svg")
    plt.close(fig)


def run(cache_dir: Path, grenzen_path: Path, out_root: Path, palette: str | None = None) -> Path:
    if palette is not None:
        set_palette(palette)
    npz, counts, prov_raw = load_cache(cache_dir)
    prov = dict(prov_raw)
    sha_short = prov["tif_sha256_short"]
    prov["figure_source_line"] = f"Daten: Abschichtung, TIF sha256 {sha_short}, Stand {prov['tif_date']}"

    abb_dir = Path(out_root) / "abb"
    abb_dir.mkdir(parents=True, exist_ok=True)

    borders = load_borders(grenzen_path)

    fig_v1(npz, counts, prov, borders, abb_dir)
    fig_v2(npz, counts, prov, borders, abb_dir)
    fig_v3(npz, prov, borders, abb_dir)
    fig_methoden_uebersicht(npz, prov, borders, abb_dir)
    fig_bars(counts, prov, abb_dir)
    fig_waterfall(counts, prov, abb_dir)

    print(f"[abbildungen] geschrieben nach {abb_dir}")
    return abb_dir


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True, type=Path)
    ap.add_argument("--grenzen", type=Path, default=_contract.PREP_FILES["admin"]["bundesland_masken"])
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--palette", default=None, choices=sorted(PALETTE_VARIANTS),
                    help=f"Farbvariante (Default: {DEFAULT_PALETTE})")
    args = ap.parse_args()
    run(args.cache_dir, args.grenzen, args.out_root, palette=args.palette)
