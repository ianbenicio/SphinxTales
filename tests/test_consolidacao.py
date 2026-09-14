"""Testes da consolidacao de tags: dedup, fusao entre camadas, sem decaimento.

O criterio de aceite do S9 e um so, com duas metades: um conjunto com
redundancia injetada colapsa ao numero esperado, e nenhuma restricao unica se
perde no caminho. "Sem decaimento" vira aqui uma propriedade verificavel, a
idempotencia, e nao apenas uma frase na spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sphinxtales.cli import main
from sphinxtales.confirmacao import EstadoDeConfirmacao
from sphinxtales.tags import (
    CAMADA_CAPITULO,
    CAMADA_LIVRO,
    Acervo,
    TipoDeTag,
    identificar,
    materializar,
)
from sphinxtales.tags.consolidacao import consolidar, normalizar_forte

AGORA = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
DEPOIS = datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc)


# --------------------------------------------------------- normalizacao forte


def test_normalizar_forte_ignora_acento_pontuacao_e_caixa() -> None:
    formas = ["Sem jargão.", "sem jargao", "SEM, JARGÃO!!", "  sem   jargão  "]
    assert len({normalizar_forte(forma) for forma in formas}) == 1


def test_normalizar_forte_nao_apaga_diferenca_real() -> None:
    assert normalizar_forte("Sem jargão") != normalizar_forte("Sem gráfico")


# --------------------------------------- aceite: redundancia injetada colapsa


def test_redundancia_injetada_colapsa_ao_numero_esperado() -> None:
    """O cenario do criterio de aceite, escrito por extenso.

    Seis tags: tres grafias da mesma restricao (deve virar uma), duas
    instancias da mesma ideia em camadas diferentes (deve virar uma, na
    camada do livro), e uma restricao unica e genuinamente diferente (tem
    que sobreviver sozinha). Seis tags devem virar tres.
    """
    acervo = Acervo()
    acervo.propor(TipoDeTag.RESTRICAO, "Sem jargão.", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.RESTRICAO, "sem jargao", CAMADA_LIVRO, "entrevista")
    confirmada = acervo.propor(
        TipoDeTag.RESTRICAO, "SEM, JARGÃO!!", CAMADA_LIVRO, "entrevista"
    )
    acervo.confirmar(confirmada.id, "Ian", AGORA)

    acervo.propor(TipoDeTag.TERMO_CANONICO, "custo fixo", CAMADA_CAPITULO, "escritor")
    no_livro = acervo.propor(
        TipoDeTag.TERMO_CANONICO, "custo fixo", CAMADA_LIVRO, "entrevista"
    )
    acervo.confirmar(no_livro.id, "Ian", AGORA)

    acervo.propor(TipoDeTag.RESTRICAO, "Sem gráfico", CAMADA_LIVRO, "entrevista")

    assert len(acervo.tags) == 6
    relatorio = consolidar(acervo)

    assert len(acervo.tags) == 3
    assert relatorio.tags_removidas == 3
    conteudos_restantes = {tag.conteudo for tag in acervo.tags}
    assert "Sem gráfico" in conteudos_restantes


def test_restricao_unica_nunca_e_removida() -> None:
    """A metade do criterio que mais importa: nada de valor some na fusao."""
    acervo = Acervo()
    acervo.propor(TipoDeTag.RESTRICAO, "Sem jargão", CAMADA_LIVRO, "entrevista")
    unica = acervo.propor(TipoDeTag.RESTRICAO, "Sem gráfico", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.RESTRICAO, "sem jargao", CAMADA_LIVRO, "entrevista")

    consolidar(acervo)

    assert acervo.obter(unica.id) == unica


def test_conteudos_parecidos_mas_diferentes_nao_se_fundem() -> None:
    """Compartilhar palavras nao e o mesmo que dizer a mesma coisa."""
    acervo = Acervo()
    acervo.propor(
        TipoDeTag.RESTRICAO, "Sem fórmula com planilha", CAMADA_LIVRO, "entrevista"
    )
    acervo.propor(
        TipoDeTag.RESTRICAO, "Sem tabela sem planilha", CAMADA_LIVRO, "entrevista"
    )

    relatorio = consolidar(acervo)

    assert len(acervo.tags) == 2
    assert relatorio.fusoes == ()


# ---------------------------------------------------- confirmacao sobrevive


def test_fusao_preserva_estado_confirmado() -> None:
    """Uma fusao nao pode transformar uma tag confirmada em proposta de novo.

    O ponto final e o diferenciador de proposito: a normalizacao fraca do S4
    ja faz casefold, entao "Direto" e "direto" sozinhos virariam uma unica
    tag antes mesmo de chegar aqui, e o teste nao provaria nada.
    """
    acervo = Acervo()
    acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    confirmada = acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")
    acervo.confirmar(confirmada.id, "Ian", AGORA)

    consolidar(acervo)

    (sobrevivente,) = acervo.tags
    assert sobrevivente.estado is EstadoDeConfirmacao.CONFIRMADA
    assert sobrevivente.confirmacao is not None
    assert sobrevivente.confirmacao.autor == "Ian"


def test_vencedora_confirmada_e_escolhida_mesmo_fora_de_ordem() -> None:
    """A confirmada vence mesmo entrando antes da proposta na lista."""
    acervo = Acervo()
    confirmada = acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    acervo.confirmar(confirmada.id, "Ian", AGORA)
    acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")

    consolidar(acervo)

    (sobrevivente,) = acervo.tags
    assert sobrevivente.estado is EstadoDeConfirmacao.CONFIRMADA


def test_duas_confirmadas_equivalentes_pegam_a_de_menor_id() -> None:
    """Empate entre confirmadas se resolve por id, nao por ordem de insercao."""
    acervo = Acervo()
    a = acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    b = acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")
    acervo.confirmar(a.id, "Ian", AGORA)
    acervo.confirmar(b.id, "Ian", DEPOIS)

    relatorio = consolidar(acervo)

    esperada = min(a.id, b.id)
    assert relatorio.fusoes[0].sobrevivente == esperada


# -------------------------------------------------------- recusada intocada


def test_tag_recusada_nunca_e_fundida() -> None:
    """Um ramo encerrado nao ressuscita por parecer com outra coisa confirmada."""
    acervo = Acervo()
    recusada_origem = acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    acervo.recusar(recusada_origem.id)
    confirmada = acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")
    acervo.confirmar(confirmada.id, "Ian", AGORA)

    relatorio = consolidar(acervo)

    assert relatorio.fusoes == ()
    assert len(acervo.tags) == 2
    ainda_recusada = acervo.obter(recusada_origem.id)
    assert ainda_recusada.estado is EstadoDeConfirmacao.RECUSADA


def test_tag_sozinha_na_familia_fica_intocada() -> None:
    acervo = Acervo()
    sozinha = acervo.propor(TipoDeTag.PUBLICO, "Autônomos", CAMADA_LIVRO, "entrevista")

    relatorio = consolidar(acervo)

    assert relatorio.fusoes == ()
    assert acervo.obter(sozinha.id) == sozinha


# --------------------------------------------------------------- promocao


def test_mesma_ideia_em_camadas_diferentes_e_promovida_ao_livro() -> None:
    acervo = Acervo()
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_CAPITULO, "escritor")
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_LIVRO, "entrevista")

    relatorio = consolidar(acervo)

    assert relatorio.fusoes[0].promovida is True
    (sobrevivente,) = acervo.tags
    assert sobrevivente.camada == CAMADA_LIVRO


def test_id_da_tag_promovida_bate_com_a_nova_camada() -> None:
    """O id precisa acompanhar a camada, senao a propria tag fica invalida."""
    acervo = Acervo()
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_CAPITULO, "escritor")
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_LIVRO, "entrevista")
    consolidar(acervo)

    (sobrevivente,) = acervo.tags
    esperado = identificar(TipoDeTag.TERMO_CANONICO, CAMADA_LIVRO, "margem")
    assert sobrevivente.id == esperado


def test_mesma_camada_nao_conta_como_promocao() -> None:
    acervo = Acervo()
    acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")

    relatorio = consolidar(acervo)

    assert relatorio.fusoes[0].promovida is False


# ------------------------------------------- sem decaimento: idempotencia


def test_consolidar_duas_vezes_e_estavel() -> None:
    """A propriedade que operacionaliza "sem decaimento".

    Rodar de novo nao encolhe mais nada, porque tudo que era mesmo redundante
    ja foi fundido na primeira passada.
    """
    acervo = Acervo()
    acervo.propor(TipoDeTag.RESTRICAO, "Sem jargão.", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.RESTRICAO, "sem jargao", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_CAPITULO, "escritor")
    acervo.propor(TipoDeTag.TERMO_CANONICO, "margem", CAMADA_LIVRO, "entrevista")

    primeira = consolidar(acervo)
    tamanho_apos_primeira = len(acervo.tags)
    segunda = consolidar(acervo)

    assert primeira.fusoes != ()
    assert segunda.fusoes == ()
    assert len(acervo.tags) == tamanho_apos_primeira


def test_consolidar_acervo_ja_limpo_nao_faz_nada() -> None:
    acervo = Acervo()
    acervo.propor(TipoDeTag.PUBLICO, "Autônomos", CAMADA_LIVRO, "entrevista")
    acervo.propor(TipoDeTag.TOM, "Direto", CAMADA_LIVRO, "entrevista")

    relatorio = consolidar(acervo)

    assert relatorio.fusoes == ()
    assert relatorio.tags_removidas == 0
    assert len(acervo.tags) == 2


# ----------------------------------------------------- integracao com o S4


def test_materializacao_depois_de_consolidar_nao_duplica() -> None:
    acervo = Acervo()
    a = acervo.propor(TipoDeTag.TOM, "Direto.", CAMADA_LIVRO, "entrevista")
    b = acervo.propor(TipoDeTag.TOM, "direto", CAMADA_LIVRO, "escritor")
    acervo.confirmar(a.id, "Ian", AGORA)
    acervo.confirmar(b.id, "Ian", DEPOIS)

    consolidar(acervo)
    texto = materializar(acervo)

    assert texto.count("Direto") + texto.count("direto") == 1


# -------------------------------------------------------- pela linha de comando


def test_cli_consolidar_relata_e_persiste(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acervo_path = tmp_path / "tags.json"
    base = ["tags", "--acervo", str(acervo_path)]

    main([*base, "propor", "--tipo", "tom", "--conteudo", "Direto."])
    main([*base, "propor", "--tipo", "tom", "--conteudo", "direto"])
    capsys.readouterr()

    assert main([*base, "consolidar"]) == 0
    saida = capsys.readouterr().out
    assert "fusao" in saida.lower() or "fundida" in saida.lower()

    recarregado = Acervo.carregar(acervo_path)
    assert len(recarregado.tags) == 1


def test_cli_consolidar_acervo_limpo_diz_que_nao_ha_nada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acervo_path = tmp_path / "tags.json"
    base = ["tags", "--acervo", str(acervo_path)]
    main([*base, "propor", "--tipo", "tom", "--conteudo", "Direto"])
    capsys.readouterr()

    assert main([*base, "consolidar"]) == 0
    assert "nada para consolidar" in capsys.readouterr().out
