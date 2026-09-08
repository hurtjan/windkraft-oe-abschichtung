"""Mindestflächen-Filter: nur Kantenkontakt verbindet (4er-Nachbarschaft).

Zwei Teilflächen, die sich nur an einer Ecke berühren, sind real über eine
0-m-Verbindung "verbunden" - keine durchgängige Fläche. Entscheidung Aug 2026,
vorher 8er-Nachbarschaft (np.ones((3,3))).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from affine import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.abschichtung_common import TARGET_CRS, min_area_filter  # noqa: E402

CELL_M = 25.0  # 1 Zelle = 625 m²; 1 ha = 16 Zellen


def _grid(cells: int = 40) -> dict:
    size = cells * CELL_M
    return {
        "shape": (cells, cells),
        "transform": Affine(CELL_M, 0.0, 500_000.0, 0.0, -CELL_M, 400_000.0 + size),
        "crs": TARGET_CRS,
        "bounds": (500_000.0, 400_000.0, 500_000.0 + size, 400_000.0 + size),
    }


def test_keeps_single_block_at_threshold():
    # Arrange - 4x4-Block = 16 Zellen = genau 1 ha
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:14, 10:14] = True

    # Act
    kept = min_area_filter(mask, _grid(), min_area_ha=1.0)

    # Assert
    assert kept.sum() == 16


def test_diagonal_corner_touch_does_not_merge():
    # Arrange - zwei 3x3-Blöcke (je 9 Zellen < 16), nur über eine Ecke verbunden:
    # zusammen 18 Zellen > Schwelle, aber ohne Kantenkontakt
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:13, 10:13] = True
    mask[13:16, 13:16] = True

    # Act
    kept = min_area_filter(mask, _grid(), min_area_ha=1.0)

    # Assert - beide einzeln unter der Schwelle, keine zählt
    assert not kept.any()


def test_edge_adjacency_does_merge():
    # Arrange - dieselben zwei 3x3-Blöcke, aber mit gemeinsamer Kante
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:13, 10:13] = True
    mask[13:16, 10:13] = True

    # Act
    kept = min_area_filter(mask, _grid(), min_area_ha=1.0)

    # Assert - verkettet 18 Zellen >= 16
    assert kept.sum() == 18


def test_does_not_mutate_input():
    # Arrange
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:12, 10:12] = True
    before = mask.copy()

    # Act
    min_area_filter(mask, _grid(), min_area_ha=1.0)

    # Assert - caller's array untouched (immutability rule)
    assert np.array_equal(mask, before)
