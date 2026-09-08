# Paket W3.2 (docs/rewrite/PLAN.md §7) - Validierung: vergleicht ein
# finalisiertes TIF bandweise gegen run1 und schreibt
# docs/rewrite/abweichungen.tsv nach der Ampel aus §6. Siehe
# make/validate/README.md für die Konvention.
#
#   make validate PAKET=W3.1
#
# PAKET ist Pflicht - ohne Zuordnung landet die Zeile im Register keinem
# Arbeitspaket zu, und genau das soll §6 verhindern.

.PHONY: validate
validate:
	@if [ -z "$(PAKET)" ]; then \
		echo "Nutzung: make validate PAKET=<paket>  (z.B. PAKET=W3.1)"; \
		exit 1; \
	fi
	uv run python -m pipeline.validate --paket "$(PAKET)"
