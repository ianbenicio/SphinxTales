"""Typst para PDF.

O codigo Typst intermediario e escrito em disco ao lado do PDF de proposito.
Quando a diagramacao sai errada, a pergunta e sempre se o erro esta no IR, no
emissor ou no Typst, e so o arquivo intermediario responde isso.
"""

from __future__ import annotations

import json
from pathlib import Path

import typst

from sphinxtales.ir import Book
from sphinxtales.render.emissor import TOTAL_DE_PAGINAS, emitir_documento
from sphinxtales.render.tema import Tema


class CompilacaoFalhou(RuntimeError):
    """O Typst recusou o documento. A mensagem dele vem junto."""

    def __init__(self, mensagem: str, caminho_typst: Path):
        self.caminho_typst = caminho_typst
        super().__init__(
            f"{mensagem}\n\nO codigo Typst gerado ficou em {caminho_typst}"
        )


def escrever_typst(livro: Book, tema: Tema, destino: Path) -> Path:
    """Emite o .typ e devolve o caminho. Nao compila."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(emitir_documento(livro, tema), encoding="utf-8")
    return destino


def renderizar(
    livro: Book, destino_pdf: Path, tema: Tema | None = None
) -> tuple[Path, Path]:
    """Do IR ao PDF. Devolve (pdf, typst) para que o intermediario fique achavel."""
    tema = tema or Tema()
    caminho_typst = destino_pdf.with_suffix(".typ")
    escrever_typst(livro, tema, caminho_typst)

    try:
        pdf = typst.compile(str(caminho_typst))
    except Exception as erro:  # o binding levanta typst.TypstError e afins
        raise CompilacaoFalhou(str(erro), caminho_typst) from erro

    destino_pdf.parent.mkdir(parents=True, exist_ok=True)
    destino_pdf.write_bytes(pdf)
    return destino_pdf, caminho_typst


def contar_paginas(caminho_typst: Path) -> int:
    """Pergunta ao documento, que carrega um selo com o total de paginas.

    Recebe o `.typ`, nao o PDF. Contar `/Type /Page` no PDF da numero errado,
    porque a marca aparece mais vezes do que ha paginas.
    """
    resposta = typst.query(str(caminho_typst), TOTAL_DE_PAGINAS, field="value")
    return int(json.loads(resposta)[0])
