"""Consolidacao periodica do acervo de tags. Sem decaimento.

Um passe que roda de tempos em tempos, nao a cada proposta. Ele funde tags
que dizem a mesma coisa e a normalizacao fraca do S4 nao pegou (acento,
pontuacao, maiuscula perdida), e promove para a camada do livro uma tag que
existe igualmente em camada de capitulo e em camada de livro.

Nunca apaga nada por idade, por falta de uso ou por qualquer criterio que nao
seja "isto e a mesma afirmacao que aquilo". Rodar o passe duas vezes seguidas
na mesma entrada produz o mesmo resultado na segunda vez: nada novo para
fundir. Essa idempotencia e o jeito de testar "sem decaimento": nao e
descricao, e propriedade verificavel.

Fundir e deliberadamente conservador: so quando a comparacao forte (sem
acento, sem pontuacao, sem espaco duplicado) produz a mesma chave. Preferir
nao fundir a fundir duas restricoes que dizem coisas diferentes e o que o
criterio de aceite exige: nunca perder uma restricao unica.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sphinxtales.confirmacao import EstadoDeConfirmacao
from sphinxtales.tags.acervo import Acervo
from sphinxtales.tags.modelo import CAMADA_LIVRO, Tag, TipoDeTag, identificar

_PONTUACAO = re.compile(r"[^\w\s]", re.UNICODE)
_ESPACOS = re.compile(r"\s+")


def normalizar_forte(conteudo: str) -> str:
    """Alem do que o S4 ja faz: sem acento e sem pontuacao.

    E o que separa "Sem jargao." de "sem jargao" de "SEM, JARGAO!!" -- tres
    grafias da mesma restricao que a normalizacao fraca do S4 trata como
    tres tags diferentes.
    """
    sem_acento = unicodedata.normalize("NFKD", conteudo)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    sem_pontuacao = _PONTUACAO.sub(" ", sem_acento)
    return _ESPACOS.sub(" ", sem_pontuacao).strip().casefold()


def _chave_da_familia(tipo: TipoDeTag, conteudo: str) -> tuple[str, str]:
    """Agrupa por tipo e conteudo forte, ignorando camada de proposito.

    Ignorar a camada e o que torna a promocao possivel: a mesma restricao
    dita em camada de capitulo e em camada de livro cai na mesma familia.
    """
    return (tipo.value, normalizar_forte(conteudo))


@dataclass(frozen=True)
class Fusao:
    """Registro de uma fusao: quem sobreviveu e quem foi absorvido."""

    sobrevivente: str
    absorvidas: tuple[str, ...]
    promovida: bool


@dataclass(frozen=True)
class RelatorioDeConsolidacao:
    """O que o passe fez. Vazio quando nao havia nada para consolidar."""

    fusoes: tuple[Fusao, ...] = ()

    @property
    def tags_removidas(self) -> int:
        return sum(len(fusao.absorvidas) for fusao in self.fusoes)

    @property
    def tags_promovidas(self) -> int:
        return sum(1 for fusao in self.fusoes if fusao.promovida)


def _promover(tag: Tag, camada_alvo: int) -> Tag:
    """Reconstroi a tag na camada alvo. O id muda junto, e o validador confere.

    `model_copy(update=...)` nao roda validador, entao uma tag promovida por
    ele ficaria com o id de outra camada e passaria a violar a propria
    invariante em silencio. Reconstruir com `model_validate` fecha essa porta.
    """
    if tag.camada == camada_alvo:
        return tag
    dados = tag.model_dump(mode="python")
    dados["camada"] = camada_alvo
    dados["id"] = identificar(tag.tipo, camada_alvo, tag.conteudo)
    return Tag.model_validate(dados)


def _vencedora(tags: list[Tag]) -> Tag:
    """Confirmada vence proposta. Empate se resolve pelo id, nunca pela ordem.

    Depender da ordem de insercao tornaria o resultado da fusao dependente de
    como o acervo foi montado, o que quebraria a idempotencia.
    """
    confirmadas = [t for t in tags if t.estado is EstadoDeConfirmacao.CONFIRMADA]
    candidatas = confirmadas or tags
    return min(candidatas, key=lambda t: t.id)


def consolidar(acervo: Acervo) -> RelatorioDeConsolidacao:
    """Funde duplicatas e promove padroes recorrentes. Muda o acervo no lugar.

    Tag recusada fica de fora do agrupamento: e um ramo encerrado, e fundi-la
    ressuscitaria uma decisao que ja foi tomada.
    """
    familias: dict[tuple[str, str], list[Tag]] = {}
    for tag in acervo.tags:
        if tag.estado is EstadoDeConfirmacao.RECUSADA:
            continue
        chave = _chave_da_familia(tag.tipo, tag.conteudo)
        familias.setdefault(chave, []).append(tag)

    fusoes: list[Fusao] = []
    for membros in familias.values():
        if len(membros) < 2:
            continue

        camadas = {membro.camada for membro in membros}
        camada_alvo = CAMADA_LIVRO if len(camadas) > 1 else next(iter(camadas))

        vencedora = _promover(_vencedora(membros), camada_alvo)
        absorvidas = tuple(sorted(m.id for m in membros if m.id != vencedora.id))

        for membro in membros:
            if membro in acervo.tags:
                acervo.tags.remove(membro)
        if vencedora not in acervo.tags:
            acervo.tags.append(vencedora)

        fusoes.append(
            Fusao(
                sobrevivente=vencedora.id,
                absorvidas=absorvidas,
                promovida=len(camadas) > 1,
            )
        )

    return RelatorioDeConsolidacao(fusoes=tuple(sorted(fusoes, key=lambda f: f.sobrevivente)))
