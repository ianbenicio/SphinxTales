"""Percursos sobre a arvore do IR.

Blocos aninham (`callout`, `exercise`) e nos inline aninham (`emph`, `strong`,
`footnote`, `term_ref`). Qualquer consumidor que precise ver *todos* os blocos
ou *todos* os termos citados usa estas funcoes, em vez de reimplementar a
descida e esquecer um ramo.
"""

from __future__ import annotations

from typing import Any, Iterator

from bookshelf.ir.blocks import (
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
)
from bookshelf.ir.inline import Emph, Footnote, Strong, TermRef


def percorrer_blocos(
    blocos: list[Any], prefixo: str = ""
) -> Iterator[tuple[str, Any]]:
    """Emite (caminho, bloco) em ordem de leitura, descendo nos aninhados."""
    for indice, bloco in enumerate(blocos):
        caminho = f"{prefixo}[{indice}]" if prefixo else f"[{indice}]"
        yield caminho, bloco
        if isinstance(bloco, Callout):
            yield from percorrer_blocos(bloco.conteudo, f"{caminho}.conteudo")
        elif isinstance(bloco, Exercise):
            yield from percorrer_blocos(bloco.enunciado, f"{caminho}.enunciado")
            if bloco.resposta is not None:
                yield from percorrer_blocos(bloco.resposta, f"{caminho}.resposta")


def percorrer_inline(nos: list[Any] | None) -> Iterator[Any]:
    """Emite todo no inline em ordem de leitura, descendo nos aninhados."""
    if not nos:
        return
    for no in nos:
        yield no
        if isinstance(no, (Emph, Strong, Footnote, TermRef)):
            yield from percorrer_inline(no.conteudo)


def _richtext_de_itens(itens: list[ListItem]) -> Iterator[list[Any]]:
    for item in itens:
        yield item.conteudo
        yield from _richtext_de_itens(item.subitens)


def campos_richtext(bloco: Any) -> Iterator[list[Any]]:
    """Emite cada campo RichText *proprio* do bloco.

    Nao desce em campos que contem outros blocos (`callout.conteudo`,
    `exercise.enunciado`): esses sao alcancados por `percorrer_blocos`.
    """
    match bloco:
        case Paragraph() | Heading():
            yield bloco.conteudo
        case ListBlock():
            yield from _richtext_de_itens(bloco.itens)
        case TableBlock():
            for coluna in bloco.colunas:
                yield coluna.cabecalho
            for linha in bloco.linhas:
                yield from linha
            if bloco.legenda is not None:
                yield bloco.legenda
        case CodeBlock() | Figure():
            if bloco.legenda is not None:
                yield bloco.legenda
        case Callout():
            if bloco.titulo is not None:
                yield bloco.titulo
        case Definition():
            yield bloco.definicao
        case Exercise():
            return


def termos_citados(blocos: list[Any]) -> Iterator[tuple[str, str]]:
    """Emite (caminho_do_bloco, termo) para cada `term_ref` do documento."""
    for caminho, bloco in percorrer_blocos(blocos):
        for richtext in campos_richtext(bloco):
            for no in percorrer_inline(richtext):
                if isinstance(no, TermRef):
                    yield caminho, no.termo


def definicoes(blocos: list[Any]) -> Iterator[tuple[str, Definition]]:
    """Emite (caminho, bloco) para cada `definition`, inclusive aninhada."""
    for caminho, bloco in percorrer_blocos(blocos):
        if isinstance(bloco, Definition):
            yield caminho, bloco
