# make/verify/ — Konvention für die zwei Verify-Pakete

Vorpaket **W4.P0** (`docs/rewrite/PLAN.md` §13.10, Regel 9) hat dieses
Verzeichnis angelegt, damit die zwei parallelen Verify-Pakete (W4.1
Dashboard, W4.2 Gemeindegrenzen-Export) nicht beide dieselbe Zeile im
`Makefile` ändern müssen. Das `Makefile` liest `make/verify/*.mk` per
`-include` ein — zwei verschiedene Dateien statt zwei Änderungen an
einer. Genau dasselbe Muster wie bei `make/prep/` und `make/layers/`
(siehe deren `README.md` — "nicht ähnlich, sondern dasselbe").

## Konvention

- Dein Make-Ziel heißt `verify-<domäne>` (z. B. `verify-dashboard`,
  `verify-gemeinden`) und steht in `make/verify/<domäne>.mk` — sonst
  nirgends. `<domäne>` ist der Name deines Moduls unter
  `pipeline/verify/` ohne `.py` (also `dashboard` bzw. `gemeinden` —
  siehe `docs/rewrite/PLAN.md` §7, Spalte "Ort" für W4.1/W4.2).
- Deine Produktpfade (`out/dashboard/`, `out/gemeinden.geojson`) stehen
  bereits in `pipeline/contract.py:PRODUCTS` (Schlüssel
  `dashboard_dir`, `gemeinden_geojson`) — importieren, nicht neu
  erklären. Beispiel:

  ```python
  from pipeline import contract
  out_dir = contract.PRODUCTS["dashboard_dir"]
  ```

  Das fertige TIF und das Bandmanifest, gegen die deine Verify-Stufe
  liest, stehen ebenso bereits in `pipeline/contract.py:PRODUCTS`
  (Schlüssel `abschichtung_tif`, `abschichtung_bands_json`) und liegen
  unter `out/` (siehe make/finalize/README.md, make/validate/README.md).
- `make verify` ruft am Ende alle vorhandenen `verify-*`-Ziele auf. Das
  geschieht automatisch über `VERIFY_TARGETS` im `Makefile` (aus den
  Dateinamen unter `make/verify/` abgeleitet) — du musst `verify:` selbst
  nicht anfassen, nur dein eigenes `verify-<domäne>:` deklarieren.
- Deklariere dein Ziel als `.PHONY` **in deiner eigenen Datei**, nicht im
  Haupt-`Makefile` (das trägt `VERIFY_TARGETS` bereits automatisch in
  `.PHONY` ein, schadet aber nicht, wenn du es zusätzlich in deiner
  Datei tust).

## Minimalbeispiel

Siehe `_beispiel.mk.txt` in diesem Verzeichnis — die Endung `.mk.txt`
(nicht `.mk`) ist Absicht: sie wird von `-include make/verify/*.mk` nicht
eingelesen, dient nur als Vorlage zum Kopieren.

```make
.PHONY: verify-dashboard
verify-dashboard:
	uv run python -m pipeline.verify.dashboard
```

## Worktree: build/layers/ und das fertige TIF sind schon da

`make worktree PAKET=<dein-paket>` verlinkt seit W4.P0 auch
`build/layers/` (die 33 Checkpoints) sowie `out/abschichtung.tif` und
`out/abschichtung.bands.json` (das fertige TIF samt Bandmanifest) in dein
Worktree hinein — alle drei als Symlinks auf dieses Repo, read-only,
geteilt über alle Verify-Worktrees (siehe die Warnungen im `worktree`-Ziel
selbst). Du musst weder die Layer-Stufe noch die Finalisierung in deinem
Worktree neu rechnen, um gegen ihre Ausgaben zu prüfen.

`out/` selbst ist dabei **kein** Symlink, sondern ein echtes, privates
Verzeichnis in deinem Worktree — nur die zwei genannten Dateien darin
sind Symlinks. Dein eigenes Produkt (`out/dashboard/` bzw.
`out/gemeinden.geojson`) schreibst du also normal dorthin, ohne das
Hauptrepo oder ein Geschwister-Worktree zu berühren. Ein Symlink auf das
ganze `out/`-Verzeichnis wäre falsch gewesen: W4.1 und W4.2 schreiben
beide nach `out/`, und zwei Worktrees hätten sich über einen
`out/`-Symlink gegenseitig überschrieben.

## Warum diese Datei existiert

`docs/rewrite/PLAN.md` §13.10 (Regel 9): Sobald eine Welle eine neue Art
von Datei hervorbringt, gehört die gemeinsame Verdrahtung dafür vor die
Welle und braucht einen benannten Besitzer. Ohne diese Konvention hätten
W4.1 und W4.2 beide dieselbe `-include`-Zeile im `Makefile` beansprucht —
genau die Lücke, die Welle 3 offen ließ (`make finalize` war nach W3.1
nicht erreichbar, siehe §13.10) und die hier von vornherein vermieden
wird.
