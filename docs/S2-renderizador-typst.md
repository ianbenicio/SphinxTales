# S2 — Renderizador Typst

**Critério de aceite:** nenhum tipo do IR fica sem regra de render, verificado na compilação e
não por inspeção; tabela larga e bloco de código quebram página sem cortar conteúdo.

**Estado:** atendido. Verificável por outra pessoa com os comandos ao fim deste documento.

**Depende de:** S1.

## Como usar

```bash
python -m sphinxtales.cli render examples/livro-exemplo.json
```

Sai em `out/livro.pdf`, com o código Typst intermediário em `out/livro.typ`. Formato e corpo são
parâmetros:

```bash
python -m sphinxtales.cli render meu-livro.json --largura 148 --altura 210 --corpo 9.5
```

O comando valida o documento antes de diagramar. IR inválido não vira PDF.

## Decisões

**Texto do autor nunca vira markup.** Todo caractere escrito por uma pessoa ou por um modelo
entra no documento como string literal Typst, dentro de `#("...")`. O escape trata dois
caracteres, barra e aspas, em vez de uma dezena de símbolos.

Isso não é conveniência, é contenção. O texto que o S7 vai gerar passa por aqui, e um parágrafo
contendo `#calc.pow(2,10)` precisa sair impresso com esses caracteres, nunca virar 1024 na
página. Sem essa regra, conteúdo gerado executaria código na diagramação. O teste correspondente
extrai o texto do PDF e exige as duas coisas: que a sequência apareça e que o resultado da conta
não apareça.

**Nenhum bloco cai em silêncio.** O despacho é um dicionário explícito, e o fim do módulo compara
as chaves dele com os tipos declarados no IR. Um bloco novo no esquema sem regra de render aqui
derruba a importação do módulo. É o mais perto de uma verificação em tempo de compilação que
Python oferece, e é bem diferente de descobrir o problema quando o livro sai com um trecho
faltando.

**O glossário sai do IR, o índice sai do Typst.** O glossário é derivado dos blocos `definition`
por código Python, porque é determinístico e não depende de paginação. O índice remissivo precisa
do número de página, que só existe depois da diagramação, então quem o monta é o Typst, com
`metadata`, `query` e o contador de página.

**O documento declara quantas páginas tem.** Um selo no fim registra o total, e a contagem o lê
com `query`. Raspar `/Type /Page` do PDF dá número errado: no livro de exemplo a marca aparece
quatorze vezes para sete páginas.

**A folha de rosto conta como página.** Ela não exibe número, mas o contador não é reiniciado
depois dela. A gráfica fecha cadernos pelo total físico de folhas, e um contador que recomeça
faria o selo informar menos páginas do que o livro tem.

**As fontes são as que o Typst embute.** Libertinus Serif no texto e DejaVu Sans Mono no código.
Um PDF que depende de fonte instalada na máquina sai diferente em cada máquina, e prepress não
perdoa isso.

**Figura vira moldura com o texto alternativo.** Imagem está fora do MVP, mas o bloco existe no
IR. Em vez de ignorá-lo, o renderizador desenha uma moldura com o alternativo dentro, para que a
ausência da arte seja visível na prova em vez de silenciosa.

## O que o S2 deliberadamente não faz

Um tema só, sem variantes. Sem imagens, sem capa, sem EPUB. Sem sangria nem marcas de corte, que
são do S3b. Sem numeração de capítulo, porque a decisão editorial ainda não existe.

## Como verificar

```bash
python -m sphinxtales.cli render examples/livro-exemplo.json
```

Saída esperada: `diagramado: ... - 7 pagina(s) em 160 x 230 mm`, código de saída 0.

```bash
python -m pytest tests/test_render.py -v
```

Os dois critérios de aceite têm testes próprios. O primeiro compara as chaves do despacho com os
tipos do IR e confirma que um tipo sem regra derruba a importação. O segundo monta um livro com
setenta linhas de tabela e noventa linhas de código, renderiza, extrai o texto do PDF e exige que
cada uma das cento e sessenta linhas esteja presente. Se a quebra de página cortasse conteúdo,
alguma linha sumiria e o teste apontaria quais.
