"""Referencias por upload, com decomposicao que o autor confirma.

Descoberta na web fica fora do MVP. O que entra, entra porque o autor enviou, e
o que influencia a geracao influencia porque ele confirmou a decomposicao.
"""

from sphinxtales.referencias.acervo import (
    AcervoDeReferencias,
    ReferenciaNaoEncontrada,
    SemDecomposicao,
)
from sphinxtales.referencias.checklist import (
    ItemDeChecklist,
    checklist_de,
    checklist_do_acervo,
)
from sphinxtales.referencias.materializacao import (
    materializar,
    referencias_materializaveis,
)
from sphinxtales.referencias.modelo import (
    Decomposicao,
    ItemDaDecomposicao,
    Referencia,
    TipoDeContribuicao,
)

__all__ = [
    "AcervoDeReferencias",
    "Decomposicao",
    "ItemDaDecomposicao",
    "ItemDeChecklist",
    "Referencia",
    "ReferenciaNaoEncontrada",
    "SemDecomposicao",
    "TipoDeContribuicao",
    "checklist_de",
    "checklist_do_acervo",
    "materializar",
    "referencias_materializaveis",
]
