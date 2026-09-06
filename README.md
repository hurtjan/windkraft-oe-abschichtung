# Abschichtung Widmung v2

Dies ist ein neues, eigenständiges Repo für die Widmung-v2-Kette, additiv neben
dem alten, gewachsenen Repo `windkraft_ö_karten` angelegt. Das alte Repo bleibt
unangetastet als Sicherheitsnetz, bis dieses Repo einen verifizierten Durchlauf
vorzuweisen hat.

## Struktur

- `data/` = alle Quelldaten, roh, gitignored außer `data/README.md`
- `output/` = alle erzeugten Artefakte, komplett gitignored
- `windkraft/` = Python-Paket
- `scripts/` = dünne CLI-Einstiegspunkte
- `config/`
- `docs/`
- `tests/`

## Status

Schritt 1 (Gerüst) erledigt; Code-Übernahme, `data/README.md` und der
Manifest-Emitter folgen.
