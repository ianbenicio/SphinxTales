"""Geometria de pagina para prepress.

Tudo que entra aqui vem em milimetros, porque e assim que grafica e autor falam.
Tudo que sai daqui vai em pontos PostScript, porque e assim que o arquivo fala.
A conversao acontece num lugar so.
"""

from __future__ import annotations

from dataclasses import dataclass

PT_POR_MM = 72.0 / 25.4


def mm(valor: float) -> float:
    """Milimetros para pontos PostScript."""
    return valor * PT_POR_MM


@dataclass(frozen=True)
class Formato:
    """Formato de corte mais tudo que vive fora dele.

    A midia e maior que o corte porque precisa caber a sangria e as marcas.
    Nenhum desses numeros e constante do sistema: sao parametros, e a grafica
    e quem diz quais valem.
    """

    largura_mm: float = 160.0
    altura_mm: float = 230.0
    sangria_mm: float = 3.0
    offset_marca_mm: float = 3.0
    comprimento_marca_mm: float = 5.0
    espessura_marca_pt: float = 0.25

    @property
    def margem_midia_mm(self) -> float:
        """Espaco entre o corte e a borda do papel, suficiente para as marcas."""
        return self.offset_marca_mm + self.comprimento_marca_mm + 2.0

    @property
    def midia_largura(self) -> float:
        return mm(self.largura_mm + 2 * self.margem_midia_mm)

    @property
    def midia_altura(self) -> float:
        return mm(self.altura_mm + 2 * self.margem_midia_mm)

    @property
    def trim_x(self) -> float:
        return mm(self.margem_midia_mm)

    @property
    def trim_y(self) -> float:
        return mm(self.margem_midia_mm)

    @property
    def trim_largura(self) -> float:
        return mm(self.largura_mm)

    @property
    def trim_altura(self) -> float:
        return mm(self.altura_mm)

    @property
    def trim_box(self) -> tuple[float, float, float, float]:
        return (
            self.trim_x,
            self.trim_y,
            self.trim_x + self.trim_largura,
            self.trim_y + self.trim_altura,
        )

    @property
    def bleed_box(self) -> tuple[float, float, float, float]:
        s = mm(self.sangria_mm)
        x0, y0, x1, y1 = self.trim_box
        return (x0 - s, y0 - s, x1 + s, y1 + s)

    @property
    def media_box(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, self.midia_largura, self.midia_altura)

    @classmethod
    def de_texto(cls, texto: str, **extras: float) -> Formato:
        """Interpreta "160x230" como formato de corte em milimetros."""
        try:
            largura, altura = (float(parte) for parte in texto.lower().split("x"))
        except ValueError as erro:
            raise ValueError(
                f"formato invalido: {texto!r}. Use LARGURAxALTURA em mm, por exemplo 160x230"
            ) from erro
        return cls(largura_mm=largura, altura_mm=altura, **extras)
