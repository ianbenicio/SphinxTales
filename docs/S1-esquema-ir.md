# S1 — Esquema IR

**Critério de aceite:** livro de exemplo à mão valida; campo obrigatório ausente
falha nomeando o campo, nunca em silêncio.

**Estado:** atendido. Verificável por outra pessoa com os comandos ao fim deste
documento.

## O que o esquema cobre

Nove blocos: `paragraph`, `heading`, `list`, `table`, `code`, `figure`,
`callout`, `definition`, `exercise`. Seis nós inline: `text`, `emph`, `strong`,
`code_span`, `term_ref`, `footnote`. Mais `meta`, `bible` e o contrato de
capítulo com `requer`, `introduz` e `nao_repetir`.

## Decisões

**Campo desconhecido é erro.** Todo nó usa `extra="forbid"`. Um `nivell` digitado
errado não é descartado em silêncio: é rejeitado apontando o caminho. Esse é o
modo de falha que o critério de aceite existe para impedir.

**União discriminada por `tipo`.** Um bloco de tipo inexistente falha na entrada,
não na diagramação. O erro nomeia a variante, então a mensagem diz qual bloco
falhou e não apenas onde.

**String é açúcar para `[text]`.** Onde o esquema pede texto rico, uma string
simples é aceita e convertida. A conversão é documentada e testada, o que a
separa de uma coerção silenciosa.

**Prepress fica fora do IR.** Formato de página, margens e perfil de cor são
parâmetros de S3, não propriedades do texto. O mesmo IR precisa render em
qualquer formato sem ser reescrito.

**Um termo, uma definição.** Duas definições do mesmo termo produziriam duas
entradas de glossário para a mesma coisa e um índice remissivo que aponta para a
errada. Aliases contam como termo para efeito de colisão.

**Um só percurso da árvore.** `ir/walk.py` é o único lugar que desce em blocos e
inline aninhados. Quem precisar de todos os blocos ou todos os termos citados usa
essas funções, para que nenhum consumidor esqueça um ramo.

## O que S1 deliberadamente não faz

Não verifica contratos entre capítulos vizinhos nem uso de termo antes da
definição. Isso é S5 e S8. O esquema apenas guarda os campos que essas specs vão
consumir.

## Como verificar

```bash
python -m bookshelf.cli validate examples/livro-exemplo.json
```

Saída esperada: `aceito: ... - 2 capitulo(s), 19 bloco(s)`, código de saída 0.

Plante um defeito e confirme que a mensagem nomeia o campo:

```bash
python -m pytest tests/test_falhas_nomeadas.py -v
```

Cada teste desse arquivo remove ou corrompe um campo e exige que o caminho
apareça na mensagem. Um teste que só verificasse "levantou exceção" não provaria
o critério.
