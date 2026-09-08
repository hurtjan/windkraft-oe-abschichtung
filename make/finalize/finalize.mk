# Paket W3.1 (docs/rewrite/PLAN.md §7) - Finalisierung: 38-Band-GeoTIFF plus
# Manifest aus den Checkpoint-Layern der neuen Kette (derived/layers/, siehe
# make/layers/README.md). Siehe make/finalize/README.md für die Konvention
# UND für den offenen Punkt: Makefile liest dieses Verzeichnis noch nicht
# per -include (das Paket durfte Makefile nicht anfassen) - bis ein
# spaeteres Paket diese eine Zeile nachtraegt, direkt aufrufen mit
#
#   make -f make/finalize/finalize.mk finalize
#
# oder ohne make:
#
#   uv run python -m pipeline.finalize

.PHONY: finalize
finalize:
	uv run python -m pipeline.finalize
