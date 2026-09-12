# MVP SphinxTales — plano v0.2

**Data:** 2026-09-10
**Substitui:** v0.1 de 2026-08-28, [artefato](https://claude.ai/code/artifact/b306004c-441c-47f5-92f1-87a19bcc3307)
**Origem das mudanças:** [Crítica do MVP SphinxTales](https://claude.ai/code/artifact/fc1e0c1c-9eaf-4e83-9b56-bdbd17c97fb0), 2026-09-10
**Companheiro de:** `claude/sphinxtales-arquitetura-v0.1.md` e `claude/benchmark-competitivo.md`

---

## O que mudou desde a v0.1

Nada foi cortado do escopo. Duas specs foram divididas, uma foi acrescentada, e quatro critérios
de aceite foram reescritos para decidir alguma coisa.

| Achado da crítica | Mudança nesta versão |
|---|---|
| O aceite do S7 não decide nada | S7 dividido em **S7a** (braço de controle) e **S7b** (escritor). Ficha de pré-registro virou **gate G2** |
| O S3 é caminho crítico vestido de paralelo | S3 dividido em **S3a** (prova de prensa mínima, dispara no dia 1) e **S3b** (prepress do livro) |
| O loop não define o terceiro estado | S8 passa a ter três saídas nomeadas, e um defeito insolúvel plantado precisa sair como escalado |
| O aceite do S5 é fraco | S5 ganha verificação de **cobertura**, não só de não sobreposição |
| Nenhuma spec menciona custo ou tempo | Teto declarado antes de rodar, medido em S7b e S8. Ver requisitos transversais |
| Falta o que acontece quando o autor recusa | Nova **S11**, deliberadamente mínima |
| O S9 fecha com teste sintético | Aceite dividido em provisório e definitivo, com o definitivo preso ao volume do S7b |
| O S10 é o único item cortável | Marcado **opcional** no corpo do plano, não só na ordem |
| O S1 não é fundação neutra | Registrado no corpo da S1, com o que ele efetivamente fixou |

---

## Escopo, inalterado

Fatia **vertical**: um livro de 6 a 8 capítulos, 40 a 60 páginas, um autor real, da entrevista
ao arquivo aceito pela gráfica. Prova a **integração**, que é o que mata projeto assim.

Cortado do MVP: plataforma multi-cliente. Interface do MVP é uma tela, um autor, o amigo do lado.

**Princípio sobre a entrevista:** ela fornece **valores, não arquitetura**. Formato de corte,
perfil de cor e roteiro de perguntas são parâmetros configuráveis. Se a entrevista mudar código,
especificamos errado.

**Regra de especificação:** nenhuma spec entra em construção sem critério de aceite verificável
por outra pessoa. "Funciona bem" não é aceite; "a gráfica aceitou o arquivo" é.

**Regra nova nesta versão:** nenhum aceite que dependa de medição entra em construção sem o
limiar escrito antes. Um limiar escolhido depois de ver o resultado não é aceite, é narrativa.

---

## Gates

Três pré-condições bloqueiam trabalho a jusante. Não são recomendações.

**G1 — Parecer da gráfica antes do prepress do livro.**
Nenhuma linha de S3b antes de o S3a voltar com parecer por escrito. Se o parecer exigir mudança
no esquema, o trabalho para e o S1 é reaberto antes de o S2 avançar.

**G2 — Ficha congelada antes do escritor.**
Nenhuma linha de S7b antes de a ficha de pré-registro estar preenchida, datada e congelada, e do
S7a estar rodando. A ficha está neste documento.

**G3 — Volume real antes de declarar o S9 pronto.**
O aceite provisório do S9 libera a etapa 2. O definitivo só é declarado com as tags que o S7b
produzir.

---

## As onze especificações

S3 e S7 têm dois entregáveis cada, o que dá treze itens construíveis.

| ID | Spec | Critério de aceite | Depende de | Estado |
|---|---|---|---|---|
| **S1** | Esquema IR em Pydantic com JSON Schema derivado. Nove blocos, seis nós inline, mais meta, bíblia e contrato de capítulo | Livro de exemplo à mão valida e exercita todos os blocos e nós; campo obrigatório ausente falha nomeando o campo; campo desconhecido é rejeitado, nunca descartado | — | **construído** |
| **S2** | Renderizador Typst por binding Python, um tema, glossário e índice derivados de `definition`, sumário paginado | Nenhum tipo do IR fica sem regra de render, verificado na compilação e não por inspeção; tabela larga e bloco de código quebram página sem cortar conteúdo | S1 | não iniciado |
| **S3a** | Prova de prensa mínima. Uma página feita à mão, sem IR e sem renderizador: sangria, marcas de corte, CMYK, preto chapado, uma imagem e texto pequeno em preto total | A gráfica devolve parecer por escrito sobre perfil, sangria, marcas e resolução, com aceitação ou lista de correções | — | **dispara no dia 1** |
| **S3b** | Prepress do livro. Ghostscript para PDF/X-1a ou X-4, CMYK, sangria, marcas. Formato, margens e perfil são **parâmetros**, com os valores que o S3a confirmou | **A gráfica aceita o arquivo do livro em teste real, sem retrabalho.** Critério externo, e é o critério de saída da etapa 1 | S2, S3a, valores do bloco 5 da entrevista | não iniciado |
| **S4** | Taxonomia fechada de tags: termo canônico, restrição, decisão editorial, público, tom, pré-requisito. Ciclo propor, confirmar, vincular | Nenhuma tag influencia geração sem registro de confirmação; recuperáveis por tipo e camada; tipo inexistente é rejeitado na entrada | S1 | não iniciado |
| **S5** | Entrevista camada 1. Público, gênero, tom, nível e objetivo viram estrutura e contratos. Roteiro provisório, substituído pelo real depois | Ao fim existem estrutura, bíblia inicial e tags confirmadas. Duas verificações automáticas sobre os contratos: **não sobreposição** entre vizinhos e **cobertura**, isto é, todo termo em `requer` aparece em `introduz` de um capítulo anterior e nenhum termo é introduzido duas vezes | S1, S4 | não iniciado |
| **S6** | Referências **só por upload**. O autor declara o tipo de contribuição e o sistema devolve decomposição verificável para confirmação | Referência estrutural vira checklist consumível pelo loop; referência não confirmada não aparece em prompt nenhum, verificável por inspeção; **o autor confirma a decomposição sem reescrevê-la**, porque uma decomposição que precisa ser reescrita falhou | S4 | não iniciado |
| **S7a** | Braço de controle. O mesmo escritor sem bíblia, sem contrato e sem tags materializadas | Produz os mesmos capítulos com o mesmo modelo, roteiro e semente do S7b, variando só a presença de estado. Sem esse braço, o número do S7b não significa nada | S1, S5 | não iniciado |
| **S7b** | Escritor com estado. Contrato, bíblia e tags materializadas dentro de orçamento de relevância por importância, mais referências vinculadas, produzem IR | Repetição entre capítulos **não adjacentes**, medida por embeddings, fica **abaixo do limiar pré-registrado** na comparação com o S7a. Mais os tetos de custo e tempo por capítulo. Gate G2 se aplica | S1, S4, S5, S6, S7a | não iniciado |
| **S8** | Um loop de consistência, três predicados binários, teto de três iterações: termo antes da definição, cobertura do contrato, checklist da referência estrutural. **Três saídas nomeadas:** aprovado, corrigido, escalado | Em manuscrito com defeitos plantados encontra os três tipos; zero falso positivo no manuscrito limpo; **um defeito insolúvel plantado sai como escalado e nunca como aprovado**, com os predicados que não convergiram nomeados. Mais os tetos de custo e tempo | S6, S7b | não iniciado |
| **S9** | Consolidação de tags: deduplicação, fusão, promoção de padrão a esquema. **Sem decaimento** | **Provisório:** conjunto com redundância injetada colapsa ao número esperado sem perder restrição única. **Definitivo:** o mesmo vale para as tags que o S7b produziu de fato. Gate G3 se aplica | S4 | não iniciado |
| **S10** | **Opcional.** Export Obsidian: vault por projeto, registro de construção, tags e referências como notas, wikilinks de decisão para referência | Partindo de qualquer capítulo chega-se às tags e referências que o determinaram, sem consultar o sistema | S4, S6, S7b | opcional, corta primeiro |
| **S11** | Recusa e reentrada do autor. Deliberadamente mínima: o autor edita o documento à mão ou marca o trecho recusado, e o sistema revalida e reaproveita o resto | Um capítulo editado à mão revalida e volta ao loop sem perder tags nem contratos; a edição do autor sobrevive a uma nova passada do escritor, verificável por inspeção | S1, S7b | não iniciado |

---

## Nota sobre o S1, que não era fundação neutra

O v0.1 tratava o S1 como o degrau mais barato, aquele que só descreve estruturas. Construindo,
apareceu o contrário: o S1 decide se o S2 e o S8 são viáveis, numa escolha que passa
despercebida, a de quanta semântica o texto corrido carrega.

Se o conteúdo dentro do parágrafo fosse apenas uma sequência de caracteres, o glossário e o
índice remissivo do S2 seriam impossíveis de derivar, e o predicado de termo usado antes da
definição, no S8, não teria em que se apoiar. Por isso a referência a termo e a definição
entraram como elementos de primeira classe, e não como convenção de formatação dentro do texto.

O registro completo do que foi decidido está em `docs/S1-esquema-ir.md`.

---

## Ficha de pré-registro do S7

Preencher, datar e congelar antes da primeira linha do S7b. Depois disso o resultado é o que
for, e essa é a ideia.

| Campo | Valor | Preenchido em |
|---|---|---|
| Braço de controle | S7a: mesmo modelo, roteiro e semente, sem bíblia, sem contrato, sem tags | |
| Métrica | Similaridade por embeddings entre pares de capítulos **não adjacentes**, com repetição de conceito separada de repetição de formulação | |
| Limiar | | |
| Capítulos por execução | | |
| Execuções por braço | | |
| Modelo e versão | | |
| Semente | | |
| Teto de custo por capítulo | | |
| Teto de tempo por capítulo | | |
| Congelada por | | |

**Por que a amostra preocupa.** Com 6 a 8 capítulos há de 15 a 28 pares, dos quais 10 a 21 não
são adjacentes. Com capítulos de 5 a 10 páginas, um efeito real pode não se separar do ruído.
Decidir o número de execuções por braço a partir do poder estatístico, não da conveniência.

---

## Requisitos transversais

Valem para todo item que consome modelo. Declarados antes de rodar, medidos durante, reportados
junto do resultado.

| Requisito | Onde é medido |
|---|---|
| Custo por capítulo, nos dois braços | S7a, S7b |
| Tempo por capítulo, nos dois braços | S7a, S7b |
| Custo e tempo por iteração do loop | S8 |
| Custo total do livro, somando tudo | fechamento da etapa 3 |

Um MVP que prova a tese e custa caro demais por livro morre do mesmo jeito que um que falha, só
que mais tarde.

---

## Ordem de construção

**Dia 1, em paralelo com tudo:** disparar o **S3a**. É externo, mede-se em dias, e é a única
coisa cujo atraso ninguém consegue recuperar depois.

1. **Sem IA** — S1 → S2 → S3b.
   Prova que o esquema serve à diagramação e que a gráfica aceita. Falhando aqui, nada mais
   importa, e nenhuma execução de modelo foi desperdiçada. *S1 construído.*
2. **Conhecimento** — S4 → S6 → S9 provisório.
   Tags e referências vinculam só com confirmação e não degeneram com volume.
3. **Geração** — S5 → S7a → **G2** → S7b.
   Prova ou mata a tese.
4. **Fechamento** — S8 → S11 → S9 definitivo → S10 se sobrar prazo.

---

## Fora do MVP

Plataforma multi-cliente. Descoberta de referências na web, pela alucinação de título somada à
exposição jurídica. Ancoragem e checagem factual, que é o próximo diferencial e não parte deste
teste. Camadas 3 e acima. EPUB, imagens e capa. Livro longo.

---

## Pontos de parada honestos

**No S3a.** Se o parecer da gráfica exigir mudança no esquema, parar e reabrir o S1 antes de o
S2 avançar. Custa uma tarde agora e duas semanas depois.

**No S7b.** A tese pode reprovar. Se a repetição não ficar abaixo do limiar pré-registrado, a
tese central, de que estado acumulado somado a contrato produz coerência, está errada, e o certo
é parar antes de construir S8, S9, S10 e S11.

Um MVP que não pode falhar não é teste, é demonstração. O limiar escrito antes é o que mantém a
diferença.
