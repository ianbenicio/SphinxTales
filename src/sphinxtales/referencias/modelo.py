"""Referencias enviadas pelo autor, e a decomposicao que ele confirma.

Uma referencia entra no sistema por upload e por mais nada. Descoberta na web
fica fora do MVP, porque alucinar titulo de livro cria exposicao juridica e
nenhuma das duas coisas e necessaria para provar a tese.

O que o autor confirma nao e o arquivo, e a **decomposicao** dele: a lista de
itens que o sistema afirma ter extraido. Confirmar um arquivo inteiro seria
confirmar uma intencao. Confirmar uma lista e confirmar algo verificavel.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.confirmacao import (
    Confirmacao,
    EstadoDeConfirmacao,
    exigir_coerencia,
)

TAMANHO_DO_ID = 16


class TipoDeContribuicao(StrEnum):
    """O que esta referencia empresta ao livro. Lista fechada."""

    ESTRUTURA = "estrutura"
    TOM = "tom"
    PROFUNDIDADE = "profundidade"
    EXEMPLOS = "exemplos"
    CONTRA_EXEMPLO = "contra_exemplo"
    DIAGRAMACAO = "diagramacao"


class ItemDaDecomposicao(BaseModel):
    """Um item extraido, e o registro de o autor ter precisado reescreve-lo.

    `texto_proposto` so existe quando o autor mudou o item. Guardar o que o
    sistema tinha proposto e o que torna mensuravel o criterio de aceite: uma
    decomposicao que o autor precisa reescrever inteira falhou, mesmo que ele
    acabe confirmando.
    """

    model_config = ConfigDict(extra="forbid")

    ordem: int = Field(ge=1)
    texto: str = Field(min_length=1)
    texto_proposto: str | None = None

    @property
    def foi_editado(self) -> bool:
        return self.texto_proposto is not None

    @model_validator(mode="after")
    def _edicao_precisa_mudar_algo(self) -> ItemDaDecomposicao:
        if self.texto_proposto is not None and self.texto_proposto == self.texto:
            raise ValueError(
                f"item {self.ordem} marcado como editado, mas o texto e o mesmo"
            )
        return self


class Decomposicao(BaseModel):
    """A lista que o autor confirma, em ordem."""

    model_config = ConfigDict(extra="forbid")

    itens: list[ItemDaDecomposicao] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordens_sao_sequenciais(self) -> Decomposicao:
        ordens = [item.ordem for item in self.itens]
        if ordens != list(range(1, len(ordens) + 1)):
            raise ValueError(
                f"as ordens precisam ser 1..{len(ordens)} sem buracos, "
                f"e vieram {ordens}"
            )
        return self

    @property
    def itens_editados(self) -> list[ItemDaDecomposicao]:
        return [item for item in self.itens if item.foi_editado]

    @property
    def taxa_de_edicao(self) -> float:
        """Quanto da decomposicao o autor precisou reescrever, de 0 a 1."""
        return len(self.itens_editados) / len(self.itens)


def identificar(conteudo: bytes) -> str:
    """Id do conteudo: o mesmo arquivo enviado duas vezes e a mesma referencia."""
    return hashlib.sha256(conteudo).hexdigest()[:TAMANHO_DO_ID]


def resumir(conteudo: bytes) -> str:
    """Sha256 completo, para detectar que o arquivo mudou depois da analise."""
    return hashlib.sha256(conteudo).hexdigest()


class Referencia(BaseModel):
    """Material do autor, com o tipo de contribuicao que ele declarou."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    contribuicao: TipoDeContribuicao
    arquivo: str = Field(min_length=1)
    decomposicao: Decomposicao | None = None
    estado: EstadoDeConfirmacao = EstadoDeConfirmacao.PROPOSTA
    confirmacao: Confirmacao | None = None

    @model_validator(mode="after")
    def _confirmada_tem_registro(self) -> Referencia:
        exigir_coerencia(self.estado, self.confirmacao, f"referencia {self.id}")
        return self

    @model_validator(mode="after")
    def _nao_se_confirma_o_que_nao_foi_decomposto(self) -> Referencia:
        if self.estado is EstadoDeConfirmacao.CONFIRMADA and self.decomposicao is None:
            raise ValueError(
                f"referencia {self.id} esta confirmada sem decomposicao, "
                "e o que o autor confirma e a decomposicao"
            )
        return self

    @model_validator(mode="after")
    def _id_vem_do_conteudo(self) -> Referencia:
        if self.id != self.sha256[:TAMANHO_DO_ID]:
            raise ValueError(
                f"id {self.id} nao corresponde ao sha256 do arquivo desta referencia"
            )
        return self

    @classmethod
    def de_arquivo(
        cls, caminho: Path, contribuicao: TipoDeContribuicao, arquivo: str
    ) -> Referencia:
        conteudo = caminho.read_bytes()
        return cls(
            id=identificar(conteudo),
            nome=caminho.name,
            sha256=resumir(conteudo),
            contribuicao=contribuicao,
            arquivo=arquivo,
        )

    def arquivo_mudou(self, raiz: Path) -> bool:
        """O arquivo em disco ainda e o que foi decomposto?

        Se mudou, a decomposicao confirmada passou a descrever outra coisa.
        """
        caminho = raiz / self.arquivo
        if not caminho.exists():
            return True
        return resumir(caminho.read_bytes()) != self.sha256
