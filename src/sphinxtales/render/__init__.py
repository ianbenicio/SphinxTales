"""Diagramacao: do IR ao PDF, via Typst.

Formato de pagina, margens, corpo e fontes sao parametros do tema. O emissor
nao conhece nenhum valor tipografico, e o tema nao conhece nenhum bloco.
"""

from sphinxtales.render.compilar import (
    CompilacaoFalhou,
    contar_paginas,
    escrever_typst,
    renderizar,
)
from sphinxtales.render.emissor import (
    EMISSORES_DE_BLOCO,
    EMISSORES_INLINE,
    emitir_documento,
    escapar,
    literal,
)
from sphinxtales.render.tema import Tema

__all__ = [
    "CompilacaoFalhou",
    "EMISSORES_DE_BLOCO",
    "EMISSORES_INLINE",
    "Tema",
    "contar_paginas",
    "emitir_documento",
    "escapar",
    "escrever_typst",
    "literal",
    "renderizar",
]
