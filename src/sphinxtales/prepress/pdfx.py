"""Conversao de PostScript para PDF/X pelo Ghostscript.

O Ghostscript e quem escreve o PDF final, e ele precisa de duas coisas que nao
estao no PostScript: a declaracao da versao PDF/X e o OutputIntent com o perfil
de saida. As duas sao montadas aqui, a partir de parametros, nunca de
constantes embutidas.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

VERSOES = {
    "X-1a": ("PDF/X-1a:2001", "1.3"),
    "X-3": ("PDF/X-3:2002", "1.4"),
    "X-4": ("PDF/X-4", "1.6"),
}

EXECUTAVEIS = ("gswin64c", "gswin32c", "gs")


class GhostscriptAusente(RuntimeError):
    """Ghostscript nao esta no PATH."""


class ConversaoFalhou(RuntimeError):
    """Ghostscript rodou e recusou o arquivo. A saida dele vem junto."""

    def __init__(self, comando: list[str], codigo: int, saida: str):
        self.comando = comando
        self.codigo = codigo
        self.saida = saida
        super().__init__(f"Ghostscript saiu com codigo {codigo}:\n{saida}")


@dataclass(frozen=True)
class PerfilDeSaida:
    """A condicao de impressao que o arquivo declara cumprir.

    Nenhum destes valores e escolha nossa. Sao o que a grafica responde quando
    perguntada, e por isso entram como parametro.
    """

    caminho_icc: Path
    condicao: str = "Commercial and specialty printing"
    identificador: str = "Custom"
    info: str = "perfil a confirmar com a grafica"

    @property
    def icc_para_postscript(self) -> str:
        return self.caminho_icc.resolve().as_posix()


def localizar_ghostscript() -> str:
    for nome in EXECUTAVEIS:
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    raise GhostscriptAusente(
        "Ghostscript nao encontrado no PATH. Procurei por: " + ", ".join(EXECUTAVEIS)
    )


def perfil_padrao_do_ghostscript() -> Path | None:
    """O perfil CMYK generico que acompanha o Ghostscript.

    Serve para produzir um arquivo valido antes de a grafica dizer qual perfil
    ela quer. Nao e um perfil de condicao de impressao real, e a prova declara
    isso no rodape.
    """
    executavel = Path(localizar_ghostscript())
    candidato = executavel.parent.parent / "iccprofiles" / "default_cmyk.icc"
    return candidato if candidato.exists() else None


def montar_definicao(titulo: str, perfil: PerfilDeSaida, versao: str) -> str:
    """Gera o prefixo PostScript que declara PDF/X e o OutputIntent."""
    if versao not in VERSOES:
        raise ValueError(
            f"versao PDF/X desconhecida: {versao!r}. Use uma de: "
            + ", ".join(sorted(VERSOES))
        )
    rotulo, _ = VERSOES[versao]
    return f"""%!
% Gerado por sphinxtales.prepress.pdfx. Nao editar a mao.

[ /GTS_PDFXVersion ({rotulo})
  /Title ({_escapar(titulo)})
  /Trapped /False
/DOCINFO pdfmark

/ICCProfile ({_escapar(perfil.icc_para_postscript)}) def

[/_objdef {{icc_PDFX}} /type /stream /OBJ pdfmark
[{{icc_PDFX}} << /N 4 >> /PUT pdfmark
[{{icc_PDFX}} ICCProfile (r) file /PUT pdfmark

[/_objdef {{OutputIntent_PDFX}} /type /dict /OBJ pdfmark
[{{OutputIntent_PDFX}} <<
  /Type /OutputIntent
  /S /GTS_PDFX
  /OutputCondition ({_escapar(perfil.condicao)})
  /Info ({_escapar(perfil.info)})
  /OutputConditionIdentifier ({_escapar(perfil.identificador)})
  /RegistryName (http://www.color.org)
  /DestOutputProfile {{icc_PDFX}}
>> /PUT pdfmark
[{{Catalog}} << /OutputIntents [ {{OutputIntent_PDFX}} ] >> /PUT pdfmark
"""


def _escapar(texto: str) -> str:
    barra = chr(92)
    saida = texto.replace(barra, barra * 2)
    saida = saida.replace("(", barra + "(")
    return saida.replace(")", barra + ")")


def converter(
    entrada_ps: Path,
    saida_pdf: Path,
    titulo: str,
    perfil: PerfilDeSaida,
    versao: str = "X-1a",
) -> Path:
    """Roda o Ghostscript e devolve o caminho do PDF escrito."""
    executavel = localizar_ghostscript()
    _, compatibilidade = VERSOES[versao]

    saida_pdf.parent.mkdir(parents=True, exist_ok=True)
    definicao = saida_pdf.with_suffix(".pdfx_def.ps")
    definicao.write_text(montar_definicao(titulo, perfil, versao), encoding="latin-1")

    comando = [
        executavel,
        "-dPDFX",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-dQUIET",
        f"--permit-file-read={perfil.caminho_icc.resolve().as_posix()}",
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel={compatibilidade}",
        "-sColorConversionStrategy=CMYK",
        "-dProcessColorModel=/DeviceCMYK",
        "-dAutoRotatePages=/None",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dDownsampleColorImages=false",
        "-dDownsampleGrayImages=false",
        "-dDownsampleMonoImages=false",
        "-dAutoFilterColorImages=false",
        "-dColorImageFilter=/FlateEncode",
        f"-sOutputFile={saida_pdf}",
        str(definicao),
        str(entrada_ps),
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not saida_pdf.exists():
        raise ConversaoFalhou(
            comando, resultado.returncode, (resultado.stdout + resultado.stderr).strip()
        )
    return saida_pdf
