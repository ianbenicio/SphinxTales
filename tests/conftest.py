from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EXEMPLO = RAIZ / "examples" / "livro-exemplo.json"


@pytest.fixture(scope="session")
def caminho_exemplo() -> Path:
    return EXEMPLO


@pytest.fixture(scope="session")
def dados_exemplo() -> dict[str, Any]:
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


@pytest.fixture
def dados_mutaveis(dados_exemplo: dict[str, Any]) -> dict[str, Any]:
    """Copia do exemplo, para que cada teste plante seu proprio defeito."""
    return copy.deepcopy(dados_exemplo)
