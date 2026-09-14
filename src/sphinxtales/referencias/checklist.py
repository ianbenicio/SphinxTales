"""Referencia de estrutura vira checklist consumivel pelo loop.

O S8 precisa perguntar, para cada capitulo, se o checklist da referencia
estrutural foi cumprido. Para isso o checklist tem que ser uma lista de itens
discretos e ordenados, nao um paragrafo descrevendo a estrutura.

So referencia de estrutura vira checklist, e so depois de confirmada. As demais
contribuicoes entram como contexto na materializacao.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sphinxtales.confirmacao import EstadoDeConfirmacao
from sphinxtales.referencias.acervo import AcervoDeReferencias
from sphinxtales.referencias.modelo import Referencia, TipoDeContribuicao


class ItemDeChecklist(BaseModel):
    """Um estagio que o capitulo precisa cumprir."""

    model_config = ConfigDict(extra="forbid")

    referencia: str = Field(min_length=1)
    ordem: int = Field(ge=1)
    descricao: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"[{self.ordem}] {self.descricao}"


def checklist_de(referencia: Referencia) -> list[ItemDeChecklist]:
    """Itens da referencia, ou lista vazia se ela nao qualifica.

    Nao levanta erro para referencia de outro tipo ou nao confirmada: o loop
    pede o checklist de tudo e espera vazio quando nao ha o que cobrar.
    """
    if referencia.contribuicao is not TipoDeContribuicao.ESTRUTURA:
        return []
    if referencia.estado is not EstadoDeConfirmacao.CONFIRMADA:
        return []
    if referencia.decomposicao is None:
        return []

    return [
        ItemDeChecklist(
            referencia=referencia.id, ordem=item.ordem, descricao=item.texto
        )
        for item in referencia.decomposicao.itens
    ]


def checklist_do_acervo(acervo: AcervoDeReferencias) -> list[ItemDeChecklist]:
    """Todos os itens cobraveis, de todas as referencias estruturais."""
    itens: list[ItemDeChecklist] = []
    for referencia in acervo.referencias:
        itens.extend(checklist_de(referencia))
    return itens
