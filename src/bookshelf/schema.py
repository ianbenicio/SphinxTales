"""Exportacao do JSON Schema do IR.

O esquema Pydantic e a fonte; o JSON Schema e derivado dele. Nunca o contrario.
Assim nenhum consumidor externo depende de uma copia que possa divergir.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bookshelf.ir import Book

CAMINHO_PADRAO = Path("schemas/book.schema.json")


def gerar_json_schema() -> dict[str, Any]:
    esquema = Book.model_json_schema(mode="validation")
    esquema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    esquema["title"] = "BookShelf IR"
    return esquema


def escrever_json_schema(destino: str | Path = CAMINHO_PADRAO) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(gerar_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destino
