"""A CLI e a primeira interface do sistema, entao ela e testada como interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sphinxtales.cli import main


def test_validate_aceita_o_exemplo(
    caminho_exemplo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", str(caminho_exemplo)]) == 0
    assert "aceito" in capsys.readouterr().out


def test_validate_rejeita_documento_defeituoso(
    dados_mutaveis: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del dados_mutaveis["capitulos"][0]["blocos"][2]["termo"]
    arquivo = tmp_path / "defeituoso.json"
    arquivo.write_text(json.dumps(dados_mutaveis, ensure_ascii=False), encoding="utf-8")

    assert main(["validate", str(arquivo)]) == 1
    assert "<definition>.termo" in capsys.readouterr().err


def test_validate_reporta_arquivo_inexistente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", str(tmp_path / "nao-existe.json")]) == 1
    assert "nao foi possivel ler" in capsys.readouterr().err


def test_schema_escreve_o_arquivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "book.schema.json"
    assert main(["schema", "-o", str(destino)]) == 0
    assert destino.exists()
    assert "JSON Schema" in capsys.readouterr().out
