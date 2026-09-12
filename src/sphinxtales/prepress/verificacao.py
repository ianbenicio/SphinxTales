"""Conferencia do PDF antes de ele sair para a grafica.

Mandar arquivo errado custa dias de espera. Estas checagens custam
milissegundos e pegam os erros que a pre-impressao devolveria: versao PDF/X
ausente, OutputIntent faltando, caixas de corte e sangria erradas, fonte nao
embutida, cor fora de CMYK.

Nenhuma delas substitui o parecer da grafica. Elas so garantem que a pergunta
que chega la e a pergunta certa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sphinxtales.prepress.geometria import Formato

TOLERANCIA_PT = 0.5


@dataclass(frozen=True)
class Checagem:
    """Uma pergunta feita ao arquivo, com a resposta que ele deu."""

    nome: str
    passou: bool
    detalhe: str

    def __str__(self) -> str:
        marca = "ok  " if self.passou else "FALHA"
        return f"{marca} {self.nome}: {self.detalhe}"


def _caixas(dados: bytes, nome: str) -> list[tuple[float, ...]]:
    padrao = re.compile(
        rb"/" + nome.encode("ascii") + rb"\s*\[([^\]]*)\]", re.MULTILINE
    )
    encontradas = []
    for bruto in padrao.findall(dados):
        try:
            encontradas.append(tuple(float(v) for v in bruto.split()))
        except ValueError:
            continue
    return encontradas


def _mesma_caixa(
    obtida: tuple[float, ...], esperada: tuple[float, float, float, float]
) -> bool:
    return len(obtida) == 4 and all(
        abs(a - b) <= TOLERANCIA_PT for a, b in zip(obtida, esperada)
    )


def conferir(caminho: Path, formato: Formato, versao: str = "X-1a") -> list[Checagem]:
    """Roda todas as checagens e devolve uma linha por pergunta."""
    dados = caminho.read_bytes()
    checagens: list[Checagem] = []

    cabecalho = dados[:8].decode("ascii", errors="replace")
    esperado_versao_pdf = {"X-1a": "%PDF-1.3", "X-3": "%PDF-1.4", "X-4": "%PDF-1.6"}
    alvo = esperado_versao_pdf.get(versao, "%PDF-1.3")
    checagens.append(
        Checagem(
            "versão do PDF",
            cabecalho == alvo,
            f"{cabecalho}, esperado {alvo} para PDF/{versao}",
        )
    )

    marca_pdfx = re.search(rb"/GTS_PDFXVersion\s*\(([^)]*)\)", dados)
    checagens.append(
        Checagem(
            "declaração PDF/X",
            marca_pdfx is not None,
            marca_pdfx.group(1).decode("latin-1") if marca_pdfx else "ausente",
        )
    )

    tem_intent = b"/GTS_PDFX" in dados and b"/OutputIntent" in dados
    condicao = re.search(rb"/OutputCondition\s*\(([^)]*)\)", dados)
    checagens.append(
        Checagem(
            "OutputIntent",
            tem_intent,
            condicao.group(1).decode("latin-1") if condicao else "ausente",
        )
    )

    checagens.append(
        Checagem(
            "perfil de saída embutido",
            b"/DestOutputProfile" in dados,
            "DestOutputProfile presente" if b"/DestOutputProfile" in dados else "ausente",
        )
    )

    for nome, esperada in (
        ("TrimBox", formato.trim_box),
        ("BleedBox", formato.bleed_box),
    ):
        obtidas = _caixas(dados, nome)
        bate = any(_mesma_caixa(caixa, esperada) for caixa in obtidas)
        alvo_texto = " ".join(f"{v:.2f}" for v in esperada)
        obtido_texto = (
            " | ".join(" ".join(f"{v:.2f}" for v in c) for c in obtidas) or "ausente"
        )
        checagens.append(
            Checagem(nome, bate, f"esperado [{alvo_texto}], encontrado [{obtido_texto}]")
        )

    fontes = set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)", dados))
    arquivos = re.findall(rb"/FontFile\d?", dados)
    checagens.append(
        Checagem(
            "fontes embutidas",
            len(fontes) > 0 and len(arquivos) >= len(fontes),
            f"{len(fontes)} fonte(s), {len(arquivos)} arquivo(s) embutido(s)",
        )
    )

    proibidos = [
        rotulo
        for rotulo in (b"/DeviceRGB", b"/CalRGB", b"/DeviceN", b"/Separation")
        if rotulo in dados
    ]
    checagens.append(
        Checagem(
            "somente CMYK",
            not proibidos,
            "nenhum espaço fora de CMYK"
            if not proibidos
            else "encontrado " + ", ".join(r.decode() for r in proibidos),
        )
    )

    paginas = len(re.findall(rb"/Type\s*/Page[^s]", dados))
    checagens.append(
        Checagem("uma página", paginas == 1, f"{paginas} página(s)")
    )

    return checagens


def tudo_passou(checagens: list[Checagem]) -> bool:
    return all(checagem.passou for checagem in checagens)
