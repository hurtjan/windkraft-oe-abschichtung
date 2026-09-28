# Optionale Analyse vorhandener Checkpoint-Layer, Stil wie
# make/analysis/flaechenanteile.mk. Dieses Ziel ist Teil von `make analysis`,
# aber nicht von `make all` oder `make export`.
#
# Der Hauptname des Ziels ist bewusst `bilanz` (nicht `analysis-bilanz` oder
# `analysis-flaechenbilanz`) - `analysis-flaechenbilanz` existiert zusaetzlich
# nur als Alias, weil das Haupt-Makefile ANALYSIS_TARGETS automatisch aus den
# Dateinamen unter make/analysis/*.mk ableitet
# (`$(addprefix analysis-,$(basename $(notdir $(wildcard make/analysis/*.mk))))`)
# und `make analysis` sonst auf ein fehlendes `analysis-flaechenbilanz`-Ziel
# liefe.
.PHONY: bilanz analysis-flaechenbilanz
analysis-flaechenbilanz: bilanz
bilanz:
	$(PYTHON) -m pipeline.analysis.flaechenbilanz \
		--tif out/abschichtung.tif \
		--bands-json out/abschichtung.bands.json \
		--wka out/wka_bestand_punkte.geojson \
		--out docs/flaechenbilanz.tsv
