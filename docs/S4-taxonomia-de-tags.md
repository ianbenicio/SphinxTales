# S4 — Taxonomia de tags e ciclo de confirmação

**Critério de aceite:** nenhuma tag influencia geração sem registro de confirmação com autor e
data; tags são recuperáveis por tipo e por camada; tipo inexistente é rejeitado na entrada.

**Estado:** atendido. Verificável por outra pessoa com os comandos ao fim deste documento.

**Depende de:** S1. Pelo [ADR-001](ADR-001-nucleo-casca-e-interface.md), a camada de condução
propõe as tags e o núcleo as persiste.

## Como usar

```bash
python -m sphinxtales.cli tags propor --tipo tom --conteudo "Direto, sem jargão"
python -m sphinxtales.cli tags listar
python -m sphinxtales.cli tags confirmar <id> --autor "Nome de quem confirmou"
python -m sphinxtales.cli tags materializar
```

O acervo fica em `tags.json` por padrão, e `--acervo` aponta para outro arquivo.

## Os seis tipos

A taxonomia é fechada. Conteúdo dentro do tipo é livre, porque o que o autor diz sobre o livro
dele não cabe em enumeração, mas o tipo não é livre.

| Tipo | O que guarda |
|---|---|
| `publico` | Para quem o livro é escrito |
| `tom` | Como o texto soa |
| `pre_requisito` | O que o leitor já precisa saber |
| `termo_canonico` | A forma correta de nomear uma coisa neste livro |
| `restricao` | O que o texto não pode fazer |
| `decisao_editorial` | Escolha de estrutura ou formato já decidida |

## Decisões

**Tag confirmada exige registro, e isso é invariante de modelo.** Não existe estado do sistema em
que uma tag conte como confirmada sem que se saiba quem confirmou e quando. A validação roda nas
duas direções: confirmada sem registro é erro, e registro em tag não confirmada também é erro.
Não é disciplina de quem escreve o código, é impossibilidade.

**A data de confirmação precisa declarar fuso.** Um registro sem fuso não é comparável entre
máquinas, e um registro que não se pode comparar não serve de registro.

**A materialização é o único caminho de tag para prompt, e ela só enxerga confirmadas.** Não há
parâmetro que a faça incluir uma proposta. Quem quiser burlar precisa mudar aquele arquivo, o que
aparece no diff. Um dos testes varre todos os filtros de camada possíveis e exige que nenhuma
combinação deixe uma proposta vazar.

**O identificador é determinístico e vem do conteúdo normalizado.** Propor duas vezes a mesma
coisa devolve a mesma tag, mesmo com grafia diferente: `Custo  Fixo` e `custo fixo` têm o mesmo
identificador. A deduplicação cai fora de graça, e o S9 herda um acervo que já não acumula cópias
triviais.

**Repropor não rebaixa uma tag confirmada.** É um caminho real de bug: a entrevista sugere de
novo algo que o autor já confirmou, e o registro seria apagado. O teste correspondente existe
porque o erro é silencioso e o efeito só apareceria na geração.

**Recusar apaga o registro.** Uma tag recusada não guarda quem a confirmou um dia, senão o
registro passaria a significar duas coisas.

## O que o S4 deliberadamente não faz

Sem orçamento de materialização por relevância e importância, que é do S7b. Sem consolidação,
dedup semântica ou promoção a esquema, que é do S9. Sem vínculo a referências, que é do S6. Sem
camadas acima da segunda, que o plano coloca fora do MVP.

## Como verificar

```bash
python -m sphinxtales.cli tags --acervo out/demo.json propor --tipo tom --conteudo "Seco"
python -m sphinxtales.cli tags --acervo out/demo.json materializar
```

A segunda linha sai com código 1 e diz que não há nada a materializar, porque propor não
confirma. Depois de `tags confirmar <id> --autor "Alguém"`, a mesma linha passa a imprimir a tag.

```bash
python -m pytest tests/test_tags.py -v
```

Os três critérios de aceite têm seção própria no arquivo de teste.
