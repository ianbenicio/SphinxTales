"""IR para codigo Typst.

Duas regras governam este modulo.

**Texto do autor nunca vira markup.** Todo caractere escrito por uma pessoa ou
por um modelo entra no documento como string literal Typst, dentro de
`#("...")`. Escapar isso exige tratar dois caracteres, barra e aspas, em vez de
uma dezena de simbolos de markup. O efeito colateral importa: um texto que
contenha `#calc.pow(2,10)` sai impresso como esses caracteres, e nao como 1024.
Sem essa regra, o conteudo gerado poderia executar codigo na diagramacao.

**Nenhum bloco cai em silencio.** O despacho e um dicionario explicito, e a
ultima secao deste arquivo compara as chaves dele com os tipos declarados no
IR. Um bloco novo no esquema sem regra de render aqui derruba a importacao do
modulo, nao a diagramacao do livro.
"""

from __future__ import annotations

from typing import Any, Callable

from sphinxtales.ir import (
    TIPOS_BLOCO,
    TIPOS_INLINE,
    Book,
    Callout,
    Chapter,
    CodeBlock,
    Definition,
    Exercise,
    Figure,
    Heading,
    ListBlock,
    ListItem,
    Paragraph,
    TableBlock,
    definicoes,
)

BARRA = chr(92)

ALINHAMENTO_TYPST = {
    "esquerda": "left",
    "centro": "center",
    "direita": "right",
}

ROTULO_CALLOUT = {
    "nota": "Nota",
    "aviso": "Aviso",
    "dica": "Dica",
    "importante": "Importante",
    "exemplo": "Exemplo",
}

ROTULO_DIFICULDADE = {
    "basico": "básico",
    "intermediario": "intermediário",
    "avancado": "avançado",
}


# --------------------------------------------------------------- texto literal


def escapar(texto: str) -> str:
    """Escapa para dentro de uma string Typst: barra e aspas, so isso."""
    return texto.replace(BARRA, BARRA * 2).replace('"', BARRA + '"')


def literal(texto: str) -> str:
    """A unica porta por onde texto de autor entra no documento."""
    return f'#("{escapar(texto)}")'


def _cru(texto: str) -> str:
    """String Typst nua, para argumentos de funcao."""
    return f'"{escapar(texto)}"'


# ----------------------------------------------------------------- nos inline


def _inline_text(no: Any) -> str:
    return literal(no.conteudo)


def _inline_emph(no: Any) -> str:
    return f"#emph[{emitir_richtext(no.conteudo)}]"


def _inline_strong(no: Any) -> str:
    return f"#strong[{emitir_richtext(no.conteudo)}]"


def _inline_code_span(no: Any) -> str:
    return f"#raw({_cru(no.conteudo)})"


def _inline_term_ref(no: Any) -> str:
    """Marca a ocorrencia para o indice e imprime o texto de exibicao."""
    exibido = emitir_richtext(no.conteudo) if no.conteudo else literal(no.termo)
    return f"#marca-termo({_cru(no.termo)}){exibido}"


def _inline_footnote(no: Any) -> str:
    return f"#footnote[{emitir_richtext(no.conteudo)}]"


EMISSORES_INLINE: dict[str, Callable[[Any], str]] = {
    "text": _inline_text,
    "emph": _inline_emph,
    "strong": _inline_strong,
    "code_span": _inline_code_span,
    "term_ref": _inline_term_ref,
    "footnote": _inline_footnote,
}


def emitir_richtext(nos: list[Any] | None) -> str:
    if not nos:
        return ""
    return "".join(EMISSORES_INLINE[no.tipo](no) for no in nos)


# --------------------------------------------------------------------- blocos


def _bloco_paragraph(bloco: Paragraph, nivel: int) -> str:
    return f"#par[{emitir_richtext(bloco.conteudo)}]"


def _bloco_heading(bloco: Heading, nivel: int) -> str:
    """Desloca a hierarquia: o capitulo ja ocupa o nivel 1 do documento."""
    return f"#heading(level: {bloco.nivel + nivel})[{emitir_richtext(bloco.conteudo)}]"


def _itens(itens: list[ListItem], funcao: str) -> str:
    """Subitens viram uma lista aninhada dentro do item, nao itens irmaos.

    O `ListItem` nao declara se o subnivel e ordenado, entao ele herda a
    natureza da lista que o contem.
    """
    partes = []
    for item in itens:
        corpo = emitir_richtext(item.conteudo)
        if item.subitens:
            corpo += f"#{funcao}({_itens(item.subitens, funcao)})"
        partes.append(f"[{corpo}]")
    return ", ".join(partes)


def _bloco_list(bloco: ListBlock, nivel: int) -> str:
    funcao = "enum" if bloco.ordenada else "list"
    return f"#{funcao}({_itens(bloco.itens, funcao)})"


def _bloco_table(bloco: TableBlock, nivel: int) -> str:
    larguras = ", ".join(
        "auto" if coluna.largura is None else f"{coluna.largura}fr"
        for coluna in bloco.colunas
    )
    alinhamentos = ", ".join(
        ALINHAMENTO_TYPST[coluna.alinhamento] for coluna in bloco.colunas
    )
    cabecalho = ", ".join(f"[{emitir_richtext(c.cabecalho)}]" for c in bloco.colunas)
    celulas = ", ".join(
        f"[{emitir_richtext(celula)}]" for linha in bloco.linhas for celula in linha
    )
    legenda = f"[{emitir_richtext(bloco.legenda)}]" if bloco.legenda else "none"
    repetir = "true" if bloco.repetir_cabecalho else "false"
    return (
        f"#bloco-tabela(({larguras},), ({alinhamentos},), "
        f"({cabecalho},), ({celulas},), {legenda}, {repetir})"
    )


def _bloco_code(bloco: CodeBlock, nivel: int) -> str:
    lingua = _cru(bloco.linguagem) if bloco.linguagem else "none"
    legenda = f"[{emitir_richtext(bloco.legenda)}]" if bloco.legenda else "none"
    numerar = "true" if bloco.numerar_linhas else "false"
    return f"#bloco-codigo({_cru(bloco.conteudo)}, {lingua}, {legenda}, {numerar})"


def _bloco_figure(bloco: Figure, nivel: int) -> str:
    """Imagem esta fora do MVP, entao a figura vira moldura com o alternativo.

    O bloco continua ocupando espaco no documento, para que a ausencia da arte
    seja visivel na prova em vez de silenciosa.
    """
    legenda = f"[{emitir_richtext(bloco.legenda)}]" if bloco.legenda else "none"
    credito = _cru(bloco.credito) if bloco.credito else "none"
    return f"#bloco-figura({_cru(bloco.fonte)}, {_cru(bloco.alt)}, {legenda}, {credito})"


def _bloco_callout(bloco: Callout, nivel: int) -> str:
    titulo = (
        f"[{emitir_richtext(bloco.titulo)}]"
        if bloco.titulo
        else f"[{literal(ROTULO_CALLOUT[bloco.variante])}]"
    )
    corpo = emitir_blocos(bloco.conteudo, nivel)
    return f"#bloco-destaque({_cru(bloco.variante)}, {titulo}, [{corpo}])"


def _bloco_definition(bloco: Definition, nivel: int) -> str:
    return f"#bloco-definicao({_cru(bloco.termo)}, [{emitir_richtext(bloco.definicao)}])"


def _bloco_exercise(bloco: Exercise, nivel: int) -> str:
    dificuldade = (
        _cru(ROTULO_DIFICULDADE[bloco.dificuldade]) if bloco.dificuldade else "none"
    )
    enunciado = emitir_blocos(bloco.enunciado, nivel)
    resposta = f"[{emitir_blocos(bloco.resposta, nivel)}]" if bloco.resposta else "none"
    return (
        f"#bloco-exercicio({_cru(bloco.id)}, {dificuldade}, [{enunciado}], {resposta})"
    )


EMISSORES_DE_BLOCO: dict[str, Callable[[Any, int], str]] = {
    "paragraph": _bloco_paragraph,
    "heading": _bloco_heading,
    "list": _bloco_list,
    "table": _bloco_table,
    "code": _bloco_code,
    "figure": _bloco_figure,
    "callout": _bloco_callout,
    "definition": _bloco_definition,
    "exercise": _bloco_exercise,
}


def emitir_blocos(blocos: list[Any], nivel: int = 1) -> str:
    return "\n".join(EMISSORES_DE_BLOCO[b.tipo](b, nivel) for b in blocos)


# ------------------------------------------------------------------ documento


def preambulo(tema: Any) -> str:
    """Ajustes de pagina e as funcoes Typst que os blocos chamam."""
    fontes = ", ".join(_cru(f) for f in tema.fontes_texto)
    fontes_codigo = ", ".join(_cru(f) for f in tema.fontes_codigo)
    justificar = "true" if tema.justificar else "false"
    hifenizar = "true" if tema.hifenizar else "false"
    return f"""
#set page(
  width: {tema.largura_mm}mm,
  height: {tema.altura_mm}mm,
  margin: (
    inside: {tema.margem_interna_mm}mm,
    outside: {tema.margem_externa_mm}mm,
    top: {tema.margem_superior_mm}mm,
    bottom: {tema.margem_inferior_mm}mm,
  ),
  binding: left,
  numbering: "1",
)
#set text(
  font: ({fontes},),
  size: {tema.corpo_pt}pt,
  lang: {_cru(tema.idioma)},
  hyphenate: {hifenizar},
)
#set par(justify: {justificar}, leading: {tema.entrelinha}em,
         first-line-indent: {tema.recuo_paragrafo_em}em)
#set heading(numbering: none)
#show heading.where(level: 1): it => {{
  pagebreak(weak: true)
  block(above: 2em, below: 1.2em, text(size: 1.7em, weight: 700, it.body))
}}
#show heading.where(level: 2): it => block(
  above: 1.6em, below: 0.7em, text(size: 1.2em, weight: 600, it.body))
#show heading.where(level: 3): it => block(
  above: 1.2em, below: 0.5em, text(size: 1.05em, weight: 600, it.body))
#show raw: set text(font: ({fontes_codigo},), size: 0.88em)

#let marca-termo(termo) = [#metadata(termo)<idx>]

#let bloco-tabela(larguras, alinhamentos, cabecalho, celulas, legenda, repetir) = {{
  block(breakable: true, above: 1em, below: 1em)[
    #table(
      columns: larguras,
      align: (col, _) => alinhamentos.at(col),
      stroke: 0.4pt + luma(140),
      inset: 6pt,
      table.header(repeat: repetir, ..cabecalho.map(c => strong(c))),
      ..celulas,
    )
    #if legenda != none [#v(0.3em) #text(size: 0.85em, style: "italic", legenda)]
  ]
}}

#let bloco-codigo(conteudo, lingua, legenda, numerar) = {{
  block(breakable: true, above: 1em, below: 1em, width: 100%,
        fill: luma(246), inset: 8pt, radius: 2pt)[
    #if numerar {{
      let linhas = conteudo.split("\\n")
      let largura = str(linhas.len()).len()
      for (indice, linha) in linhas.enumerate() [
        #text(fill: luma(150), size: 0.88em)[#box(width: (largura + 1) * 0.62em,
          align(right, raw(str(indice + 1))))]#h(0.5em)#raw(linha, lang: lingua) \\
      ]
    }} else {{
      raw(conteudo, lang: lingua, block: true)
    }}
    #if legenda != none [#v(0.3em) #text(size: 0.85em, style: "italic", legenda)]
  ]
}}

#let bloco-figura(fonte, alt, legenda, credito) = {{
  block(breakable: false, above: 1em, below: 1em, width: 100%,
        stroke: 0.5pt + luma(160), inset: 10pt)[
    #align(center)[
      #text(size: 0.8em, fill: luma(110))[figura ausente nesta etapa: #fonte]
      #v(0.4em)
      #text(size: 0.9em, style: "italic")[#alt]
    ]
    #if legenda != none [#v(0.5em) #text(size: 0.85em)[#legenda]]
    #if credito != none [#v(0.2em) #text(size: 0.75em, fill: luma(110))[#credito]]
  ]
}}

#let bloco-destaque(variante, titulo, corpo) = {{
  block(breakable: true, above: 1em, below: 1em, width: 100%,
        stroke: (left: 2pt + luma(80)), inset: (left: 10pt, rest: 8pt))[
    #text(size: 0.85em, weight: 700, tracking: 0.06em)[#upper(titulo)]
    #v(0.3em)
    #corpo
  ]
}}

#let bloco-definicao(termo, corpo) = {{
  block(above: 1em, below: 1em, width: 100%)[
    #marca-termo(termo)#strong(termo)#h(0.4em)#corpo
  ]
}}

#let bloco-exercicio(id, dificuldade, enunciado, resposta) = {{
  block(breakable: true, above: 1.2em, below: 1.2em, width: 100%,
        stroke: 0.5pt + luma(180), inset: 9pt, radius: 2pt)[
    #text(size: 0.8em, weight: 700, tracking: 0.06em)[EXERCÍCIO #id]
    #if dificuldade != none [#text(size: 0.8em, fill: luma(110))[ · #dificuldade]]
    #v(0.4em)
    #enunciado
    #if resposta != none [
      #v(0.5em)
      #text(size: 0.8em, weight: 700, tracking: 0.06em)[RESPOSTA]
      #v(0.2em)
      #resposta
    ]
  ]
}}
"""


def _folha_de_rosto(livro: Book) -> str:
    """A folha de rosto nao exibe numero, mas conta como pagina.

    O contador nao e reiniciado depois dela de proposito: a grafica fecha
    cadernos pelo total fisico de folhas, e um contador que recomeca faria o
    selo do fim do documento informar um numero menor que o real.
    """
    subtitulo = (
        f'#v(0.6em) #text(size: 1.2em, style: "italic")[{literal(livro.meta.subtitulo)}]'
        if livro.meta.subtitulo
        else ""
    )
    return f"""
#page(numbering: none)[
  #v(28%)
  #text(size: 2.4em, weight: 700)[{literal(livro.meta.titulo)}]
  {subtitulo}
  #v(2em)
  #text(size: 1.05em)[{literal(livro.meta.autor)}]
]
"""


def _sumario(tema: Any) -> str:
    return (
        f"#heading(level: 1, outlined: false)[{literal(tema.titulo_sumario)}]\n"
        f"#outline(title: none, depth: {tema.profundidade_sumario})\n"
    )


def _glossario(livro: Book, tema: Any) -> str:
    """Derivado dos blocos `definition`, em ordem alfabetica do termo.

    A fonte e o IR, nao uma lista mantida a mao. Um termo definido e um termo
    no glossario, sem passo intermediario que possa divergir.
    """
    entradas: list[tuple[str, str]] = []
    for capitulo in livro.capitulos:
        for _, definicao in definicoes(capitulo.blocos):
            entradas.append((definicao.termo, emitir_richtext(definicao.definicao)))
    if not entradas:
        return ""

    linhas = [
        f"#bloco-definicao({_cru(termo)}, [{corpo}])"
        for termo, corpo in sorted(entradas, key=lambda par: par[0].casefold())
    ]
    return f"#heading(level: 1)[{literal(tema.titulo_glossario)}]\n" + "\n".join(linhas)


def _indice_remissivo(tema: Any) -> str:
    """Precisa do numero de pagina, entao quem monta e o Typst, nao o Python."""
    return f"""
#heading(level: 1)[{literal(tema.titulo_indice)}]
#context {{
  let mapa = (:)
  for entrada in query(<idx>) {{
    let termo = entrada.value
    let pagina = str(counter(page).at(entrada.location()).first())
    let paginas = mapa.at(termo, default: ())
    if not paginas.contains(pagina) {{ mapa.insert(termo, paginas + (pagina,)) }}
  }}
  for termo in mapa.keys().sorted() [
    #termo #box(width: 1fr, repeat[.]) #mapa.at(termo).join(", ") \\
  ]
}}
"""


def _capitulo(capitulo: Chapter) -> str:
    return f"#heading(level: 1)[{literal(capitulo.titulo)}]\n" + emitir_blocos(
        capitulo.blocos, nivel=1
    )


TOTAL_DE_PAGINAS = "<total-paginas>"

_SELO_DE_PAGINAS = """
#context [#metadata(counter(page).final().first())<total-paginas>]
"""


def emitir_documento(livro: Book, tema: Any) -> str:
    """Monta o arquivo Typst inteiro, do preambulo ao selo final.

    O selo faz o documento declarar quantas paginas tem. Contar isso raspando
    o PDF por expressao regular da numero errado, porque a marca `/Type /Page`
    aparece mais vezes do que ha paginas.
    """
    partes = [
        preambulo(tema),
        _folha_de_rosto(livro),
        _sumario(tema),
        *(_capitulo(capitulo) for capitulo in livro.capitulos),
        _glossario(livro, tema),
        _indice_remissivo(tema),
        _SELO_DE_PAGINAS,
    ]
    return "\n\n".join(parte for parte in partes if parte.strip()) + "\n"


# ------------------------------------------------- exaustividade na importacao

_blocos_sem_regra = TIPOS_BLOCO - set(EMISSORES_DE_BLOCO)
if _blocos_sem_regra:
    raise RuntimeError(
        "blocos do IR sem regra de render: " + ", ".join(sorted(_blocos_sem_regra))
    )

_inline_sem_regra = TIPOS_INLINE - set(EMISSORES_INLINE)
if _inline_sem_regra:
    raise RuntimeError(
        "nós inline do IR sem regra de render: " + ", ".join(sorted(_inline_sem_regra))
    )
