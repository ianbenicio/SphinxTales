"""Conteudo inline do IR.

Todo texto corrido do livro e uma sequencia de nos inline. Um no `text` carrega
caracteres literais; os demais carregam semantica que a diagramacao traduz em
estilo e que o glossario e o indice consomem.

Acucar sintatico: onde o esquema pede `RichText`, uma string simples e aceita e
convertida em `[Text]`. A conversao e explicita e documentada, nunca silenciosa.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class NoInline(BaseModel):
    """Base de todo no inline. Campo desconhecido e erro, nao e ignorado."""

    model_config = ConfigDict(extra="forbid")


class Text(NoInline):
    """Caracteres literais, sem semantica adicional."""

    tipo: Literal["text"] = "text"
    conteudo: str


class Emph(NoInline):
    """Enfase leve (italico na maioria dos temas)."""

    tipo: Literal["emph"] = "emph"
    conteudo: RichText


class Strong(NoInline):
    """Enfase forte (negrito na maioria dos temas)."""

    tipo: Literal["strong"] = "strong"
    conteudo: RichText


class CodeSpan(NoInline):
    """Identificador ou trecho de codigo dentro do texto corrido."""

    tipo: Literal["code_span"] = "code_span"
    conteudo: str


class TermRef(NoInline):
    """Referencia a um termo definido por um bloco `definition`.

    Alimenta o indice remissivo e permite ao loop de consistencia detectar uso
    de termo antes da definicao.
    """

    tipo: Literal["term_ref"] = "term_ref"
    termo: str
    conteudo: RichText | None = None


class Footnote(NoInline):
    """Nota de rodape ancorada na posicao em que aparece."""

    tipo: Literal["footnote"] = "footnote"
    conteudo: RichText


Inline = Annotated[
    Union[Text, Emph, Strong, CodeSpan, TermRef, Footnote],
    Field(discriminator="tipo"),
]

TIPOS_INLINE: frozenset[str] = frozenset(
    {"text", "emph", "strong", "code_span", "term_ref", "footnote"}
)


def _normalizar_richtext(valor: Any) -> Any:
    """Converte acucar de string em nos `text`, preservando o resto intacto."""
    if isinstance(valor, str):
        return [{"tipo": "text", "conteudo": valor}]
    if isinstance(valor, list):
        return [
            {"tipo": "text", "conteudo": item} if isinstance(item, str) else item
            for item in valor
        ]
    return valor


RichText = Annotated[list[Inline], BeforeValidator(_normalizar_richtext)]

for _modelo in (Emph, Strong, TermRef, Footnote):
    _modelo.model_rebuild()
