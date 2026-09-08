# Paket W4.1 (docs/rewrite/PLAN.md §7) - Dashboard: Prüfbericht aus dem
# Band-Manifest. Siehe make/export/README.md für die Konvention
# (Ziel-Name export-<domäne>, eigene Datei je Export-Paket). Bis W6.2 hiess
# dieses Verzeichnis make/verify/ und das Ziel verify-dashboard.

.PHONY: export-dashboard
export-dashboard:
	uv run python -m pipeline.export.dashboard
