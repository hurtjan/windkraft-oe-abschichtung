# Nicht Teil der v2-Kette: dieses Skript wird von keinem Kettenschritt und von
# keinem Makefile-Target aufgerufen. Es liegt hier als Herleitung der fest
# verdrahteten Konstante HIG_CHAIN_M = 200 (Meter Verkettungsdistanz).
# Verwendet wird die Konstante heute in:
#   windkraft/calc/abschichtung_common.py:159  (Definition HIG_CHAIN_M = 200.0)
#   scripts/widmung_v2/02_build_hig_sources.py:205  (Default fuer --chain-m)
#   scripts/widmung_v2/04_create_distance_zones.py:477  (GeoTIFF-Metadatum)
"""Knie-Parametersuche für die Streusiedlungs-Erkennung (ε und Schwelle à la DBSCAN).

Die Verkettungsdistanz ist DBSCANs ε, die Adress-Schwelle verwandt mit minPts.
Statt Kombinationen zu raten, sucht dieses Skript die Knie in den Daten:

1. **k-Distanz-Kurven** (Lehrbuch-ε-Wahl): Distanz jedes adressierten Objekts
   zu seinem k-nächsten Nachbarn, sortiert; das Knie trennt "Nachbar gehört
   zur selben Streusiedlung" von "nächstes Objekt ist schon das nächste Gebiet".
   Auch je Bundesland - die Siedlungsmuster (Riedel vs. Täler) unterscheiden sich.
2. **ε-Sweep der Clusterstatistik**: Single-Linkage-Cluster (= das Verkettungs-
   verhalten der Pipeline auf Punktebene) für ein ε-Raster aus EINEM Kantensatz.
   Je Schwelle T: erfasster Anteil adressierter Objekte, Clusterzahl, größter
   Cluster (Perkolationswarnung). Knie der Anteilskurve = ab hier verschmelzen
   getrennte Gebiete statt Streusiedlungslücken zu schließen.
3. **DBSCAN-Vergleich**: echtes DBSCAN (lokales minPts-Kriterium) am
   empfohlenen ε - zeigt, was das Kernpunkt-Kriterium gegenüber Single-Linkage
   ändern würde (dünne Brücken zwischen Gebieten).

Ausgabe: knee_kdist.png, knee_eps_sweep.png, knee_eps_sweep.csv, knee_summary.md
im Sweep-Ordner. Die empfohlene Verkettung ist ε abzüglich des mittleren
Gebäudedurchmessers (Hüllen verketten Kante-zu-Kante, Punkte Zentroid-zu-Zentroid).

Run:  uv run python scripts/analysis/streusiedlung_knee.py
      uv run python scripts/analysis/streusiedlung_knee.py --bbox ... --bl Steiermark
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import shapely  # noqa: E402

from windkraft.config import load_config  # noqa: E402
from windkraft.calc.abschichtung_common import load_grid, timed  # noqa: E402
from cluster_knee import (  # noqa: E402
    chord_knee,
    cluster_stats,
    dbscan_labels,
    eps_components,
    kdist_curve,
    pair_edges,
)
from windkraft.calc.hig_detection import DISPLAY_BUNDESLAND  # noqa: E402
from windkraft.calc.streusiedlung import load_candidate_signals  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Knie-Suche für Verkettungs-ε und Adress-Schwelle.")
    p.add_argument("--config", default="config/config.json")
    p.add_argument("--zoning-dir", default="output/abschichtung_widmung_v2/zoning_vectors")
    p.add_argument("--noe-dir", default="output/noe")
    p.add_argument("--dkm-parquet", default="output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet")
    p.add_argument("--address-dir", default="data/adressregister")
    p.add_argument("--cache-dir", default="output/abschichtung_widmung_v2/_cache")
    p.add_argument("--out-dir", default="output/analysis/streusiedlung_sweep")
    p.add_argument("--bbox", default=None)
    p.add_argument("--bl", action="append", default=None)
    p.add_argument("--eps-min", type=float, default=50.0)
    p.add_argument("--max-eps", type=float, default=600.0)
    p.add_argument("--eps-step", type=float, default=25.0)
    p.add_argument("--clip-m", type=float, default=1200.0,
                   help="k-Distanzen oberhalb ignorieren (Almhütten-Ausreißer)")
    p.add_argument("--ks", default="4,8", help="k-Werte der k-Distanz-Kurven")
    p.add_argument("--thresholds", default="3,5,8", help="Adress-Schwellen T des ε-Sweeps")
    p.add_argument("--min-pts", type=int, default=5, help="minPts des DBSCAN-Vergleichs")
    return p.parse_args(argv)


def mean_footprint_diameter(geometries: np.ndarray) -> float:
    """Mittlerer Äquivalentdurchmesser der Bauflächen (für ε -> Verkettung)."""
    areas = shapely.area(geometries)
    return float(2.0 * np.sqrt(np.median(areas) / np.pi))


def kdist_analysis(points_by_set: dict[str, np.ndarray], ks: list[int],
                   clip_m: float, out_png: Path) -> pd.DataFrame:
    """k-Distanz-Kurven + Knie je (Punktmenge, k); Plot mit Knie-Markern."""
    rows = []
    fig, axes = plt.subplots(1, len(points_by_set), figsize=(6.4 * len(points_by_set), 4.6))
    axes = np.atleast_1d(axes)
    for ax, (set_name, pts) in zip(axes, points_by_set.items()):
        for k in ks:
            ranks, dists, knee = kdist_curve(pts, k, clip_m)
            if len(dists) == 0:
                continue
            knee_m = float(dists[knee])
            rows.append({"punktmenge": set_name, "k": k, "n": len(pts),
                         "knie_eps_m": round(knee_m, 0),
                         "knie_rang_anteil": round(knee / max(len(dists) - 1, 1), 3)})
            share = ranks / max(len(ranks) - 1, 1)
            ax.plot(share, dists, label=f"k={k} → Knie {knee_m:.0f} m")
            ax.axhline(knee_m, ls=":", lw=0.8, color="grey")
        ax.set_title(f"k-Distanz — {set_name} (n={len(pts):,})".replace(",", "."))
        ax.set_xlabel("Rang-Anteil der Objekte")
        ax.set_ylabel("Distanz zum k-nächsten Nachbarn [m]")
        ax.legend()
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return pd.DataFrame(rows)


def kdist_per_bundesland(points: np.ndarray, bundesland: np.ndarray,
                         k: int, clip_m: float) -> pd.DataFrame:
    rows = []
    for bl_ascii in sorted(set(bundesland)):
        pts = points[bundesland == bl_ascii]
        if len(pts) < 50:
            continue
        _, dists, knee = kdist_curve(pts, k, clip_m)
        if len(dists) == 0:
            continue
        rows.append({"bundesland": DISPLAY_BUNDESLAND.get(bl_ascii, bl_ascii),
                     "n_objekte": len(pts), "knie_eps_m": round(float(dists[knee]), 0)})
    return pd.DataFrame(rows).sort_values("knie_eps_m", ascending=False).reset_index(drop=True)


def eps_sweep(points: np.ndarray, weights: np.ndarray, eps_grid: np.ndarray,
              thresholds: list[int], out_png: Path, out_csv: Path) -> tuple[pd.DataFrame, dict]:
    """Single-Linkage-Statistik je ε + Knie der Anteilskurven."""
    with timed(f"Kantensatz bis {eps_grid[-1]:g} m"):
        edges, dists = pair_edges(points, float(eps_grid[-1]))
        print(f"[info]  {len(edges):,} Kanten unter {eps_grid[-1]:g} m", flush=True)

    rows = []
    for eps in eps_grid:
        labels = eps_components(edges, dists, len(points), float(eps))
        rows.append({"eps_m": float(eps), **cluster_stats(labels, weights, thresholds)})
    table = pd.DataFrame(rows)
    table.to_csv(out_csv, index=False)

    knees = {}
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for thr in thresholds:
        share = table[f"anteil_ge{thr}"].to_numpy()
        knee_idx = chord_knee(table["eps_m"].to_numpy(), share)
        knees[thr] = float(table["eps_m"].iloc[knee_idx])
        axes[0].plot(table["eps_m"], table[f"n_cluster_ge{thr}"], label=f"T={thr}")
        axes[1].plot(table["eps_m"], 100 * share, label=f"T={thr} → Knie {knees[thr]:.0f} m")
        axes[1].axvline(knees[thr], ls=":", lw=0.8, color="grey")
    axes[2].plot(table["eps_m"], table["max_cluster"], color="#8a4205")
    axes[0].set_title("Cluster mit ≥ T adressierten Objekten")
    axes[0].set_xlabel("ε [m]"); axes[0].set_ylabel("Anzahl Cluster")
    axes[1].set_title("erfasster Anteil adressierter Objekte")
    axes[1].set_xlabel("ε [m]"); axes[1].set_ylabel("%")
    axes[2].set_title("größter Cluster (Perkolationswarnung)")
    axes[2].set_xlabel("ε [m]"); axes[2].set_ylabel("adressierte Objekte"); axes[2].set_yscale("log")
    for ax in axes:
        ax.grid(alpha=0.3)
        if ax.get_legend_handles_labels()[0]:
            ax.legend()
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return table, {"edges": edges, "dists": dists, "knees": knees}


def dbscan_comparison(edges: np.ndarray, dists: np.ndarray, n_points: int,
                      weights: np.ndarray, eps: float, min_pts: int,
                      thresholds: list[int]) -> pd.DataFrame:
    """Single-Linkage vs. echtes DBSCAN am selben ε - was ändert das Kernpunkt-Kriterium?"""
    rows = []
    single = eps_components(edges, dists, n_points, eps)
    rows.append({"methode": f"Single-Linkage (Pipeline), ε={eps:.0f} m",
                 **cluster_stats(single, weights, thresholds)})
    db = dbscan_labels(edges, dists, n_points, eps, min_pts)
    clustered = db >= 0
    # total_weight = ALLE Objekte, damit die Anteile beider Zeilen vergleichbar
    # sind - DBSCANs Rauschpunkte fehlen sonst im Nenner.
    rows.append({"methode": f"DBSCAN minPts={min_pts}, ε={eps:.0f} m",
                 **cluster_stats(db[clustered], weights[clustered], thresholds,
                                 total_weight=float(weights.sum()))})
    return pd.DataFrame(rows)


def to_markdown(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ks = [int(v) for v in args.ks.split(",") if v.strip()]
    thresholds = [int(v) for v in args.thresholds.split(",") if v.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(args.config)
    grid = load_grid(cfg, args.bbox)
    bl_filter = set(args.bl) if args.bl else None
    _, scan, signals = load_candidate_signals(
        cfg, grid,
        zoning_dir=Path(args.zoning_dir), noe_dir=Path(args.noe_dir),
        dkm_parquet=Path(args.dkm_parquet), address_dir=Path(args.address_dir),
        cache_dir=Path(args.cache_dir), include_noe_pdf=True,
        bl_filter=bl_filter, max_chain_m=args.max_eps,
    )

    points = scan.centroids
    # Adressierte, nicht-industrielle Objekte: das ist die Dichte, um die es bei
    # "Streusiedlung" geht - Industrieareale haben Adressen, aber andere Muster.
    addressed = (signals["has_address"] & ~signals["is_industrial"]).to_numpy()
    points_adr = points[addressed]
    diameter = mean_footprint_diameter(scan.geometries)
    print(f"[info]  {len(points):,} Kandidaten, davon {len(points_adr):,} adressiert "
          f"(nicht-industriell); Median-Gebäudedurchmesser {diameter:.0f} m", flush=True)

    with timed("k-Distanz-Kurven"):
        kdist = kdist_analysis(
            {"adressierte Objekte": points_adr, "alle Kandidaten": points},
            ks, args.clip_m, out_dir / "knee_kdist.png",
        )
        print(kdist.to_string(index=False), flush=True)
        per_bl = kdist_per_bundesland(points_adr, scan.bundesland[addressed], ks[0], args.clip_m)
        print("\n" + per_bl.to_string(index=False), flush=True)

    eps_grid = np.arange(args.eps_min, args.max_eps + 1e-9, args.eps_step)
    with timed("ε-Sweep (Single-Linkage)"):
        sweep, extra = eps_sweep(
            points, addressed.astype(float), eps_grid, thresholds,
            out_dir / "knee_eps_sweep.png", out_dir / "knee_eps_sweep.csv",
        )

    mid_thr = thresholds[len(thresholds) // 2]
    eps_star = extra["knees"][mid_thr]
    chain_suggest = round((eps_star - diameter) / 25.0) * 25
    with timed("DBSCAN-Vergleich"):
        compare = dbscan_comparison(
            extra["edges"], extra["dists"], len(points), addressed.astype(float),
            eps_star, args.min_pts, thresholds,
        )
        print(compare.to_string(index=False), flush=True)

    lines = [
        "# Knie-Parametersuche Streusiedlung",
        "",
        "## k-Distanz-Knie (ε-Kandidaten, Zentroid-Distanzen)",
        "",
        to_markdown(kdist),
        "",
        "## k-Distanz-Knie je Bundesland (adressierte Objekte, k=" + str(ks[0]) + ")",
        "",
        to_markdown(per_bl),
        "",
        "## Knie der ε-Sweep-Anteilskurven",
        "",
        to_markdown(pd.DataFrame([
            {"schwelle_T": t, "knie_eps_m": e} for t, e in extra["knees"].items()
        ])),
        "",
        "## Single-Linkage vs. DBSCAN am Knie-ε",
        "",
        to_markdown(compare),
        "",
        f"**Empfehlung:** ε ≈ {eps_star:.0f} m (Zentroid) − {diameter:.0f} m Gebäudedurchmesser "
        f"→ Verkettungsdistanz ≈ **{chain_suggest:.0f} m** für den Sweep/Viewer "
        f"(`--chains ...,{chain_suggest:.0f},...`). Die Schwelle T bleibt eine "
        "Politikfrage (siehe NÖ-Validierung); die Knie zeigen nur, wo ε aufhört, "
        "Streusiedlungslücken zu schließen, und anfängt, getrennte Gebiete zu verschmelzen.",
    ]
    (out_dir / "knee_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nEmpfehlung: ε* ≈ {eps_star:.0f} m -> Verkettung ≈ {chain_suggest:.0f} m "
          f"(Median-Gebäudedurchmesser {diameter:.0f} m abgezogen)", flush=True)
    print(f"Geschrieben: {out_dir}/knee_summary.md, knee_kdist.png, knee_eps_sweep.png", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
