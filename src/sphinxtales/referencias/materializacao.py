"""O texto de referencias que chega ao gerador.

Mesma regra das tags: este e o unico caminho de referencia para prompt, e ele
so enxerga confirmadas. Uma referencia enviada mas nao confirmada nao existe
para a geracao, e isso e verificavel inspecionando o prompt montado.
"""

from __future__ import annotations

from sphinxtales.referencias.acervo import AcervoDeReferencias
from sphinxtales.referencias.modelo import Referencia, TipoDeContribuicao

ROTULO = {
    TipoDeContribuicao.ESTRUTURA: "Estrutura a seguir",
    TipoDeContribuicao.TOM: "Tom de referência",
    TipoDeContribuicao.PROFUNDIDADE: "Profundidade esperada",
    TipoDeContribuicao.EXEMPLOS: "Exemplos de referência",
    TipoDeContribuicao.CONTRA_EXEMPLO: "O que evitar",
    TipoDeContribuicao.DIAGRAMACAO: "Diagramação de referência",
}

ORDEM = (
    TipoDeContribuicao.ESTRUTURA,
    TipoDeContribuicao.TOM,
    TipoDeContribuicao.PROFUNDIDADE,
    TipoDeContribuicao.EXEMPLOS,
    TipoDeContribuicao.CONTRA_EXEMPLO,
    TipoDeContribuicao.DIAGRAMACAO,
)


def referencias_materializaveis(acervo: AcervoDeReferencias) -> list[Referencia]:
    """Confirmadas, e so elas."""
    return acervo.confirmadas()


def materializar(acervo: AcervoDeReferencias) -> str:
    """Monta o bloco de contexto que o gerador recebe."""
    selecionadas = referencias_materializaveis(acervo)
    if not selecionadas:
        return ""

    linhas: list[str] = []
    for contribuicao in ORDEM:
        do_tipo = [r for r in selecionadas if r.contribuicao is contribuicao]
        if not do_tipo:
            continue
        linhas.append(f"{ROTULO[contribuicao]}:")
        for referencia in sorted(do_tipo, key=lambda r: r.nome.casefold()):
            linhas.append(f"- {referencia.nome}")
            if referencia.decomposicao is not None:
                linhas.extend(
                    f"  {item.ordem}. {item.texto}"
                    for item in referencia.decomposicao.itens
                )
        linhas.append("")

    return "\n".join(linhas).rstrip() + "\n"
