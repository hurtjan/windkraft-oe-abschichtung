# Abschichtung Windkraft Österreich

Wo in Österreich könnte ein Windrad stehen? Dieses Repo beantwortet die Frage durch **Abschichtung**: Alle Flächen, auf denen Windkraft aus Gründen des Siedlungsschutzes, des Naturschutzes oder der Geografie ausscheidet, werden übereinandergelegt. Was übrig bleibt und zusammenhängend mindestens 10 ha groß ist, ist die Eignungsfläche. Das ist keine Standortprüfung und keine Genehmigungsgrundlage.

![Ausschlussflächen Mensch, Natur, Geografie und Eignungsfläche ≥ 10 ha](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/abb_methoden_uebersicht.png)

Ausführlich: **[Whitepaper](docs/whitepaper/paper.md)** (Methode, Daten, alle Kriterien).

## Ergebnis

Von {{z:k_referenzflaeche_at_km2|0}} km² Landesfläche sind {{z:k_ausschluss_gesamt_pct|%1}} ausgeschlossen. Als Eignungsfläche ab 10 ha bleiben **{{z:k_eignung_ge_10_ha_km2|0}} km²**, das sind **{{z:k_eignung_ge_10_ha_pct|%1}}** der Landesfläche. {{z:k_anteil_burgenland_niederoesterreich_an_eignung_pct|%0}} davon liegen in Niederösterreich und im Burgenland.

**Ausschluss und Eignung je Bundesland** (in % der Landesfläche; „nur“ = durch keine andere Gruppe ausgeschlossen):

{{tab:T1_haupttabelle}}

![Anteil der Ausschlussgruppen und der Eignungsfläche je Bundesland](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/abb2_balken.png)

**Wald und landwirtschaftliche Flächen** (Kataster; zum Vergleich, kein Ausschluss). *Bestand* = amtliche Windkraftzonen der Länder und bestehende Windparks außerhalb dieser Zonen (Hülle um die Windräder plus 200 m); *Potentialfläche* = Eignungsfläche ab 10 ha, soweit sie nicht schon Bestand ist; *C48* = Äcker, Wiesen, Weiden.

{{tab:L1_landnutzung}}

## Kriterien

| Gruppe | Kriterium | Regel | Quelle |
| --- | --- | --- | --- |
| Mensch | Siedlung | 1 000 m Abstand zu gewidmetem Wohnbauland (NÖ 1 200 m) | Flächenwidmung der Länder |
| Mensch | Häuser im Grünen | 750 m Abstand zu Sonderwidmungen und erkannten Streusiedlungen | Flächenwidmung, Kataster, Adressregister, NÖ-Mindestabstandszonen |
| Mensch | Gebäude | 25 m Abstand (Seilbahnstationen 50 m) | Kataster, OpenStreetMap |
| Mensch | Verkehr | 150 m zu höherrangigen Straßen, Hauptbahnen, Personenseilbahnen | OpenStreetMap |
| Mensch | Militär | ohne Abstand | OpenStreetMap |
| Mensch | Luftfahrt | Areal der sechs Verkehrsflughäfen und Anflugkorridore | OpenStreetMap |
| Natur | Schutzgebiete | per Verordnung oder Bescheid geschützt, ohne Abstand | Umweltbundesamt |
| Geografie | Hangneigung | steiler als 15° | Höhenraster 25 m (BEV) |
| Geografie | Seehöhe | über 2 500 m | Höhenraster 25 m (BEV) |
| Geografie | Wind | unter 150 W/m² in 130 m Höhe | Global Wind Atlas |
| Geografie | Gewässer | ab 1 ha | OpenStreetMap |

Gerechnet wird auf einem Raster von 25 × 25 m (EPSG:31287); Abstände sind Kreise um jede betroffene Zelle.

## Produkte

- `out/abschichtung.tif`: **45 Bänder**, 25 m, EPSG:31287, `uint8`; jedes Kriterium als eigene Maske, dazu Summen je Gruppe und die Eignungsfläche. Manifest `out/abschichtung.bands.json`, Schema **2.3.0**, TIF-sha256 `{{s:tif_sha12}}…`. TIF und Manifest nur zusammen weitergeben; Vertrag für Weiterverarbeiter: [`docs/HANDOFF.md`](docs/HANDOFF.md).
- `out/abschichtung_analyse.tif`: gleiches Raster, Landnutzungsklassen aus dem Kataster (Wald, Äcker/Wiesen/Weiden u. a.); nur für Auswertungen.

Die Ausgaben liegen nicht im Repo (`out/` ist gitignored). Abbildungen hängen am Release [`abbildungen-latest`](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/tag/abbildungen-latest).

## Ausführen

Voraussetzungen: Python mit [uv](https://docs.astral.sh/uv/), `osmium-tool` (`brew install osmium-tool`), rund 25 GB Plattenplatz; zum Veröffentlichen der Abbildungen die GitHub-CLI `gh`.

```bash
uv sync                # Abhängigkeiten
# Rohdaten nach data/ — siehe docs/rohdaten.md
make check-guards      # Wächter: data/ wird nur gelesen
make                   # prep → layers → finalize → analyse-raster → export
make test
make bilanz            # Flächenbilanz je Bundesland (docs/flaechenbilanz.tsv)
make whitepaper        # Zahlen, Tabellen, Abbildungen; erzeugt paper.md und diese README
make abb-publish       # Probelauf; mit CONFIRM=1 werden die Abbildungen hochgeladen
```

Ein Kaltstart dauert deutlich über eine Stunde; allein die Kataster-Aufbereitung braucht 45–70 Minuten. Unvollständige Rohdaten führen **nicht** zum Abbruch, sondern zu einem plausibel aussehenden, aber falschen Ergebnis — vorher [`docs/rohdaten.md`](docs/rohdaten.md), Abschnitt 0, lesen.

Diese README und das Whitepaper werden von `make whitepaper` aus [`docs/whitepaper/readme_vorlage.md`](docs/whitepaper/readme_vorlage.md) und [`docs/whitepaper/paper_vorlage.md`](docs/whitepaper/paper_vorlage.md) erzeugt; Änderungen gehören in die Vorlagen.

## Dokumentation

- [`docs/whitepaper/paper.md`](docs/whitepaper/paper.md): Whitepaper
- [`docs/BETRIEB.md`](docs/BETRIEB.md): Kette im Detail, Wiederholbarkeit, Tests
- [`docs/HANDOFF.md`](docs/HANDOFF.md): Vertrag für alle, die das GeoTIFF weiterverarbeiten
- [`docs/LAYER-MANIFEST.md`](docs/LAYER-MANIFEST.md): Bänder und Manifest
- [`docs/rohdaten.md`](docs/rohdaten.md): Herkunft und Lizenz jeder Eingangsdatei
- [`docs/whitepaper/README.md`](docs/whitepaper/README.md): Whitepaper-Erzeugung und Abbildungs-Veröffentlichung
- [`docs/dataflow/`](docs/dataflow/): Datenfluss-Diagramm

## Datenquellen und deren Lizenzen

Die Rohdaten sind nicht Teil des Repos und behalten ihre eigenen Bedingungen (Details und Bezugswege: [`docs/rohdaten.md`](docs/rohdaten.md)):

- OpenStreetMap (Geofabrik-Extrakt): ODbL 1.0, © OpenStreetMap-Mitwirkende
- BEV (Adressregister, Digitale Katastralmappe, Verwaltungsgrenzen, Geländemodell): CC BY 4.0, soweit dort ausgewiesen
- Flächenwidmung der neun Länder: je Land eigene Bedingungen (OÖ und Tirol CC BY 4.0); siehe `docs/rohdaten.md`
- Schutzgebiete: Umweltbundesamt (SG_AT_2024)
- NÖ SekROP Windkraft: Land Niederösterreich
- Global Wind Atlas: Zitat und Bedingungen wie in `docs/rohdaten.md` und im Whitepaper (Davis et al. 2023)

## Lizenz

Code: MIT ([`LICENSE`](LICENSE)). Texte, Dokumentation und Abbildungen: CC BY 4.0 ([`LICENSE-docs`](LICENSE-docs)), © 2026 Jan Hurt.
