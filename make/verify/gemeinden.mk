# make/verify/gemeinden.mk — Paket W4.2 (docs/rewrite/PLAN.md §7)
#
# Siehe make/verify/README.md für die Konvention (verify-<domäne>, eigene
# Datei je Verify-Paket, gelesen per -include make/verify/*.mk im
# Haupt-Makefile - keine gemeinsame Änderung an einer Stelle nötig).
#
# pipeline/verify/gemeinden.py schreibt out/gemeinden.geojson (2093
# Gemeinden, EPSG:31287, CRS-Member ausdrücklich gesetzt) und weist danach
# die Deckungsabweichung gegen out/abschichtung.tif aus - siehe dessen
# Moduldocstring für Herleitung und Schwellwert. Exit-Code 1, wenn die
# Abweichung über dem selbst hergeleiteten Schwellwert liegt oder die
# Gemeinden-/Bundesländerzahl nicht stimmt (2093 bzw. 9) - kein stiller
# Fehlschlag.

.PHONY: verify-gemeinden
verify-gemeinden:
	$(PYTHON) -m pipeline.verify.gemeinden
