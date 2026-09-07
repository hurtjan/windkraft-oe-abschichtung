# Prep: Windzonen (Paket W1.P8, docs/rewrite/PLAN.md §7, §4).
# Siehe make/prep/README.md für die Konvention.

.PHONY: prep-zonen
prep-zonen:
	uv run python -m pipeline.prep.zonen
