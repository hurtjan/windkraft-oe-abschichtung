# make/export/wka_bestand.mk — Paket W7.1, Bahn 3 (docs/rewrite/PLAN.md)
#
# Siehe make/export/README.md für die Konvention (export-<domäne>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile - keine gemeinsame Änderung an einer Stelle nötig).
#
# pipeline/export/wka_bestand.py schreibt out/wka_bestand_punkte.geojson
# (alle OSM-Windkraftanlagen Österreichs, EPSG:31287, CRS-Member
# ausdrücklich gesetzt, Properties laut schnittstelle-manifest-2.2.md §3).
# Braucht derived/prep/osm/b_layers/windpower.parquet (W1.P5) und
# derived/layers/official_wind_zoning.tif (W2.4/Bahn 1).

.PHONY: export-wka_bestand
export-wka_bestand:
	$(PYTHON) -m pipeline.export.wka_bestand
