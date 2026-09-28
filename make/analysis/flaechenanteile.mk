# Optionale Analyse vorhandener Checkpoint-Layer. Dieses Ziel ist Teil von
# `make analysis`, aber nicht von `make all` oder `make export`.
.PHONY: analysis-flaechenanteile
analysis-flaechenanteile:
	$(PYTHON) -m pipeline.analysis.flaechenanteile
