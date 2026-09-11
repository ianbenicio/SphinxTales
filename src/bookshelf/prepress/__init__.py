"""Prepress: da pagina ao arquivo que a grafica aceita.

Formato de corte, sangria, marcas e perfil de saida sao parametros deste
pacote, nunca constantes dele. Quem decide os valores e a grafica.
"""

from bookshelf.prepress.geometria import Formato, mm
from bookshelf.prepress.pdfx import (
    ConversaoFalhou,
    GhostscriptAusente,
    PerfilDeSaida,
    converter,
    localizar_ghostscript,
    perfil_padrao_do_ghostscript,
)
from bookshelf.prepress.prova import OpcoesDaProva, gerar_postscript

__all__ = [
    "ConversaoFalhou",
    "Formato",
    "GhostscriptAusente",
    "OpcoesDaProva",
    "PerfilDeSaida",
    "converter",
    "gerar_postscript",
    "localizar_ghostscript",
    "mm",
    "perfil_padrao_do_ghostscript",
]
