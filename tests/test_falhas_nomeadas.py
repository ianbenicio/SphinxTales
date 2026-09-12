"""Criterio de aceite S1, segunda metade.

Todo defeito plantado aqui precisa produzir uma mensagem que nomeie o campo. Um
teste que so verifica "levantou excecao" nao prova o criterio: o que se exige e
que a mensagem diga *onde*.
"""

from __future__ import annotations

from typing import Any

import pytest

from sphinxtales.validation import ErroDeValidacao, validar


def _caminhos(erro: ErroDeValidacao) -> list[str]:
    return [problema.caminho for problema in erro.problemas]


def test_campo_obrigatorio_ausente_na_raiz_nomeia_o_campo(
    dados_mutaveis: dict[str, Any],
) -> None:
    del dados_mutaveis["meta"]["autor"]
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert "meta.autor" in _caminhos(capturado.value)


def test_campo_obrigatorio_ausente_em_bloco_aninhado_nomeia_o_caminho(
    dados_mutaveis: dict[str, Any],
) -> None:
    definicao = dados_mutaveis["capitulos"][0]["blocos"][2]
    assert definicao["tipo"] == "definition"
    del definicao["termo"]

    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)

    caminhos = _caminhos(capturado.value)
    assert "capitulos[0].blocos[2]<definition>.termo" in caminhos


def test_campo_desconhecido_e_rejeitado_e_nao_ignorado(
    dados_mutaveis: dict[str, Any],
) -> None:
    """O modo silencioso a evitar: um campo com erro de digitacao ser descartado."""
    dados_mutaveis["capitulos"][0]["blocos"][0]["nivell"] = 2

    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)

    problema = next(
        p for p in capturado.value.problemas if p.caminho.endswith("nivell")
    )
    assert problema.tipo == "extra_forbidden"


def test_tipo_de_bloco_desconhecido_e_rejeitado(
    dados_mutaveis: dict[str, Any],
) -> None:
    dados_mutaveis["capitulos"][0]["blocos"][0]["tipo"] = "sidebar"
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert any("capitulos[0].blocos[0]" in c for c in _caminhos(capturado.value))


def test_figura_sem_texto_alternativo_e_rejeitada(
    dados_mutaveis: dict[str, Any],
) -> None:
    figura = dados_mutaveis["capitulos"][1]["blocos"][4]
    assert figura["tipo"] == "figure"
    figura["alt"] = ""

    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)

    assert "capitulos[1].blocos[4]<figure>.alt" in _caminhos(capturado.value)


def test_linha_de_tabela_com_aridade_errada_diz_qual_linha(
    dados_mutaveis: dict[str, Any],
) -> None:
    tabela = dados_mutaveis["capitulos"][0]["blocos"][5]
    assert tabela["tipo"] == "table"
    tabela["linhas"][1] = ["Fevereiro", "R$ 11.000"]

    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)

    mensagens = " ".join(p.mensagem for p in capturado.value.problemas)
    assert "linha 1" in mensagens
    assert "3 colunas" in mensagens


def test_id_de_capitulo_repetido_aponta_os_dois(
    dados_mutaveis: dict[str, Any],
) -> None:
    dados_mutaveis["capitulos"][1]["id"] = dados_mutaveis["capitulos"][0]["id"]
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    mensagens = " ".join(p.mensagem for p in capturado.value.problemas)
    assert "capitulos[1].id" in mensagens
    assert "capitulos[0]" in mensagens


def test_numero_de_capitulo_repetido_e_rejeitado(
    dados_mutaveis: dict[str, Any],
) -> None:
    dados_mutaveis["capitulos"][1]["numero"] = 1
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert "numero" in " ".join(p.mensagem for p in capturado.value.problemas)


def test_termo_definido_duas_vezes_e_rejeitado(
    dados_mutaveis: dict[str, Any],
) -> None:
    """Duas definicoes do mesmo termo quebrariam glossario e indice."""
    dados_mutaveis["capitulos"][1]["blocos"][2]["termo"] = "custo fixo"

    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)

    mensagens = " ".join(p.mensagem for p in capturado.value.problemas)
    assert "custo fixo" in mensagens
    assert "capitulos[0]" in mensagens


def test_alias_colidindo_com_termo_existente_e_rejeitado(
    dados_mutaveis: dict[str, Any],
) -> None:
    dados_mutaveis["capitulos"][1]["blocos"][2]["aliases"] = ["custos fixos"]
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert "custos fixos" in " ".join(p.mensagem for p in capturado.value.problemas)


def test_contrato_com_termo_em_requer_e_introduz_e_rejeitado(
    dados_mutaveis: dict[str, Any],
) -> None:
    dados_mutaveis["capitulos"][1]["contrato"]["introduz"].append("custo fixo")
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    mensagens = " ".join(p.mensagem for p in capturado.value.problemas)
    assert "custo fixo" in mensagens


def test_livro_sem_capitulos_e_rejeitado(dados_mutaveis: dict[str, Any]) -> None:
    dados_mutaveis["capitulos"] = []
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert "capitulos" in _caminhos(capturado.value)


def test_erro_reune_todos_os_problemas_nao_apenas_o_primeiro(
    dados_mutaveis: dict[str, Any],
) -> None:
    del dados_mutaveis["meta"]["autor"]
    del dados_mutaveis["bible"]["tom"]
    with pytest.raises(ErroDeValidacao) as capturado:
        validar(dados_mutaveis)
    assert {"meta.autor", "bible.tom"} <= set(_caminhos(capturado.value))


def test_json_invalido_nomeia_linha_e_coluna(tmp_path: Any) -> None:
    from sphinxtales.validation import carregar

    arquivo = tmp_path / "quebrado.json"
    arquivo.write_text('{"meta": {,}}', encoding="utf-8")

    with pytest.raises(ErroDeValidacao) as capturado:
        carregar(arquivo)

    problema = capturado.value.problemas[0]
    assert problema.tipo == "json_decode_error"
    assert "linha" in problema.caminho
