"""O texto de tags que chega ao gerador.

Esta funcao e o unico ponto por onde tag vira contexto de geracao, e ela so
enxerga o que foi confirmado. Nao ha parametro que a faca incluir uma proposta.
Quem quiser burlar precisa mudar este arquivo, o que aparece no diff.

O orcamento por relevancia e importancia e do S7b. Aqui a materializacao e
completa e ordenada, para que o teste do S4 fale de uma coisa so: nada entra
sem confirmacao.
"""

from __future__ import annotations

from sphinxtales.tags.acervo import Acervo
from sphinxtales.tags.modelo import Tag, TipoDeTag

ROTULO = {
    TipoDeTag.PUBLICO: "Público",
    TipoDeTag.TOM: "Tom",
    TipoDeTag.TERMO_CANONICO: "Termos canônicos",
    TipoDeTag.PRE_REQUISITO: "Pré-requisitos",
    TipoDeTag.RESTRICAO: "Restrições",
    TipoDeTag.DECISAO_EDITORIAL: "Decisões editoriais",
}

ORDEM = (
    TipoDeTag.PUBLICO,
    TipoDeTag.TOM,
    TipoDeTag.PRE_REQUISITO,
    TipoDeTag.TERMO_CANONICO,
    TipoDeTag.RESTRICAO,
    TipoDeTag.DECISAO_EDITORIAL,
)


def tags_materializaveis(acervo: Acervo, camadas: set[int] | None = None) -> list[Tag]:
    """Confirmadas, e so elas, opcionalmente filtradas por camada."""
    confirmadas = acervo.confirmadas()
    if camadas is None:
        return confirmadas
    return [tag for tag in confirmadas if tag.camada in camadas]


def materializar(acervo: Acervo, camadas: set[int] | None = None) -> str:
    """Monta o bloco de contexto que o gerador recebe."""
    selecionadas = tags_materializaveis(acervo, camadas)
    if not selecionadas:
        return ""

    linhas: list[str] = []
    for tipo in ORDEM:
        do_tipo = sorted(
            (tag for tag in selecionadas if tag.tipo is tipo),
            key=lambda tag: (tag.camada, tag.conteudo.casefold()),
        )
        if not do_tipo:
            continue
        linhas.append(f"{ROTULO[tipo]}:")
        linhas.extend(f"- {tag.conteudo}" for tag in do_tipo)
        linhas.append("")

    return "\n".join(linhas).rstrip() + "\n"
