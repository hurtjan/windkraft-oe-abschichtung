# HERKUNFT — White-Paper-Analyse

## Eingaben
- TIF: `out/abschichtung.tif`, sha256 `58caa8ffa69454fdc691fff96d5734f0820dfac07be11238d38330a720ee3a93`
- Manifest: `out/abschichtung.bands.json` (schema_version 2.3.0, band_schema clean-45-freileitungen-110kv-sep-2026)
- Bundeslandgrenzen (prep-Produkt, nur fuer Regionszuordnung/Bezugsflaeche und Kartenumrisse): `derived/prep/admin/bundesland_masken.parquet`

## Bundeslandgrenzen (prep-Produkt)
Bundeslandgrenzen kommen aus dem prep-Produkt `derived/prep/admin/bundesland_masken.parquet` (`pipeline/prep/admin`, dissolve nach 'BL' aus der generalisierten Verwaltungsgrenzen-Datei VGD 50, BEV, Stand 02.10.2022, 7850 Katastralgemeinde-Polygone, EPSG:31287, Spalte 'BL'). `pipeline/analysis/flaechenanteile.py:_load_regions/_make_region_raster` rasterisiert diese Maske per Zellmittelpunkt (all_touched=False). Diese Analyse liest das prep-Produkt direkt und bildet denselben Rasterisierungs-Schritt in `wp_common.py` eigenstaendig nach.

## TIF-Datum
Aus dem Manifest-Feld `generated_at` (manifest:generated_at): 2026-10-12 (stimmt mit dem Dateidatum des TIF ueberein).

## Bezugsflaeche
Summe der Bundesland-Masken (Zellmittelpunkt): 134 206 485 Zellen = 83 879,05 km². Die volle Staatsgebietsmaske (all_touched-Zustandsmaske) wird aus dem TIF berechnet, als Vereinigung von Band 30 (all_exclusions) und Band 31 (available_after_all_exclusions_raw); die Schnittmenge dieser beiden Baender ist 0 Zellen (Selbstpruefung, siehe unten). Ergebnis: 134 274 137 Zellen = 83 921,34 km².

## Aufruf
```
uv run python -m pipeline.analysis.whitepaper.run_all --tif out/abschichtung.tif --manifest out/abschichtung.bands.json --grenzen derived/prep/admin/bundesland_masken.parquet
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

## L1_landnutzung (Landnutzungs-Tabelle)

- Haupt-TIF: `out/abschichtung.tif`, sha256 `58caa8ffa69454fdc691fff96d5734f0820dfac07be11238d38330a720ee3a93`
- Analyse-Raster: `out/abschichtung_analyse.tif`, sha256 `89b89f1fb66684b5d3f4ac78022e31136f54d338837b82b5b1ee9e1ee4f02ef4`, Manifest `out/abschichtung_analyse.bands.json` (referenziert den sha256 des Haupt-TIF; Abbruch bei Abweichung)
- Baender per Name: `official_wind_zoning`, `wka_bestand_ausserhalb_zonen`, `available_cleaned_min_10ha` (Haupt-TIF); `kataster_wald`, `kataster_aecker_wiesen_weiden` (Analyse-Raster)
- Bestand = official_wind_zoning ODER wka_bestand_ausserhalb_zonen; Potentialfläche = available_cleaned_min_10ha UND NICHT Bestand
- Länderzuordnung: Zellmittelpunkt, BEV-Ländergrenzen wie oben (einzige Vektorquelle)
