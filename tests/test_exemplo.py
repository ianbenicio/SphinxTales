"""Criterio de aceite S1, primeira metade: o livro de exemplo a mao valida.

O exemplo nao serve so para passar: ele precisa exercitar o esquema inteiro.
Um exemplo que valida sem tocar em metade dos blocos nao prova nada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bookshelf.ir import (
    TIPOS_BLOCO,
    TIPOS_INLINE,
    Book,
    campos_richtext,
    percorrer_blocos,
    percorrer_inline,
)
from bookshelf.validation import carregar


def test_exemplo_valida(caminho_exemplo: Path) -> None:
    livro = carregar(caminho_exemplo)
    assert isinstance(livro, Book)
    assert livro.meta.titulo == "Precificação para Serviços Criativos"
    assert len(livro.capitulos) == 2


def _tipos_de_bloco(livro: Book) -> set[str]:
    return {
        bloco.tipo
        for capitulo in livro.capitulos
        for _, bloco in percorrer_blocos(capitulo.blocos)
    }


def _tipos_inline(livro: Book) -> set[str]:
    encontrados: set[str] = set()
    for capitulo in livro.capitulos:
        for _, bloco in percorrer_blocos(capitulo.blocos):
            for richtext in campos_richtext(bloco):
                for no in percorrer_inline(richtext):
                    encontrados.add(no.tipo)
    return encontrados


def test_exemplo_exercita_os_nove_blocos(caminho_exemplo: Path) -> None:
    livro = carregar(caminho_exemplo)
    assert _tipos_de_bloco(livro) == TIPOS_BLOCO


def test_exemplo_exercita_todo_no_inline(caminho_exemplo: Path) -> None:
    livro = carregar(caminho_exemplo)
    assert _tipos_inline(livro) == TIPOS_INLINE


def test_serializar_e_revalidar_nao_perde_nada(dados_exemplo: dict[str, Any]) -> None:
    """Ida e volta pelo IR e idempotente: o que sai valida e da no mesmo."""
    livro = Book.model_validate(dados_exemplo)
    revalidado = Book.model_validate(livro.model_dump(mode="json"))
    assert revalidado == livro


def test_contratos_do_exemplo_encadeiam(caminho_exemplo: Path) -> None:
    """O que o capitulo 2 requer, o capitulo 1 introduz."""
    livro = carregar(caminho_exemplo)
    introduzidos = set(livro.capitulos[0].contrato.introduz)
    assert set(livro.capitulos[1].contrato.requer) <= introduzidos
