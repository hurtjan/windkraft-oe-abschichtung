PYTHON = uv run python
CONFIG = config.json

V2_DIR = output/abschichtung_widmung_v2
V2_TIF = $(V2_DIR)/osm_wka_distance_zones_widmung_v2.tif

.PHONY: widmung-v2 widmung-v2-zoning widmung-v2-hig widmung-v2-osm widmung-v2-tif \
        widmung-v2-validate check-hardlinks check-raw-only check-guards prep all test worktree
.PHONY: layers
.PHONY: verify

# Ohne dieses .DEFAULT_GOAL würde make(1) das erste im File stehende Ziel
# nehmen - das ist widmung-v2-zoning (nur Stufe 1 von 5), nicht die volle
# Kette. Siehe docs/rewrite/PLAN.md §7, Paket W0.3: "make ohne Argument
# tatsächlich das Standardziel trifft und nicht zufällig das erste im
# Makefile". widmung-v2 bleibt dabei unverändert - Standardziel wird nur
# umgehängt, nicht neu gebaut.
.DEFAULT_GOAL := widmung-v2

## Widmungs-Abschichtung v2 — die Referenzkarte
## Doku: docs/widmung_v2.md
## Die Ordner sind hier ausgeschrieben: build_official_zoning_layers.py wird von
## v1 und v2 geteilt, ein Lauf in den falschen Ordner fällt sonst nicht auf.
widmung-v2-zoning:
	$(PYTHON) scripts/widmung_v2/01_build_official_zoning_layers.py --out-dir $(V2_DIR)/zoning_vectors

widmung-v2-hig:
	$(PYTHON) scripts/widmung_v2/02_build_hig_sources.py --zoning-dir $(V2_DIR)/zoning_vectors --out-dir $(V2_DIR)

widmung-v2-osm:
	$(PYTHON) scripts/widmung_v2/03_build_osm_layers.py --layer-dir $(V2_DIR)/distance_layers

widmung-v2-tif:
	$(PYTHON) scripts/widmung_v2/04_create_distance_zones.py --layer-dir $(V2_DIR)/distance_layers --output $(V2_TIF)

widmung-v2-validate:
	$(PYTHON) scripts/widmung_v2/05_validate.py --tif $(V2_TIF)

## Volle v2-Kette inkl. Testpunkt-Prüfung (mehrstündig)
widmung-v2: widmung-v2-zoning widmung-v2-hig widmung-v2-osm widmung-v2-tif widmung-v2-validate

## Prüft mechanisch, dass jede Datei unter data/ Link-Count 1 hat und keine
## Ausgabe unter output/ einer ist (siehe tools/check_hardlink_safety.py,
## Regel A/B - seit W1.3 ist Regel B eine echte Invariante, keine
## deklarierte Liste mehr). Nach jedem Hinzufügen neuer Daten laufen lassen
## — schnell, ohne Abhängigkeiten.
check-hardlinks:
	$(PYTHON) tools/check_hardlink_safety.py

## Prüft statisch (per AST, kein Lauf nötig), dass kein Code nach data/
## schreibt - data/ wird nur gelesen (siehe tools/check_raw_only.py für den
## Umfang und die dort dokumentierten bekannten Lücken). Ergänzt
## check-hardlinks: der eine prüft eine Tatsache am Dateisystem, der andere
## den Code, der sie herbeiführen könnte.
check-raw-only:
	$(PYTHON) tools/check_raw_only.py

## Beide Rohdaten-Wächter zusammen.
check-guards: check-hardlinks check-raw-only

## --- Neues Gerüst (docs/rewrite/PLAN.md §3, §7 Paket W0.3) ---------------
## Fünf-Stufen-Modell: Roh -> Prep -> Layer -> Finalize -> verify. `make`
## (Standard, siehe .DEFAULT_GOAL oben) bleibt weiterhin `widmung-v2`, die
## alte Kette (scripts/widmung_v2/01…05_*.py) - unverändert seit W0.3.
## `all` ist seit W5.P0 (docs/rewrite/PLAN.md §13.10, Regel 9) die neue
## Kette selbst: prep -> layers -> finalize -> verify, siehe deren
## Definition weiter unten. Die beiden Ziele sind seither verschieden:
## `make` (ohne Argument) lässt weiterhin nur die alte Kette laufen,
## `make all` nur die neue - keines ruft mehr das andere auf.

## Vorpaket W1.P0 (docs/rewrite/PLAN.md §13.4): statt dass jedes der neun
## parallelen Prep-Pakete (W1.P1-W1.P9) ein eigenes Ziel HIER anhängt - ein
## garantierter neunfacher Konflikt an derselben Stelle -, bekommt jedes
## Paket seine eigene Datei make/prep/<domäne>.mk mit dem Ziel
## `prep-<domäne>`. Siehe make/prep/README.md für die Konvention. Das
## führende "-" lässt make weiterlaufen, solange noch keine einzige Datei
## existiert (kein Fehler, kein Abbruch).
-include make/prep/*.mk

# Namen aller so eingelesenen Ziele, aus den Dateinamen abgeleitet -
# make/prep/admin.mk ergibt prep-admin. Leer, solange kein make/prep/*.mk
# existiert.
PREP_TARGETS := $(addprefix prep-,$(basename $(notdir $(wildcard make/prep/*.mk))))
.PHONY: $(PREP_TARGETS)

## Ruft alle neun (bzw. die bereits vorhandenen) prep-<domäne>-Ziele auf.
## Bewusst kein stiller Erfolg und kein Fehler, solange noch keines
## existiert - nur die Auskunft, dass hier noch nichts läuft. Rückgabewert
## in jedem Fall 0.
prep: $(PREP_TARGETS)
ifeq ($(strip $(PREP_TARGETS)),)
	@echo "prep: noch keine Prep-Pakete vorhanden - die entstehen erst in Welle 1 (docs/rewrite/PLAN.md §7, W1.P1-W1.P9)."
endif

## Vorpaket W2.P0 (docs/rewrite/PLAN.md §13.8): dasselbe Muster wie oben bei
## Prep, diesmal für die drei parallelen Layer-Pakete (W2.1, W2.3, W2.4).
## Jedes bekommt seine eigene Datei make/layers/<domäne>.mk mit dem Ziel
## `layer-<domäne>`. Siehe make/layers/README.md für die Konvention. Das
## führende "-" lässt make weiterlaufen, solange noch keine einzige Datei
## existiert (kein Fehler, kein Abbruch).
-include make/layers/*.mk

# Namen aller so eingelesenen Ziele, aus den Dateinamen abgeleitet -
# make/layers/hig.mk ergibt layer-hig. Leer, solange kein make/layers/*.mk
# existiert.
LAYER_TARGETS := $(addprefix layer-,$(basename $(notdir $(wildcard make/layers/*.mk))))
.PHONY: $(LAYER_TARGETS)

## Ruft alle drei (bzw. die bereits vorhandenen) layer-<domäne>-Ziele auf.
## Bewusst kein stiller Erfolg und kein Fehler, solange noch keines
## existiert - nur die Auskunft, dass hier noch nichts läuft. Rückgabewert
## in jedem Fall 0.
layers: $(LAYER_TARGETS)
ifeq ($(strip $(LAYER_TARGETS)),)
	@echo "layers: noch keine Layer-Pakete vorhanden - die entstehen erst in Welle 2 (docs/rewrite/PLAN.md §7, W2.1/W2.3/W2.4)."
endif

## Vorpaket W3.1 (docs/rewrite/PLAN.md §7, siehe make/finalize/README.md):
## die Finalisierungs-Stufe (33 Checkpoints -> 38-Band-GeoTIFF + Manifest)
## bekommt ihre eigene Datei make/finalize/finalize.mk mit dem Ziel
## `finalize`. Anders als bei prep/layers gibt es hier nur eine Domäne,
## also kein <domäne>-Ableitungsmuster und keine eigene TARGETS-Liste -
## `finalize.mk` deklariert `.PHONY: finalize` und die Regel selbst. Das
## führende "-" lässt make weiterlaufen, solange die Datei fehlt (kein
## Fehler, kein Abbruch).
-include make/finalize/*.mk

## Paket W3.2 (docs/rewrite/PLAN.md §7, siehe make/validate/README.md): die
## Validierungs-Stufe (finalisiertes TIF bandweise gegen run1, Ampel aus §6)
## bekommt ihre eigene Datei make/validate/validate.mk mit dem Ziel
## `validate`. Dasselbe Muster wie bei make/finalize/ - nur eine Domäne,
## kein <domäne>-Ableitungsmuster. Anders als bei W3.1 durfte dieses Paket
## Makefile anfassen (Regel 9, docs/rewrite/PLAN.md §13.10) und trägt bei
## derselben Gelegenheit auch die zuvor fehlende finalize-Zeile (Punkt 36)
## nach, statt dieselbe Lücke ein zweites Mal offen zu lassen.
-include make/validate/*.mk

## Vorpaket W4.P0 (docs/rewrite/PLAN.md §13.10, Regel 9): dasselbe Muster
## wie oben bei Prep und Layers, diesmal für die zwei parallelen
## Verify-Pakete (W4.1 Dashboard, W4.2 Gemeindegrenzen-Export). Jedes
## bekommt seine eigene Datei make/verify/<domäne>.mk mit dem Ziel
## `verify-<domäne>`. Siehe make/verify/README.md für die Konvention. Das
## führende "-" lässt make weiterlaufen, solange noch keine einzige Datei
## existiert (kein Fehler, kein Abbruch).
-include make/verify/*.mk

# Namen aller so eingelesenen Ziele, aus den Dateinamen abgeleitet -
# make/verify/dashboard.mk ergibt verify-dashboard. Leer, solange kein
# make/verify/*.mk existiert.
VERIFY_TARGETS := $(addprefix verify-,$(basename $(notdir $(wildcard make/verify/*.mk))))
.PHONY: $(VERIFY_TARGETS)

## Ruft alle zwei (bzw. die bereits vorhandenen) verify-<domäne>-Ziele auf.
## Bewusst kein stiller Erfolg und kein Fehler, solange noch keines
## existiert - nur die Auskunft, dass hier noch nichts läuft. Rückgabewert
## in jedem Fall 0.
verify: $(VERIFY_TARGETS)
ifeq ($(strip $(VERIFY_TARGETS)),)
	@echo "verify: noch keine Verify-Pakete vorhanden - die entstehen erst in Welle 4 (docs/rewrite/PLAN.md §7, W4.1/W4.2)."
endif

## Der Beweislauf aus Rohdaten (Welle 5: W5.1, Vorfeld W5.P0,
## docs/rewrite/PLAN.md §13.10 Regel 9 - "wem gehört die Zeile, die alles
## zusammenhält"). Bis W5.P0 rief `all` `prep` und danach `widmung-v2`
## auf - die ALTE Kette, die nichts unter out/ schreibt (Punkt: die vier
## Endprodukte aus §3 liegen ausschließlich dort). Damit hätte der
## Beweislauf der Welle 5 die alte Kette bewiesen, nicht die vier Wellen
## Umbau. Jetzt die fünf Stufen aus §3 in ihrer vorgeschriebenen
## Reihenfolge ("Jede Stufe darf nur aus der vorigen lesen"): Roh (data/,
## keine eigene Stufe - dafür steht `rm -rf build` vor diesem Ziel im
## Beweislauf selbst, nicht hier), Prep (inkl. Prep II - Kataster/OSM/
## NÖ-SekROP sind innerhalb ihres eigenen prep-<domäne>-Ziels bereits
## zweistufig, siehe make/prep/README.md), Layer, Finalize, danach
## verify (Dashboard + Gemeindegrenzen, §3 Stufe 5 wörtlich: "Danach
## verify"). `validate` ABSICHTLICH NICHT Teil dieser Kette: es prüft
## (Abweichung gegen run1 nach der Ampel aus §6), erzeugt aber kein
## Produkt aus §3 und ist keine der fünf Stufen dort; es verlangt ein
## Pflichtargument PAKET ohne sinnvollen Default für einen Kettenlauf und
## schriebe bei jedem `make all` eine weitere Zeile in
## docs/rewrite/abweichungen.tsv - das Register ist eine Zeile je
## (Paket, Band), nicht je Lauf (§6: "Nur so ist jede Abweichung genau
## einem Paket zuzuordnen"). Für den Beweislauf selbst gehört die Prüfung
## trotzdem dazu, nur als eigener, bewusster Schritt danach: von Hand
## `make validate PAKET=W5.1` (siehe make/validate/README.md). Die alte
## Kette bleibt unter `widmung-v2` erreichbar (unser run1, siehe
## docs/RUN1_VERGLEICH.md) - nur nicht mehr unter `all`.
all: prep layers finalize verify

## Verdrahtet die 131 heute unerreichbaren Tests (kein `make test` bisher,
## siehe PLAN.md Ausgangslage: "12 unerreichbare Skripte, davon 8 Tests
## ohne make test"). `pytest tests/` sammelt bereits rekursiv alles unter
## tests/ ein (kein testpaths/norecursedirs in pyproject.toml, das
## einschränkt) - W4.3 legt seine neuen Vertragstests dort einfach als
## weitere tests/test_*.py ab und braucht dafür KEINE Änderung an diesem
## Ziel oder sonst am Makefile mehr (Regel 9, docs/rewrite/PLAN.md §13.10:
## W4.P0 besitzt Makefile als einziges Paket der Welle 4).
test:
	uv run pytest tests/ -v

## Legt neben dem Repo ein einsatzfähiges Worktree für ein Paket an, siehe
## docs/rewrite/PLAN.md §8 Regel 3 und FORTSCHRITT.md "Offene Punkte" #1:
## data/ ist gitignoriert, ein frisches Worktree wäre sonst leer und ein
## Abnahmelauf dort unmöglich. Aufruf: make worktree PAKET=w1.1
worktree:
	@if [ -z "$(PAKET)" ]; then \
		echo "Nutzung: make worktree PAKET=<paket>  (z.B. PAKET=w1.1)"; \
		exit 1; \
	fi
	@if ! printf '%s' "$(PAKET)" | grep -Eq '^[A-Za-z0-9]+([.-][A-Za-z0-9]+)*$$'; then \
		echo "Ungueltiger PAKET-Wert '$(PAKET)': erlaubt sind nur Buchstaben, Ziffern, Punkt und Bindestrich - kein '/', kein '..', kein Leerzeichen, kein fuehrendes/abschliessendes Sonderzeichen (z.B. PAKET=w1.1)."; \
		exit 1; \
	fi
	@WT_DIR=../abschichtung-$(PAKET); \
	CLEANUP="Manuell pruefen. Aufraeumen mit: git worktree remove --force $$WT_DIR && git branch -D $(PAKET)"; \
	if [ -e "$$WT_DIR" ]; then \
		WT_ABS=$$(cd "$$WT_DIR" 2>/dev/null && pwd -P); \
		if [ -z "$$WT_ABS" ] || ! git worktree list --porcelain | grep -Fxq "worktree $$WT_ABS"; then \
			echo "Abbruch: $$WT_DIR existiert bereits, ist aber kein von diesem Ziel angelegtes Worktree - nichts geloescht."; \
			echo "Von Hand pruefen (git worktree list); falls es weg soll, manuell entfernen."; \
			exit 1; \
		fi; \
		BR=$$(git -C "$$WT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null); \
		if [ "$$BR" != "$(PAKET)" ]; then \
			echo "Abbruch: $$WT_DIR ist ein Worktree, aber auf Zweig '$$BR' statt '$(PAKET)' - nichts geloescht."; \
			exit 1; \
		fi; \
		echo "Hinweis: $$WT_DIR existiert schon als Worktree auf Zweig $(PAKET) - zweiter Lauf, wird idempotent fortgesetzt."; \
	else \
		if ! git worktree add -b $(PAKET) "$$WT_DIR" HEAD; then \
			echo "Abbruch: git worktree add fehlgeschlagen - es wurde nichts angelegt. Falls von einem frueheren, abgebrochenen Lauf ein Zweig '$(PAKET)' uebrig ist: 'git branch -D $(PAKET)' bzw. 'git worktree prune'."; \
			exit 1; \
		fi; \
	fi; \
	if [ -L "$$WT_DIR/data" ]; then \
		: schon ein Symlink - unveraendert uebernehmen; \
	elif [ ! -e "$$WT_DIR/data" ]; then \
		: kein data/ im frischen Checkout - seit W1.2 ist data/README.md \
			nach docs/rohdaten.md verschoben, git versioniert also keine \
			Datei mehr unter data/ und legt das Verzeichnis bei einem \
			Checkout gar nicht erst an, weiter direkt zum Symlink unten; \
	elif [ -d "$$WT_DIR/data" ]; then \
		TRACKED=$$(git -C "$$WT_DIR" ls-files -- data | sort); \
		ACTUAL=$$(cd "$$WT_DIR" && find data -mindepth 1 -type f | sort); \
		if [ "$$ACTUAL" != "$$TRACKED" ]; then \
			echo "Abbruch: $$WT_DIR/data enthaelt mehr oder anderes als die versionierten Dateien - nichts geloescht."; \
			echo "Erwartet (git ls-files): $$TRACKED"; \
			echo "Vorgefunden: $$ACTUAL"; \
			echo "$$CLEANUP"; \
			exit 1; \
		fi; \
		printf '%s\n' "$$TRACKED" | while IFS= read -r f; do \
			[ -n "$$f" ] && rm -f "$$WT_DIR/$$f"; \
		done; \
		if ! find "$$WT_DIR/data" -depth -type d -exec rmdir {} +; then \
			echo "Abbruch: $$WT_DIR/data liess sich nach dem Leeren nicht vollstaendig entfernen (rmdir schlug fehl) - vermutlich doch nicht leer."; \
			echo "$$CLEANUP"; \
			exit 1; \
		fi; \
	else \
		echo "Abbruch: $$WT_DIR/data ist weder Verzeichnis noch Symlink - unerwarteter Zustand, nichts geloescht."; \
		echo "$$CLEANUP"; \
		exit 1; \
	fi; \
	if [ ! -L "$$WT_DIR/data" ]; then \
		ln -s $(CURDIR)/data "$$WT_DIR/data"; \
	fi; \
	COMMON_DIR=$$(git -C "$$WT_DIR" rev-parse --git-common-dir); \
	if ! grep -qxF '/data' "$$COMMON_DIR/info/exclude" 2>/dev/null; then \
		echo '/data' >> "$$COMMON_DIR/info/exclude"; \
	fi; \
	mkdir -p "$$WT_DIR/output/abschichtung_widmung_v2"; \
	if [ ! -L "$$WT_DIR/output/abschichtung_widmung_v2/distance_layers" ]; then \
		ln -s $(CURDIR)/output/abschichtung_widmung_v2/distance_layers \
			"$$WT_DIR/output/abschichtung_widmung_v2/distance_layers"; \
	fi; \
	if [ -L "$$WT_DIR/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif" ]; then \
		: schon ein Symlink - unveraendert uebernehmen; \
	elif [ -e "$$WT_DIR/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif" ]; then \
		echo "Abbruch: $$WT_DIR/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif existiert bereits, ist aber kein Symlink - unerwarteter Zustand, nichts geloescht."; \
		echo "$$CLEANUP"; \
		exit 1; \
	elif [ -e "$(CURDIR)/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif" ]; then \
		ln -s $(CURDIR)/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif \
			"$$WT_DIR/output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif"; \
	fi; \
	mkdir -p "$$WT_DIR/build"; \
	if [ -L "$$WT_DIR/build/prep" ]; then \
		: schon ein Symlink - unveraendert uebernehmen; \
	elif [ ! -e "$$WT_DIR/build/prep" ]; then \
		ln -s $(CURDIR)/build/prep "$$WT_DIR/build/prep"; \
	else \
		echo "Abbruch: $$WT_DIR/build/prep existiert bereits, ist aber kein Symlink - unerwarteter Zustand, nichts geloescht."; \
		echo "$$CLEANUP"; \
		exit 1; \
	fi; \
	if [ -L "$$WT_DIR/build/layers" ]; then \
		: schon ein Symlink - unveraendert uebernehmen; \
	elif [ ! -e "$$WT_DIR/build/layers" ]; then \
		ln -s $(CURDIR)/build/layers "$$WT_DIR/build/layers"; \
	else \
		echo "Abbruch: $$WT_DIR/build/layers existiert bereits, ist aber kein Symlink - unerwarteter Zustand, nichts geloescht."; \
		echo "$$CLEANUP"; \
		exit 1; \
	fi; \
	mkdir -p "$$WT_DIR/out"; \
	for f in abschichtung.tif abschichtung.bands.json; do \
		if [ -L "$$WT_DIR/out/$$f" ]; then \
			: schon ein Symlink - unveraendert uebernehmen; \
		elif [ -e "$$WT_DIR/out/$$f" ]; then \
			echo "Abbruch: $$WT_DIR/out/$$f existiert bereits, ist aber kein Symlink - unerwarteter Zustand, nichts geloescht."; \
			echo "$$CLEANUP"; \
			exit 1; \
		elif [ -e "$(CURDIR)/out/$$f" ]; then \
			ln -s $(CURDIR)/out/$$f "$$WT_DIR/out/$$f"; \
		fi; \
	done; \
	echo "Angelegt: $$WT_DIR auf Zweig $(PAKET). data/, distance_layers/ und die run1-Vergleichsbasis (osm_wka_distance_zones_widmung_v2_run1.tif) sind Symlinks auf dieses Repo (read-only, kein Kopieraufwand)."; \
	echo "WARNUNG: ein Lauf mit --force-layers dort schreibt in das GETEILTE distance_layers/ und zerstört die Arbeit aller anderen Worktrees - nicht verwenden."; \
	echo "Zusaetzlich (W2.P0, docs/rewrite/PLAN.md §13.8): build/prep/ ist ebenfalls ein Symlink auf dieses Repo (read-only, kein Kopieraufwand - die Prep-Ausgaben muessten sonst je Worktree neu gerechnet werden, allein Kataster 45-70 Minuten)."; \
	echo "WARNUNG: build/prep/ ist GETEILT und nur zum Lesen gedacht - ein Schreibzugriff (z.B. ein erneutes 'make prep' aus diesem Worktree) trifft alle Layer-Worktrees gleichzeitig; nur die Prep-Stufe im Hauptrepo darf dort schreiben."; \
	echo "Zusaetzlich (W4.P0, docs/rewrite/PLAN.md §13.10): build/layers/ ist ebenfalls ein Symlink auf dieses Repo (read-only, kein Kopieraufwand - die 33 Checkpoints muessten sonst je Worktree neu gerechnet werden, dazu rund 165 s Finalisierung fuer das TIF)."; \
	echo "WARNUNG: build/layers/ ist GETEILT und nur zum Lesen gedacht - ein Schreibzugriff (z.B. ein erneutes 'make layers' aus diesem Worktree) trifft alle Verify-Worktrees gleichzeitig; nur die Layer-Stufe im Hauptrepo darf dort schreiben."; \
	echo "out/ selbst ist KEIN Symlink, sondern ein echtes, privates Verzeichnis in diesem Worktree - nur out/abschichtung.tif und out/abschichtung.bands.json darin sind Symlinks auf das fertige TIF samt Bandmanifest im Hauptrepo (read-only, falls dort schon finalisiert)."; \
	echo "WARNUNG: out/abschichtung.tif und out/abschichtung.bands.json sind GETEILT und nur zum Lesen gedacht - ein Schreibzugriff (z.B. ein erneutes 'make finalize' aus diesem Worktree) trifft alle Verify-Worktrees gleichzeitig; nur die Finalize-Stufe im Hauptrepo darf dort schreiben. Alles andere unter out/ (z.B. out/dashboard/, out/gemeinden.geojson) ist frei beschreibbar, ohne das Hauptrepo oder ein Geschwister-Worktree zu beruehren."; \
	echo "git status ist absichtlich sauber: data/ ist seit W1.2 ohne jede versionierte Datei (kein --skip-worktree mehr noetig), der Symlink 'data' selbst steht in .git/info/exclude (geteilt ueber alle Worktrees, nicht versioniert)."; \
	echo "build/ und out/ sind zusaetzlich ueber .gitignore repoweit ausgeschlossen - fuer die Symlinks unter build/ und out/ ist kein weiterer Eintrag in .git/info/exclude noetig."; \
	echo "Entfernen mit: git worktree remove $$WT_DIR && git branch -d $(PAKET)"
