"""Gemeinsame PDF-Alignment-Utilities für NÖ-Karten.

Enthält render_pdf_viewport und Affin-Warp-Funktionen,
die von allen NÖ-Alignment-Skripten geteilt werden.
"""

import re
from pathlib import Path

import numpy as np


# Standard-Viewport-BBox für die NÖ-Zonierungskarten
VP_BBOX_DEFAULT = [62.39916, 2355.6873, 2928.2005, 28.28232]

# Vier Eckpunkte (lat, lon im MGI-Datum EPSG:4312) aus dem /GPTS-Eintrag im
# /Measure-Dictionary (referenziert vom /VP-Viewport-Dictionary der Seite 0)
# des GeoPDFs data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf.
# Verifizierbar per PyMuPDF:
#   doc = fitz.open(pdf_path); doc.xref_object(doc[0].xref)   # -> /VP [ << ... /Measure N 0 R >> ]
#   doc.xref_object(N)                                         # -> /Measure-Dict mit /GPTS
# liefert:
#   /Type /Measure /Subtype /GEO
#   /Bounds [ 0 1 0 0 1 0 1 1 ]
#   /GPTS [ 47.37897 14.27125 49.03936 14.20346 49.05484 17.31548 47.39358 17.2842 ]
#   /LPTS [ 0 1 0 0 1 0 1 1 ]
# Punktreihenfolge (siehe /LPTS, u=horizontal 0=links/1=rechts,
# v=vertikal 0=oben/1=unten; bestätigt durch die Kommentare in
# align_naturschutz.py:36-43 und align_pdf_shapefile.py):
#   LPTS (0,1) = BL (links unten), (0,0) = TL (links oben),
#   (1,0) = TR (rechts oben), (1,1) = BR (rechts unten)
GPTS_LATLON_MINDESTABSTAND = [
    (47.37897, 14.27125),  # BL
    (49.03936, 14.20346),  # TL
    (49.05484, 17.31548),  # TR
    (47.39358, 17.28420),  # BR
]

# Dieselben LPTS/Viewport gelten auch für die zwei weiteren TeilC-Karten
# (Naturschutz, Landschaftsraum), die über denselben Kartenrahmen gedruckt
# sind (siehe combine_all_layers.py).
LPTS_DEFAULT = [(0, 1), (0, 0), (1, 0), (1, 1)]

_PDF_PATH_MINDESTABSTAND_DEFAULT = Path(
    "data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf"
)


def get_gpts_latlon_mindestabstand(pdf_path=None):
    """Liest die vier GPTS-Eckpunkte (lat, lon, EPSG:4312) der Mindestabstandskarte.

    Liest sie bevorzugt direkt aus dem `/GPTS`-Eintrag im `/Measure`-Dictionary
    des GeoPDFs (via PyMuPDF/fitz und `xref_object`), damit die Zahlen
    jederzeit gegen die Originaldatei nachprüfbar sind. Fällt auf das
    hartkodierte Literal GPTS_LATLON_MINDESTABSTAND zurück, wenn das PDF
    fehlt, PyMuPDF nicht installiert ist oder das Auslesen aus anderen
    Gründen scheitert -- die Funktion funktioniert also auch ganz ohne PDF.

    Args:
        pdf_path: Pfad zum GeoPDF. Default: die Mindestabstandszonen-Karte
            unter data/nö_zonierung/.

    Returns:
        Liste von 4 (lat, lon)-Tupeln in der Reihenfolge BL, TL, TR, BR.
    """
    path = Path(pdf_path) if pdf_path is not None else _PDF_PATH_MINDESTABSTAND_DEFAULT
    try:
        import fitz  # PyMuPDF

        if not path.exists():
            raise FileNotFoundError(path)
        doc = fitz.open(path)
        try:
            page_obj = doc.xref_object(doc[0].xref)
            vp_match = re.search(r"/Measure\s+(\d+)\s+0\s+R", page_obj)
            if not vp_match:
                raise ValueError("Kein /Measure-Verweis im /VP-Dictionary gefunden")
            measure_obj = doc.xref_object(int(vp_match.group(1)))
            gpts_match = re.search(r"/GPTS\s*\[([^\]]+)\]", measure_obj)
            if not gpts_match:
                raise ValueError("Kein /GPTS-Eintrag im /Measure-Dictionary gefunden")
            nums = [float(x) for x in gpts_match.group(1).split()]
            if len(nums) != 8:
                raise ValueError(f"/GPTS hat {len(nums)} Werte, erwartet 8")
            return [(nums[i], nums[i + 1]) for i in range(0, 8, 2)]
        finally:
            doc.close()
    except Exception:
        return list(GPTS_LATLON_MINDESTABSTAND)


def render_pdf_viewport(pdf_path, vp_bbox, render_dpi=200):
    """Rendert einen PDF-Viewport als RGBA numpy-Array.

    Args:
        pdf_path: Pfad zur PDF-Datei
        vp_bbox: [x0, y0, x1, y1] Viewport-Koordinaten
        render_dpi: Render-Auflösung

    Returns:
        RGBA numpy array (H, W, 4)
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    page = doc[0]

    clip = fitz.Rect(*vp_bbox)
    mat = fitz.Matrix(render_dpi / 72, render_dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=True)

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 4).copy()
    doc.close()
    return img
