# Nicht Teil der v2-Kette: dieses Modul wird von keinem Kettenschritt und von
# keinem Makefile-Target importiert. Es liegt hier als Herleitung der fest
# verdrahteten Konstante HIG_CHAIN_M = 200 (Meter Verkettungsdistanz) und wird
# nur von docs/analysis/streusiedlung_knee.py benutzt.
# Verwendet wird die Konstante heute in:
#   windkraft/calc/abschichtung_common.py:159  (Definition HIG_CHAIN_M = 200.0)
#   scripts/widmung_v2/02_build_hig_sources.py:205  (Default fuer --chain-m)
#   scripts/widmung_v2/04_create_distance_zones.py:477  (GeoTIFF-Metadatum)
"""DBSCAN-artige Parametersuche für die Streusiedlungs-Erkennung.

Die Verkettungsdistanz der Hüllenbildung ist DBSCANs ε, die Adress-Schwelle
verwandt mit minPts - mit einem Unterschied: die Pipeline verkettet per
Single-Linkage (morphologisches Closing) und schwellt auf *Cluster*-Ebene,
DBSCANs minPts ist ein *lokales* Dichtekriterium je Punkt. Dieses Modul
liefert beides:

* ``knn_distances`` + ``chord_knee``  - das Lehrbuch-Verfahren zur ε-Wahl
  (k-Distanz-Kurve, Knie = Punkt mit maximalem Abstand zur Sehne).
* ``pair_edges`` + ``eps_components`` - Single-Linkage-Cluster für ein ε-Raster
  aus EINEM vorberechneten Kantensatz (exakt das Verkettungsverhalten der
  Pipeline, nur auf Punktebene statt auf dem 25-m-Raster).
* ``dbscan_labels``                   - echtes DBSCAN (Kernpunkte, Randpunkte,
  Rauschen), um zu messen, was das lokale Dichtekriterium gegenüber
  Single-Linkage ändern würde (dünne Brücken zwischen Gebieten).

Alles scipy-basiert (cKDTree + csgraph); kein scikit-learn nötig.
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def chord_knee(x: np.ndarray, y: np.ndarray) -> int:
    """Index des Knies einer monotonen Kurve: maximaler Normalabstand zur Sehne.

    x und y werden auf [0, 1] normiert, damit das Ergebnis nicht von den
    Einheiten abhängt (Rang vs. Meter).
    """
    if len(x) < 3:
        return 0
    xn = (x - x[0]) / max(x[-1] - x[0], 1e-12)
    yn = (y - y[0]) / max(abs(y[-1] - y[0]), 1e-12) * np.sign(y[-1] - y[0] or 1.0)
    # Abstand jedes Punkts zur Geraden durch (0,0)-(1,1): |yn - xn| / sqrt(2)
    return int(np.argmax(np.abs(yn - xn)))


def knn_distances(points: np.ndarray, k: int) -> np.ndarray:
    """Distanz jedes Punkts zu seinem k-nächsten Nachbarn (ohne sich selbst)."""
    if len(points) <= k:
        return np.zeros(0)
    tree = cKDTree(points)
    dist, _ = tree.query(points, k=k + 1)
    return dist[:, k]


def kdist_curve(points: np.ndarray, k: int, clip_m: float) -> tuple[np.ndarray, np.ndarray, int]:
    """Sortierte k-Distanz-Kurve (aufsteigend, auf clip_m gekappt) + Knie-Index.

    Gekappt, weil abgelegene Almhütten km-weite Nachbardistanzen haben und die
    Sehne sonst von Ausreißern dominiert würde.
    """
    dists = np.sort(knn_distances(points, k))
    dists = dists[dists <= clip_m]
    ranks = np.arange(len(dists), dtype=float)
    knee = chord_knee(ranks, dists)
    return ranks, dists, knee


def pair_edges(points: np.ndarray, max_eps: float) -> tuple[np.ndarray, np.ndarray]:
    """Alle Punktpaare mit Abstand <= max_eps: (Kanten (M,2), Distanzen (M,))."""
    tree = cKDTree(points)
    pairs = tree.query_pairs(r=float(max_eps), output_type="ndarray")
    if len(pairs) == 0:
        return pairs.reshape(0, 2), np.zeros(0)
    delta = points[pairs[:, 0]] - points[pairs[:, 1]]
    return pairs, np.hypot(delta[:, 0], delta[:, 1])


def eps_components(edges: np.ndarray, dists: np.ndarray, n_points: int, eps: float) -> np.ndarray:
    """Single-Linkage-Clusterlabels für ein ε (Teilmenge des Kantensatzes)."""
    keep = dists <= eps
    if not keep.any():
        return np.arange(n_points)
    sub = edges[keep]
    graph = coo_matrix(
        (np.ones(len(sub), dtype=np.int8), (sub[:, 0], sub[:, 1])),
        shape=(n_points, n_points),
    )
    _, labels = connected_components(graph, directed=False)
    return labels


def cluster_stats(labels: np.ndarray, weights: np.ndarray, thresholds: list[int],
                  total_weight: float | None = None) -> dict:
    """Kennzahlen je Adress-Schwelle: Clusterzahl, erfasster Gewichtsanteil, Maximum.

    ``total_weight`` erlaubt einen abweichenden Anteils-Nenner - nötig, wenn
    ``labels``/``weights`` schon gefiltert sind (DBSCAN ohne Rauschpunkte),
    der Anteil aber auf ALLE Objekte bezogen sein soll.
    """
    weighted = np.bincount(labels, weights=weights)
    total = float(weights.sum()) if total_weight is None else float(total_weight)
    out = {"max_cluster": int(weighted.max()) if len(weighted) else 0}
    for thr in thresholds:
        passing = weighted >= thr
        out[f"n_cluster_ge{thr}"] = int(passing.sum())
        out[f"anteil_ge{thr}"] = round(float(weighted[passing].sum()) / max(total, 1.0), 4)
    return out


def dbscan_labels(edges: np.ndarray, dists: np.ndarray, n_points: int,
                  eps: float, min_pts: int) -> np.ndarray:
    """DBSCAN über den vorberechneten Kantensatz. -1 = Rauschen.

    minPts zählt wie bei sklearn den Punkt selbst mit. Randpunkte erhalten das
    Label eines beliebigen Kern-Nachbarn (die klassische DBSCAN-Mehrdeutigkeit).
    """
    keep = dists <= eps
    sub = edges[keep]
    degree = np.bincount(sub.ravel(), minlength=n_points)
    core = (degree + 1) >= min_pts

    labels = np.full(n_points, -1, dtype=np.int64)
    core_core = sub[core[sub[:, 0]] & core[sub[:, 1]]]
    graph = coo_matrix(
        (np.ones(len(core_core), dtype=np.int8), (core_core[:, 0], core_core[:, 1])),
        shape=(n_points, n_points),
    )
    _, comp = connected_components(graph, directed=False)
    labels[core] = comp[core]

    # Randpunkte: Nicht-Kern mit Kern-Nachbar übernimmt dessen Cluster.
    one_core = core[sub[:, 0]] ^ core[sub[:, 1]]
    border_edges = sub[one_core]
    core_first = core[border_edges[:, 0]]
    border = np.where(core_first, border_edges[:, 1], border_edges[:, 0])
    anchor = np.where(core_first, border_edges[:, 0], border_edges[:, 1])
    labels[border] = labels[anchor]
    return labels
