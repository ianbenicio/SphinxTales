"""Raster CMYK sintetico para a prova de prensa.

Nenhum arquivo de imagem entra no repositorio: o bitmap e gerado, para que a
resolucao seja exata e o conteudo teste o que precisa ser testado. Tres faixas,
tres perguntas: o degrade tem banding, o cinza composto vira que cor na prensa,
e ate que espessura de linha a prensa resolve.
"""

from __future__ import annotations

import base64
import zlib

CANAIS = 4


def gerar_raster(largura: int, altura: int) -> bytes:
    """Bytes CMYK entrelacados, um byte por canal, sem compressao."""
    pixels = bytearray(largura * altura * CANAIS)
    faixa = altura // 3

    for linha in range(altura):
        base_linha = linha * largura * CANAIS
        for coluna in range(largura):
            posicao = base_linha + coluna * CANAIS
            fracao = coluna / max(largura - 1, 1)

            if linha < faixa:
                # Degrade de preto puro: procura banding na chapa K.
                c = m = y = 0
                k = round(fracao * 255)
            elif linha < 2 * faixa:
                # Cinza composto: procura desvio de matiz na conversao.
                c = m = y = round(fracao * 255)
                k = 0
            else:
                # Listras de periodo crescente: procura o limite de resolucao.
                periodo = 1 + int(fracao * 7)
                c = m = y = 0
                k = 255 if (coluna // periodo) % 2 == 0 else 0

            pixels[posicao] = c
            pixels[posicao + 1] = m
            pixels[posicao + 2] = y
            pixels[posicao + 3] = k

    return bytes(pixels)


def codificar_para_postscript(dados: bytes, largura_linha: int = 76) -> str:
    """Comprime com Flate e codifica em ASCII85, quebrado em linhas."""
    comprimido = zlib.compress(dados, level=9)
    texto = base64.a85encode(comprimido).decode("ascii")
    linhas = [
        texto[inicio : inicio + largura_linha]
        for inicio in range(0, len(texto), largura_linha)
    ]
    return "\n".join(linhas) + "~>"
