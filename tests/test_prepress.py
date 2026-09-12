"""Testes do prepress, incluindo os que exigem Ghostscript de verdade.

Os testes de geometria e de PostScript rodam em qualquer maquina. Os que
produzem PDF/X pulam quando o Ghostscript nao esta instalado, porque nesse caso
nao ha o que verificar: o arquivo simplesmente nao existe.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from sphinxtales.prepress import (
    Formato,
    OpcoesDaProva,
    PerfilDeSaida,
    converter,
    gerar_postscript,
    mm,
    perfil_padrao_do_ghostscript,
)
from sphinxtales.prepress.imagem import codificar_para_postscript, gerar_raster
from sphinxtales.prepress.pdfx import (
    VERSOES,
    GhostscriptAusente,
    localizar_ghostscript,
    montar_definicao,
)
from sphinxtales.prepress.verificacao import conferir, tudo_passou


def _ghostscript_disponivel() -> bool:
    try:
        localizar_ghostscript()
    except GhostscriptAusente:
        return False
    return True


precisa_de_ghostscript = pytest.mark.skipif(
    not _ghostscript_disponivel(), reason="Ghostscript nao esta instalado"
)


# ---------------------------------------------------------------- geometria


def test_uma_polegada_tem_setenta_e_dois_pontos() -> None:
    assert mm(25.4) == pytest.approx(72.0)


def test_midia_cabe_o_corte_mais_as_marcas() -> None:
    formato = Formato(largura_mm=160, altura_mm=230)
    sobra_horizontal = formato.midia_largura - formato.trim_largura
    assert sobra_horizontal == pytest.approx(2 * mm(formato.margem_midia_mm))


def test_sangria_expande_o_corte_em_todos_os_lados() -> None:
    formato = Formato(sangria_mm=3.0)
    tx0, _, tx1, ty1 = formato.trim_box
    bx0, _, bx1, by1 = formato.bleed_box
    assert tx0 - bx0 == pytest.approx(mm(3.0))
    assert by1 - ty1 == pytest.approx(mm(3.0))
    assert (bx1 - bx0) - (tx1 - tx0) == pytest.approx(2 * mm(3.0))


def test_formato_vem_de_texto() -> None:
    formato = Formato.de_texto("148x210", sangria_mm=5.0)
    assert (formato.largura_mm, formato.altura_mm) == (148.0, 210.0)
    assert formato.sangria_mm == 5.0


def test_formato_invalido_diz_o_que_esperava() -> None:
    with pytest.raises(ValueError, match="LARGURAxALTURA"):
        Formato.de_texto("A5")


# ------------------------------------------------------------------ imagem


def test_raster_tem_quatro_canais_por_pixel() -> None:
    dados = gerar_raster(10, 9)
    assert len(dados) == 10 * 9 * 4


def test_as_tres_faixas_do_raster_sao_diferentes() -> None:
    largura, altura = 60, 30
    dados = gerar_raster(largura, altura)

    def linha(indice: int) -> bytes:
        inicio = indice * largura * 4
        return dados[inicio : inicio + largura * 4]

    degrade_k, cinza_composto, listras = linha(2), linha(12), linha(25)
    assert degrade_k != cinza_composto
    assert cinza_composto != listras
    # Na faixa de cima so a chapa K trabalha.
    assert set(degrade_k[0::4]) == {0}
    # Na faixa do meio o K fica fora e C, M e Y sobem juntos.
    assert set(cinza_composto[3::4]) == {0}


def test_codificacao_fecha_o_ascii85() -> None:
    codificado = codificar_para_postscript(gerar_raster(8, 6))
    assert codificado.endswith("~>")


# -------------------------------------------------------------- postscript


def _postscript() -> str:
    return gerar_postscript().decode("latin-1")


def test_postscript_declara_as_caixas() -> None:
    texto = _postscript()
    assert texto.startswith("%!PS-Adobe-3.0")
    assert "/TrimBox" in texto
    assert "/BleedBox" in texto
    assert texto.rstrip().endswith("%%EOF")


def test_postscript_traz_as_seis_perguntas() -> None:
    texto = _postscript()
    for titulo in (
        "Pretos chapados",
        "Texto miúdo",
        "Texto reverso",
        "Imagem em 300 dpi",
        "Fios finos",
        "Barra de controle",
    ):
        assert titulo in texto, f"faltou a seção {titulo}"


def test_postscript_desenha_oito_marcas_de_corte() -> None:
    texto = _postscript()
    # O bloco vai do comentario ate a linha em branco que o fecha.
    bloco = texto.split("% marcas de corte")[1].split("\n\n")[0]
    assert sum(1 for linha in bloco.splitlines() if linha.endswith(" L")) == 8


def test_nada_escapa_da_area_de_corte() -> None:
    """O bug que a inspecao visual pegou: conteudo estourando pela base.

    O orcamento vertical e apertado e qualquer bloco que cresca empurra o
    rodape para fora da pagina. Aqui isso falha antes de virar PDF.
    """
    formato = Formato()
    texto = _postscript()
    limite_inferior = formato.trim_y
    limite_superior = formato.trim_y + formato.trim_altura

    for _, base, _, altura in re.findall(
        r"^([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) FR$", texto, re.MULTILINE
    ):
        if float(base) < limite_inferior - 0.5:
            continue  # a faixa de sangria sai de proposito
        assert float(base) + float(altura) <= limite_superior + 0.5

    linhas_de_texto = re.findall(r"^([\d.]+) ([\d.]+) \(.*\) T$", texto, re.MULTILINE)
    assert linhas_de_texto, "nenhuma linha de texto encontrada"
    for _, base in linhas_de_texto:
        assert limite_inferior <= float(base) <= limite_superior, (
            f"texto em y={base} fora do corte "
            f"[{limite_inferior:.2f}, {limite_superior:.2f}]"
        )


def test_parenteses_no_texto_nao_quebram_o_postscript() -> None:
    opcoes = OpcoesDaProva(titulo="Prova (v2) de prensa")
    texto = gerar_postscript(opcoes=opcoes).decode("latin-1")
    assert "Prova " + chr(92) + "(v2" + chr(92) + ") de prensa" in texto


# --------------------------------------------------------------- definicao


def test_definicao_declara_a_versao_pedida() -> None:
    perfil = PerfilDeSaida(caminho_icc=Path("perfil.icc"))
    for versao, (rotulo, _) in VERSOES.items():
        assert f"/GTS_PDFXVersion ({rotulo})" in montar_definicao("t", perfil, versao)


def test_versao_desconhecida_e_recusada() -> None:
    perfil = PerfilDeSaida(caminho_icc=Path("perfil.icc"))
    with pytest.raises(ValueError, match="X-1a"):
        montar_definicao("t", perfil, "X-9")


# ------------------------------------------------------ arquivo de verdade


@pytest.fixture(scope="module")
def pdf_da_prova(tmp_path_factory: pytest.TempPathFactory) -> Path:
    icc = perfil_padrao_do_ghostscript()
    if icc is None:
        pytest.skip("perfil CMYK padrao do Ghostscript nao encontrado")

    destino = tmp_path_factory.mktemp("prova")
    postscript = destino / "prova.ps"
    postscript.write_bytes(gerar_postscript())
    return converter(
        postscript,
        destino / "prova.pdf",
        "Prova de prensa minima",
        PerfilDeSaida(caminho_icc=icc),
    )


@precisa_de_ghostscript
def test_pdf_passa_em_todas_as_checagens(pdf_da_prova: Path) -> None:
    checagens = conferir(pdf_da_prova, Formato())
    falhas = [str(c) for c in checagens if not c.passou]
    assert tudo_passou(checagens), "checagens reprovadas:\n" + "\n".join(falhas)


@precisa_de_ghostscript
def test_caixa_errada_reprova(pdf_da_prova: Path) -> None:
    """A conferencia precisa saber dizer nao, senao ela nao vale nada."""
    checagens = conferir(pdf_da_prova, Formato(largura_mm=100, altura_mm=100))
    nomes = {c.nome for c in checagens if not c.passou}
    assert {"TrimBox", "BleedBox"} <= nomes


@precisa_de_ghostscript
def test_as_marcas_de_corte_chegam_ao_papel(
    pdf_da_prova: Path, tmp_path: Path
) -> None:
    """A 0,25 pt as marcas somem num preview. Aqui elas sao contadas."""
    pgm = tmp_path / "prova.pgm"
    resolucao = 150
    subprocess.run(
        [
            localizar_ghostscript(),
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pgmraw",
            f"-r{resolucao}",
            f"-o{pgm}",
            str(pdf_da_prova),
        ],
        check=True,
        capture_output=True,
    )

    largura, altura, pixels = _ler_pgm(pgm)
    formato = Formato()
    escala = resolucao / 72.0

    def tinta(x0: float, y0: float, x1: float, y1: float) -> int:
        ix0, ix1 = int(x0 * escala), int(x1 * escala)
        iy0 = int((formato.midia_altura - y1) * escala)
        iy1 = int((formato.midia_altura - y0) * escala)
        total = 0
        for y in range(max(iy0, 0), min(iy1, altura)):
            faixa = pixels[y * largura : (y + 1) * largura]
            total += sum(1 for v in faixa[max(ix0, 0) : min(ix1, largura)] if v < 200)
        return total

    tx0, ty0, tx1, ty1 = formato.trim_box
    perto = mm(formato.offset_marca_mm)
    longe = mm(formato.offset_marca_mm + formato.comprimento_marca_mm)

    for x, sentido_x in ((tx0, -1), (tx1, 1)):
        for y, sentido_y in ((ty0, -1), (ty1, 1)):
            horizontal = sorted((x + sentido_x * perto, x + sentido_x * longe))
            vertical = sorted((y + sentido_y * perto, y + sentido_y * longe))
            assert (
                tinta(horizontal[0], y - 1.5, horizontal[1], y + 1.5) > 0
            ), f"marca horizontal ausente no canto ({x:.0f}, {y:.0f})"
            assert (
                tinta(x - 1.5, vertical[0], x + 1.5, vertical[1]) > 0
            ), f"marca vertical ausente no canto ({x:.0f}, {y:.0f})"


def _ler_pgm(caminho: Path) -> tuple[int, int, bytes]:
    """PGM binario, pulando comentarios que o Ghostscript escreve."""
    dados = caminho.read_bytes()
    posicao = 0
    campos: list[bytes] = []
    while len(campos) < 4:
        while dados[posicao : posicao + 1].isspace():
            posicao += 1
        if dados[posicao : posicao + 1] == b"#":
            while dados[posicao : posicao + 1] not in (b"\n", b""):
                posicao += 1
            continue
        inicio = posicao
        while not dados[posicao : posicao + 1].isspace():
            posicao += 1
        campos.append(dados[inicio:posicao])
    posicao += 1
    return int(campos[1]), int(campos[2]), dados[posicao:]
