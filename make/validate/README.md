# make/validate/ — Konvention für die Validierungs-Stufe

Paket **W3.2** (`docs/rewrite/PLAN.md` §7) legt dieses Verzeichnis nach
demselben Muster wie `make/prep/`, `make/layers/` und `make/finalize/` an
(siehe deren `README.md` - "nicht ähnlich, sondern dasselbe"). Wie bei
`make/finalize/` gibt es hier nur eine Domäne (Validierung ist eine eigene
Stufe, §3: Roh → Prep → Layer → Finalize → Export - §3 nennt die fünfte
Stufe verify, bis W6.2 hiess sie so auch im Code), also kein
`<domäne>`-Ableitungsmuster und keine eigene `*_TARGETS`-Liste -
`validate.mk` deklariert Ziel und `.PHONY` direkt selbst.

## Anders als bei make/finalize/: die -include-Zeile steht schon im Makefile

`make/finalize/` musste ohne `-include`-Zeile auskommen, weil W3.1
`Makefile` nicht anfassen durfte (siehe dortiges `README.md`). W3.2 hat
diese Lücke in Schritt 0c geschlossen (Punkt 36, `docs/rewrite/PLAN.md`
§13.10, Regel 9) und trägt bei derselben Gelegenheit die zweite
`-include`-Zeile - für `make/validate/*.mk` - gleich mit ein, statt dieselbe
Lücke ein zweites Mal offen zu lassen. `make validate PAKET=<paket>` ist
damit ab W3.2 direkt erreichbar.

## Konvention (wie make/finalize/README.md)

- Das Ziel heißt `validate` und steht in `make/validate/validate.mk` -
  sonst nirgends.
- `PAKET=<name>` ist ein Pflichtargument (dasselbe Muster wie beim
  bestehenden `worktree`-Ziel, `make worktree PAKET=w1.1`) - es landet als
  `--paket` in `docs/rewrite/abweichungen.tsv` und macht jede Zeile im
  Register genau einem Arbeitspaket zuordenbar (§6: "Nur so ist jede
  Abweichung genau einem Paket zuzuordnen").
- Die Vergleichsbasis (`run1`), das Standard-TIF
  (`pipeline.contract.PRODUCTS['abschichtung_tif']`) und der Registerpfad
  (`docs/rewrite/abweichungen.tsv`) sind in `pipeline/validate.py` fest
  verankert - keine weiteren Pflichtargumente nötig für den Normalfall.
- `.PHONY: validate` steht in dieser eigenen Datei, nicht im
  Haupt-`Makefile`.

## Beispielaufruf

```
make validate PAKET=W3.1
```

Voraussetzung: `out/abschichtung.tif` (und das dazugehörige
`.bands.json`-Manifest) existieren bereits - `make finalize` zuerst.
