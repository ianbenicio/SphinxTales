"""Comportamentos do esquema que a diagramacao vai depender."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from bookshelf.ir import VERSAO_IR, TIPOS_BLOCO, Book, RichText, Text
from bookshelf.schema import escrever_json_schema, gerar_json_schema

_richtext = TypeAdapter(RichText)


def test_string_vira_no_de_texto() -> None:
    assert _richtext.validate_python("oi") == [Text(conteudo="oi")]


def test_lista_mista_de_string_e_no_e_normalizada() -> None:
    resultado = _richtext.validate_python(
        ["antes ", {"tipo": "code_span", "conteudo": "x"}]
    )
    assert [no.tipo for no in resultado] == ["text", "code_span"]


def test_no_inline_desconhecido_e_rejeitado() -> None:
    with pytest.raises(Exception):
        _richtext.validate_python([{"tipo": "blink", "conteudo": "x"}])


def test_versao_ir_tem_valor_padrao(dados_exemplo: dict[str, Any]) -> None:
    dados = {**dados_exemplo}
    dados["meta"] = {k: v for k, v in dados["meta"].items() if k != "versao_ir"}
    assert Book.model_validate(dados).meta.versao_ir == VERSAO_IR


def test_json_schema_declara_os_nove_blocos() -> None:
    esquema = gerar_json_schema()
    definicoes = esquema["$defs"]
    tipos = {
        definicao["properties"]["tipo"]["const"]
        for definicao in definicoes.values()
        if "properties" in definicao
        and "tipo" in definicao["properties"]
        and "const" in definicao["properties"]["tipo"]
    }
    assert TIPOS_BLOCO <= tipos


def test_json_schema_e_escrito_em_utf8(tmp_path: Path) -> None:
    destino = escrever_json_schema(tmp_path / "sub" / "book.schema.json")
    carregado = json.loads(destino.read_text(encoding="utf-8"))
    assert carregado["title"] == "BookShelf IR"
