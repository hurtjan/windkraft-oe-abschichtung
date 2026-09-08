# make/export/gemeinden.mk — Paket W4.2 (docs/rewrite/PLAN.md §7)
# (bis W6.2: make/verify/gemeinden.mk)
#
# Siehe make/export/README.md für die Konvention (export-<domäne>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile - keine gemeinsame Änderung an einer Stelle nötig).
#
# pipeline/export/gemeinden.py schreibt out/gemeinden.geojson (2093
# Gemeinden, EPSG:31287, CRS-Member ausdrücklich gesetzt) und weist danach
# die Deckungsabweichung gegen out/abschichtung.tif aus - siehe dessen
# Moduldocstring für Herleitung und Schwellwert. Exit-Code 1, wenn die
# Abweichung über dem selbst hergeleiteten Schwellwert liegt oder die
# Gemeinden-/Bundesländerzahl nicht stimmt (2093 bzw. 9) - kein stiller
# Fehlschlag.

.PHONY: export-gemeinden
export-gemeinden:
	$(PYTHON) -m pipeline.export.gemeinden
