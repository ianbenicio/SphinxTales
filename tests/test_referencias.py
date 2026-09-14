"""Testes das referencias por upload e da decomposicao confirmada.

Os tres criterios de aceite do S6 tem secao propria: referencia de estrutura
vira checklist consumivel pelo loop, referencia nao confirmada nao aparece em
prompt nenhum, e o custo de reescrita do autor e medido em vez de suposto.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from sphinxtales.cli import main
from sphinxtales.referencias import (
    AcervoDeReferencias,
    Decomposicao,
    ItemDaDecomposicao,
    Referencia,
    ReferenciaNaoEncontrada,
    SemDecomposicao,
    TipoDeContribuicao,
    checklist_de,
    checklist_do_acervo,
    materializar,
)

AGORA = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)

ESTAGIOS = [
    "Abre com o problema do leitor",
    "Dá o conceito",
    "Fecha com exercício",
]


@pytest.fixture
def manual(tmp_path: Path) -> Path:
    arquivo = tmp_path / "manual.txt"
    arquivo.write_text("Capítulo modelo de um manual prático.", encoding="utf-8")
    return arquivo


@pytest.fixture
def acervo(manual: Path, tmp_path: Path) -> AcervoDeReferencias:
    """Uma referencia de estrutura, subida e decomposta, ainda nao confirmada."""
    acervo = AcervoDeReferencias()
    referencia = acervo.subir(manual, TipoDeContribuicao.ESTRUTURA, tmp_path)
    acervo.decompor(referencia.id, ESTAGIOS)
    return acervo


def _primeira(acervo: AcervoDeReferencias) -> Referencia:
    return acervo.referencias[0]


# ------------------ aceite 1: estrutura vira checklist consumivel pelo loop


def test_estrutura_confirmada_vira_checklist_ordenado(
    acervo: AcervoDeReferencias,
) -> None:
    identificador = _primeira(acervo).id
    acervo.confirmar(identificador, "Ian", AGORA)

    itens = checklist_do_acervo(acervo)
    assert [item.ordem for item in itens] == [1, 2, 3]
    assert [item.descricao for item in itens] == ESTAGIOS
    assert all(item.referencia == identificador for item in itens)


def test_estrutura_nao_confirmada_nao_gera_checklist(
    acervo: AcervoDeReferencias,
) -> None:
    """O loop nao pode cobrar um capitulo por algo que o autor nao aprovou."""
    assert checklist_do_acervo(acervo) == []


def test_outra_contribuicao_nao_gera_checklist(manual: Path, tmp_path: Path) -> None:
    acervo = AcervoDeReferencias()
    referencia = acervo.subir(manual, TipoDeContribuicao.TOM, tmp_path)
    acervo.decompor(referencia.id, ["Frases curtas", "Sem adjetivo de efeito"])
    confirmada = acervo.confirmar(referencia.id, "Ian", AGORA)

    assert checklist_de(confirmada) == []


def test_checklist_reflete_a_edicao_do_autor(acervo: AcervoDeReferencias) -> None:
    """O loop cobra o que o autor confirmou, nao o que o sistema propos."""
    acervo.confirmar(
        _primeira(acervo).id,
        "Ian",
        AGORA,
        edicoes={2: "Define o conceito num exemplo"},
    )
    descricoes = [item.descricao for item in checklist_do_acervo(acervo)]
    assert descricoes[1] == "Define o conceito num exemplo"


# --------------- aceite 2: nao confirmada nao aparece em prompt nenhum


def test_referencia_apenas_subida_nao_chega_ao_gerador(
    acervo: AcervoDeReferencias,
) -> None:
    assert materializar(acervo) == ""


def test_referencia_confirmada_chega_ao_gerador(acervo: AcervoDeReferencias) -> None:
    acervo.confirmar(_primeira(acervo).id, "Ian", AGORA)
    texto = materializar(acervo)
    assert "manual.txt" in texto
    for estagio in ESTAGIOS:
        assert estagio in texto


def test_recusar_tira_do_gerador(acervo: AcervoDeReferencias) -> None:
    identificador = _primeira(acervo).id
    acervo.confirmar(identificador, "Ian", AGORA)
    assert materializar(acervo) != ""

    recusada = acervo.recusar(identificador)
    assert recusada.confirmacao is None
    assert materializar(acervo) == ""


def test_confirmar_sem_decomposicao_e_recusado(manual: Path, tmp_path: Path) -> None:
    """O que o autor confirma e a decomposicao, nao o arquivo."""
    acervo = AcervoDeReferencias()
    referencia = acervo.subir(manual, TipoDeContribuicao.ESTRUTURA, tmp_path)

    with pytest.raises(SemDecomposicao):
        acervo.confirmar(referencia.id, "Ian", AGORA)


def test_modelo_recusa_confirmada_sem_decomposicao(
    manual: Path, tmp_path: Path
) -> None:
    acervo = AcervoDeReferencias()
    referencia = acervo.subir(manual, TipoDeContribuicao.ESTRUTURA, tmp_path)

    dados = referencia.model_dump(mode="json")
    dados["estado"] = "confirmada"
    dados["confirmacao"] = {"autor": "Ian", "em": AGORA.isoformat()}

    with pytest.raises(ValidationError, match="sem decomposicao"):
        Referencia.model_validate(dados)


def test_modelo_recusa_confirmada_sem_registro(acervo: AcervoDeReferencias) -> None:
    dados = _primeira(acervo).model_dump(mode="json")
    dados["estado"] = "confirmada"
    with pytest.raises(ValidationError, match="sem registro"):
        Referencia.model_validate(dados)


# -------------------- aceite 3: o custo de reescrita do autor e medido


def test_confirmar_sem_editar_da_taxa_zero(acervo: AcervoDeReferencias) -> None:
    confirmada = acervo.confirmar(_primeira(acervo).id, "Ian", AGORA)
    assert confirmada.decomposicao is not None
    assert confirmada.decomposicao.taxa_de_edicao == 0.0
    assert confirmada.decomposicao.itens_editados == []


def test_edicao_guarda_o_que_o_sistema_havia_proposto(
    acervo: AcervoDeReferencias,
) -> None:
    """Sem guardar o proposto, nao da para dizer se a decomposicao prestou."""
    confirmada = acervo.confirmar(
        _primeira(acervo).id,
        "Ian",
        AGORA,
        edicoes={2: "Define o conceito num exemplo"},
    )
    assert confirmada.decomposicao is not None
    editado = confirmada.decomposicao.itens[1]
    assert editado.texto == "Define o conceito num exemplo"
    assert editado.texto_proposto == "Dá o conceito"
    assert round(confirmada.decomposicao.taxa_de_edicao, 2) == 0.33


def test_reescrever_tudo_da_taxa_um(acervo: AcervoDeReferencias) -> None:
    """Uma decomposicao reescrita inteira falhou, ainda que confirmada."""
    confirmada = acervo.confirmar(
        _primeira(acervo).id,
        "Ian",
        AGORA,
        edicoes={1: "Outro um", 2: "Outro dois", 3: "Outro três"},
    )
    assert confirmada.decomposicao is not None
    assert confirmada.decomposicao.taxa_de_edicao == 1.0


def test_edicao_igual_ao_original_nao_conta_como_reescrita(
    acervo: AcervoDeReferencias,
) -> None:
    confirmada = acervo.confirmar(
        _primeira(acervo).id, "Ian", AGORA, edicoes={1: ESTAGIOS[0]}
    )
    assert confirmada.decomposicao is not None
    assert confirmada.decomposicao.taxa_de_edicao == 0.0


def test_item_marcado_editado_sem_mudanca_e_rejeitado() -> None:
    with pytest.raises(ValidationError, match="o texto e o mesmo"):
        ItemDaDecomposicao(ordem=1, texto="igual", texto_proposto="igual")


# --------------------------------------------------- upload e integridade


def test_subir_copia_o_arquivo_para_o_acervo(manual: Path, tmp_path: Path) -> None:
    """Guardar so o caminho original quebraria se o autor movesse a pasta."""
    acervo = AcervoDeReferencias()
    referencia = acervo.subir(manual, TipoDeContribuicao.ESTRUTURA, tmp_path)

    copia = tmp_path / referencia.arquivo
    assert copia.exists()
    assert copia.read_bytes() == manual.read_bytes()
    assert copia != manual


def test_subir_o_mesmo_arquivo_duas_vezes_nao_duplica(
    manual: Path, tmp_path: Path
) -> None:
    acervo = AcervoDeReferencias()
    primeira = acervo.subir(manual, TipoDeContribuicao.ESTRUTURA, tmp_path)
    segunda = acervo.subir(manual, TipoDeContribuicao.TOM, tmp_path)

    assert primeira.id == segunda.id
    assert len(acervo.referencias) == 1


def test_arquivo_alterado_depois_da_decomposicao_e_detectado(
    acervo: AcervoDeReferencias, tmp_path: Path
) -> None:
    """Decomposicao confirmada sobre arquivo trocado descreve outra coisa."""
    referencia = _primeira(acervo)
    assert not referencia.arquivo_mudou(tmp_path)

    (tmp_path / referencia.arquivo).write_text("outro conteúdo", encoding="utf-8")
    assert referencia.arquivo_mudou(tmp_path)


def test_id_que_nao_vem_do_arquivo_e_rejeitado(acervo: AcervoDeReferencias) -> None:
    dados = _primeira(acervo).model_dump(mode="json")
    dados["id"] = "0" * 16
    with pytest.raises(ValidationError, match="nao corresponde"):
        Referencia.model_validate(dados)


def test_contribuicao_fora_da_lista_e_rejeitada(acervo: AcervoDeReferencias) -> None:
    dados = _primeira(acervo).model_dump(mode="json")
    dados["contribuicao"] = "inventada"
    with pytest.raises(ValidationError):
        Referencia.model_validate(dados)


def test_ordens_com_buraco_sao_rejeitadas() -> None:
    with pytest.raises(ValidationError, match="sem buracos"):
        Decomposicao(
            itens=[
                ItemDaDecomposicao(ordem=1, texto="um"),
                ItemDaDecomposicao(ordem=3, texto="tres"),
            ]
        )


def test_referencia_inexistente_levanta(acervo: AcervoDeReferencias) -> None:
    with pytest.raises(ReferenciaNaoEncontrada):
        acervo.obter("naoexiste")


# ------------------------------------------------------------- persistencia


def test_ida_e_volta_pelo_disco(acervo: AcervoDeReferencias, tmp_path: Path) -> None:
    acervo.confirmar(_primeira(acervo).id, "Ian", AGORA, edicoes={1: "Outro começo"})

    caminho = acervo.salvar(tmp_path / "referencias.json")
    recarregado = AcervoDeReferencias.carregar(caminho)

    assert recarregado == acervo
    decomposicao = recarregado.referencias[0].decomposicao
    assert decomposicao is not None
    assert decomposicao.itens[0].texto_proposto == ESTAGIOS[0]


def test_acervo_ausente_comeca_vazio(tmp_path: Path) -> None:
    assert AcervoDeReferencias.carregar(tmp_path / "nada.json").referencias == []


# ---------------------------------------------------- pela linha de comando


def test_ciclo_completo_pela_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arquivo = tmp_path / "manual.txt"
    arquivo.write_text("Modelo de manual.", encoding="utf-8")
    base = [
        "referencias",
        "--acervo",
        str(tmp_path / "referencias.json"),
        "--raiz",
        str(tmp_path),
    ]

    assert main([*base, "subir", str(arquivo), "--contribuicao", "estrutura"]) == 0
    identificador = capsys.readouterr().out.split()[1]

    assert main([*base, "checklist"]) == 1
    assert "so referencia de estrutura confirmada" in capsys.readouterr().err

    assert main([*base, "decompor", identificador, "--item", "Um", "--item", "Dois"]) == 0
    capsys.readouterr()

    assert main([*base, "materializar"]) == 1
    assert "nenhuma referencia confirmada" in capsys.readouterr().err

    assert main([*base, "confirmar", identificador, "--autor", "Ian"]) == 0
    assert "taxa de reescrita: 0%" in capsys.readouterr().out

    assert main([*base, "checklist"]) == 0
    assert "[1] Um" in capsys.readouterr().out


def test_cli_confirma_com_edicao_e_mostra_a_taxa(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arquivo = tmp_path / "manual.txt"
    arquivo.write_text("Modelo de manual.", encoding="utf-8")
    base = [
        "referencias",
        "--acervo",
        str(tmp_path / "referencias.json"),
        "--raiz",
        str(tmp_path),
    ]

    main([*base, "subir", str(arquivo), "--contribuicao", "estrutura"])
    identificador = capsys.readouterr().out.split()[1]
    main([*base, "decompor", identificador, "--item", "Um", "--item", "Dois"])
    capsys.readouterr()

    argumentos = [
        *base,
        "confirmar",
        identificador,
        "--autor",
        "Ian",
        "--editar",
        "2=Dois revisado",
    ]
    assert main(argumentos) == 0
    assert "taxa de reescrita: 50%" in capsys.readouterr().out


def test_cli_recusa_edicao_mal_formada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arquivo = tmp_path / "manual.txt"
    arquivo.write_text("Modelo.", encoding="utf-8")
    base = [
        "referencias",
        "--acervo",
        str(tmp_path / "referencias.json"),
        "--raiz",
        str(tmp_path),
    ]

    main([*base, "subir", str(arquivo), "--contribuicao", "estrutura"])
    identificador = capsys.readouterr().out.split()[1]
    main([*base, "decompor", identificador, "--item", "Um"])
    capsys.readouterr()

    argumentos = [*base, "confirmar", identificador, "--autor", "Ian", "--editar", "2"]
    assert main(argumentos) == 1
    assert "edicao sem texto" in capsys.readouterr().err


def test_cli_recusa_arquivo_inexistente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = [
        "referencias",
        "--acervo",
        str(tmp_path / "referencias.json"),
        "--raiz",
        str(tmp_path),
    ]
    argumentos = [
        *base,
        "subir",
        str(tmp_path / "nao-existe.txt"),
        "--contribuicao",
        "tom",
    ]
    assert main(argumentos) == 1
    assert "nao encontrado" in capsys.readouterr().err
