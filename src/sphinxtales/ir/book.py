"""Documento completo: metadados, biblia, contratos de capitulo e capitulos.

`Meta` guarda dados bibliograficos. `Bible` guarda o estado que o escritor
acumula e reusa entre capitulos. `ChapterContract` guarda o que cada capitulo
pode assumir, o que ele introduz e o que nao pode repetir.

Formato de pagina, margens e perfil de cor nao vivem aqui: sao parametros de
prepress, nao propriedades do texto.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.ir.blocks import Block
from sphinxtales.ir.walk import definicoes

VERSAO_IR = "0.1"


class NoDocumento(BaseModel):
    """Base dos nos estruturais. Campo desconhecido e erro."""

    model_config = ConfigDict(extra="forbid")


class Meta(NoDocumento):
    """Dados bibliograficos do livro."""

    titulo: str = Field(min_length=1)
    autor: str = Field(min_length=1)
    subtitulo: str | None = None
    idioma: str = "pt-BR"
    versao_ir: str = VERSAO_IR


class Bible(NoDocumento):
    """Biblia do livro: o que todo capitulo pode assumir sobre o conjunto.

    Preenchida pela entrevista de camada 1 e consumida pelo escritor com estado.
    """

    publico: str = Field(min_length=1)
    genero: str = Field(min_length=1)
    tom: str = Field(min_length=1)
    nivel: str = Field(min_length=1)
    objetivo: str = Field(min_length=1)
    restricoes: list[str] = Field(default_factory=list)
    decisoes_editoriais: list[str] = Field(default_factory=list)


class ChapterContract(NoDocumento):
    """Contrato de um capitulo perante os vizinhos.

    `requer`: termos que o capitulo assume ja definidos.
    `introduz`: termos que este capitulo define pela primeira vez.
    `nao_repetir`: o que ja foi dito e nao pode voltar.
    """

    requer: list[str] = Field(default_factory=list)
    introduz: list[str] = Field(default_factory=list)
    nao_repetir: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _introduz_e_requer_sao_disjuntos(self) -> ChapterContract:
        colisao = sorted(set(self.requer) & set(self.introduz))
        if colisao:
            raise ValueError(
                "termos aparecem em `requer` e `introduz` ao mesmo tempo: "
                + ", ".join(colisao)
            )
        return self


class Chapter(NoDocumento):
    """Capitulo: contrato mais uma lista de blocos."""

    id: str = Field(min_length=1)
    numero: int = Field(ge=0)
    titulo: str = Field(min_length=1)
    contrato: ChapterContract = Field(default_factory=ChapterContract)
    blocos: list[Block] = Field(min_length=1)


class Book(NoDocumento):
    """Raiz do IR."""

    meta: Meta
    bible: Bible
    capitulos: list[Chapter] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_de_capitulo_sao_unicos(self) -> Book:
        vistos: dict[str, int] = {}
        for indice, capitulo in enumerate(self.capitulos):
            if capitulo.id in vistos:
                raise ValueError(
                    f"capitulos[{indice}].id repete o id '{capitulo.id}' "
                    f"ja usado em capitulos[{vistos[capitulo.id]}]"
                )
            vistos[capitulo.id] = indice
        return self

    @model_validator(mode="after")
    def _numeros_de_capitulo_sao_unicos(self) -> Book:
        vistos: dict[int, int] = {}
        for indice, capitulo in enumerate(self.capitulos):
            if capitulo.numero in vistos:
                raise ValueError(
                    f"capitulos[{indice}].numero repete o numero "
                    f"{capitulo.numero} ja usado em capitulos[{vistos[capitulo.numero]}]"
                )
            vistos[capitulo.numero] = indice
        return self

    @model_validator(mode="after")
    def _cada_termo_tem_uma_definicao(self) -> Book:
        """Glossario e indice exigem um termo canonico por definicao.

        Duas definicoes do mesmo termo produziriam duas entradas de glossario
        para a mesma coisa, e o indice remissivo apontaria para a errada.
        """
        origem: dict[str, str] = {}
        for indice, capitulo in enumerate(self.capitulos):
            for caminho, definicao in definicoes(capitulo.blocos):
                local = f"capitulos[{indice}].blocos{caminho}"
                for nome in (definicao.termo, *definicao.aliases):
                    if nome in origem:
                        raise ValueError(
                            f"{local} define o termo '{nome}', "
                            f"que ja foi definido em {origem[nome]}"
                        )
                    origem[nome] = local
        return self
