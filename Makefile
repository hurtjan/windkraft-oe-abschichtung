PYTHON = uv run python
CONFIG = config.json

V2_DIR = output/abschichtung_widmung_v2
V2_TIF = $(V2_DIR)/osm_wka_distance_zones_widmung_v2.tif

.PHONY: widmung-v2 widmung-v2-zoning widmung-v2-hig widmung-v2-osm widmung-v2-tif \
        widmung-v2-validate check-hardlinks check-raw-only check-guards prep all test worktree
.PHONY: layers

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
## (Standard, siehe .DEFAULT_GOAL oben) ist Layer+Finalize, unverändert die
## heutige Kette. `prep` existiert als Ziel; solange keine make/prep/*.mk
## vorliegt, tut es noch nichts. `all` hängt beides zusammen; solange prep
## leer ist, ist das dasselbe wie `make`.

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

## Prep und Kette zusammen - der Beweislauf aus Rohdaten (Welle 5: W5.1).
all: prep widmung-v2

## Verdrahtet die 131 heute unerreichbaren Tests (kein `make test` bisher,
## siehe PLAN.md Ausgangslage: "12 unerreichbare Skripte, davon 8 Tests
## ohne make test"). W4.3 erweitert dieses Ziel später um Vertragstests.
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
	echo "Angelegt: $$WT_DIR auf Zweig $(PAKET). data/ und distance_layers/ sind Symlinks auf dieses Repo (read-only, kein Kopieraufwand)."; \
	echo "WARNUNG: ein Lauf mit --force-layers dort schreibt in das GETEILTE distance_layers/ und zerstört die Arbeit aller anderen Worktrees - nicht verwenden."; \
	echo "Zusaetzlich (W2.P0, docs/rewrite/PLAN.md §13.8): build/prep/ ist ebenfalls ein Symlink auf dieses Repo (read-only, kein Kopieraufwand - die Prep-Ausgaben muessten sonst je Worktree neu gerechnet werden, allein Kataster 45-70 Minuten)."; \
	echo "WARNUNG: build/prep/ ist GETEILT und nur zum Lesen gedacht - ein Schreibzugriff (z.B. ein erneutes 'make prep' aus diesem Worktree) trifft alle Layer-Worktrees gleichzeitig; nur die Prep-Stufe im Hauptrepo darf dort schreiben."; \
	echo "git status ist absichtlich sauber: data/ ist seit W1.2 ohne jede versionierte Datei (kein --skip-worktree mehr noetig), der Symlink 'data' selbst steht in .git/info/exclude (geteilt ueber alle Worktrees, nicht versioniert)."; \
	echo "build/ ist zusaetzlich ueber .gitignore repoweit ausgeschlossen - fuer den build/prep-Symlink ist kein weiterer Eintrag in .git/info/exclude noetig."; \
	echo "Entfernen mit: git worktree remove $$WT_DIR && git branch -d $(PAKET)"
