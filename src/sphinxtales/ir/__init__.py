"""Representacao intermediaria (IR) do livro.

O IR e o unico contrato entre a geracao de texto e a diagramacao. Nada entra na
diagramacao sem passar por aqui, e nada passa por aqui em silencio: campo
desconhecido e erro, campo obrigatorio ausente e erro que nomeia o campo.
"""

from sphinxtales.ir.blocks import (
    TIPOS_BLOCO,
    Block,
    Callout,
    CodeBlock,
    Definition,
    Exercise,
    Figure,
    Heading,
    ListBlock,
    ListItem,
    Paragraph,
    TableBlock,
    TableColumn,
)
from sphinxtales.ir.book import (
    VERSAO_IR,
    Bible,
    Book,
    Chapter,
    ChapterContract,
    Meta,
)
from sphinxtales.ir.inline import (
    TIPOS_INLINE,
    CodeSpan,
    Emph,
    Footnote,
    Inline,
    RichText,
    Strong,
    TermRef,
    Text,
)
from sphinxtales.ir.walk import (
    campos_richtext,
    definicoes,
    percorrer_blocos,
    percorrer_inline,
    termos_citados,
)

__all__ = [
    "VERSAO_IR",
    "TIPOS_BLOCO",
    "TIPOS_INLINE",
    "Bible",
    "Block",
    "Book",
    "Callout",
    "Chapter",
    "ChapterContract",
    "CodeBlock",
    "CodeSpan",
    "Definition",
    "Emph",
    "Exercise",
    "Figure",
    "Footnote",
    "Heading",
    "Inline",
    "ListBlock",
    "ListItem",
    "Meta",
    "Paragraph",
    "RichText",
    "Strong",
    "TableBlock",
    "TableColumn",
    "TermRef",
    "Text",
    "campos_richtext",
    "definicoes",
    "percorrer_blocos",
    "percorrer_inline",
    "termos_citados",
]
