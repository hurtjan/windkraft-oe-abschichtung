"""prep-Grenze (CLAUDE.md): alles nach prep liest nur derived/prep, nie data/.

Statischer AST-Check (Docstrings und Kommentare zählen nicht) über die
Module nach prep; dazu Formatregeln für contract.PREP_FILES.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.contract as contract  # noqa: E402

POST_PREP = (
    sorted((ROOT / "pipeline" / "layers").glob("*.py"))
    + sorted((ROOT / "pipeline" / "export").glob("*.py"))
    + sorted((ROOT / "pipeline" / "analysis").glob("*.py"))
    + [ROOT / "pipeline" / "finalize.py", ROOT / "pipeline" / "analyse_raster.py",
       ROOT / "pipeline" / "validate.py"]
    + [ROOT / "calc" / n for n in (
        "bev_register.py", "hig_source_masks.py", "hig_detection.py",
        "streusiedlung.py", "abschichtung_common.py", "config.py")]
)
POST_PREP = [p for p in POST_PREP if p.exists()]

RAW_CFG_KEYS = {"data_dir", "output_dir", "vgd", "osm_dir", "wind_pd_150",
                "wind_pd_100", "dgm", "nsg_zip"}


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                doc_nodes.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "contract" and node.attr in {"RAW", "DATA", "LEGACY_TOT", "LEGACY_ENTFAELLT"}:
            out.append(f"{path.name}:{node.lineno} contract.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
            v = node.value
            if v.startswith("data/") or v == "data":
                out.append(f"{path.name}:{node.lineno} Pfad {v!r}")
        elif isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Constant) and sl.value in RAW_CFG_KEYS \
                    and isinstance(node.value, ast.Subscript) \
                    and isinstance(node.value.slice, ast.Constant) and node.value.slice.value == "paths":
                out.append(f"{path.name}:{node.lineno} cfg['paths'][{sl.value!r}]")
    return out


@pytest.mark.parametrize("path", POST_PREP, ids=[str(p.relative_to(ROOT)) for p in POST_PREP])
def test_post_prep_module_does_not_touch_raw(path):
    assert not _violations(path)


@pytest.mark.parametrize(
    "path",
    [p for p in POST_PREP if p.name != "analyse_raster.py"],
    ids=lambda p: str(p.relative_to(ROOT)),
)
def test_only_analyse_raster_reads_big_kataster_parquet(path):
    """Das große DKM-GeoParquet liest nach prep nur analyse_raster.py; die
    Layer-Stufe (hig) liest die kleinen streusiedlung_*-Produkte."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == "at_dkm_gst_nfl":
            raise AssertionError(f"{path.name}:{node.lineno} liest at_dkm_gst_nfl")
        if isinstance(node, ast.Name) and node.id in {"KATASTER_PARQUET", "scan_dkm_candidates"}:
            raise AssertionError(f"{path.name}:{node.lineno} nutzt {node.id}")


def test_post_prep_list_is_not_empty():
    assert len(POST_PREP) >= 15


def test_prep_is_flat_and_files_have_product_format():
    for domain, d in contract.PREP.items():
        assert isinstance(d, Path) and d.parent == contract.DERIVED_PREP
    for files in contract.PREP_FILES.values():
        for p in files.values():
            assert p.suffix in contract.PREP_PRODUCT_SUFFIXES


def test_work_is_separate_from_prep():
    for domain in contract.PREP:
        assert contract.WORK[domain] != contract.PREP[domain]
        assert contract.DERIVED_PREP not in contract.WORK[domain].parents


def test_prep_modules_write_no_vector_files_other_than_parquet():
    """prep-Module schreiben nach PREP nur Parquet (to_file nur für WORK)."""
    offenders = []
    for p in sorted((ROOT / "pipeline" / "prep").rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and node.value.endswith(".gpkg") and "PREP" in ast.unparse(node):
                offenders.append(f"{p.name}:{node.lineno}")
    assert not offenders


def test_prep_dir_on_disk_only_has_known_suffixes_if_migrated():
    prep = contract.DERIVED_PREP
    if not prep.is_dir() or any((prep / d).is_dir() and any(c.is_dir() for c in (prep / d).iterdir())
                                for d in contract.PREP if (prep / d).is_dir()):
        pytest.skip("derived/prep noch im Altlayout (Phase B steht aus)")
    allowed = set(contract.PREP_PRODUCT_SUFFIXES) | set(contract.PREP_REPORT_SUFFIXES)
    bad = [str(p) for p in prep.rglob("*") if p.is_file() and not p.name.startswith(".") and p.suffix not in allowed]
    assert not bad
