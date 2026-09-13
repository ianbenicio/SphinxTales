"""Testes da diagramacao, incluindo os dois criterios de aceite do S2.

O primeiro criterio, nenhum tipo do IR sem regra de render, e verificado na
importacao do emissor e reconferido aqui. O segundo, tabela larga e bloco de
codigo quebram pagina sem cortar conteudo, e verificado extraindo o texto do
PDF e exigindo que cada linha esteja la.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sphinxtales.ir import TIPOS_BLOCO, TIPOS_INLINE, Book
from sphinxtales.render import (
    EMISSORES_DE_BLOCO,
    EMISSORES_INLINE,
    Tema,
    contar_paginas,
    emitir_documento,
    escapar,
    literal,
    renderizar,
)

BARRA = chr(92)


def _ghostscript() -> str | None:
    for nome in ("gswin64c", "gswin32c", "gs"):
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    return None


precisa_de_ghostscript = pytest.mark.skipif(
    _ghostscript() is None, reason="Ghostscript nao esta instalado"
)


def extrair_texto(caminho_pdf: Path, destino: Path) -> str:
    """Texto do PDF, que e a unica prova de que nada foi cortado na quebra."""
    subprocess.run(
        [
            _ghostscript(),
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=txtwrite",
            f"-o{destino}",
            str(caminho_pdf),
        ],
        check=True,
        capture_output=True,
    )
    return destino.read_text(encoding="utf-8", errors="replace")


# ----------------------------------------------- aceite 1: nada sem regra


def test_todo_bloco_do_ir_tem_regra_de_render() -> None:
    assert set(EMISSORES_DE_BLOCO) == TIPOS_BLOCO


def test_todo_no_inline_do_ir_tem_regra_de_render() -> None:
    assert set(EMISSORES_INLINE) == TIPOS_INLINE


def test_bloco_sem_regra_derruba_a_importacao(monkeypatch: pytest.MonkeyPatch) -> None:
    """A falta de regra precisa falhar ao carregar o modulo, nao ao diagramar."""
    import importlib

    import sphinxtales.ir as ir
    import sphinxtales.render.emissor as emissor

    monkeypatch.setattr(ir, "TIPOS_BLOCO", ir.TIPOS_BLOCO | {"sidebar"})
    with pytest.raises(RuntimeError, match="sidebar"):
        importlib.reload(emissor)

    monkeypatch.undo()
    importlib.reload(emissor)


# ------------------------------------------ texto do autor nao vira comando


def test_escape_cobre_barra_e_aspas() -> None:
    assert escapar(BARRA) == BARRA * 2
    assert escapar('"') == BARRA + '"'


def test_literal_envolve_em_string_typst() -> None:
    assert literal("oi") == '#("oi")'


@precisa_de_ghostscript
def test_markup_no_texto_do_autor_sai_impresso_e_nao_executado(
    dados_mutaveis: dict[str, Any], tmp_path: Path
) -> None:
    """O defeito que esta regra impede: conteudo gerado virar codigo.

    Um modelo pode escrever `#calc.pow(2,10)` no meio de um paragrafo. Isso
    tem que sair impresso assim, e nao virar 1024 na pagina.
    """
    hostil = "Formula #calc.pow(2,10) com *asterisco* e _sublinhado_"
    dados_mutaveis["capitulos"][0]["blocos"][1]["conteudo"] = hostil

    livro = Book.model_validate(dados_mutaveis)
    pdf, _ = renderizar(livro, tmp_path / "hostil.pdf")
    texto = extrair_texto(pdf, tmp_path / "hostil.txt")

    assert "#calc.pow(2,10)" in texto
    assert "1024" not in texto
    assert "*asterisco*" in texto


# -------------------------------- aceite 2: quebra de pagina sem cortar nada


def _livro_com_tabela_e_codigo_longos(base: dict[str, Any]) -> dict[str, Any]:
    """Conteudo que obrigatoriamente atravessa mais de uma pagina."""
    linhas_tabela = [
        [f"Linha {n:03d}", f"R$ {n * 137}", f"R$ {n * 41}"] for n in range(1, 71)
    ]
    codigo = "\n".join(f"marcador_de_linha_{n:03d} = {n} * 7" for n in range(1, 91))

    base["capitulos"][0]["blocos"] = [
        {
            "tipo": "table",
            "legenda": "Tabela que nao cabe numa pagina",
            "colunas": [
                {"cabecalho": "Mês"},
                {"cabecalho": "Receita", "alinhamento": "direita"},
                {"cabecalho": "Custo", "alinhamento": "direita"},
            ],
            "linhas": linhas_tabela,
        },
        {"tipo": "code", "linguagem": "python", "conteudo": codigo},
    ]
    base["capitulos"][0]["contrato"] = {"requer": [], "introduz": [], "nao_repetir": []}
    base["capitulos"][1]["blocos"] = [
        {"tipo": "paragraph", "conteudo": "Capítulo curto para fechar o livro."}
    ]
    base["capitulos"][1]["contrato"] = {"requer": [], "introduz": [], "nao_repetir": []}
    return base


@pytest.fixture
def pdf_longo(dados_mutaveis: dict[str, Any], tmp_path: Path) -> tuple[Path, Path, str]:
    dados = _livro_com_tabela_e_codigo_longos(dados_mutaveis)
    livro = Book.model_validate(dados)
    pdf, typst = renderizar(livro, tmp_path / "longo.pdf")
    return pdf, typst, extrair_texto(pdf, tmp_path / "longo.txt")


@precisa_de_ghostscript
def test_tabela_longa_quebra_pagina_sem_perder_linha(
    pdf_longo: tuple[Path, Path, str],
) -> None:
    _, typst, texto = pdf_longo
    assert contar_paginas(typst) > 3, "o conteudo deveria atravessar varias paginas"

    perdidas = [f"Linha {n:03d}" for n in range(1, 71) if f"Linha {n:03d}" not in texto]
    assert not perdidas, f"linhas de tabela cortadas na quebra: {perdidas[:5]}"


@precisa_de_ghostscript
def test_codigo_longo_quebra_pagina_sem_perder_linha(
    pdf_longo: tuple[Path, Path, str],
) -> None:
    _, _, texto = pdf_longo
    perdidas = [
        f"marcador_de_linha_{n:03d}"
        for n in range(1, 91)
        if f"marcador_de_linha_{n:03d}" not in texto
    ]
    assert not perdidas, f"linhas de codigo cortadas na quebra: {perdidas[:5]}"


@precisa_de_ghostscript
def test_cabecalho_da_tabela_repete_a_cada_pagina(
    pdf_longo: tuple[Path, Path, str],
) -> None:
    _, _, texto = pdf_longo
    assert texto.count("Receita") > 1, "o cabecalho deveria repetir na quebra"


# --------------------------------------------------- documento do exemplo


@pytest.fixture(scope="module")
def livro_renderizado(
    dados_exemplo: dict[str, Any], tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    destino = tmp_path_factory.mktemp("render")
    livro = Book.model_validate(dados_exemplo)
    return renderizar(livro, destino / "livro.pdf")


@precisa_de_ghostscript
def test_o_exemplo_inteiro_diagrama(livro_renderizado: tuple[Path, Path]) -> None:
    pdf, typst = livro_renderizado
    assert pdf.stat().st_size > 10_000
    assert contar_paginas(typst) >= 5


@precisa_de_ghostscript
def test_glossario_traz_todo_termo_definido(
    livro_renderizado: tuple[Path, Path], dados_exemplo: dict[str, Any], tmp_path: Path
) -> None:
    """O glossario sai do IR, entao termo definido e termo no glossario."""
    pdf, _ = livro_renderizado
    texto = extrair_texto(pdf, tmp_path / "exemplo.txt")

    assert "Glossário" in texto
    termos = [
        bloco["termo"]
        for capitulo in dados_exemplo["capitulos"]
        for bloco in capitulo["blocos"]
        if bloco["tipo"] == "definition"
    ]
    assert termos, "o exemplo precisa ter definicoes"
    # rsplit, porque o título aparece antes no sumário.
    depois_do_glossario = texto.rsplit("Glossário", 1)[1]
    for termo in termos:
        assert termo in depois_do_glossario, f"termo fora do glossário: {termo}"


@precisa_de_ghostscript
def test_indice_remissivo_aponta_paginas(
    livro_renderizado: tuple[Path, Path], tmp_path: Path
) -> None:
    pdf, _ = livro_renderizado
    texto = extrair_texto(pdf, tmp_path / "exemplo.txt")

    assert "Índice remissivo" in texto
    # rsplit, porque o título aparece antes no sumário: o índice é o último.
    indice = texto.rsplit("Índice remissivo", 1)[1]
    linhas = [linha for linha in indice.splitlines() if "custo fixo" in linha]
    assert linhas, "custo fixo deveria estar no índice"
    assert any(char.isdigit() for char in linhas[0]), "faltou o número de página"


@precisa_de_ghostscript
def test_sumario_nao_lista_a_si_mesmo(
    livro_renderizado: tuple[Path, Path], tmp_path: Path
) -> None:
    pdf, _ = livro_renderizado
    texto = extrair_texto(pdf, tmp_path / "exemplo.txt")
    antes_do_capitulo = texto.split("Horas não são o produto", 1)[0]
    assert antes_do_capitulo.count("Sumário") == 1


def test_documento_declara_o_total_de_paginas(dados_exemplo: dict[str, Any]) -> None:
    codigo = emitir_documento(Book.model_validate(dados_exemplo), Tema())
    assert "<total-paginas>" in codigo


def test_tema_e_parametro_e_nao_constante(dados_exemplo: dict[str, Any]) -> None:
    livro = Book.model_validate(dados_exemplo)
    estreito = emitir_documento(livro, Tema(largura_mm=120.0, corpo_pt=9.0))
    largo = emitir_documento(livro, Tema(largura_mm=210.0, corpo_pt=12.0))
    assert "120.0mm" in estreito and "9.0pt" in estreito
    assert "210.0mm" in largo and "12.0pt" in largo
