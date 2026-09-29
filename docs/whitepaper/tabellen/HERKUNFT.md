# HERKUNFT — White-Paper-Analyse

## Eingaben
- TIF: `out/abschichtung.tif`, sha256 `bd5ddacc1d231cd43d507eece4536a6cfde57e5af912bdcbeec716212878bf1c`
  - erwarteter sha256 (Auftrag): `bd5ddacc1d231cd43d507eece4536a6cfde57e5af912bdcbeec716212878bf1c`
- Manifest: `out/abschichtung.bands.json` (schema_version 2.2.1, band_schema clean-44-ohne-wichtige-objekte-aug-2026)
- Bundeslandgrenzen (gewaehlte Rohquelle, nur fuer Regionszuordnung/Bezugsflaeche und Kartenumrisse): `data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp`

## Wahl der Bundeslandgrenzen-Rohquelle
`derived/` ist waehrend dieses Laufs im Umbau (Cold-Rebuild) und wurde nicht gelesen. Stattdessen wurde die Kette bis zur Rohquelle zurueckverfolgt: `pipeline/prep/admin.py` baut `derived/prep/admin/bundesland_masken.gpkg` per `gdf.dissolve(by="BL")` aus `contract.RAW["admin"]["vgd"]` (`data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp`, 7850 Katastralgemeinde-Polygone, EPSG:31287, Spalte 'BL'). `pipeline/analysis/flaechenanteile.py:_load_regions/_make_region_raster` rasterisiert diese Maske per Zellmittelpunkt (all_touched=False). Diese Analyse liest die Rohquelle direkt (kein Import aus pipeline/*) und bildet denselben Dissolve/Rasterisierungs-Schritt in `wp_common.py` eigenstaendig nach.

## TIF-Datum
Aus dem Manifest-Feld `generated_at` (manifest:generated_at): 2026-09-28 (stimmt mit dem Dateidatum des TIF ueberein).

## Bezugsflaeche
Summe der Bundesland-Masken (Zellmittelpunkt): 134 206 485 Zellen = 83 879,05 km². Die volle Staatsgebietsmaske (all_touched-Zustandsmaske) wird aus dem TIF berechnet, als Vereinigung von Band 30 (all_exclusions) und Band 31 (available_after_all_exclusions_raw); die Schnittmenge dieser beiden Baender ist 0 Zellen (Selbstpruefung, siehe unten). Ergebnis: 134 274 137 Zellen = 83 921,34 km².

## Aufruf
```
uv run python -m pipeline.analysis.whitepaper.run_all --tif out/abschichtung.tif --manifest out/abschichtung.bands.json --grenzen data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp
```

## Selbstpruefungen (zaehlen.py)
- `AT_cells`: 134206485
- `AT_mask_cells_total`: 134206485
- `region_sum_cells_total`: 134206485
- `sum7_plus_frei_equals_region_cells`: True
- `hng_union_equals_all_exclusions_mismatches`: 0
- `frei_equals_raw_mismatches`: 0
- `cleaned_subset_of_raw_violations`: 0
- `regions_sum_to_AT_all_items`: True
- `full_grid_union_intersection_cells`: 0
- `full_grid_union_cells`: 134274137
