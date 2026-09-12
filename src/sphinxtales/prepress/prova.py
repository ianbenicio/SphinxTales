"""Pagina de prova de prensa, escrita em PostScript direto.

Esta pagina nao passa pelo IR nem pelo renderizador, e isso e deliberado. Ela
existe para levar uma pergunta a grafica antes de o renderizador existir: quais
valores de perfil, sangria, marcas e resolucao voces aceitam? A resposta vira
parametro do prepress do livro.

Cada bloco da pagina corresponde a uma pergunta que a pre-impressao sabe
responder olhando o arquivo impresso.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sphinxtales.prepress.geometria import Formato, mm
from sphinxtales.prepress.imagem import codificar_para_postscript, gerar_raster

DPI_IMAGEM = 300

REGISTRO = (1.0, 1.0, 1.0, 1.0)
PRETO_CHAPA = (0.0, 0.0, 0.0, 1.0)
PRETO_RICO = (0.60, 0.40, 0.40, 1.0)
SANGRIA_COR = (1.0, 0.20, 0.0, 0.0)
CINZA_FIO = (0.0, 0.0, 0.0, 0.35)

PATCHES: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("C 100", (1.0, 0.0, 0.0, 0.0)),
    ("M 100", (0.0, 1.0, 0.0, 0.0)),
    ("Y 100", (0.0, 0.0, 1.0, 0.0)),
    ("K 100", (0.0, 0.0, 0.0, 1.0)),
    ("C 50", (0.5, 0.0, 0.0, 0.0)),
    ("M 50", (0.0, 0.5, 0.0, 0.0)),
    ("Y 50", (0.0, 0.0, 0.5, 0.0)),
    ("K 50", (0.0, 0.0, 0.0, 0.5)),
    ("K 10", (0.0, 0.0, 0.0, 0.1)),
    ("K 3", (0.0, 0.0, 0.0, 0.03)),
    ("CMY 100", (1.0, 1.0, 1.0, 0.0)),
    ("Registro", REGISTRO),
)

FIOS_PT: tuple[float, ...] = (0.1, 0.15, 0.25, 0.5, 0.75, 1.0)

# Orcamento vertical, em milimetros. A pagina tem altura fixa e sete blocos
# disputando o mesmo espaco: estes numeros sao o rateio, e mudar um exige
# conferir a sobra no rodape.
MARGEM_TOPO_MM = 10.0
ALTURA_CABECALHO_MM = 13.0
ALTURA_SECAO_MM = 7.0
RESPIRO_MM = 7.0
ALTURA_PRETOS_MM = 16.0
ALTURA_REVERSO_MM = 15.0
ALTURA_IMAGEM_MM = 24.0
ALTURA_BARRA_MM = 10.0
PASSO_TEXTO_MM = 7.2
PASSO_FIOS_MM = 3.6

AMOSTRA = "A gráfica aceita o arquivo, ou devolve a lista do que precisa mudar."


@dataclass
class OpcoesDaProva:
    """Tudo que a prova declara sobre si mesma no rodapé."""

    titulo: str = "Prova de prensa mínima"
    projeto: str = "SphinxTales"
    condicao_impressao: str = "a definir com a gráfica"
    perfil: str = "a definir com a gráfica"
    data: str = ""
    observacao: str = "Página de teste. Nenhum conteúdo aqui é material do livro."


@dataclass
class _Folha:
    """Acumula linhas de PostScript e resolve coordenadas relativas ao corte."""

    formato: Formato
    linhas: list[str] = field(default_factory=list)

    def x(self, mm_x: float) -> float:
        return self.formato.trim_x + mm(mm_x)

    def y(self, mm_y: float) -> float:
        return self.formato.trim_y + mm(mm_y)

    def escrever(self, *linhas: str) -> None:
        self.linhas.extend(linhas)

    def cor(self, valores: tuple[float, float, float, float]) -> None:
        c, m, y, k = valores
        self.escrever(f"{c:.3f} {m:.3f} {y:.3f} {k:.3f} setcmykcolor")

    def retangulo(self, mm_x: float, mm_y: float, mm_w: float, mm_h: float) -> None:
        self.escrever(
            f"{self.x(mm_x):.3f} {self.y(mm_y):.3f} {mm(mm_w):.3f} {mm(mm_h):.3f} FR"
        )

    def linha_reta(
        self, mm_x0: float, mm_y0: float, mm_x1: float, mm_y1: float
    ) -> None:
        self.escrever(
            f"{self.x(mm_x0):.3f} {self.y(mm_y0):.3f} "
            f"{self.x(mm_x1):.3f} {self.y(mm_y1):.3f} L"
        )

    def texto(
        self, mm_x: float, mm_y: float, conteudo: str, fonte: str, corpo: float
    ) -> None:
        self.escrever(
            f"/{fonte} {corpo:.2f} selectfont",
            f"{self.x(mm_x):.3f} {self.y(mm_y):.3f} ({_escapar(conteudo)}) T",
        )


def _escapar(texto: str) -> str:
    """Barra, abre e fecha parenteses precisam de escape dentro de string PS."""
    barra = chr(92)
    saida = texto.replace(barra, barra * 2)
    saida = saida.replace("(", barra + "(")
    return saida.replace(")", barra + ")")


def _prologo(formato: Formato, opcoes: OpcoesDaProva) -> list[str]:
    largura, altura = formato.midia_largura, formato.midia_altura
    trim = " ".join(f"{v:.3f}" for v in formato.trim_box)
    bleed = " ".join(f"{v:.3f}" for v in formato.bleed_box)
    return [
        "%!PS-Adobe-3.0",
        f"%%Title: {opcoes.titulo} - {opcoes.projeto}",
        "%%Creator: sphinxtales.prepress.prova",
        "%%LanguageLevel: 3",
        "%%Pages: 1",
        f"%%BoundingBox: 0 0 {largura:.0f} {altura:.0f}",
        "%%EndComments",
        "",
        f"<< /PageSize [{largura:.3f} {altura:.3f}] >> setpagedevice",
        f"[ /TrimBox [{trim}] /PAGE pdfmark",
        f"[ /BleedBox [{bleed}] /PAGE pdfmark",
        "",
        "% fontes reencodadas para ISO Latin 1, senao os acentos somem",
        "/Helvetica findfont dup length dict copy begin",
        "  /Encoding ISOLatin1Encoding def currentdict end",
        "/FH exch definefont pop",
        "/Helvetica-Bold findfont dup length dict copy begin",
        "  /Encoding ISOLatin1Encoding def currentdict end",
        "/FHB exch definefont pop",
        "/Times-Roman findfont dup length dict copy begin",
        "  /Encoding ISOLatin1Encoding def currentdict end",
        "/FT exch definefont pop",
        "",
        "/R { /bh exch def /bw exch def /by exch def /bx exch def",
        "  newpath bx by moveto bw 0 rlineto 0 bh rlineto bw neg 0 rlineto closepath",
        "} bind def",
        "/FR { R fill } bind def",
        "/T { 3 1 roll moveto show } bind def",
        "/L { newpath 4 2 roll moveto lineto stroke } bind def",
        "",
    ]


def _marcas_de_corte(folha: _Folha) -> None:
    formato = folha.formato
    offset = mm(formato.offset_marca_mm)
    comprimento = mm(formato.comprimento_marca_mm)
    x0, y0, x1, y1 = formato.trim_box

    folha.escrever("% marcas de corte, em preto de registro")
    folha.cor(REGISTRO)
    folha.escrever(f"{formato.espessura_marca_pt} setlinewidth")

    for x, sentido in ((x0, -1), (x1, 1)):
        for y in (y0, y1):
            inicio = x + sentido * offset
            fim = x + sentido * (offset + comprimento)
            folha.escrever(f"{inicio:.3f} {y:.3f} {fim:.3f} {y:.3f} L")

    for y, sentido in ((y0, -1), (y1, 1)):
        for x in (x0, x1):
            inicio = y + sentido * offset
            fim = y + sentido * (offset + comprimento)
            folha.escrever(f"{x:.3f} {inicio:.3f} {x:.3f} {fim:.3f} L")

    folha.escrever("")


def _faixa_de_sangria(folha: _Folha) -> None:
    """Barra que atravessa o corte por tres lados. Corte torto aparece."""
    bx0, by0, _, by1 = folha.formato.bleed_box
    folha.escrever("% faixa que sangra pela esquerda, pelo topo e pela base")
    folha.cor(SANGRIA_COR)
    folha.escrever(f"{bx0:.3f} {by0:.3f} {folha.x(8.0) - bx0:.3f} {by1 - by0:.3f} FR")
    folha.escrever("")


def _cabecalho(folha: _Folha, opcoes: OpcoesDaProva, topo: float) -> float:
    formato = folha.formato
    folha.cor(PRETO_CHAPA)
    folha.texto(14, topo, opcoes.titulo, "FHB", 13)
    folha.texto(
        14,
        topo - 6,
        f"{opcoes.projeto} · corte {formato.largura_mm:g} × {formato.altura_mm:g} mm"
        f" · sangria {formato.sangria_mm:g} mm",
        "FH",
        7.5,
    )
    folha.cor(CINZA_FIO)
    folha.escrever("0.4 setlinewidth")
    folha.linha_reta(14, topo - 9.5, 148, topo - 9.5)
    folha.escrever("")
    return topo - ALTURA_CABECALHO_MM


def _secao(folha: _Folha, topo: float, titulo: str, pergunta: str) -> float:
    folha.cor(PRETO_CHAPA)
    folha.texto(14, topo, titulo, "FHB", 7.5)
    folha.cor((0.0, 0.0, 0.0, 0.65))
    folha.texto(14, topo - 4, pergunta, "FH", 6)
    return topo - ALTURA_SECAO_MM


def _pretos(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "1 · Pretos chapados",
        "O preto de uma chapa só fica lavado ao lado do preto composto?",
    )
    altura, largura, intervalo = ALTURA_PRETOS_MM, 65.0, 4.0
    base = topo - altura

    folha.cor(PRETO_CHAPA)
    folha.retangulo(14, base, largura, altura)
    folha.cor(PRETO_RICO)
    folha.retangulo(14 + largura + intervalo, base, largura, altura)

    folha.escrever("0 0 0 0 setcmykcolor")
    folha.texto(17, base + 3, "K 100 sozinho", "FHB", 7)
    folha.texto(14 + largura + intervalo + 3, base + 3, "C60 M40 Y40 K100", "FHB", 7)
    folha.escrever("")
    return base - RESPIRO_MM


def _texto_miudo(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "2 · Texto miúdo",
        "Em que corpo o texto de quatro chapas perde registro?",
    )
    linha = topo
    for corpo in (6.0, 7.0, 8.0):
        folha.cor(PRETO_CHAPA)
        folha.texto(14, linha, f"{corpo:g} pt · K 100 · {AMOSTRA}", "FT", corpo)
        folha.cor(PRETO_RICO)
        folha.texto(
            14, linha - 3.6, f"{corpo:g} pt · 4 chapas · {AMOSTRA}", "FT", corpo
        )
        linha -= PASSO_TEXTO_MM
    folha.escrever("")
    return linha - 4


def _texto_reverso(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "3 · Texto reverso",
        "Em que corpo o branco sobre chapado fecha e some?",
    )
    altura = ALTURA_REVERSO_MM
    base = topo - altura
    folha.cor(PRETO_RICO)
    folha.retangulo(14, base, 134, altura)

    folha.escrever("0 0 0 0 setcmykcolor")
    linha = base + altura - 5
    for corpo in (6.0, 7.0, 8.0):
        folha.texto(17, linha, f"{corpo:g} pt reverso · {AMOSTRA}", "FT", corpo)
        linha -= 4.6
    folha.escrever("")
    return base - RESPIRO_MM


def _imagem(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "4 · Imagem em 300 dpi",
        "O degradê tem banding, e até que espessura a prensa resolve a listra?",
    )
    largura_mm, altura_mm = 62.0, ALTURA_IMAGEM_MM
    base = topo - altura_mm
    largura_px = round(largura_mm / 25.4 * DPI_IMAGEM)
    altura_px = round(altura_mm / 25.4 * DPI_IMAGEM)

    dados = codificar_para_postscript(gerar_raster(largura_px, altura_px))
    folha.escrever(
        "% imagem CMYK gerada aqui, nao e arquivo externo",
        "gsave",
        f"{folha.x(14):.3f} {folha.y(base):.3f} translate",
        f"{mm(largura_mm):.3f} {mm(altura_mm):.3f} scale",
        "/DeviceCMYK setcolorspace",
        "<<",
        "  /ImageType 1",
        f"  /Width {largura_px} /Height {altura_px}",
        "  /BitsPerComponent 8",
        "  /Decode [0 1 0 1 0 1 0 1]",
        f"  /ImageMatrix [{largura_px} 0 0 -{altura_px} 0 {altura_px}]",
        "  /DataSource currentfile /ASCII85Decode filter /FlateDecode filter",
        ">>",
        "image",
        dados,
        "grestore",
    )

    legenda_x = 14 + largura_mm + 5
    folha.cor(PRETO_CHAPA)
    folha.texto(
        legenda_x, base + altura_mm - 4, f"{largura_px} × {altura_px} px", "FHB", 7
    )
    legendas = (
        f"{DPI_IMAGEM} dpi no tamanho impresso.",
        "Faixa de cima: degradê de K puro.",
        "Faixa do meio: cinza de C, M e Y.",
        "Faixa de baixo: listras de 1 a 8 px.",
    )
    for indice, texto in enumerate(legendas):
        folha.cor((0.0, 0.0, 0.0, 0.75))
        folha.texto(legenda_x, base + altura_mm - 9 - indice * 4, texto, "FH", 6)
    folha.escrever("")
    return base - RESPIRO_MM


def _fios(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "5 · Fios finos",
        "Abaixo de que espessura o fio some ou engorda?",
    )
    linha = topo - 2
    for espessura in FIOS_PT:
        folha.cor(PRETO_CHAPA)
        folha.escrever(f"{espessura} setlinewidth")
        folha.linha_reta(30, linha, 148, linha)
        folha.texto(14, linha - 0.8, f"{espessura:g} pt", "FH", 6)
        linha -= PASSO_FIOS_MM
    folha.escrever("")
    return linha - 2


def _barra_de_cor(folha: _Folha, topo: float) -> float:
    topo = _secao(
        folha,
        topo,
        "6 · Barra de controle",
        "As chapas batem com o que a prova de vocês espera?",
    )
    largura = 134.0 / len(PATCHES)
    altura = ALTURA_BARRA_MM
    base = topo - altura

    for indice, (rotulo, cor) in enumerate(PATCHES):
        posicao = 14 + indice * largura
        folha.cor(cor)
        folha.retangulo(posicao, base, largura - 0.6, altura)
        folha.cor(PRETO_CHAPA)
        folha.texto(posicao, base - 3.2, rotulo, "FH", 4.6)
    folha.escrever("")
    return base - 9


def _rodape(folha: _Folha, opcoes: OpcoesDaProva, topo: float) -> None:
    formato = folha.formato
    folha.cor(CINZA_FIO)
    folha.escrever("0.4 setlinewidth")
    folha.linha_reta(14, topo + 3, 148, topo + 3)

    declaracoes = (
        f"Formato de corte {formato.largura_mm:g} × {formato.altura_mm:g} mm"
        f" · sangria {formato.sangria_mm:g} mm"
        f" · marcas a {formato.offset_marca_mm:g} mm do corte",
        f"Condição de impressão declarada: {opcoes.condicao_impressao}",
        f"Perfil de saída: {opcoes.perfil}",
        f"Imagem em {DPI_IMAGEM} dpi, gerada e não digitalizada. {opcoes.data}".strip(),
        opcoes.observacao,
    )
    linha = topo
    for texto in declaracoes:
        folha.cor((0.0, 0.0, 0.0, 0.8))
        folha.texto(14, linha, texto, "FH", 6)
        linha -= 3.4


def gerar_postscript(
    formato: Formato | None = None, opcoes: OpcoesDaProva | None = None
) -> bytes:
    """Monta a pagina inteira e devolve PostScript codificado em Latin-1."""
    formato = formato or Formato()
    opcoes = opcoes or OpcoesDaProva()

    folha = _Folha(formato)
    folha.escrever(*_prologo(formato, opcoes))
    _faixa_de_sangria(folha)
    _marcas_de_corte(folha)

    cursor = _cabecalho(folha, opcoes, topo=formato.altura_mm - MARGEM_TOPO_MM)
    cursor = _pretos(folha, cursor)
    cursor = _texto_miudo(folha, cursor)
    cursor = _texto_reverso(folha, cursor)
    cursor = _imagem(folha, cursor)
    cursor = _fios(folha, cursor)
    cursor = _barra_de_cor(folha, cursor)
    _rodape(folha, opcoes, cursor)

    folha.escrever("showpage", "%%EOF", "")
    return "\n".join(folha.linhas).encode("latin-1", errors="replace")
