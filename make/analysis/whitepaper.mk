# White-Paper-Analyse: eigenstaendiges Paket unter pipeline/analysis/whitepaper/,
# das alle Zahlen, Tabellen und Abbildungen direkt aus dem TIF berechnet (kein
# Bezug zu `make analysis` / flaechenanteile oder `make bilanz`, keine Importe
# aus pipeline.* oder calc.*). Siehe
# pipeline/analysis/whitepaper/run_all.py und docs/whitepaper/tabellen/HERKUNFT.md.
#
# Eingaben sind ausschliesslich das TIF, sein Manifest und die
# Bundeslandgrenzen-Rohquelle (nur fuer Regionszuordnung/Bezugsflaeche und
# Kartenumrisse). Ueberschreibbar, z. B. fuer einen Lauf auf einem
# Backup-Stand:
#   make whitepaper WP_TIF=backup/.../abschichtung.tif \
#                   WP_MANIFEST=backup/.../abschichtung.bands.json

WP_TIF ?= out/abschichtung.tif
WP_MANIFEST ?= out/abschichtung.bands.json
WP_GRENZEN ?= data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp

.PHONY: whitepaper
whitepaper:
	$(PYTHON) -m pipeline.analysis.whitepaper.run_all \
		--tif $(WP_TIF) \
		--manifest $(WP_MANIFEST) \
		--grenzen $(WP_GRENZEN)
