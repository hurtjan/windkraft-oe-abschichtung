"""prep/adressen: HNR_ADR_ZUSAMMEN bleibt als String erhalten, Reihenfolge und x/y unveraendert."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.prep.adressen import build_address_frame  # noqa: E402

CSV = (
    "ADRCD;GKZ;RW;HW;EPSG;HNR_ADR_ZUSAMMEN;QUELLADRESSE\n"
    '"1";"10101";14347.76;300941.93;31256;"4";"G"\n'
    '"2";"10101";12761.00;300090.18;31256;"12a";"G"\n'
    '"3";"10101";#;#;31256;"7";"G"\n'
    '"4";"10101";12781.98;300067.18;31256;"";"P"\n'
)


def test_address_frame_traegt_hausnummer(tmp_path):
    (tmp_path / "ADRESSE.csv").write_text(CSV, encoding="utf-8-sig")
    frame = build_address_frame(tmp_path)
    assert list(frame.columns) == ["x", "y", "HNR_ADR_ZUSAMMEN"]
    assert len(frame) == 3  # Zeile ohne Koordinate entfaellt
    assert frame["HNR_ADR_ZUSAMMEN"].tolist()[:2] == ["4", "12a"]
    assert frame["HNR_ADR_ZUSAMMEN"].isna().tolist() == [False, False, True]
    assert frame["x"].notna().all() and frame["y"].notna().all()
