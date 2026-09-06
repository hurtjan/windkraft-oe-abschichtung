"""Verwaltungsgrenzen laden (VGD Shapefile)."""

import geopandas as gpd


def load_vgd(path):
    """Lädt das VGD-Shapefile."""
    return gpd.read_file(path)


def load_laender(vgd):
    """Dissolve nach Bundesland."""
    return vgd.dissolve(by="BL").reset_index()


def load_bezirke(vgd):
    """Dissolve nach Bezirk."""
    return vgd.dissolve(by="PB").reset_index()


def load_austria(laender):
    """Dissolve zu Gesamtösterreich."""
    return laender.dissolve()
