"""Gauß-verschmierte Eignungsflächen als Unsicherheitsbänder (0-100).

`uncertainty_blur` verschmiert die binäre Eignungsmaske mit einem Gauß-Kern
(Sigma in Metern). Der Wert einer Zelle ist der gewichtete Eignungsanteil der
Umgebung: 100 tief in einer großen Zone, ~50 an der Kante, 0 im Fernfeld.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from affine import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.abschichtung_common import TARGET_CRS, uncertainty_blur  # noqa: E402

CELL_M = 25.0


def _grid(cells: int = 120) -> dict:
    size = cells * CELL_M
    return {
        "shape": (cells, cells),
        "transform": Affine(CELL_M, 0.0, 500_000.0, 0.0, -CELL_M, 400_000.0 + size),
        "crs": TARGET_CRS,
        "bounds": (500_000.0, 400_000.0, 500_000.0 + size, 400_000.0 + size),
    }


def _block_mask(cells: int = 120, half: int = 30) -> np.ndarray:
    """Zentrierter Block (2*half)^2 Zellen in einem cells^2-Raster."""
    mask = np.zeros((cells, cells), dtype=bool)
    c = cells // 2
    mask[c - half:c + half, c - half:c + half] = True
    return mask


def test_returns_uint8_percent_range():
    # Arrange / Act
    blurred = uncertainty_blur(_block_mask(), _grid(), sigma_m=100.0)

    # Assert
    assert blurred.dtype == np.uint8
    assert blurred.min() >= 0 and blurred.max() <= 100


def test_center_of_large_zone_stays_full():
    # Arrange - Block 1.500x1.500 m, Sigma 100 m: Zentrum weit > 3 Sigma vom Rand
    blurred = uncertainty_blur(_block_mask(), _grid(), sigma_m=100.0)

    # Assert
    assert blurred[60, 60] == 100


def test_far_field_is_zero():
    blurred = uncertainty_blur(_block_mask(), _grid(), sigma_m=100.0)
    assert blurred[2, 2] == 0


def test_zone_edge_is_half():
    # Arrange - an einer geraden Kante ist der Gauß-Anteil ~50 %
    blurred = uncertainty_blur(_block_mask(), _grid(), sigma_m=100.0)

    # Assert - Kantenzelle des Blocks (Zeile 30 = erste True-Zeile)
    assert 40 <= blurred[30, 60] <= 60


def test_wider_sigma_smears_further():
    # Arrange
    narrow = uncertainty_blur(_block_mask(), _grid(), sigma_m=100.0)
    wide = uncertainty_blur(_block_mask(), _grid(), sigma_m=300.0)

    # Assert - 250 m vor der Kante (Zeile 20): breites Sigma leckt weiter hinaus
    assert wide[20, 60] > narrow[20, 60]


def test_empty_mask_stays_zero():
    blurred = uncertainty_blur(np.zeros((120, 120), dtype=bool), _grid(), sigma_m=200.0)
    assert not blurred.any()


def test_does_not_mutate_input():
    mask = _block_mask()
    before = mask.copy()
    uncertainty_blur(mask, _grid(), sigma_m=100.0)
    assert np.array_equal(mask, before)
