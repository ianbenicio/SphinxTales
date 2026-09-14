"""O ciclo propor, confirmar, recusar, e a invariante que o sustenta.

Tags e referencias percorrem o mesmo ciclo e carregam a mesma promessa: nada
influencia geracao sem que se saiba quem confirmou e quando. Essa regra mora
aqui, num lugar so, porque uma invariante escrita duas vezes e uma invariante
que um dia vai divergir.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EstadoDeConfirmacao(StrEnum):
    """Onde algo esta no ciclo."""

    PROPOSTA = "proposta"
    CONFIRMADA = "confirmada"
    RECUSADA = "recusada"


class Confirmacao(BaseModel):
    """Quem confirmou e quando. Sem isso nao ha confirmacao."""

    model_config = ConfigDict(extra="forbid")

    autor: str = Field(min_length=1)
    em: datetime

    @model_validator(mode="after")
    def _data_precisa_de_fuso(self) -> Confirmacao:
        if self.em.tzinfo is None:
            raise ValueError(
                "a data de confirmacao precisa declarar fuso horario, "
                "senao o registro nao e comparavel entre maquinas"
            )
        return self


def exigir_coerencia(
    estado: EstadoDeConfirmacao,
    confirmacao: Confirmacao | None,
    identificador: str,
) -> None:
    """Estado e registro precisam concordar, nas duas direcoes.

    Confirmado sem registro seria uma promessa sem lastro. Registro em algo
    nao confirmado faria o registro significar duas coisas.
    """
    confirmado = estado is EstadoDeConfirmacao.CONFIRMADA
    if confirmado and confirmacao is None:
        raise ValueError(
            f"{identificador} esta confirmada sem registro de quem confirmou"
        )
    if not confirmado and confirmacao is not None:
        raise ValueError(
            f"{identificador} tem registro de confirmacao mas esta {estado.value}"
        )
