"""Os nove blocos do IR.

Um capitulo e uma lista de blocos. Cada bloco declara seu `tipo`; o esquema usa
uniao discriminada, de modo que um tipo desconhecido falha na entrada em vez de
atravessar o pipeline e sumir na diagramacao.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.ir.inline import RichText

AlinhamentoColuna = Literal["esquerda", "centro", "direita"]
VarianteCallout = Literal["nota", "aviso", "dica", "importante", "exemplo"]
Dificuldade = Literal["basico", "intermediario", "avancado"]


class NoBloco(BaseModel):
    """Base de todo bloco. Campo desconhecido e erro, nao e ignorado."""

    model_config = ConfigDict(extra="forbid")


class Paragraph(NoBloco):
    """Paragrafo de texto corrido."""

    tipo: Literal["paragraph"] = "paragraph"
    conteudo: RichText


class Heading(NoBloco):
    """Titulo de secao. Alimenta o sumario paginado."""

    tipo: Literal["heading"] = "heading"
    nivel: int = Field(ge=1, le=4)
    conteudo: RichText
    id: str | None = None


class ListItem(NoBloco):
    """Item de lista, com aninhamento de um ou mais niveis."""

    conteudo: RichText
    subitens: list[ListItem] = Field(default_factory=list)


class ListBlock(NoBloco):
    """Lista ordenada ou nao ordenada."""

    tipo: Literal["list"] = "list"
    ordenada: bool = False
    itens: list[ListItem] = Field(min_length=1)


class TableColumn(NoBloco):
    """Coluna de tabela: cabecalho, alinhamento e largura relativa opcional."""

    cabecalho: RichText
    alinhamento: AlinhamentoColuna = "esquerda"
    largura: float | None = Field(default=None, gt=0)


class TableBlock(NoBloco):
    """Tabela com cabecalho repetido a cada quebra de pagina."""

    tipo: Literal["table"] = "table"
    colunas: list[TableColumn] = Field(min_length=1)
    linhas: list[list[RichText]] = Field(min_length=1)
    legenda: RichText | None = None
    repetir_cabecalho: bool = True

    @model_validator(mode="after")
    def _linhas_tem_aridade_das_colunas(self) -> TableBlock:
        esperado = len(self.colunas)
        for indice, linha in enumerate(self.linhas):
            if len(linha) != esperado:
                raise ValueError(
                    f"linha {indice} tem {len(linha)} celulas, "
                    f"mas a tabela declara {esperado} colunas"
                )
        return self


class CodeBlock(NoBloco):
    """Bloco de codigo literal. O conteudo nunca e reformatado."""

    tipo: Literal["code"] = "code"
    conteudo: str
    linguagem: str | None = None
    legenda: RichText | None = None
    numerar_linhas: bool = False


class Figure(NoBloco):
    """Figura com texto alternativo obrigatorio."""

    tipo: Literal["figure"] = "figure"
    fonte: str = Field(min_length=1)
    alt: str = Field(min_length=1)
    legenda: RichText | None = None
    credito: str | None = None


class Callout(NoBloco):
    """Caixa destacada, com blocos aninhados."""

    tipo: Literal["callout"] = "callout"
    variante: VarianteCallout
    titulo: RichText | None = None
    conteudo: list[Block] = Field(min_length=1)


class Definition(NoBloco):
    """Definicao canonica de um termo.

    Fonte unica do glossario e do indice remissivo. O termo definido aqui e o
    alvo de todo `term_ref` que o cite.
    """

    tipo: Literal["definition"] = "definition"
    termo: str = Field(min_length=1)
    definicao: RichText
    aliases: list[str] = Field(default_factory=list)
    ver_tambem: list[str] = Field(default_factory=list)


class Exercise(NoBloco):
    """Exercicio com enunciado e resposta opcional."""

    tipo: Literal["exercise"] = "exercise"
    id: str = Field(min_length=1)
    enunciado: list[Block] = Field(min_length=1)
    dificuldade: Dificuldade | None = None
    resposta: list[Block] | None = None


Block = Annotated[
    Union[
        Paragraph,
        Heading,
        ListBlock,
        TableBlock,
        CodeBlock,
        Figure,
        Callout,
        Definition,
        Exercise,
    ],
    Field(discriminator="tipo"),
]

TIPOS_BLOCO: frozenset[str] = frozenset(
    {
        "paragraph",
        "heading",
        "list",
        "table",
        "code",
        "figure",
        "callout",
        "definition",
        "exercise",
    }
)

for _modelo in (ListItem, Callout, Exercise):
    _modelo.model_rebuild()
