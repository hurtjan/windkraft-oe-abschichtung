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
WP_GRENZEN ?= derived/prep/admin/bundesland_masken.parquet

.PHONY: whitepaper
whitepaper:
	$(PYTHON) -m pipeline.analysis.whitepaper.run_all \
		--tif $(WP_TIF) \
		--manifest $(WP_MANIFEST) \
		--grenzen $(WP_GRENZEN)

# Abbildungen als Assets des festen Releases `abbildungen-latest` veroeffentlichen.
# Standard = Trockenlauf; echt nur mit `make abb-publish CONFIRM=1`. Braucht `gh`.
.PHONY: abb-publish
abb-publish:
	$(PYTHON) -m pipeline.analysis.whitepaper.abb_publish $(if $(CONFIRM),--confirm)
