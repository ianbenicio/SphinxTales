"""O conjunto de tags de um projeto, e as unicas operacoes sobre ele.

O ciclo propor, confirmar, vincular acontece aqui e em lugar nenhum mais. Se
houvesse um segundo caminho para marcar uma tag como confirmada, o registro de
quem confirmou deixaria de ser garantia e viraria costume.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.tags.modelo import (
    EstadoDaTag,
    Tag,
    TipoDeTag,
    identificar,
)


class TagNaoEncontrada(KeyError):
    """Pediram uma tag que nao esta no acervo."""


class Acervo(BaseModel):
    """Todas as tags do projeto, em qualquer estado."""

    model_config = ConfigDict(extra="forbid")

    tags: list[Tag] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_sao_unicos(self) -> Acervo:
        vistos: set[str] = set()
        for tag in self.tags:
            if tag.id in vistos:
                raise ValueError(f"o acervo tem duas tags com o id {tag.id}")
            vistos.add(tag.id)
        return self

    # ------------------------------------------------------------ consultas

    def obter(self, id_da_tag: str) -> Tag:
        for tag in self.tags:
            if tag.id == id_da_tag:
                return tag
        raise TagNaoEncontrada(id_da_tag)

    def por_tipo(self, tipo: TipoDeTag) -> list[Tag]:
        return [tag for tag in self.tags if tag.tipo is tipo]

    def por_camada(self, camada: int) -> list[Tag]:
        return [tag for tag in self.tags if tag.camada == camada]

    def por_estado(self, estado: EstadoDaTag) -> list[Tag]:
        return [tag for tag in self.tags if tag.estado is estado]

    def confirmadas(self) -> list[Tag]:
        return self.por_estado(EstadoDaTag.CONFIRMADA)

    # -------------------------------------------------------------- o ciclo

    def propor(
        self, tipo: TipoDeTag, conteudo: str, camada: int, origem: str
    ) -> Tag:
        """Propoe, ou devolve a que ja existe.

        Propor duas vezes a mesma coisa nao cria duas tags, e nao rebaixa uma
        tag ja confirmada de volta a proposta.
        """
        id_previsto = identificar(tipo, camada, conteudo)
        try:
            return self.obter(id_previsto)
        except TagNaoEncontrada:
            pass

        nova = Tag.propor(tipo, conteudo, camada, origem)
        self.tags.append(nova)
        return nova

    def confirmar(self, id_da_tag: str, autor: str, em: datetime) -> Tag:
        """Registra quem confirmou e quando. Unico caminho para o estado."""
        atual = self.obter(id_da_tag)
        confirmada = atual.confirmada_por(autor, em)
        self.tags[self.tags.index(atual)] = confirmada
        return confirmada

    def recusar(self, id_da_tag: str) -> Tag:
        atual = self.obter(id_da_tag)
        recusada = atual.recusada()
        self.tags[self.tags.index(atual)] = recusada
        return recusada

    # --------------------------------------------------------- persistencia

    @classmethod
    def carregar(cls, caminho: Path) -> Acervo:
        if not caminho.exists():
            return cls()
        return cls.model_validate_json(caminho.read_text(encoding="utf-8"))

    def salvar(self, caminho: Path) -> Path:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(
                self.model_dump(mode="json"), ensure_ascii=False, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        return caminho
