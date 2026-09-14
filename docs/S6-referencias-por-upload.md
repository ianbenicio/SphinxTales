# S6 — Referências só por upload

**Critério de aceite:** referência de estrutura vira checklist consumível pelo loop; referência
não confirmada não aparece em prompt nenhum, verificável por inspeção; o autor confirma a
decomposição sem reescrevê-la.

**Estado:** atendido nos dois primeiros critérios. O terceiro ficou **mensurável**, e a medida só
pode ser lida no uso real com o autor. Ver a seção sobre isso adiante.

**Depende de:** S4. Pelo [ADR-001](ADR-001-nucleo-casca-e-interface.md), a camada de condução
extrai a decomposição e o núcleo a persiste.

## Como usar

```bash
python -m sphinxtales.cli referencias subir manual.pdf --contribuicao estrutura
python -m sphinxtales.cli referencias decompor <id> --item "Abre com o problema" --item "Dá o conceito"
python -m sphinxtales.cli referencias confirmar <id> --autor "Nome" --editar "2=Define com um exemplo"
python -m sphinxtales.cli referencias checklist
```

O acervo fica em `referencias.json` e os arquivos em `referencias/`.

## Os seis tipos de contribuição

O autor declara o que a referência empresta ao livro. A lista é fechada.

| Contribuição | O que o material ensina |
|---|---|
| `estrutura` | Em que ordem um capítulo se desenrola |
| `tom` | Como o texto soa |
| `profundidade` | Até onde descer num assunto |
| `exemplos` | Que tipo de exemplo funciona |
| `contra_exemplo` | O que não fazer |
| `diagramacao` | Como a página se organiza |

Só `estrutura` vira checklist. As outras entram como contexto na materialização, porque não são
cobráveis item a item.

## Decisões

**O autor confirma a decomposição, não o arquivo.** Confirmar um PDF inteiro seria confirmar uma
intenção. Confirmar uma lista de estágios é confirmar algo que depois se pode cobrar. O modelo
recusa uma referência confirmada sem decomposição.

**O arquivo é copiado para dentro do acervo.** Guardar só o caminho original deixaria o vínculo
quebrar assim que o autor movesse a pasta dele, e uma decomposição confirmada sobre um arquivo
que sumiu não vale nada.

**O identificador vem do conteúdo.** Subir o mesmo arquivo duas vezes devolve a mesma referência,
mesmo que o autor declare outra contribuição na segunda vez.

**O sha256 detecta que o arquivo mudou depois da análise.** Se o autor substituir o material, a
decomposição confirmada passa a descrever outra coisa. A listagem avisa.

**A materialização só enxerga confirmadas.** Mesma regra das tags, e pelo mesmo motivo. Este é o
único caminho de referência para prompt.

**O ciclo de confirmação foi extraído.** Tags e referências percorrem o mesmo ciclo e carregam a
mesma promessa, então a invariante mora em `sphinxtales/confirmacao.py`, num lugar só. Uma
invariante escrita duas vezes é uma invariante que um dia vai divergir.

## Sobre o terceiro critério de aceite

"O autor confirma a decomposição sem reescrevê-la" descreve um custo humano, e custo humano não
se prova com teste automatizado. O que dá para fazer é **medir**, e é isso que o sistema faz.

Cada edição na confirmação guarda o texto que o sistema havia proposto. A partir daí existe uma
taxa de reescrita, que a linha de comando mostra no momento da confirmação:

```
✓ b38e29cc360b06ab  estrutura  manual.txt  (3 item(ns), 1 reescrito(s))
taxa de reescrita: 33%
```

Uma decomposição reescrita inteira falhou, ainda que o autor a confirme no fim. O plano não fixa
um limiar, e inventar um aqui seria pior que não ter: o número tem que ser lido no teste com o
autor real, que é quando ele passa a significar alguma coisa.

## O que o S6 deliberadamente não faz

Sem descoberta de referências na web, que o plano corta pela alucinação de título somada à
exposição jurídica. Sem extração automática do conteúdo do arquivo, que é trabalho da camada de
condução. Sem vínculo entre referência e tag, que aparece no S10.

## Como verificar

```bash
python -m pytest tests/test_referencias.py -v
```

Os três critérios têm seção própria. O segundo é verificável também à mão: depois de `subir` e
`decompor`, o comando `materializar` sai com código 1 e diz que não há nada a materializar. Só
depois de `confirmar` a referência aparece.
