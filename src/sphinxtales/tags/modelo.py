"""Tipos de tag e a invariante que sustenta o ciclo de confirmacao.

A taxonomia e **fechada**: seis tipos, e um tipo fora da lista e rejeitado na
entrada pelo proprio esquema. Conteudo dentro do tipo e livre, porque o que o
autor diz sobre o livro dele nao cabe em enumeracao.

A invariante que importa: **tag confirmada exige registro de confirmacao**. Isso
nao e convencao nem disciplina de quem escreve o codigo, e validacao de modelo.
Nao existe estado do sistema em que uma tag conte como confirmada sem que se
saiba quem confirmou e quando.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.confirmacao import Confirmacao, EstadoDeConfirmacao, exigir_coerencia

TAMANHO_DO_ID = 16

CAMADA_LIVRO = 1
CAMADA_CAPITULO = 2


class TipoDeTag(StrEnum):
    """Os seis tipos. A lista e fechada e mudar exige mudar o esquema."""

    TERMO_CANONICO = "termo_canonico"
    RESTRICAO = "restricao"
    DECISAO_EDITORIAL = "decisao_editorial"
    PUBLICO = "publico"
    TOM = "tom"
    PRE_REQUISITO = "pre_requisito"


# O ciclo e o mesmo que as referencias percorrem, entao ele vive em
# `sphinxtales.confirmacao`. Aqui fica so o apelido com o nome do dominio.
EstadoDaTag = EstadoDeConfirmacao


def normalizar(conteudo: str) -> str:
    """Forma canonica para comparar duas tags que dizem a mesma coisa."""
    return re.sub(r"\s+", " ", conteudo).strip().casefold()


def identificar(tipo: TipoDeTag, camada: int, conteudo: str) -> str:
    """Id determinístico: propor a mesma coisa duas vezes da a mesma tag.

    A deduplicacao cai fora de graca, e o S9 herda um acervo que ja nao
    acumula copias triviais do mesmo conteudo.
    """
    semente = f"{tipo.value}|{camada}|{normalizar(conteudo)}".encode("utf-8")
    return hashlib.blake2b(semente, digest_size=TAMANHO_DO_ID // 2).hexdigest()


class Tag(BaseModel):
    """Uma afirmacao sobre o livro, de um tipo conhecido, com dono e estado."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    tipo: TipoDeTag
    conteudo: str = Field(min_length=1)
    camada: int = Field(ge=1)
    origem: str = Field(min_length=1)
    estado: EstadoDaTag = EstadoDaTag.PROPOSTA
    confirmacao: Confirmacao | None = None

    @model_validator(mode="after")
    def _confirmada_tem_registro(self) -> Tag:
        exigir_coerencia(self.estado, self.confirmacao, f"tag {self.id}")
        return self

    @model_validator(mode="after")
    def _id_corresponde_ao_conteudo(self) -> Tag:
        esperado = identificar(self.tipo, self.camada, self.conteudo)
        if self.id != esperado:
            raise ValueError(
                f"id {self.id} nao corresponde ao conteudo desta tag, "
                f"esperado {esperado}"
            )
        return self

    @classmethod
    def propor(
        cls, tipo: TipoDeTag, conteudo: str, camada: int, origem: str
    ) -> Tag:
        """Cria a tag no estado inicial do ciclo. Nunca ja confirmada."""
        return cls(
            id=identificar(tipo, camada, conteudo),
            tipo=tipo,
            conteudo=conteudo,
            camada=camada,
            origem=origem,
        )

    def confirmada_por(self, autor: str, em: datetime) -> Tag:
        """Devolve uma copia confirmada. A original nao muda de estado."""
        return self.model_copy(
            update={
                "estado": EstadoDaTag.CONFIRMADA,
                "confirmacao": Confirmacao(autor=autor, em=em),
            }
        )

    def recusada(self) -> Tag:
        return self.model_copy(
            update={"estado": EstadoDaTag.RECUSADA, "confirmacao": None}
        )
