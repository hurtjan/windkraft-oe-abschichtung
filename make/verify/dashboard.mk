# Paket W4.1 (docs/rewrite/PLAN.md §7) - Dashboard: Prüfbericht aus dem
# Band-Manifest. Siehe make/verify/README.md für die Konvention
# (Ziel-Name verify-<domäne>, eigene Datei je Verify-Paket).

.PHONY: verify-dashboard
verify-dashboard:
	uv run python -m pipeline.verify.dashboard
