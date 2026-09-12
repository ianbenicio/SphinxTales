"""Porta de entrada do IR.

Uma so regra governa este modulo: nada falha em silencio. Todo problema vira um
`Problema` com o caminho exato do campo, e o caminho e legivel por quem escreveu
o JSON, nao apenas por quem escreveu o esquema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from sphinxtales.ir import TIPOS_BLOCO, TIPOS_INLINE, Book

_VARIANTES = TIPOS_BLOCO | TIPOS_INLINE


@dataclass(frozen=True)
class Problema:
    """Um defeito localizado no documento."""

    caminho: str
    mensagem: str
    tipo: str

    def __str__(self) -> str:
        return f"{self.caminho}: {self.mensagem} [{self.tipo}]"


class ErroDeValidacao(Exception):
    """Documento rejeitado. Carrega todos os problemas, nao apenas o primeiro."""

    def __init__(self, problemas: Sequence[Problema], origem: str | None = None):
        self.problemas = list(problemas)
        self.origem = origem
        cabecalho = f"{len(self.problemas)} problema(s)"
        if origem:
            cabecalho += f" em {origem}"
        super().__init__(cabecalho + ":\n" + formatar_problemas(self.problemas))


def formatar_caminho(loc: tuple[Any, ...]) -> str:
    """Converte o `loc` do Pydantic em caminho legivel.

    Indices viram colchetes e o nome da variante da uniao discriminada vira
    `<tipo>`, para que se veja *qual* bloco falhou, nao so onde.
    """
    if not loc:
        return "<raiz>"
    partes: list[str] = []
    for segmento in loc:
        if isinstance(segmento, int):
            partes.append(f"[{segmento}]")
        elif segmento in _VARIANTES:
            partes.append(f"<{segmento}>")
        else:
            partes.append(("." if partes else "") + str(segmento))
    return "".join(partes).lstrip(".")


def _problemas_de(erro: ValidationError) -> list[Problema]:
    return [
        Problema(
            caminho=formatar_caminho(detalhe["loc"]),
            mensagem=detalhe["msg"],
            tipo=detalhe["type"],
        )
        for detalhe in erro.errors()
    ]


def formatar_problemas(problemas: Sequence[Problema]) -> str:
    return "\n".join(f"  - {problema}" for problema in problemas)


def validar(dados: Any, origem: str | None = None) -> Book:
    """Valida dados ja desserializados e devolve o `Book`.

    Levanta `ErroDeValidacao` com todos os problemas encontrados.
    """
    try:
        return Book.model_validate(dados)
    except ValidationError as erro:
        raise ErroDeValidacao(_problemas_de(erro), origem) from erro


def carregar(caminho: str | Path) -> Book:
    """Le um arquivo JSON e valida. Erro de sintaxe tambem e nomeado."""
    caminho = Path(caminho)
    texto = caminho.read_text(encoding="utf-8")
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        problema = Problema(
            caminho=f"linha {erro.lineno}, coluna {erro.colno}",
            mensagem=f"JSON invalido: {erro.msg}",
            tipo="json_decode_error",
        )
        raise ErroDeValidacao([problema], str(caminho)) from erro
    return validar(dados, origem=str(caminho))
