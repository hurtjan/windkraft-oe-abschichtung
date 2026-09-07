#!/usr/bin/env python3
"""
2_normalize.py -- repariert docs/dataflow/flow_graph.json (+ nodes.tsv/edges.tsv)

Behebt drei Maengel des von 6 Fragment-Agenten gemergten Datenfluss-Graphen
(geschrieben von 1_merge.py):
  1. uneinheitliche Kantenrichtung (reads/writes/invokes wurden von manchen
     Fragmenten in Produzenten-, von anderen in Konsumentenrichtung notiert)
  2. aussagekraftlose Sackgassen-Flags (basierten auf den kaputten Graden)
  3. offene Klassifikationen (42 raw_class-Konflikte, 7 Nodes ohne stage)
Traegt zusaetzlich 13 empirisch belegte "tot"-Befunde eines Faktencheck-Agenten
als verified_dead-Flags samt Belegnotiz ein.

Step 2 of 3 in the dataflow-graph generation chain (see docs/dataflow/README.md,
Abschnitt "Neu erzeugen"). Run from anywhere; paths resolve relative to the
repo root found via this file's location, unless DATAFLOW_ROOT is set (used
for verification runs against a throwaway copy of docs/dataflow/).
"""
import json
import csv
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# docs/dataflow/src/2_normalize.py -> parents[0]=src, [1]=dataflow, [2]=docs, [3]=repo root
ROOT = Path(os.environ.get("DATAFLOW_ROOT", Path(__file__).resolve().parents[3]))
DF = ROOT / 'docs' / 'dataflow'
SRC = DF / 'flow_graph.json'

d = json.loads(SRC.read_text(encoding='utf-8'))
nodes = {n['id']: n for n in d['nodes']}
edges = d['edges']

# Reparatur: dieses Skript lief versehentlich schon zweimal auf demselben Output
# (docs/dataflow/ ist ungetrackt, `git checkout` davor griff nicht) -- dadurch
# koennen 'notes'-Felder Segmente doppelt enthalten. Vor jeder inhaltlichen
# Verarbeitung einmal deduplizieren (Reihenfolge des ersten Auftretens erhalten).
for n in d['nodes']:
    notes = n.get('notes')
    if notes:
        seen = []
        for seg in notes.split(' | '):
            if seg not in seen:
                seen.append(seg)
        n['notes'] = ' | '.join(seen)

# ---------------------------------------------------------------------------
# MANGEL 1 -- Kantenrichtung normalisieren
# ---------------------------------------------------------------------------

def kind_group(nid):
    """script/module -> 'actor' (Akteur, liest/schreibt);
    file/dir/layer -> 'artifact' (Datenobjekt);
    sonst der rohe kind-Wert (config_key, make_target, external, unknown)."""
    if nid not in nodes:
        return 'MISSING'
    k = nodes[nid]['kind']
    if k in ('script', 'module'):
        return 'actor'
    if k in ('file', 'dir', 'layer'):
        return 'artifact'
    return k

direction_unresolved = []
n_reversed = 0

for e in edges:
    f, t, k = e['from'], e['to'], e['kind']
    fg, tg = kind_group(f), kind_group(t)
    e['flow'] = False
    e['reversed'] = False

    if k == 'writes':
        # kanonisch: script/module (Produzent) -> Datei/Layer (Artefakt)
        if fg == 'actor' and tg == 'artifact':
            e['flow'] = True
        elif fg == 'artifact' and tg == 'actor':
            e['from'], e['to'] = t, f
            e['reversed'] = True
            e['flow'] = True
        elif (fg == 'artifact' and tg == 'artifact') or (fg == 'actor' and tg == 'actor'):
            direction_unresolved.append({
                **e,
                'from': f, 'to': t,  # unveraendert
                'reason': "writes: beide Endpunkte in derselben Gruppe (beide Datei/Layer oder beide Skript/Modul) -- Inventurfehler, Kante unveraendert gelassen",
            })
        # sonst (config_key/make_target/external beteiligt): flow bleibt False, unveraendert

    elif k == 'reads':
        # kanonisch: Datei/Layer (Artefakt) -> script/module (Konsument)
        if fg == 'artifact' and tg == 'actor':
            e['flow'] = True
        elif fg == 'actor' and tg == 'artifact':
            e['from'], e['to'] = t, f
            e['reversed'] = True
            e['flow'] = True
            n_reversed += 1
        elif (fg == 'artifact' and tg == 'artifact') or (fg == 'actor' and tg == 'actor'):
            direction_unresolved.append({
                **e,
                'from': f, 'to': t,
                'reason': "reads: beide Endpunkte in derselben Gruppe (beide Datei/Layer oder beide Skript/Modul) -- Inventurfehler, Kante unveraendert gelassen",
            })
        # sonst (config_key beteiligt, z.B. cfg:paths.X <-> Datei oder Skript <-> cfg:paths.X):
        # kein script/module<->file/dir/layer-Paar im Sinne der Regel -> flow bleibt False, unveraendert.
        # (Diese Kanten modellieren Config-Aufloesung, nicht direkten Datenfluss; der eigentliche
        # Datenfluss Datei->Skript ist i.d.R. zusaetzlich als direkte reads-Kante vorhanden.)

    elif k == 'invokes':
        # kanonisch: make_target -> script
        if fg == 'make_target' and tg == 'actor':
            e['flow'] = True
        elif fg == 'actor' and tg == 'make_target':
            e['from'], e['to'] = t, f
            e['reversed'] = True
            e['flow'] = True
        # sonst (actor->actor Funktionsaufruf, actor->external Tool-Aufruf,
        # artifact->actor Pseudo-Invoke/Fehlermeldung): keine make_target->script-Kante,
        # flow bleibt False, Richtung unveraendert (kein Produzent/Konsument-Fall im Sinne
        # dieser Kantenart).

    elif k == 'imports':
        # importierendes modul -> importiertes modul; per Vorgabe nie flow, zaehlt nicht in Grade
        e['flow'] = False

    else:  # 'depends' und alles sonstige (make_target-Sequencing, pyproject-Abhaengigkeiten)
        e['flow'] = False

# --- Reparatur-Override -----------------------------------------------------
# Dieses Skript lief versehentlich zweimal auf demselben (ungetrackten, daher
# per `git checkout` nicht wiederherstellbaren) docs/dataflow/flow_graph.json.
# Nach dem ersten Lauf stehen alle reads-Kanten bereits in kanonischer Form
# (Datei -> Skript); ein erneuter Durchlauf erkennt daher fuer diese Kanten
# keinen Reversal-Bedarf mehr ("flow=True, reversed bleibt False"), obwohl sie
# gegenueber der urspruenglichen Fragment-Konvention sehr wohl umgedreht
# wurden. Aus der Erstanalyse (Kind/kind_group-Kombinationskoerung VOR jeder
# Skriptausfuehrung) ist zweifelsfrei bekannt: von den 159 reads-Kanten, die
# flow=true werden, war GENAU EINE bereits in den Fragmenten korrekt in
# Artefakt->Skript-Richtung notiert (output/noe/alignment_*.json ->
# scripts/noe/extract_noe_vector_layers.py); alle uebrigen 158 lagen als
# Skript->Datei vor und wurden umgedreht. Kanten anderer Art (writes,
# invokes make_target->script) waren nie umzudrehen (0 Faelle laut
# urspruenglicher Kombinationsauszaehlung). Dieser Override macht das
# Ergebnis unabhaengig davon, ob dieser Lauf die tatsaechliche Vertauschung
# vollzieht oder ob sie (durch den versehentlichen Vorlauf) bereits vollzogen
# vorliegt.
ALREADY_CORRECT_READS_EDGE = ('output/noe/alignment_*.json', 'scripts/noe/extract_noe_vector_layers.py')
for e in edges:
    if e['kind'] == 'reads' and e.get('flow'):
        e['reversed'] = (e['from'], e['to']) != ALREADY_CORRECT_READS_EDGE
    elif e['kind'] != 'reads':
        # writes/invokes/imports/depends: laut Erstanalyse nie ein Reversal noetig/erfolgt
        pass

# reversed-Zaehlung robust direkt aus den Kanten ziehen
n_reversed = sum(1 for e in edges if e.get('reversed'))

# alle bisherigen (Fragment-)Kanten sind per Definition nicht abgeleitet
for e in edges:
    e.setdefault('derived', False)

# Reparatur/Idempotenz: dieses Skript kann (wie oben dokumentiert) versehentlich
# zweimal auf demselben Output laufen. Vor dem Neu-Ableiten alle Kanten aus
# einem frueheren Lauf dieses Skripts entfernen, sonst verdoppeln sich die
# provides-Kanten bei jedem erneuten Lauf.
edges[:] = [e for e in edges if not e.get('derived')]

# ---------------------------------------------------------------------------
# MANGEL 5 -- Skript/Modul-Grenze: abgeleitete provides-Kanten
# ---------------------------------------------------------------------------
# Ein Teil der Datei-Ein-/Ausgabe findet nicht in den Skripten selbst statt,
# sondern in Modulen des windkraft-Pakets. Skripte (und andere Module) sind
# mit diesen Modulen nur ueber imports-Kanten verbunden, und imports-Kanten
# tragen bewusst flow: false (sie modellieren Codeabhaengigkeit, keinen
# Datenfluss). Dadurch reisst der Datenflusspfad an der Modulgrenze ab:
# Rohdatei -> Modul -> (Abbruch), obwohl das Modul die Daten im Auftrag des
# importierenden Akteurs liest/schreibt und dieser (das Modul selbst oder,
# nach evtl. weiteren Import-Ebenen, ein Skript) daraus einen Layer baut.
#
# Fix: fuer jede imports-Kante Importeur -> M, bei der M ein Modul des
# windkraft-Pakets ist UND M selbst mindestens eine eigene reads/writes-Kante
# mit flow=true hat (M macht also selbst Datei-I/O), wird eine abgeleitete
# Gegenkante M -> Importeur mit kind="provides", flow=true, derived=true
# eingefuegt (evidence = Evidenz der zugrunde liegenden imports-Kante).
#
# "Importeur" ist bewusst NICHT auf kind=='script' beschraenkt: module->
# module-Importe (z. B. windkraft/calc/abschichtung_common.py importiert
# windkraft/calc/wind_zones.py) sind exakt dieselbe Luecke eine Ebene
# tiefer -- die Delegation reicht mehrere Modul-Ebenen weit, bevor sie
# wieder in einem Skript "auftaucht" (oder, wie bei abschichtung_common.py,
# das Modul schreibt den finalen Layer sogar selbst). Ohne diese
# Verallgemeinerung wuerde z. B. der Pfad
# output/steiermark_zonen/sapro2026/sapro2026_zonen.geojson -> wind_zones.py
# an der naechsten Modulgrenze (wind_zones.py -> abschichtung_common.py)
# erneut abreissen.
#
# "eigene flow-Kante" bezieht sich ausschliesslich auf die urspruenglichen
# reads/writes-Kanten der Fragmente (vor dieser Erweiterung) -- ein einziger
# flacher Durchlauf, keine Transitivitaet ueber bereits abgeleitete
# provides-Kanten (macht das Ergebnis unabhaengig von der Iterationsreihenfolge
# und vermeidet Rueckkopplung).

own_flow_edge_count = {}
for e in edges:
    if not e.get('flow') or e['kind'] not in ('reads', 'writes'):
        continue
    own_flow_edge_count[e['from']] = own_flow_edge_count.get(e['from'], 0) + 1
    own_flow_edge_count[e['to']] = own_flow_edge_count.get(e['to'], 0) + 1

derived_edges = []
for e in list(edges):
    if e['kind'] != 'imports':
        continue
    importer, m = e['from'], e['to']
    if importer not in nodes or m not in nodes:
        continue
    if nodes[m]['kind'] != 'module' or not m.startswith('windkraft/'):
        continue
    if own_flow_edge_count.get(m, 0) == 0:
        continue
    derived_edges.append({
        'from': m,
        'to': importer,
        'kind': 'provides',
        'optional': False,
        'evidence': list(e.get('evidence') or []),
        'note': 'abgeleitet: Modul liest/schreibt im Auftrag des importierenden Skripts',
        'sources': list(e.get('sources') or []),
        'flow': True,
        'reversed': False,
        'derived': True,
    })

edges.extend(derived_edges)
n_derived = len(derived_edges)

# ---------------------------------------------------------------------------
# MANGEL 3a -- raw_class-Konflikte aufloesen
# ---------------------------------------------------------------------------

def add_note(nid, text):
    """Idempotent: haengt text nur an, wenn er nicht schon (als eines der
    ' | '-getrennten Segmente) vorhanden ist -- notwendig, weil dieses Skript
    versehentlich zweimal auf demselben Output gelaufen ist (docs/dataflow/
    ist ungetrackt, ein git checkout davor war ein no-op) und sonst Notizen
    dupliziert wuerden."""
    n = nodes[nid]
    old = n.get('notes') or ''
    segments = [s for s in old.split(' | ')] if old else []
    if text in segments:
        return
    segments.append(text)
    n['notes'] = ' | '.join(segments)

RAW_README = "data/README.md"
MIG_MAP = "docs/MIGRATION_MAP.tsv"

CFG_NOTE = ("RAW_CLASS-ENTSCHEIDUNG: code. Config-Key ist Teil der Codebasis "
            "(config/config.json + windkraft/config.py), keine eigenstaendigen "
            "Daten-Bytes auf der Platte -- raw_class beschreibt Byte-Herkunft, "
            "hier gibt es nur den Code selbst. Konsistent mit den bereits "
            "unstrittig als code eingestuften uebrigen cfg:paths.*-Keys.")

CFG_KEYS = [
    'cfg:paths.vgd', 'cfg:paths.osm_dir', 'cfg:paths.dgm', 'cfg:paths.wind_pd_150',
    'cfg:paths.nsg_zip', 'cfg:paths.powerlines_gpkg', 'cfg:paths.data_dir',
    'cfg:paths.wind_pd_100', 'cfg:paths.nsg_gpkg', 'cfg:paths.output_dir',
]
for nid in CFG_KEYS:
    nodes[nid]['raw_class'] = 'code'
    add_note(nid, CFG_NOTE)

RAW_DATA = {
    'data/admin_boundaries/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp':
        f"{RAW_README} §2: BEV, generalisiert 1:50.000, extern bezogen (Neu beschaffbar: ja, eingeschraenkt); kein Hinweis auf Handarbeit.",
    'data/DGM_R25.tif':
        f"{RAW_README} §2: BEV/Land Austria, manueller Download extern, Neu beschaffbar: ja, eingeschraenkt; keine Handdigitalisierung.",
    'data/AUT_power-density_150m.tif':
        f"{RAW_README} §2: Global Wind Atlas (globalwindatlas.info), Neu beschaffbar: ja.",
    'data/naturschutzgebiete/SG_AT_2024_v_April_Stand_3_April_2024.zip':
        f"{RAW_README} §2: Umweltbundesamt/DORIS OGD, Neu beschaffbar: ja, eingeschraenkt.",
    'data/austria-260330.osm.pbf':
        f"{RAW_README} §2: Geofabrik-Download (download.geofabrik.de), ODbL 1.0, Neu beschaffbar: ja.",
    'data/zonierung_noe.json':
        f"{RAW_README} §3.1: WFS-Export von data.gv.at (LGBl. 47/2024), Neu beschaffbar: ja -- unveraenderter externer Datenexport, keine Handdigitalisierung wie bei luca_zonen (§0.1).",
    'data/WK_Eignungszonen.zip':
        f"{RAW_README} §3.1: Land Burgenland, Neu beschaffbar: ja, eingeschraenkt.",
    'data/RED_III_Windkraftbeschleunigungszone.zip':
        f"{RAW_README} §3.1: Land Kaernten, Neu beschaffbar: ja, eingeschraenkt.",
    'data/new_widmungs_data/niederoesterreich/RRU_WI_HUELLE.gpkg':
        f"{RAW_README} §3.3: Amt der NOE Landesregierung, NOE Atlas OGD.",
    'data/new_widmungs_data/oberoesterreich/FLWI_WIDMUNGEN_F.zip':
        f"{RAW_README} §3.3: Land OOE, DORIS, CC-BY 4.0.",
    'data/new_widmungs_data/salzburg/Flaechenwidmung_Shapefile.zip':
        f"{RAW_README} §3.3: Land Salzburg, SAGIS OGD.",
    'data/new_widmungs_data/steiermark/Bauland.zip':
        f"{RAW_README} §3.3: Land Steiermark OGD.",
    'data/flächenwidmungen/Flaewi.shp.zip':
        f"{RAW_README} §3.3: Land Steiermark OGD, zweite zwingend benoetigte Stmk-Quelle (Gruenland/Freizeit, EPSG:4258).",
    'data/new_widmungs_data/kaernten/flawi_ktn_gpkg.zip':
        f"{RAW_README} §3.3: Land Kaernten, KAGIS OGD.",
    'data/new_widmungs_data/vorarlberg/fwp_flaeche.gpkg':
        f"{RAW_README} §3.3: Land Vorarlberg, VoGIS OGD.",
    'data/new_widmungs_data/wien/genflwidmung_wien.geojson':
        f"{RAW_README} §3.3: Stadt Wien WFS ogdwien:GENFLWIDMUNGOGD, manuell per curl bezogen -- Bytes selbst unveraendert extern; manueller Bezugsweg begruendet keine manual-Klassifikation (Regel: manual = haendisch ERSTELLT).",
    'data/flächenwidmungen/WIDMUNGSFLAECHEN.zip':
        f"{RAW_README} §3.3: Land Burgenland OGD.",
    'data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf':
        f"{RAW_README} §3.2: Amt der NOE Landesregierung, Neu beschaffbar: ja, eingeschraenkt -- extern bezogener Kartenscan, unveraendert.",
}
for nid, cite in RAW_DATA.items():
    nodes[nid]['raw_class'] = 'raw'
    add_note(nid, f"RAW_CLASS-ENTSCHEIDUNG: raw. {cite}")

nodes['data/osm_power_lines.gpkg']['raw_class'] = 'derived_elsewhere'
add_note('data/osm_power_lines.gpkg',
    f"RAW_CLASS-ENTSCHEIDUNG: derived_elsewhere. {RAW_README} §2: 'abgeleitet aus Geofabrik-OSM "
    "... (Export aus OSM-PBF)'; per {mig} als Hardlink aus windkraft_ö_karten/data/ uebernommen -- "
    "die vorliegenden Bytes stammen aus einem Export im Alt-Projekt, nicht aus einem Lauf in diesem "
    "Repo -- derived_elsewhere (kein Handprodukt, daher nicht manual).".format(mig=MIG_MAP))

# output/-Konflikte: Bytes-Herkunft entlang der Hardlink->Kopie-Migration (§9) bzw. RUN1_VERGLEICH.md
GEOPARQUET = 'output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet'
nodes[GEOPARQUET]['raw_class'] = 'derived_elsewhere'
nodes[GEOPARQUET]['layer'] = 'intermediate'
add_note(GEOPARQUET,
    f"RAW_CLASS/LAYER-ENTSCHEIDUNG: derived_elsewhere, layer=intermediate. {RAW_README} §9 "
    "'Bekannter Verstoss -- behoben': Datei war per Hardlink migriert, beim Umstieg auf echte Kopie "
    "'Inhalt byteidentisch zum Alt-Repo geprueft (cmp)' -- die vorliegenden Bytes stammen aus einem "
    "Lauf von scripts/preprocessing/export_at_dkm_geoparquet.py im ALTEN Repo (windkraft_ö_karten), "
    "nicht aus einem Lauf hier, obwohl das Erzeugerskript hier byteidentisch vorliegt -> "
    "derived_elsewhere per Definition. layer=intermediate: wird von windkraft/calc/hig_detection.py "
    "weitergelesen, kein Endprodukt.")

NOE_PRECOND = [
    'output/noe/pdf_750m_geb.geojson', 'output/noe/pdf_750m_gwr.geojson',
    'output/noe/pdf_750m_gruenland_widmung.geojson', 'output/noe/pdf_750m_*.geojson',
]
for nid in NOE_PRECOND:
    nodes[nid]['raw_class'] = 'derived_elsewhere'
    add_note(nid,
        f"RAW_CLASS-ENTSCHEIDUNG: derived_elsewhere. {RAW_README} §9: eines der '7 tatsaechlichen "
        "Schreibziele' unter output/noe/, beim Hardlink->Kopie-Fix 'Inhalt byteidentisch zum Alt-Repo "
        "geprueft (cmp)' -- Bytes stammen aus einem Lauf von scripts/noe/extract_noe_vector_layers.py "
        "im Alt-Repo. RUN1_VERGLEICH.md dokumentiert nur einen Lauf der 5 widmung_v2-Stufen in diesem "
        "Repo, nicht der scripts/noe/-Precondition-Skripte -> derived_elsewhere.")

NOE_HIG_SOURCE = [
    'output/noe/pdf_hig_source_geb.geojson', 'output/noe/pdf_hig_source_gwr.geojson',
    'output/noe/pdf_hig_source_gruenland_widmung.geojson',
]
for nid in NOE_HIG_SOURCE:
    nodes[nid]['raw_class'] = 'derived_elsewhere'
    nodes[nid]['layer'] = 'intermediate'
    add_note(nid,
        f"RAW_CLASS/LAYER-ENTSCHEIDUNG: derived_elsewhere, layer=intermediate. {RAW_README} §9, "
        "selbe Schreibziel-Liste wie pdf_750m_*.geojson -- byteidentisch zum Alt-Repo, Bytes stammen "
        "aus einem dortigen Lauf, nicht von hier. layer=intermediate: wird von "
        "02_build_hig_sources.py zum Bau von layer:noe_pdf_hig_source gelesen (siehe auch "
        "verified_dead-Befund auf diesem Node).")

ZONING_VECTORS = [
    'output/abschichtung_widmung_v2/zoning_vectors/wohn_misch_combined.gpkg',
    'output/abschichtung_widmung_v2/zoning_vectors/haeuser_im_gruenen_combined.gpkg',
    'output/abschichtung_widmung_v2/zoning_vectors/industrie_negativ_combined.gpkg',
]
for nid in ZONING_VECTORS:
    nodes[nid]['raw_class'] = 'derived_in_repo'
    add_note(nid,
        "RAW_CLASS-ENTSCHEIDUNG: derived_in_repo. docs/FOLLOWUPS.md (Schreibziel-Audit): "
        "output/abschichtung_widmung_v2/zoning_vectors/*.gpkg wird bei JEDEM Lauf von "
        "01_build_official_zoning_layers.py neu geschrieben (kein Checkpoint-Schutz). "
        "docs/RUN1_VERGLEICH.md §2 bestaetigt: Stufe 1 lief am 06.09.2026 erfolgreich in DIESEM "
        "Repo. Anders als output/noe/ und output/kataster/ ist dieser Pfad NICHT Teil der "
        f"Hardlink-Migration ({RAW_README} §9 listet ihn nicht) -> Bytes stammen aus einem Lauf hier.")

REF_TIF = 'output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif'
nodes[REF_TIF]['raw_class'] = 'derived_elsewhere'
nodes[REF_TIF]['layer'] = 'output'
add_note(REF_TIF,
    "RAW_CLASS/LAYER-ENTSCHEIDUNG: derived_elsewhere, layer=output. docs/RUN1_VERGLEICH.md §9: "
    "Referenz-TIF-Inode vor/nach dem Lauf unveraendert, SHA-256 identisch zur Kopie in "
    "windkraft_ö_karten (Alt-Repo) -- 'unterschiedliche Inodes ... aber inhaltlich exakt gleich' -> "
    "echte Kopie des im Alt-Repo erzeugten Rasters, in DIESEM Repo nie neu gerechnet (dient als "
    "unangetastete Vergleichsbasis) -> derived_elsewhere, obwohl der Erzeugerskriptpfad "
    "(04_create_distance_zones.py) hier identisch vorliegt. Die *_run1.tif-Variante dagegen stammt "
    "aus einem echten Lauf hier (siehe docs/RUN1_VERGLEICH.md) und bleibt derived_in_repo "
    "(unveraendert, war kein Konflikt).")

# einziger wirklich unentscheidbarer Fall -> bleibt in conflicts, aber mit erklaerender Notiz
WINDKRAFT_AZ = 'data/WINDKRAFT_AUSSCHLUSSZONE.zip'
add_note(WINDKRAFT_AZ,
    "RAW_CLASS bleibt UNENTSCHIEDEN (siehe flow_graph.json.conflicts): "
    f"{RAW_README} §3.1 fuehrt fuer diese Datei ALLE Felder (Herkunft, Lizenz, UND -- anders als bei "
    "jeder anderen Zeile der Tabelle -- 'Neu beschaffbar') als 'unbekannt -- zu klaeren'. Die "
    "raw/manual-Unterscheidung haengt genau an der Reproduzierbarkeit/Handarbeits-Frage, und dazu "
    "gibt es hier keinerlei Beleg in eine der beiden Richtungen (kein Hinweis auf Handdigitalisierung "
    "wie bei luca_zonen §0.1, aber auch keine Quellenangabe wie bei den uebrigen Zonen-ZIPs) -- "
    "wirklich unentscheidbar mit den vorliegenden Belegen.")

# Alle geloesten Konflikte aus der Liste entfernen -- nur der wirklich unentscheidbare bleibt
resolved_ids = set(CFG_KEYS) | set(RAW_DATA) | {'data/osm_power_lines.gpkg', GEOPARQUET} \
    | set(NOE_PRECOND) | set(NOE_HIG_SOURCE) | set(ZONING_VECTORS) | {REF_TIF}
remaining_conflicts = [c for c in d['conflicts'] if c['node'] not in resolved_ids]
assert len(remaining_conflicts) == 1 and remaining_conflicts[0]['node'] == WINDKRAFT_AZ, remaining_conflicts
d['conflicts'] = remaining_conflicts

# ---------------------------------------------------------------------------
# MANGEL 3b -- stage fuer die 7 Nodes mit stage: null
# ---------------------------------------------------------------------------

STAGE_CONTAINER = [
    'output', 'output/.DS_Store', 'output/abschichtung', 'output/abschichtung_widmung_v2',
]
for nid in STAGE_CONTAINER:
    nodes[nid]['stage'] = 'container'

STAGE_LEGACY_V1 = [
    'output/abschichtung/osm_wka_distance_zones.tif', 'output/abschichtung/simplified_150w.tif',
]
for nid in STAGE_LEGACY_V1:
    nodes[nid]['stage'] = 'legacy_v1'

SAPRO = 'output/steiermark_zonen/sapro2026/sapro2026_zonen.geojson'
nodes[SAPRO]['stage'] = 'input'
add_note(SAPRO,
    "STAGE-ENTSCHEIDUNG: input (Ermessensentscheidung, von keiner der beiden vorgegebenen neuen "
    "Stufen [legacy_v1, container] abgedeckt). Liegt zwar unter output/, nicht unter data/, "
    "funktioniert aber rollenidentisch zu den uebrigen Band-37-Referenzquellen (data/luca_zonen/*.shp, "
    "data/zonierung_noe.json, data/WK_Eignungszonen.zip -- alle stage=input): eine extern/anderswo "
    "erzeugte ('ausserhalb windkraft/ (PDF-Farbextraktion)', raw_class=derived_elsewhere) "
    "Referenzdatei, die windkraft/calc/wind_zones.py:155 als Eingabe liest, nicht Teil der "
    "stage0-5-Skriptketten dieses Repos.")

assert all(nodes[n]['stage'] is not None for n in STAGE_CONTAINER + STAGE_LEGACY_V1 + [SAPRO])

# ---------------------------------------------------------------------------
# MANGEL 4 -- empirische Befunde des Faktencheck-Agenten
# ---------------------------------------------------------------------------

VERIFIED_DEAD = {
    'cfg:paths.osm_dir':
        "FAKTENCHECK verified_dead: Pfad data/austria-260328-free.shp existiert nicht; der Zweig in "
        "windkraft/calc/abschichtung_common.py:474-485, der diesen Key nutzen wuerde, wird nie "
        "erreicht, weil pbf.exists() (Z.442-444) immer wahr ist. Toter Key.",
    'data/osm_power_lines.gpkg':
        "FAKTENCHECK verified_dead: nur im Nicht-PBF-Zweig gelesen "
        "(abschichtung_common.py:966-973), der nie eintritt (siehe cfg:paths.osm_dir); zusaetzlich "
        "existiert das Band power_380_400kv im aktuellen 38-Band-TIF nicht mehr. Doppelt tot.",
    'cfg:paths.wind_pd_100':
        "FAKTENCHECK verified_dead: Datei fehlt, und der Key wird nur in windkraft/config.py:24 "
        "aufgeloest, nie tatsaechlich gelesen.",
    'layer:noe_pdf_hig_source':
        "FAKTENCHECK verified_dead: erzeugt (von 02_build_hig_sources.py geschrieben), aber "
        "OFFICIAL_COVER_LAYERS (03_build_osm_layers.py:78-85) liest noe_pdf_750m_zones stattdessen; "
        "docs/widmung_v2_provenance.md:104-106 bestaetigt 'von niemandem gelesen'.",
    'output/noe/pdf_hig_source_*.geojson':
        "FAKTENCHECK verified_dead: die Dateien werden zwar strukturell von 02_build_hig_sources.py "
        "und windkraft/calc/hig_source_masks.py gelesen (daher hier ggf. consumers>=1 in den "
        "berechneten Graden -- das widerspricht dem Befund NICHT), aber der einzige Zweck dieser "
        "Lesung ist der Bau von layer:noe_pdf_hig_source, das seinerseits von niemandem downstream "
        "referenziert wird (siehe dortiger Befund, docs/widmung_v2_provenance.md:104-106,152) -- "
        "praktisch ein fauler Pfad trotz vorhandener Kanten.",
    'scripts/noe/derive_pdf_hig_sources.py':
        "FAKTENCHECK verified_dead: vollstaendig redundant -- extract_noe_vector_layers.py:286 ruft "
        "bereits derive_layer_files(OUT_DIR) mit identischem Verzeichnis auf; die Funktion hat nur "
        "diesen einen Parameter.",
    'scripts/webmap/build_layer_viewer.py':
        "FAKTENCHECK verified_dead: wuerde mit NameError abbrechen (SIMPLIFIED_DEFAULT_VISIBLE "
        "Z.304, FINAL_LAYER_NAMES Z.324 nirgends definiert).",
    'scripts/analysis/build_v2_dashboard_data.py':
        "FAKTENCHECK verified_dead: EXCLUSION_LAYERS (Z.66-93) nennt 8 Bandnamen, die im heutigen "
        "38-Band-TIF fehlen.",
    'data/adressregister/Aktualitaetsstand.txt':
        "FAKTENCHECK verified_dead: keine Referenz im Code.",
    'data/windkraftzonen_shapefile_2024.json':
        "FAKTENCHECK verified_dead: keine Referenz im Code (siehe auch data/README.md §3.1/§7 -- "
        "Naheduplikat von zonierung_noe.json, von keinem Skript der Referenzkette gelesen).",
    'data/adressregister/.claude':
        "FAKTENCHECK verified_dead: keine Referenz im Code (Werkzeug-/Session-Metadaten).",
    'data/.DS_Store':
        "FAKTENCHECK verified_dead: keine Referenz im Code (Finder-Metadatendatei).",
    'data/kataster/.DS_Store':
        "FAKTENCHECK verified_dead: keine Referenz im Code (Finder-Metadatendatei).",
}
for nid, note in VERIFIED_DEAD.items():
    assert nid in nodes, nid
    nodes[nid].setdefault('flags', {})
    nodes[nid]['flags']['verified_dead'] = True
    add_note(nid, note)

# ---------------------------------------------------------------------------
# MANGEL 2 -- producers/consumers + Flags aus flow==true-Kanten
# ---------------------------------------------------------------------------

for n in d['nodes']:
    n['producers'] = 0
    n['consumers'] = 0

for e in edges:
    if not e.get('flow'):
        continue
    if e['kind'] == 'writes':
        # script/module -> Datei/Layer: eingehende writes-Kante am Ziel zaehlen
        if e['to'] in nodes:
            nodes[e['to']]['producers'] += 1
    elif e['kind'] == 'reads':
        # Datei/Layer -> script/module: ausgehende reads-Kante an der QUELLE (Datei) zaehlen
        if e['from'] in nodes:
            nodes[e['from']]['consumers'] += 1

TERMINAL_PRODUCTS = {
    'output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif',
    'output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif',
    'output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.bands.json',
    'output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.bands.json',
    'output/abschichtung_widmung_v2/hig_huellen.gpkg',
    'docs/FOLLOWUPS.md', 'docs/RUN1_VERGLEICH.md', 'docs/widmung_v2_provenance.md',
}
for nid in TERMINAL_PRODUCTS:
    assert nid in nodes, nid

RAW_LIKE = {'raw', 'manual'}

# generalisierter (flow-basierter) Nachfolger des in v1 kaputten dead_end-Flags
# (1_merge.py: out_degree==0 auf UNKORRIGIERTEN Graden -- markierte 164/220
# Nodes, praktisch wertlos, siehe README). Hier stattdessen ueber ALLE
# flow==true-Kanten (writes, reads, invokes make_target->script, UND die in
# Mangel 5 neu abgeleiteten provides-Kanten) generisch fuer file/layer/module/
# script: flow_in = eingehende, flow_out = ausgehende flow-Kanten. Fuer
# file/layer-Nodes ist das rechnerisch identisch zu unused (flow_in==producers,
# flow_out==consumers); der Mehrwert liegt bei module/script-Nodes, die vorher
# gar keine dead_end-Bewertung hatten -- z. B. ein Modul, das gelesen wird,
# aber (vor Mangel 5) nichts zurueckliefert.
flow_in_count = {}
flow_out_count = {}
for e in edges:
    if not e.get('flow'):
        continue
    flow_out_count[e['from']] = flow_out_count.get(e['from'], 0) + 1
    flow_in_count[e['to']] = flow_in_count.get(e['to'], 0) + 1

DEAD_END_KINDS = {'file', 'layer', 'module', 'script'}

# make_target-Erreichbarkeit fuer 'unreachable' (nur kind=='script')
make_targets = {n['id'] for n in d['nodes'] if n['kind'] == 'make_target'}
reachable_scripts = set()
frontier = set(make_targets)
seen_targets = set()
while frontier:
    cur = frontier.pop()
    if cur in seen_targets:
        continue
    seen_targets.add(cur)
    for e in edges:
        if e['from'] != cur:
            continue
        if e['kind'] == 'invokes' and e.get('flow') and e['to'] in nodes and nodes[e['to']]['kind'] == 'script':
            reachable_scripts.add(e['to'])
        if e['kind'] == 'depends' and e['to'] in make_targets:
            frontier.add(e['to'])

for n in d['nodes']:
    nid = n['id']
    # alte, unter der kaputten Kantenrichtung berechneten v1-Flags orphan_source/
    # stub verwerfen -- nur verified_dead (Mangel 4, oben gesetzt) wird uebernommen.
    # dead_end wird unten neu (und korrekt, flow-basiert) berechnet -- siehe Mangel 5.
    flags = {'verified_dead': True} if nid in VERIFIED_DEAD else {}
    kind = n['kind']
    producers, consumers = n['producers'], n['consumers']

    if kind in ('file', 'layer'):
        is_unused = producers >= 1 and consumers == 0
        is_ext_input = producers == 0 and consumers >= 1 and n.get('raw_class') not in RAW_LIKE
        is_true_raw = producers == 0 and consumers >= 1 and n.get('raw_class') in RAW_LIKE
        if is_unused:
            flags['unused'] = True
        if is_ext_input:
            flags['external_input'] = True
        if is_true_raw:
            flags['true_raw'] = True
        if nid in TERMINAL_PRODUCTS:
            flags['terminal_product'] = True

    if kind == 'script':
        outputs = [e['to'] for e in edges if e['kind'] == 'writes' and e.get('flow') and e['from'] == nid]
        outputs_read = any(nodes[o]['consumers'] >= 1 for o in outputs if o in nodes)
        called_by_make = nid in reachable_scripts
        if not called_by_make and not outputs_read:
            flags['unreachable'] = True

    if kind in DEAD_END_KINDS and nid not in TERMINAL_PRODUCTS:
        if flow_in_count.get(nid, 0) >= 1 and flow_out_count.get(nid, 0) == 0:
            flags['dead_end'] = True

    n['flags'] = flags

# ---------------------------------------------------------------------------
# Meta + direction_unresolved + Ausgabe schreiben
# ---------------------------------------------------------------------------

TZ = timezone(timedelta(hours=2))
d['meta']['schema_version'] = 2
d['meta']['fixed_at'] = datetime.now(TZ).isoformat()
d['meta']['fix_script'] = 'docs/dataflow/src/2_normalize.py'
d['meta']['reversed_edge_count'] = n_reversed
d['meta']['direction_unresolved_count'] = len(direction_unresolved)
d['meta']['conflicts_resolved_count'] = d['meta']['conflict_count'] - len(d['conflicts'])
d['meta']['conflicts_remaining_count'] = len(d['conflicts'])
d['meta']['derived_edge_count'] = n_derived
d['meta']['edge_count'] = len(edges)

d['direction_unresolved'] = direction_unresolved

DF.joinpath('flow_graph.json').write_text(
    json.dumps(d, indent=2, ensure_ascii=False, sort_keys=False) + '\n', encoding='utf-8')

# ---------------------------------------------------------------------------
# nodes.tsv
# ---------------------------------------------------------------------------

with open(DF / 'nodes.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['id', 'kind', 'layer', 'stage', 'raw_class', 'in_degree', 'out_degree',
                'producers', 'consumers', 'flags', 'path', 'label', 'notes'])
    for n in sorted(d['nodes'], key=lambda n: n['id']):
        flagstr = ','.join(sorted(k for k, v in (n.get('flags') or {}).items() if v))
        w.writerow([
            n['id'], n['kind'], n.get('layer') or '', n.get('stage') or '',
            n.get('raw_class') or '', n.get('in_degree', ''), n.get('out_degree', ''),
            n.get('producers', 0), n.get('consumers', 0), flagstr,
            n.get('path') or '', n.get('label') or '', n.get('notes') or '',
        ])

# ---------------------------------------------------------------------------
# edges.tsv
# ---------------------------------------------------------------------------

with open(DF / 'edges.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['from', 'to', 'kind', 'flow', 'reversed', 'derived', 'optional', 'evidence', 'note'])
    for e in edges:
        ev = '; '.join(e.get('evidence') or [])
        w.writerow([
            e['from'], e['to'], e['kind'], str(bool(e.get('flow'))).lower(),
            str(bool(e.get('reversed'))).lower(), str(bool(e.get('derived'))).lower(),
            str(bool(e.get('optional'))).lower(),
            ev, e.get('note') or '',
        ])

print(f"derived (provides) edges added: {n_derived}")
print(f"reversed edges: {n_reversed}")
print(f"direction_unresolved: {len(direction_unresolved)}")
for u in direction_unresolved:
    print('  ', u['kind'], u['from'], '<->', u['to'])
print(f"remaining conflicts: {len(d['conflicts'])}")
print(f"nodes: {len(d['nodes'])}  edges: {len(d['edges'])}")

unused = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('unused') and not (n.get('flags') or {}).get('terminal_product'))
ext_input = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('external_input'))
unreachable = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('unreachable'))
true_raw = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('true_raw'))
terminal = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('terminal_product'))
verified_dead = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('verified_dead'))
dead_end = sorted(n['id'] for n in d['nodes'] if (n.get('flags') or {}).get('dead_end'))

print(f"\nunused (ohne terminal_product): {len(unused)}")
for x in unused: print('  ', x)
print(f"\nexternal_input: {len(ext_input)}")
for x in ext_input: print('  ', x)
print(f"\nunreachable: {len(unreachable)}")
for x in unreachable: print('  ', x)
print(f"\ntrue_raw: {len(true_raw)}")
print(f"\nterminal_product: {len(terminal)}")
for x in terminal: print('  ', x)
print(f"\nverified_dead: {len(verified_dead)}")
print(f"\ndead_end (flow-basiert, generalisiert ueber file/layer/module/script): {len(dead_end)}")
for x in dead_end: print('  ', x)

from collections import Counter
stages = Counter(n.get('stage') for n in d['nodes'])
print("\nstage counts:")
for s, c in sorted(stages.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"  {s}: {c}")
