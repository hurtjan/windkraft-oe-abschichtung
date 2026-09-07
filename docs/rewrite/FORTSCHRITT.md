# Fortschritt des Umbaus

Laufendes Protokoll. Eine Zeile je Paket, ergänzt um einen Eintrag je
abgeschlossenem Paket. **Diese Datei wird nach jedem Paket fortgeschrieben**
— sie ist zusammen mit `PLAN.md` das, was einen Sitzungsabbruch überlebt.

Der Plan selbst steht in [`PLAN.md`](PLAN.md); Zuschnitt und Zielbaum von
W0.1 in dessen §11. Die Belege liegen unter
[`nachweise/`](nachweise/), die Abweichungen in `abweichungen.tsv`.

## Stand

| | |
|---|---|
| Abgeschlossen | 1 von 30 (W0.1) |
| In Arbeit | W0.2 — Pfadvertrag |
| Zweig | `docs/audit-und-plan`, kein Remote |
| Letzter Commit | `3fd54a8` |
| Abweichungen bisher | keine — W0.1 bitgleich |

## Paketübersicht

Status: `offen` · `läuft` · `fertig` · `blockiert`

| Paket | Welle | Titel | Status | Commit | Abnahme |
|---|---|---|---|---|---|
| W0.1 | 0 | Rohdaten nach Thema sortieren | **fertig** | `5aab405`, `3fd54a8` | bitgleich + Inode-Abgleich |
| W0.2 | 0 | Pfadvertrag anlegen | **läuft** | — | — |
| W0.3 | 0 | Verzeichnisgerüst und Make-Ziele | offen | — | — |
| W1.1 | 1 | Adress-Cache-Weiche entfernen | offen | — | — |
| W1.2 | 1 | Tote Daten löschen, Provenienz retten | offen | — | — |
| W1.3 | 1 | Hardlinks auflösen | offen | — | — |
| W1.4 | 1 | Wächter für Rohdaten | offen | — | — |
| W1.5 | 1 | Tote Skripte löschen | offen | — | — |
| W1.6 | 1 | NÖ-PDF-HiG-Sackgasse entfernen | offen | — | — |
| W1.7 | 1 | Ausschlusszonen entfernen | offen | — | — |
| W1.8 | 1 | Paketmetadaten bereinigen | offen | — | — |
| W1.9 | 1 | Doku-Widersprüche korrigieren | offen | — | — |
| W1.P1 | 1 | Prep: Verwaltungsgrenzen | offen | — | — |
| W1.P2 | 1 | Prep: Kataster | offen | — | — |
| W1.P3 | 1 | Prep: Adressregister | offen | — | — |
| W1.P4 | 1 | Prep: Flächenwidmung | offen | — | — |
| W1.P5 | 1 | Prep: OSM, zwei Stufen | offen | — | — |
| W1.P6 | 1 | Prep: Gelände und Wind | offen | — | — |
| W1.P7 | 1 | Prep: Naturschutz | offen | — | — |
| W1.P8 | 1 | Prep: Windzonen | offen | — | — |
| W1.P9 | 1 | Prep: NÖ-SekROP-PDF, zwei Stufen | offen | — | — |
| W2.1 | 2 | Layer: Widmung | offen | — | — |
| W2.2 | 2 | Layer: Häuser im Grünen | offen | — | — |
| W2.3 | 2 | Layer: OSM und Infrastruktur | offen | — | — |
| W3.1 | 3 | Finalisierung und Manifest-Vertrag | offen | — | — |
| W3.2 | 3 | Validierung | offen | — | — |
| W4.1 | 4 | Dashboard neu | offen | — | — |
| W4.2 | 4 | Gemeindegrenzen-Export | offen | — | — |
| W4.3 | 4 | Tests verdrahten | offen | — | — |
| W5.1 | 5 | Beweislauf aus Rohdaten | offen | — | — |

## Gemessene Laufzeiten

Aus `docs/RUN1_VERGLEICH.md`, ein sequentieller Lauf am 06.09.2026 mit
warmem Cache:

| Stufe | Dauer |
|---|---:|
| `03_build_osm_layers.py` | 6:15 |
| `04_create_distance_zones.py` | 4:58 |
| `02_build_hig_sources.py` | 2:23 |
| `01_build_official_zoning_layers.py` | 0:49 |
| `05_validate.py` | 0:01 |
| **Kette gesamt** | **14:26** |

**Nicht enthalten und nirgends gemessen:** die Vorverarbeitung, die das
Kataster-GeoParquet erzeugt (`export_at_dkm_geoparquet.py` über acht
Landesarchive plus NÖ-Rekonstruktion aus DXF). Stufe 1 verarbeitet in
49 Sekunden bereits fertiges GeoParquet, nicht die 9,1 GB DKM-Archive. Das
Zielbild nennt dafür die Größenordnung fünf Stunden — eine Behauptung ohne
Messung. **W1.P2 misst sie**, bevor Welle 5 davon abhängt.

Aufwand je Paket, gemessen an W0.1: **53 Minuten** Wanduhrzeit, davon
2,5 Minuten Datenbewegung und der Rest Schreiben und Prüfen.

## Protokoll

### W0.1 — Rohdaten nach Thema sortieren · fertig

Commits `5aab405` (Umbau) und `3fd54a8` (Nachweise, Nachzügler).

`data/` ist in neun Domänenverzeichnisse gegliedert: `admin`, `kataster`,
`adressen`, `widmung`, `osm`, `gelaende`, `natur`, `zonen`, `noe_sekrop`.
Die Zwei-Ordner-Falle der Flächenwidmung ist aufgelöst —
`flächenwidmungen/` und `new_widmungs_data/` sind zu
`data/widmung/<bundesland>/` zusammengeführt, `widmung_sources.py` hat statt
zwei Wurzeln nur noch eine.

**Abnahme: bestanden, ohne Abweichung.** Vier Nachweise, Belege unter
`nachweise/w01/`:

1. 56 Inodes vor und nach dem Verschieben, jeder genau einmal
   wiedergefunden; Linkcounts und Prüfsummen unverändert.
2. 35 funktionale Pfade lösen auf; alle geänderten Dateien kompilieren.
3. Finalisierung aus 34 Checkpoint-Layern in 167 s → `sha256` identisch zu
   `run1`.
4. 30 von 30 Codestellen zeigen auf **dieselbe** Inode wie vorher.

Der vierte Nachweis war nötig, weil die ersten drei eine Lücke lassen: Der
Bitgleichheitslauf hat drei der neun Verzeichnisse gar nicht angefasst, und
„der Pfad existiert" ist schwächer als „es ist dieselbe Datei". Die beiden
steirischen Widmungsquellen liegen jetzt im selben Verzeichnis; eine
Vertauschung wäre weder an einer Fehlermeldung noch an der Bandzahl
aufgefallen.

**Gelernt, mit Folgen für spätere Pakete:**

- `layer_done()` prüft nur Form, CRS, Transform und Bandname des
  vorhandenen Checkpoints, **nicht die Rohquelle**. Eine ausgetauschte
  Rohdatei bleibt unbemerkt. Der Fingerabdruck der Eingänge gehört daher
  auch auf die Layer-Stufe (W2.1–W2.3), nicht nur ins Prep.
- Eine Textsuche nach `data/` findet nicht alles: drei Dateien setzen ihre
  Pfade zusammen (`ROOT / "data" / …`), eine weitere lag unter `docs/` und
  damit außerhalb der Suche. **Die Rückwärtssuche nach den alten Namen
  gehört in jedes Paket, das Pfade anfasst** — sie hat beide Lücken
  gefunden, die Vorwärtssuche keine.
- Ein Nachweis über Inodes ist stärker und billiger als ein Testlauf:
  Sekunden statt Stunden, und er belegt Identität statt nur Erfolg.

## Offene Punkte

| # | Punkt | Fällig |
|---|---|---|
| 1 | **Worktrees haben kein `data/`.** Regel 3 des Plans verlangt je Paket ein eigenes Worktree; `data/` ist gitignoriert, ein frisches Worktree ist also leer. Jedes Paket, dessen Abnahme einen Lauf verlangt, wäre dort nicht abnehmbar. Lösung: `data/` in jedes Worktree hineinverlinken — gefahrlos, weil der Baum unveränderlich ist. Steht so nicht im Plan. | vor Welle 1 |
| 2 | Laufzeit der Kataster-Vorverarbeitung ist unbekannt. | W1.P2 |
| 3 | `docs/widmung_v2_provenance.md` nennt Quellpfade, die es nicht mehr gibt. Unklar, ob eingefrorene Momentaufnahme wie `RUN1_VERGLEICH.md` oder lebende Doku. | Welle 1, Widmungspakete |
| 4 | `config.json:osm_dir` und `wind_pd_100` zeigen auf Dateien, die es nie gab. Mitgezogen, aber weiterhin tot. | W1.x |
