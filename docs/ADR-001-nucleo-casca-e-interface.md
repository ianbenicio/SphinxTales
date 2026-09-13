# ADR-001 — Núcleo, casca e a ordem em que a interface aparece

**Status:** aceito
**Data:** 2026-09-12
**Contexto do plano:** [plano-mvp-v0.2.md](plano-mvp-v0.2.md)

## A pergunta

Qual é a forma final da ferramenta que conduz a criação de um livro: um harness próprio, uma
skill do Claude Code, ou um site?

## Contexto

O produto tem duas metades de natureza oposta, e tratá-las com a mesma ferramenta é o erro caro.

A **metade determinística** vai do esquema ao arquivo que a gráfica aceita. Precisa ser
reproduzível, versionável e testável por outra pessoa. Hoje são as specs S1, S2, S3a e S3b, e já
está construída como biblioteca Python com linha de comando. Foi essa escolha que permitiu
mandar a prova de prensa à gráfica antes de o renderizador existir.

A **metade conversacional** é a entrevista, a confirmação de tags, a decomposição de referências
e a recusa do autor. É diálogo com estado acumulado, com uma pessoa do outro lado. São as specs
S4, S5, S6 e S11. Não cabe em linha de comando e não deve virar código de aplicação agora.

Sobre as duas pesa o ponto de parada declarado no plano: **o S7 pode reprovar**, e nesse caso o
certo é parar antes de construir o resto. Qualquer interface construída antes dessa prova é
candidata a ser descartada.

## Decisão

Três camadas, construídas nesta ordem. Só as duas primeiras entram no MVP.

**1. Núcleo: biblioteca Python com linha de comando.** Já existe. Todo comportamento que precisa
ser provado vive aqui, e todo comando é uma superfície de teste antes de ser uma funcionalidade.

**2. Condução: uma skill do Claude Code, durante o MVP.** A entrevista precisa de um laço de
diálogo com memória, e o Claude Code já é esse laço. Uma skill que conduz e chama a linha de
comando custa dias, não semanas, e serve ao cenário que o plano descreve, um autor real sentado
ao lado. Se a tese cair no S7, o que se joga fora é uma skill.

**3. Site: depois de o S7 passar.** E aí não é um site novo, é a mesma biblioteca com uma casca
web. O plano já cortou a plataforma multi-cliente do MVP, e antecipar a casca contraria a
decisão que o documento inteiro defende.

**Harness não é interface.** O escritor com estado e o loop de três predicados são código da
biblioteca, com teto de iterações e estados de saída nomeados. Chamar isso de ferramenta final
confunde o motor com o painel.

## A regra que separa as camadas

> Tudo que precisa ser **provado** fica no núcleo. Tudo que precisa ser **descartável** fica na
> casca.

Aplicada a qualquer dúvida futura sobre onde algo mora, ela decide sozinha.

## A consequência que muda o desenho do S7

**A geração não pode passar pela skill.** Se ela passar, o benchmark do S7 perde o sentido.

O Claude Code traz heurísticas próprias, contexto de sessão e comportamento que não controlamos
nem registramos. Rodar o S7a e o S7b por dentro dele faria os dois braços diferirem em mais
coisas do que a presença de estado acumulado, que é exatamente a única variável que o
experimento quer isolar.

A ficha de pré-registro exige mesmo modelo, mesmo roteiro e mesma semente. Isso só é verificável
se a geração for código chamado por comando, com os parâmetros declarados na entrada e
registrados na saída.

## Onde cada spec vive

| Spec | Camada | Por quê |
|---|---|---|
| S1, S2, S3a, S3b | núcleo | determinístico, precisa ser reproduzível |
| S4, S5, S6, S11 | skill conduz, núcleo persiste | diálogo com pessoa, estado guardado no núcleo |
| S7a, S7b, S8, S9 | núcleo | medido, precisa de semente, teto e registro |
| S10 | núcleo | exporta o que o núcleo já tem |

A skill nunca guarda estado. Ela conduz a conversa e grava tudo pelo núcleo, para que a mesma
sessão possa ser reconstituída sem ela.

## O que isso exige da linha de comando

Um verbo por spec, cada um utilizável sozinho. Três existem hoje.

| Verbo | Spec | Estado |
|---|---|---|
| `validate` | S1 | existe |
| `schema` | S1 | existe |
| `prova` | S3a | existe |
| `init` | projeto | falta |
| `entrevista` | S5 | falta |
| `escrever` | S7a, S7b | falta |
| `revisar` | S8 | falta |
| `render` | S2 | falta |
| `export` | S10 | falta |

## Alternativas consideradas

**Site desde já.** Rejeitada. É a casca certa para o produto e a errada para a pergunta que o
MVP responde. Construí-la antes do S7 gasta semanas num invólucro que a reprovação da tese
jogaria fora inteiro.

**Skill como ferramenta completa, inclusive gerando.** Rejeitada pelo motivo da seção acima.
Contamina o experimento que justifica o projeto.

**Harness próprio como interface.** Rejeitada por confusão de categoria. O harness é o motor de
geração e revisão, e ele é código da biblioteca. Promovê-lo a interface não resolve a entrevista,
que é o problema real de interação.

**Nenhuma camada de condução no MVP, só linha de comando.** Rejeitada. O autor real não opera
terminal, e o plano coloca um autor real no centro do teste.

## Quando revisitar

Na aprovação do S7. Se a tese passar, a decisão 3 sai de espera e a casca web entra em
discussão. Se reprovar, o plano manda parar, e esta decisão morre junto com o resto.
