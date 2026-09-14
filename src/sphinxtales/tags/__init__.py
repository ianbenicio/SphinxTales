"""Taxonomia fechada de tags e o ciclo propor, confirmar, vincular.

Nenhuma tag influencia geracao sem registro de quem confirmou e quando. Isso e
invariante de modelo, nao disciplina de quem escreve o codigo.
"""

from sphinxtales.tags.acervo import Acervo, TagNaoEncontrada
from sphinxtales.tags.consolidacao import (
    Fusao,
    RelatorioDeConsolidacao,
    consolidar,
    normalizar_forte,
)
from sphinxtales.tags.materializacao import (
    materializar,
    tags_materializaveis,
)
from sphinxtales.tags.modelo import (
    CAMADA_CAPITULO,
    CAMADA_LIVRO,
    Confirmacao,
    EstadoDaTag,
    Tag,
    TipoDeTag,
    identificar,
    normalizar,
)

__all__ = [
    "Acervo",
    "CAMADA_CAPITULO",
    "CAMADA_LIVRO",
    "Confirmacao",
    "EstadoDaTag",
    "Fusao",
    "RelatorioDeConsolidacao",
    "Tag",
    "TagNaoEncontrada",
    "TipoDeTag",
    "consolidar",
    "identificar",
    "materializar",
    "normalizar",
    "normalizar_forte",
    "tags_materializaveis",
]
