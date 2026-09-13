"""Parametros tipograficos e de pagina do miolo.

Nada aqui e constante do sistema. Formato de corte vem da grafica, margens e
corpo vem da decisao editorial, e as duas coisas mudam sem tocar no emissor.

As fontes padrao sao as que o Typst embute, e isso e deliberado: um PDF que
depende de fonte instalada na maquina sai diferente em cada maquina, e prepress
nao perdoa isso.
"""

from __future__ import annotations

from dataclasses import dataclass

FONTE_TEXTO = "Libertinus Serif"
FONTE_CODIGO = "DejaVu Sans Mono"


@dataclass(frozen=True)
class Tema:
    """Como o livro se parece. Um tema no MVP, mas parametrizado desde ja."""

    largura_mm: float = 160.0
    altura_mm: float = 230.0

    margem_interna_mm: float = 22.0
    margem_externa_mm: float = 17.0
    margem_superior_mm: float = 20.0
    margem_inferior_mm: float = 22.0

    fonte_texto: str = FONTE_TEXTO
    fonte_codigo: str = FONTE_CODIGO
    corpo_pt: float = 10.5
    entrelinha: float = 0.75
    recuo_paragrafo_em: float = 1.2

    idioma: str = "pt"
    hifenizar: bool = True
    justificar: bool = True

    titulo_sumario: str = "Sumário"
    titulo_glossario: str = "Glossário"
    titulo_indice: str = "Índice remissivo"

    profundidade_sumario: int = 2

    @property
    def fontes_texto(self) -> tuple[str, ...]:
        """Pilha de fontes: a embutida primeiro, substitutas depois."""
        return (self.fonte_texto, "New Computer Modern", "DejaVu Serif")

    @property
    def fontes_codigo(self) -> tuple[str, ...]:
        return (self.fonte_codigo, "Consolas", "Courier New")
