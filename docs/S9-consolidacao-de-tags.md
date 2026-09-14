# S9 — Consolidação de tags

**Critério de aceite (provisório):** conjunto com redundância injetada colapsa ao número
esperado sem perder restrição única.

**Estado:** aceite provisório atendido. O gate **G3** segura o aceite definitivo até existirem
tags de verdade produzidas pelo S7b.

**Depende de:** S4.

## Como usar

```bash
python -m sphinxtales.cli tags consolidar
```

É um passe periódico, não algo que roda a cada `propor`. Funde duplicatas e promove padrões
recorrentes à camada do livro, salva o acervo e relata o que mudou.

## O que o passe faz

**Funde** tags que dizem a mesma coisa e a normalização fraca do S4 não pegou. O S4 já resolve
espaço duplicado e caixa; o S9 acrescenta acento e pontuação. `Sem jargão.`, `sem jargao` e
`SEM, JARGAO!!` são três grafias da mesma restrição, e viram uma.

**Promove** ao nível do livro uma tag que existe igualmente em camada de capítulo e em camada de
livro. Se a mesma ideia foi dita nas duas granularidades, a mais geral vence.

**Nunca decai.** Nada é removido por idade ou por falta de uso. A única forma de uma tag sumir é
ser absorvida por outra que diz exatamente a mesma coisa.

## Decisões

**Fundir é conservador por desenho.** A comparação forte remove acento e pontuação, e para por
aí. Não há limiar de similaridade, não há comparação por palavras em comum, não há nada
aproximado. Duas restrições que compartilham metade das palavras e dizem coisas diferentes —
`Sem fórmula com planilha` e `Sem tabela sem planilha` — ficam separadas. O critério de aceite
exige nunca perder uma restrição única, e o jeito de garantir isso é nunca fundir por parecença,
só por igualdade depois de tirar ruído de formatação.

**"Sem decaimento" virou propriedade testável, não só texto da spec.** Rodar o passe duas vezes
seguidas na mesma entrada produz o mesmo resultado na segunda vez: nenhuma fusão nova, nenhuma
tag a menos. Essa idempotência é o que o teste verifica, porque uma frase na documentação não
falha sozinha quando alguém introduz um bug, e um teste falha.

**Tag recusada nunca participa da fusão.** É um ramo encerrado. Deixá-la entrar no agrupamento
arriscaria uma tag confirmada reviver, por acidente, uma proposta que o autor já rejeitou.

**Promoção reconstrói a tag, não copia o campo.** O identificador de uma tag é derivado do tipo,
da camada e do conteúdo. Mudar a camada com `model_copy` sem recalcular o id deixaria a tag
violando a própria invariante em silêncio. A promoção sempre passa pelo construtor, que confere
tudo de novo.

**Empate entre duplicatas confirmadas se resolve pelo id, nunca pela ordem da lista.** Depender
de ordem de inserção tornaria o resultado sensível a como o acervo foi montado, o que quebraria a
idempotência: duas execuções com a mesma redundância, mas escritas em ordem diferente, teriam que
dar o mesmo resultado.

## Por que o aceite fica provisório

O teste sintético planta a redundância à mão e prova que o mecanismo funciona. Não prova que o
mecanismo é suficiente para o que o S7b vai realmente produzir, porque redundância gerada por
modelo pode ter formas que o teste sintético não cobre. O plano marca isso de propósito: o
provisório libera a etapa 2, e o definitivo espera volume real.

## O que o S9 deliberadamente não faz

Sem similaridade semântica nem embeddings. É decisão do
[ADR-001](ADR-001-nucleo-casca-e-interface.md): o núcleo é determinístico e reproduzível, e uma
fusão que dependesse de um modelo tornaria o resultado da consolidação não reproduzível entre
execuções. Sem fusão automática entre tipos diferentes — uma `restricao` nunca se funde com um
`termo_canonico`, mesmo com texto idêntico.

## Como verificar

```bash
python -m pytest tests/test_consolidacao.py -v
```

O cenário do critério de aceite está escrito por extenso em
`test_redundancia_injetada_colapsa_ao_numero_esperado`: seis tags viram três, e a restrição única
sobrevive. A idempotência está em `test_consolidar_duas_vezes_e_estavel`.
