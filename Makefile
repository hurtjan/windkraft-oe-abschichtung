PYTHON = uv run python
CONFIG = config/config.json

V2_DIR = output/abschichtung_widmung_v2
V2_TIF = $(V2_DIR)/osm_wka_distance_zones_widmung_v2.tif

.PHONY: widmung-v2 widmung-v2-zoning widmung-v2-hig widmung-v2-osm widmung-v2-tif \
        widmung-v2-validate

## Widmungs-Abschichtung v2 — die Referenzkarte
## Doku: docs/widmung_v2.md
## Die Ordner sind hier ausgeschrieben: build_official_zoning_layers.py wird von
## v1 und v2 geteilt, ein Lauf in den falschen Ordner fällt sonst nicht auf.
widmung-v2-zoning:
	$(PYTHON) scripts/widmung_v2/01_build_official_zoning_layers.py --out-dir $(V2_DIR)/zoning_vectors

widmung-v2-hig:
	$(PYTHON) scripts/widmung_v2/02_build_hig_sources.py --zoning-dir $(V2_DIR)/zoning_vectors --out-dir $(V2_DIR)

widmung-v2-osm:
	$(PYTHON) scripts/widmung_v2/03_build_osm_layers.py --layer-dir $(V2_DIR)/distance_layers

widmung-v2-tif:
	$(PYTHON) scripts/widmung_v2/04_create_distance_zones.py --layer-dir $(V2_DIR)/distance_layers --output $(V2_TIF)

widmung-v2-validate:
	$(PYTHON) scripts/widmung_v2/05_validate.py --tif $(V2_TIF)

## Volle v2-Kette inkl. Testpunkt-Prüfung (mehrstündig)
widmung-v2: widmung-v2-zoning widmung-v2-hig widmung-v2-osm widmung-v2-tif widmung-v2-validate
