"""O conjunto de referencias de um projeto, e as operacoes sobre ele.

O arquivo enviado e copiado para dentro do acervo. Guardar so um caminho para o
arquivo original deixaria o vinculo quebrar assim que o autor movesse a pasta
dele, e uma decomposicao confirmada sobre um arquivo que sumiu nao vale nada.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sphinxtales.confirmacao import Confirmacao, EstadoDeConfirmacao
from sphinxtales.referencias.modelo import (
    Decomposicao,
    ItemDaDecomposicao,
    Referencia,
    TipoDeContribuicao,
    identificar,
)

PASTA_DOS_ARQUIVOS = "arquivos"


class ReferenciaNaoEncontrada(KeyError):
    """Pediram uma referencia que nao esta no acervo."""


class SemDecomposicao(ValueError):
    """Tentaram confirmar algo que ninguem decompos ainda."""


class AcervoDeReferencias(BaseModel):
    """Todas as referencias do projeto, em qualquer estado."""

    model_config = ConfigDict(extra="forbid")

    referencias: list[Referencia] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_sao_unicos(self) -> AcervoDeReferencias:
        vistos: set[str] = set()
        for referencia in self.referencias:
            if referencia.id in vistos:
                raise ValueError(
                    f"o acervo tem duas referencias com o id {referencia.id}"
                )
            vistos.add(referencia.id)
        return self

    # ------------------------------------------------------------ consultas

    def obter(self, id_da_referencia: str) -> Referencia:
        for referencia in self.referencias:
            if referencia.id == id_da_referencia:
                return referencia
        raise ReferenciaNaoEncontrada(id_da_referencia)

    def por_contribuicao(self, tipo: TipoDeContribuicao) -> list[Referencia]:
        return [r for r in self.referencias if r.contribuicao is tipo]

    def por_estado(self, estado: EstadoDeConfirmacao) -> list[Referencia]:
        return [r for r in self.referencias if r.estado is estado]

    def confirmadas(self) -> list[Referencia]:
        return self.por_estado(EstadoDeConfirmacao.CONFIRMADA)

    # -------------------------------------------------------------- o ciclo

    def subir(
        self, origem: Path, contribuicao: TipoDeContribuicao, raiz: Path
    ) -> Referencia:
        """Copia o arquivo para o acervo e registra a referencia.

        Subir o mesmo arquivo duas vezes devolve a referencia existente, porque
        o id vem do conteudo.
        """
        conteudo = origem.read_bytes()
        id_previsto = identificar(conteudo)
        try:
            return self.obter(id_previsto)
        except ReferenciaNaoEncontrada:
            pass

        destino_relativo = f"{PASTA_DOS_ARQUIVOS}/{id_previsto}-{origem.name}"
        destino = raiz / destino_relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, destino)

        nova = Referencia.de_arquivo(origem, contribuicao, destino_relativo)
        self.referencias.append(nova)
        return nova

    def decompor(self, id_da_referencia: str, textos: list[str]) -> Referencia:
        """Grava a decomposicao proposta. Nao confirma nada.

        Quem extrai os itens e a camada de conducao, conforme o ADR-001. O
        nucleo so persiste o que ela afirma ter encontrado.
        """
        atual = self.obter(id_da_referencia)
        decomposicao = Decomposicao(
            itens=[
                ItemDaDecomposicao(ordem=ordem, texto=texto)
                for ordem, texto in enumerate(textos, start=1)
            ]
        )
        atualizada = atual.model_copy(update={"decomposicao": decomposicao})
        self.referencias[self.referencias.index(atual)] = atualizada
        return atualizada

    def confirmar(
        self,
        id_da_referencia: str,
        autor: str,
        em: datetime,
        edicoes: dict[int, str] | None = None,
    ) -> Referencia:
        """Confirma a decomposicao, registrando o que o autor precisou reescrever.

        Cada edicao guarda o texto que o sistema havia proposto. E assim que o
        criterio de aceite deixa de ser opiniao e vira medida.
        """
        atual = self.obter(id_da_referencia)
        if atual.decomposicao is None:
            raise SemDecomposicao(
                f"referencia {id_da_referencia} ainda nao foi decomposta"
            )

        itens = []
        for item in atual.decomposicao.itens:
            novo_texto = (edicoes or {}).get(item.ordem)
            if novo_texto is None or novo_texto == item.texto:
                itens.append(item)
                continue
            itens.append(
                ItemDaDecomposicao(
                    ordem=item.ordem,
                    texto=novo_texto,
                    texto_proposto=item.texto_proposto or item.texto,
                )
            )

        confirmada = atual.model_copy(
            update={
                "decomposicao": Decomposicao(itens=itens),
                "estado": EstadoDeConfirmacao.CONFIRMADA,
                "confirmacao": Confirmacao(autor=autor, em=em),
            }
        )
        self.referencias[self.referencias.index(atual)] = confirmada
        return confirmada

    def recusar(self, id_da_referencia: str) -> Referencia:
        atual = self.obter(id_da_referencia)
        recusada = atual.model_copy(
            update={
                "estado": EstadoDeConfirmacao.RECUSADA,
                "confirmacao": None,
            }
        )
        self.referencias[self.referencias.index(atual)] = recusada
        return recusada

    # --------------------------------------------------------- persistencia

    @classmethod
    def carregar(cls, caminho: Path) -> AcervoDeReferencias:
        if not caminho.exists():
            return cls()
        return cls.model_validate_json(caminho.read_text(encoding="utf-8"))

    def salvar(self, caminho: Path) -> Path:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return caminho
