"""Ein Durchlauf ueber das Abschichtungs-TIF: Zellenzahlen je Bundesland/AT.

Berechnet in einem einzigen blockweisen Durchlauf ueber das TIF:
- die 18 Einzelband-Zonen (Mensch/Natur/Geografie, stufe='zone'),
- die drei Familien-Vereinigungen verkehr/luftfahrt/schutzgebiet,
- die drei Kategoriebaender (exclusion_human/_nature/_geography),
- all_exclusions, available_after_all_exclusions_raw,
  available_cleaned_min_10ha,
- kleinflaechen = raw UND NICHT cleaned,
- die 7 exklusiven Ueberschneidungsklassen von Mensch/Natur/Geografie plus
  frei,
- das amtliche Windzonenband und das WKA-ausserhalb-Zonen-Band,
- die volle Staatsgebietsmaske (all_touched) als Vereinigung von
  all_exclusions und available_after_all_exclusions_raw, mit Selbstpruefung,
  dass deren Schnittmenge leer ist (J5, siehe ``full_grid_union_counts``),
- die auf 100 m downgesampelten Arrays fuer die Kartenabbildungen.

Selbstpruefungen (siehe unten) brechen den Lauf bei Verletzung sofort mit
einer klaren Meldung ab. Ergebnisse werden in einem Temp-Verzeichnis
zwischengespeichert (niemals im Repo).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import rasterio

from . import wp_common as wc

BLOCK_ROWS = 1000  # Vielfaches von 4, Ausrichtung ab Zeile 0 wie im Referenzentwurf

CLASS_IDS = list(range(1, 8))  # 1..7 exklusive Ueberschneidungsklassen
CLASS_KEYS = [
    "nur_mensch",
    "nur_natur",
    "nur_geografie",
    "mensch_natur",
    "mensch_geografie",
    "natur_geografie",
    "alle_drei",
]


class SelfCheckError(RuntimeError):
    pass


def _family_union(bool_by_index: dict[int, np.ndarray], members: list[int]) -> np.ndarray:
    out = None
    for idx in members:
        out = bool_by_index[idx].copy() if out is None else (out | bool_by_index[idx])
    return out


def full_grid_union_counts(all_mask: np.ndarray, raw_mask: np.ndarray) -> tuple[int, int]:
    """J5: reiner Zell-Logik-Schritt (kein I/O, daher schnell testbar).

    Vereinigung und Schnittmenge der Baender ``all_exclusions`` und
    ``available_after_all_exclusions_raw`` fuer einen Block (oder das gesamte
    Raster, unbeschraenkt durch die Bundesland-Zellmittelpunkt-Maske). Die
    Vereinigung ist die volle Staatsgebietsmaske (all_touched-Zustandsmaske)
    der Pipeline; die Schnittmenge muss 0 sein (siehe Selbstpruefung in
    ``run()``). Gibt ``(union_cells, intersection_cells)`` zurueck.
    """
    union = all_mask | raw_mask
    intersection = all_mask & raw_mask
    return int(union.sum()), int(intersection.sum())


def run(
    tif_path: Path,
    manifest_path: Path,
    grenzen_path: Path,
    expected_sha256: str | None,
    cache_root: Path | None = None,
) -> Path:
    tif_path = Path(tif_path)
    manifest_path = Path(manifest_path)
    grenzen_path = Path(grenzen_path)

    print(f"[zaehlen] TIF: {tif_path}")
    tif_sha256 = wc.verify_sha256(tif_path, expected_sha256)
    print(f"[zaehlen] sha256: {tif_sha256} (match={'ok' if expected_sha256 else 'ungeprueft'})")

    manifest = wc.load_manifest(manifest_path)

    # --- Baender per Name aufloesen -----------------------------------
    idx_H = wc.band_index(manifest, "exclusion_human")
    idx_N = wc.band_index(manifest, "exclusion_nature")
    idx_G = wc.band_index(manifest, "exclusion_geography")
    idx_ALL = wc.band_index(manifest, "all_exclusions")
    idx_RAW = wc.band_index(manifest, "available_after_all_exclusions_raw")
    idx_CLEAN = wc.band_index(manifest, "available_cleaned_min_10ha")
    idx_OFFICIAL = wc.band_index(manifest, "official_wind_zoning")
    idx_WKA_OUT = wc.band_index(manifest, "wka_bestand_ausserhalb_zonen")

    zone_bands = wc.zone_bands_for_categories(manifest, {"Mensch", "Natur", "Geografie"})
    if len(zone_bands) != 18:
        raise SelfCheckError(f"Erwartet 18 Zonen-Baender (Mensch/Natur/Geografie), gefunden {len(zone_bands)}.")
    zone_band_names = [b["name"] for b in zone_bands]
    zone_band_index = {b["name"]: b["index"] for b in zone_bands}

    fam_verkehr = wc.family_member_indices(manifest, "verkehr", "Mensch")
    fam_luftfahrt = wc.family_member_indices(manifest, "luftfahrt", "Mensch")
    fam_schutzgebiet = wc.family_member_indices(manifest, "schutzgebiet", "Natur")
    print(f"[zaehlen] Familie verkehr -> Baender {fam_verkehr}")
    print(f"[zaehlen] Familie luftfahrt -> Baender {fam_luftfahrt}")
    print(f"[zaehlen] Familie schutzgebiet -> Baender {fam_schutzgebiet}")
    print(f"[zaehlen] amtliche Zonen -> Band {idx_OFFICIAL} (official_wind_zoning)")
    print(f"[zaehlen] WKA ausserhalb Zonen -> Band {idx_WKA_OUT} (wka_bestand_ausserhalb_zonen)")

    needed = sorted(set(
        [idx["index"] for idx in zone_bands]
        + fam_verkehr + fam_luftfahrt + fam_schutzgebiet
        + [idx_H, idx_N, idx_G, idx_ALL, idx_RAW, idx_CLEAN, idx_OFFICIAL, idx_WKA_OUT]
    ))
    print(f"[zaehlen] {len(needed)} Baender pro Block gelesen: {needed}")

    # --- Bundeslandgrenzen ------------------------------------------------
    regions = wc.load_bundeslaender(grenzen_path)
    state_codes = [c for c, _n, _g in regions]
    assert state_codes == wc.REGION_ORDER, f"Regionenreihenfolge unerwartet: {state_codes}"

    ds = rasterio.open(tif_path)
    height, width = ds.height, ds.width
    transform = ds.transform
    crs = str(ds.crs)
    bounds = tuple(ds.bounds)
    pixel_area_m2 = float(manifest["raster"]["pixel_size_m"]) ** 2

    # --- Item-Liste: alle einfachen (Band-/Familien-/Kategorie-/Ergebnis-)
    # Groessen, deren boolesche Maske pro Block direkt oder als Vereinigung
    # verfuegbar ist.
    simple_items: list[tuple[str, str]] = []  # (key, kind)
    for name in zone_band_names:
        simple_items.append((name, "band"))
    simple_items += [
        ("verkehr", "family"),
        ("luftfahrt", "family"),
        ("schutzgebiet", "family"),
        ("exclusion_human", "category"),
        ("exclusion_nature", "category"),
        ("exclusion_geography", "category"),
        ("all_exclusions", "result"),
        ("available_after_all_exclusions_raw", "result"),
        ("available_cleaned_min_10ha", "result"),
        ("kleinflaechen", "derived"),
        ("official_wind_zoning", "reference"),
        ("wka_bestand_ausserhalb_zonen", "reference"),
    ]
    all_item_keys = [k for k, _ in simple_items] + CLASS_KEYS + ["frei"]

    n_codes = len(state_codes) + 1  # 0 = ausserhalb jedes Bundeslands

    counters: dict[str, dict[str, int]] = {k: {c: 0 for c in state_codes} for k in all_item_keys}
    region_cells = {c: 0 for c in state_codes}

    # Selbstpruefungs-Akkumulatoren
    at_mask_cells_total = 0
    region_sum_cells_total = 0
    hng_vs_all_mismatch = 0
    frei_vs_raw_mismatch = 0
    cleaned_not_subset_of_raw = 0

    # J5: volle Staatsgebietsmaske (all_touched) = Vereinigung von
    # all_exclusions und available_after_all_exclusions_raw, ueber das ganze
    # Raster (nicht auf die Bundesland-Zellmittelpunkt-Maske beschraenkt).
    full_grid_union_cells = 0
    full_grid_intersection_cells = 0

    # --- Downsampling-Vorbereitung (100 m, 4x4-Bloecke), wie im Referenzentwurf
    width_pad = ((width + 3) // 4) * 4
    height_pad = ((height + 3) // 4) * 4
    out_h = height_pad // 4
    out_w = width_pad // 4
    pad_cols = width_pad - width

    class_ds = np.zeros((out_h, out_w), dtype=np.uint8)
    H_ds = np.zeros((out_h, out_w), dtype=bool)
    N_ds = np.zeros((out_h, out_w), dtype=bool)
    G_ds = np.zeros((out_h, out_w), dtype=bool)

    out_row_cursor = 0

    for row_off, block_h, window in wc.iter_windows(height, width, BLOCK_ROWS):
        w_transform = wc.block_transform(transform, window)
        region_raster, raster_codes = wc.make_region_raster(regions, (block_h, width), w_transform)
        region_flat = region_raster.ravel()

        stack = ds.read(indexes=needed, window=window)
        bool_by_index = {idx: (stack[pos] == 1) for pos, idx in enumerate(needed)}

        Hb = bool_by_index[idx_H]
        Nb = bool_by_index[idx_N]
        Gb = bool_by_index[idx_G]
        ALLb = bool_by_index[idx_ALL]
        RAWb = bool_by_index[idx_RAW]
        CLEANb = bool_by_index[idx_CLEAN]

        or_HNG = Hb | Nb | Gb
        frei_b = ~Hb & ~Nb & ~Gb
        klein_b = RAWb & ~CLEANb

        block_union, block_intersection = full_grid_union_counts(ALLb, RAWb)
        full_grid_union_cells += block_union
        full_grid_intersection_cells += block_intersection

        block_masks: dict[str, np.ndarray] = {}
        for name in zone_band_names:
            block_masks[name] = bool_by_index[zone_band_index[name]]
        block_masks["verkehr"] = _family_union(bool_by_index, fam_verkehr)
        block_masks["luftfahrt"] = _family_union(bool_by_index, fam_luftfahrt)
        block_masks["schutzgebiet"] = _family_union(bool_by_index, fam_schutzgebiet)
        block_masks["exclusion_human"] = Hb
        block_masks["exclusion_nature"] = Nb
        block_masks["exclusion_geography"] = Gb
        block_masks["all_exclusions"] = ALLb
        block_masks["available_after_all_exclusions_raw"] = RAWb
        block_masks["available_cleaned_min_10ha"] = CLEANb
        block_masks["kleinflaechen"] = klein_b
        block_masks["official_wind_zoning"] = bool_by_index[idx_OFFICIAL]
        block_masks["wka_bestand_ausserhalb_zonen"] = bool_by_index[idx_WKA_OUT]

        block_masks["nur_mensch"] = Hb & ~Nb & ~Gb
        block_masks["nur_natur"] = ~Hb & Nb & ~Gb
        block_masks["nur_geografie"] = ~Hb & ~Nb & Gb
        block_masks["mensch_natur"] = Hb & Nb & ~Gb
        block_masks["mensch_geografie"] = Hb & ~Nb & Gb
        block_masks["natur_geografie"] = ~Hb & Nb & Gb
        block_masks["alle_drei"] = Hb & Nb & Gb
        block_masks["frei"] = frei_b

        denom_counts = np.bincount(region_flat, minlength=n_codes)
        for code_int in range(1, n_codes):
            region_code = raster_codes.get(code_int, (None, None))[0]
            if region_code is not None:
                region_cells[region_code] += int(denom_counts[code_int])

        for key in all_item_keys:
            mask = block_masks[key]
            counts = np.bincount(region_flat, weights=mask.ravel(), minlength=n_codes)
            for code_int in range(1, n_codes):
                region_code = raster_codes.get(code_int, (None, None))[0]
                if region_code is not None:
                    counters[key][region_code] += int(round(counts[code_int]))

        inside = region_raster != 0
        at_mask_cells_total += int(inside.sum())
        region_sum_cells_total += int(denom_counts[1:].sum())

        hng_vs_all_mismatch += int(np.logical_and(inside, or_HNG != ALLb).sum())
        frei_vs_raw_mismatch += int(np.logical_and(inside, frei_b != RAWb).sum())
        cleaned_not_subset_of_raw += int((CLEANb & ~RAWb).sum())

        # --- Downsampling dieses Blocks auf 100 m -------------------------
        cls = np.zeros((block_h, width), dtype=np.uint8)
        cls[inside & block_masks["nur_mensch"]] = 1
        cls[inside & block_masks["nur_natur"]] = 2
        cls[inside & block_masks["nur_geografie"]] = 3
        cls[inside & block_masks["mensch_natur"]] = 4
        cls[inside & block_masks["mensch_geografie"]] = 5
        cls[inside & block_masks["natur_geografie"]] = 6
        cls[inside & block_masks["alle_drei"]] = 7
        cls[inside & klein_b] = 8
        cls[inside & CLEANb] = 9

        rows_needed = ((block_h + 3) // 4) * 4
        pad_rows = rows_needed - block_h

        def pad_block(arr, fill):
            if pad_rows or pad_cols:
                return np.pad(arr, ((0, pad_rows), (0, pad_cols)), constant_values=fill)
            return arr

        cls_p = pad_block(cls, 0)
        Hb_p = pad_block(Hb, False)
        Nb_p = pad_block(Nb, False)
        Gb_p = pad_block(Gb, False)

        ph, pw = cls_p.shape
        bh, bw = ph // 4, pw // 4

        def block_view(arr):
            return arr.reshape(bh, 4, bw, 4).transpose(0, 2, 1, 3).reshape(bh, bw, 16)

        cls_v = block_view(cls_p)
        counts10 = np.zeros((bh, bw, 10), dtype=np.uint8)
        for c in range(10):
            counts10[..., c] = (cls_v == c).sum(axis=-1)
        inside_count = 16 - counts10[..., 0]
        majority = 1 + np.argmax(counts10[..., 1:10], axis=-1)
        result = np.where(inside_count == 0, 0, majority).astype(np.uint8)
        eign_win = counts10[..., 9] >= 4
        result = np.where(eign_win, 9, result).astype(np.uint8)

        Hb_v = block_view(Hb_p.astype(np.uint8)).sum(axis=-1)
        Nb_v = block_view(Nb_p.astype(np.uint8)).sum(axis=-1)
        Gb_v = block_view(Gb_p.astype(np.uint8)).sum(axis=-1)

        class_ds[out_row_cursor: out_row_cursor + bh, :] = result
        H_ds[out_row_cursor: out_row_cursor + bh, :] = Hb_v >= 8
        N_ds[out_row_cursor: out_row_cursor + bh, :] = Nb_v >= 8
        G_ds[out_row_cursor: out_row_cursor + bh, :] = Gb_v >= 8

        out_row_cursor += bh
        print(f"[zaehlen] Zeilen {row_off}..{row_off + block_h} von {height} verarbeitet", flush=True)

    ds.close()
    assert out_row_cursor == out_h

    at_cells = sum(region_cells.values())
    at_counts = {k: sum(counters[k].values()) for k in all_item_keys}

    # --- Selbstpruefungen ---------------------------------------------------
    checks: dict[str, object] = {}

    checks["AT_cells"] = at_cells
    checks["AT_mask_cells_total"] = at_mask_cells_total
    checks["region_sum_cells_total"] = region_sum_cells_total
    if at_mask_cells_total != region_sum_cells_total or at_cells != at_mask_cells_total:
        raise SelfCheckError(
            f"AT-Zellensumme inkonsistent: at_cells={at_cells}, "
            f"at_mask_cells_total={at_mask_cells_total}, region_sum_cells_total={region_sum_cells_total}"
        )

    sum7_plus_frei_ok = {}
    for code in state_codes:
        total = sum(counters[k][code] for k in CLASS_KEYS) + counters["frei"][code]
        ok = total == region_cells[code]
        sum7_plus_frei_ok[code] = ok
        if not ok:
            raise SelfCheckError(
                f"Selbstpruefung fehlgeschlagen (7 Klassen + frei != Zellen): "
                f"Region {code}: {total} != {region_cells[code]}"
            )
    at_total_check = sum(at_counts[k] for k in CLASS_KEYS) + at_counts["frei"]
    if at_total_check != at_cells:
        raise SelfCheckError(f"AT: 7 Klassen + frei ({at_total_check}) != AT-Zellen ({at_cells})")
    checks["sum7_plus_frei_equals_region_cells"] = True

    if hng_vs_all_mismatch != 0:
        raise SelfCheckError(
            f"Selbstpruefung fehlgeschlagen: H|N|G != all_exclusions in {hng_vs_all_mismatch} Zellen (innerhalb AT)."
        )
    checks["hng_union_equals_all_exclusions_mismatches"] = hng_vs_all_mismatch

    if frei_vs_raw_mismatch != 0:
        raise SelfCheckError(
            f"Selbstpruefung fehlgeschlagen: frei != available_after_all_exclusions_raw "
            f"in {frei_vs_raw_mismatch} Zellen (innerhalb AT)."
        )
    checks["frei_equals_raw_mismatches"] = frei_vs_raw_mismatch

    if cleaned_not_subset_of_raw != 0:
        raise SelfCheckError(
            f"Selbstpruefung fehlgeschlagen: available_cleaned_min_10ha ist keine Teilmenge "
            f"von available_after_all_exclusions_raw ({cleaned_not_subset_of_raw} Zellen)."
        )
    checks["cleaned_subset_of_raw_violations"] = cleaned_not_subset_of_raw

    region_sum_ok = {}
    for k in all_item_keys:
        s = sum(counters[k].values())
        region_sum_ok[k] = (s == at_counts[k])
        if s != at_counts[k]:
            raise SelfCheckError(f"9 Regionen summieren nicht zu AT fuer {k}: {s} != {at_counts[k]}")
    checks["regions_sum_to_AT_all_items"] = True

    # J5: volle Staatsgebietsmaske (Vereinigung all_exclusions ∪
    # available_after_all_exclusions_raw) - Schnittmenge muss leer sein.
    if full_grid_intersection_cells != 0:
        raise SelfCheckError(
            f"Selbstpruefung fehlgeschlagen: all_exclusions (Band {idx_ALL}) und "
            f"available_after_all_exclusions_raw (Band {idx_RAW}) ueberschneiden sich in "
            f"{full_grid_intersection_cells} Zellen (erwartet: disjunkt)."
        )
    checks["full_grid_union_intersection_cells"] = full_grid_intersection_cells
    checks["full_grid_union_cells"] = full_grid_union_cells

    print("[zaehlen] Alle Selbstpruefungen bestanden.")

    tif_sha256_confirmed = tif_sha256
    provenance = wc.build_provenance(
        tif_path=tif_path,
        manifest=manifest,
        grenzen_path=grenzen_path,
        reference_area_cells=at_cells,
        pixel_area_m2=pixel_area_m2,
        tif_sha256=tif_sha256_confirmed,
    )

    if cache_root is None:
        cache_dir = Path(tempfile.mkdtemp(prefix="wp_whitepaper_analyse_"))
    else:
        cache_dir = Path(tempfile.mkdtemp(prefix="wp_whitepaper_analyse_", dir=str(cache_root)))

    np.savez_compressed(
        cache_dir / "downsampled.npz",
        class_ds=class_ds,
        H_ds=H_ds,
        N_ds=N_ds,
        G_ds=G_ds,
        out_h=out_h,
        out_w=out_w,
        bounds=np.array(bounds),
    )

    counts_out = {
        "counters": counters,
        "region_cells": region_cells,
        "at_cells": at_cells,
        "at_counts": at_counts,
        "class_keys": CLASS_KEYS,
        "state_codes": state_codes,
        "pixel_area_m2": pixel_area_m2,
        "crs": crs,
        "idx_official_wind_zoning": idx_OFFICIAL,
        "idx_wka_bestand_ausserhalb_zonen": idx_WKA_OUT,
        "full_grid_union_cells": full_grid_union_cells,
        "zone_band_names": zone_band_names,
        "fam_members": {
            "verkehr": fam_verkehr,
            "luftfahrt": fam_luftfahrt,
            "schutzgebiet": fam_schutzgebiet,
        },
    }
    (cache_dir / "counts.json").write_text(json.dumps(counts_out, ensure_ascii=False, indent=1), encoding="utf-8")
    (cache_dir / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding="utf-8")
    (cache_dir / "provenance.json").write_text(
        json.dumps(provenance.as_dict(), ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"[zaehlen] Cache geschrieben nach {cache_dir}")
    return cache_dir


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--grenzen", required=True, type=Path)
    ap.add_argument("--sha256", default=None)
    args = ap.parse_args()
    out = run(args.tif, args.manifest, args.grenzen, args.sha256)
    print(out)
