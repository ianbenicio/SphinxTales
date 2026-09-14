"""Testes da taxonomia de tags e do ciclo de confirmacao.

Os tres criterios de aceite do S4 tem secao propria aqui: tipo inexistente e
rejeitado na entrada, nada influencia geracao sem registro de confirmacao, e as
tags sao recuperaveis por tipo e por camada.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from sphinxtales.cli import main
from sphinxtales.tags import (
    Acervo,
    Confirmacao,
    EstadoDaTag,
    Tag,
    TagNaoEncontrada,
    TipoDeTag,
    identificar,
    materializar,
    normalizar,
    tags_materializaveis,
)

AGORA = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def acervo() -> Acervo:
    """Tres tags propostas, nenhuma confirmada ainda."""
    acervo = Acervo()
    acervo.propor(TipoDeTag.TOM, "Direto, sem jargão", 1, "entrevista")
    acervo.propor(TipoDeTag.PUBLICO, "Autônomos de design", 1, "entrevista")
    acervo.propor(TipoDeTag.TERMO_CANONICO, "custo fixo", 2, "escritor")
    return acervo


# -------------------------- aceite 1: tipo inexistente rejeitado na entrada


def test_tipo_fora_da_taxonomia_e_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Tag(
            id="0" * 16,
            tipo="sidebar",
            conteudo="qualquer",
            camada=1,
            origem="teste",
        )


def test_a_taxonomia_tem_exatamente_seis_tipos() -> None:
    """Fechada quer dizer fechada: crescer exige mudar o esquema."""
    assert {tipo.value for tipo in TipoDeTag} == {
        "termo_canonico",
        "restricao",
        "decisao_editorial",
        "publico",
        "tom",
        "pre_requisito",
    }


# ------------- aceite 2: nada influencia geracao sem registro de confirmacao


def test_confirmada_sem_registro_e_impossivel() -> None:
    """A invariante central, checada no modelo e nao por convencao."""
    with pytest.raises(ValidationError, match="sem registro"):
        Tag(
            id=identificar(TipoDeTag.TOM, 1, "seco"),
            tipo=TipoDeTag.TOM,
            conteudo="seco",
            camada=1,
            origem="teste",
            estado=EstadoDaTag.CONFIRMADA,
        )


def test_registro_em_tag_nao_confirmada_e_impossivel() -> None:
    with pytest.raises(ValidationError, match="registro de confirmacao"):
        Tag(
            id=identificar(TipoDeTag.TOM, 1, "seco"),
            tipo=TipoDeTag.TOM,
            conteudo="seco",
            camada=1,
            origem="teste",
            estado=EstadoDaTag.PROPOSTA,
            confirmacao=Confirmacao(autor="Alguém", em=AGORA),
        )


def test_confirmacao_sem_fuso_e_rejeitada() -> None:
    """Data sem fuso nao e comparavel entre maquinas, e o registro perde valor."""
    with pytest.raises(ValidationError, match="fuso"):
        Confirmacao(autor="Alguém", em=datetime(2026, 9, 14, 12, 0))


def test_proposta_nao_chega_ao_gerador(acervo: Acervo) -> None:
    assert materializar(acervo) == ""


def test_so_a_confirmada_chega_ao_gerador(acervo: Acervo) -> None:
    alvo = acervo.por_tipo(TipoDeTag.PUBLICO)[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)

    texto = materializar(acervo)
    assert "Autônomos de design" in texto
    assert "Direto, sem jargão" not in texto
    assert "custo fixo" not in texto


def test_nenhum_filtro_de_camada_faz_proposta_vazar(acervo: Acervo) -> None:
    """Varrer todas as camadas nao pode ser um atalho para incluir proposta."""
    alvo = acervo.por_tipo(TipoDeTag.PUBLICO)[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)

    for camadas in (None, {1}, {2}, {1, 2}, set(range(1, 10))):
        selecionadas = tags_materializaveis(acervo, camadas)
        assert all(tag.estado is EstadoDaTag.CONFIRMADA for tag in selecionadas)


def test_recusar_apaga_o_registro_e_tira_do_gerador(acervo: Acervo) -> None:
    alvo = acervo.por_tipo(TipoDeTag.PUBLICO)[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)
    assert "Autônomos" in materializar(acervo)

    recusada = acervo.recusar(alvo.id)
    assert recusada.confirmacao is None
    assert materializar(acervo) == ""


def test_o_registro_guarda_quem_e_quando(acervo: Acervo) -> None:
    alvo = acervo.tags[0]
    confirmada = acervo.confirmar(alvo.id, "Ian Benicio", AGORA)
    assert confirmada.confirmacao is not None
    assert confirmada.confirmacao.autor == "Ian Benicio"
    assert confirmada.confirmacao.em == AGORA


# ---------------------- aceite 3: recuperaveis por tipo e por camada


def test_recuperacao_por_tipo(acervo: Acervo) -> None:
    assert len(acervo.por_tipo(TipoDeTag.TOM)) == 1
    assert acervo.por_tipo(TipoDeTag.RESTRICAO) == []


def test_recuperacao_por_camada(acervo: Acervo) -> None:
    assert len(acervo.por_camada(1)) == 2
    assert len(acervo.por_camada(2)) == 1
    assert acervo.por_camada(3) == []


def test_recuperacao_por_estado(acervo: Acervo) -> None:
    alvo = acervo.tags[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)
    assert len(acervo.por_estado(EstadoDaTag.PROPOSTA)) == 2
    assert len(acervo.por_estado(EstadoDaTag.CONFIRMADA)) == 1


# ------------------------------------------------ identidade e deduplicacao


def test_mesma_afirmacao_com_outra_grafia_e_a_mesma_tag() -> None:
    assert identificar(TipoDeTag.TOM, 1, "Custo  Fixo") == identificar(
        TipoDeTag.TOM, 1, "custo fixo"
    )


def test_tipo_ou_camada_diferente_e_outra_tag() -> None:
    base = identificar(TipoDeTag.TOM, 1, "custo fixo")
    assert identificar(TipoDeTag.RESTRICAO, 1, "custo fixo") != base
    assert identificar(TipoDeTag.TOM, 2, "custo fixo") != base


def test_normalizar_colapsa_espaco_e_caixa() -> None:
    assert normalizar("  Custo   FIXO ") == "custo fixo"


def test_propor_duas_vezes_nao_duplica(acervo: Acervo) -> None:
    antes = len(acervo.tags)
    acervo.propor(TipoDeTag.TOM, "direto,   SEM JARGÃO", 1, "outra origem")
    assert len(acervo.tags) == antes


def test_propor_de_novo_nao_rebaixa_uma_confirmada(acervo: Acervo) -> None:
    """Caminho real de bug: reproposta apagando o registro de confirmacao."""
    alvo = acervo.por_tipo(TipoDeTag.TOM)[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)

    devolvida = acervo.propor(TipoDeTag.TOM, "Direto, sem jargão", 1, "escritor")
    assert devolvida.estado is EstadoDaTag.CONFIRMADA
    assert devolvida.confirmacao is not None


def test_id_que_nao_bate_com_o_conteudo_e_rejeitado() -> None:
    with pytest.raises(ValidationError, match="nao corresponde"):
        Tag(
            id="f" * 16,
            tipo=TipoDeTag.TOM,
            conteudo="seco",
            camada=1,
            origem="teste",
        )


def test_acervo_recusa_ids_repetidos() -> None:
    tag = Tag.propor(TipoDeTag.TOM, "seco", 1, "teste")
    with pytest.raises(ValidationError, match="duas tags com o id"):
        Acervo(tags=[tag, tag.model_copy()])


def test_tag_inexistente_levanta(acervo: Acervo) -> None:
    with pytest.raises(TagNaoEncontrada):
        acervo.confirmar("naoexiste", "Ian", AGORA)


# ------------------------------------------------------------- persistencia


def test_ida_e_volta_pelo_disco_preserva_o_registro(
    acervo: Acervo, tmp_path: Path
) -> None:
    alvo = acervo.tags[0]
    acervo.confirmar(alvo.id, "Ian", AGORA)

    caminho = acervo.salvar(tmp_path / "tags.json")
    recarregado = Acervo.carregar(caminho)

    assert recarregado == acervo
    confirmada = recarregado.obter(alvo.id)
    assert confirmada.confirmacao is not None
    assert confirmada.confirmacao.autor == "Ian"


def test_acervo_ausente_comeca_vazio(tmp_path: Path) -> None:
    assert Acervo.carregar(tmp_path / "nao-existe.json").tags == []


# ---------------------------------------------------- pela linha de comando


def test_ciclo_completo_pela_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acervo = tmp_path / "tags.json"

    argumentos = [
        "tags",
        "--acervo",
        str(acervo),
        "propor",
        "--tipo",
        "tom",
        "--conteudo",
        "Direto, sem jargão",
    ]
    assert main(argumentos) == 0
    id_da_tag = capsys.readouterr().out.split()[1]

    assert main(["tags", "--acervo", str(acervo), "materializar"]) == 1
    assert "nenhuma tag confirmada" in capsys.readouterr().err

    confirmar = ["tags", "--acervo", str(acervo), "confirmar", id_da_tag, "--autor", "Ian"]
    assert main(confirmar) == 0
    capsys.readouterr()

    assert main(["tags", "--acervo", str(acervo), "materializar"]) == 0
    assert "Direto, sem jargão" in capsys.readouterr().out


def test_cli_recusa_id_inexistente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acervo = tmp_path / "tags.json"
    argumentos = ["tags", "--acervo", str(acervo), "confirmar", "abc", "--autor", "Ian"]
    assert main(argumentos) == 1
    assert "nao encontrada" in capsys.readouterr().err


def test_cli_lista_com_filtros(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acervo = tmp_path / "tags.json"
    base = ["tags", "--acervo", str(acervo), "propor"]
    main([*base, "--tipo", "tom", "--conteudo", "Seco", "--camada", "1"])
    main([*base, "--tipo", "restricao", "--conteudo", "Sem planilha", "--camada", "2"])
    capsys.readouterr()

    main(["tags", "--acervo", str(acervo), "listar", "--camada", "2"])
    saida = capsys.readouterr().out
    assert "Sem planilha" in saida
    assert "Seco" not in saida


def test_data_de_confirmacao_da_cli_tem_fuso(tmp_path: Path) -> None:
    """A CLI grava em UTC. Sem fuso, o registro nao seria comparavel."""
    caminho = tmp_path / "tags.json"
    acervo = Acervo()
    tag = acervo.propor(TipoDeTag.TOM, "Seco", 1, "teste")
    acervo.salvar(caminho)

    main(["tags", "--acervo", str(caminho), "confirmar", tag.id, "--autor", "Ian"])

    gravada = Acervo.carregar(caminho).obter(tag.id)
    assert gravada.confirmacao is not None
    assert gravada.confirmacao.em.tzinfo is not None
    assert abs(gravada.confirmacao.em - datetime.now(timezone.utc)) < timedelta(
        minutes=5
    )
