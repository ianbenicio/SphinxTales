# S3a — Prova de prensa mínima

**Critério de aceite:** a gráfica devolve parecer por escrito sobre perfil, sangria, marcas e
resolução, com aceitação ou lista de correções.

**Estado:** arquivo construído e conferido. Falta o envio e o parecer, que são externos.

**Gate que esta spec destrava:** G1. Nenhuma linha de S3b antes de o parecer voltar.

## Por que esta página existe

O plano v0.1 punha a validação da gráfica correndo em paralelo com o resto. Não corre. O laço
de resposta é externo, mede-se em dias, e uma reprovação volta para o renderizador e
possivelmente para o esquema. Esta página tira essa espera do caminho crítico: ela não depende
do IR nem do renderizador, então pode ir para a gráfica hoje.

## Como gerar

```bash
python -m bookshelf.cli prova
```

Sai em `out/prova-de-prensa.pdf`, com o PostScript de origem ao lado. Todos os parâmetros têm
valor padrão e todos podem mudar:

```bash
python -m bookshelf.cli prova --formato 148x210 --sangria 5 --versao X-4
```

O comando roda nove conferências antes de terminar e sai com código 1 se qualquer uma falhar.
Um arquivo reprovado não deve ser enviado.

| Conferência | O que ela impede |
|---|---|
| Versão do PDF | X-1a exige PDF 1.3, e 1.4 seria recusado na pré-impressão |
| Declaração PDF/X | Arquivo sem `GTS_PDFXVersion` não é PDF/X, é um PDF comum |
| OutputIntent e perfil embutido | Sem eles a gráfica não sabe para que condição o arquivo foi feito |
| TrimBox e BleedBox | Caixa errada é corte errado |
| Fontes embutidas | Fonte ausente vira substituição silenciosa na prensa |
| Somente CMYK | Um RGB esquecido vira conversão que ninguém controlou |
| Uma página | Guarda contra o arquivo errado ir no lugar |

## O que a página pergunta

Cada bloco impresso é uma pergunta que a pré-impressão responde olhando o papel.

| Bloco | Pergunta |
|---|---|
| Pretos chapados | O preto de uma chapa só fica lavado ao lado do preto composto? |
| Texto miúdo | Em que corpo o texto de quatro chapas perde registro? |
| Texto reverso | Em que corpo o branco sobre chapado fecha e some? |
| Imagem em 300 dpi | O degradê tem banding, e até que espessura a prensa resolve a listra? |
| Fios finos | Abaixo de que espessura o fio some ou engorda? |
| Barra de controle | As chapas batem com o que a prova de vocês espera? |

A faixa que sangra pela esquerda, pelo topo e pela base existe para que um corte fora de
esquadro apareça.

## O que perguntar junto com o arquivo

Estas são as perguntas cuja resposta vira parâmetro. Nenhuma delas muda código.

| Pergunta à gráfica | O que a resposta define |
|---|---|
| Qual perfil ICC de saída vocês querem? | `--perfil`. Hoje o arquivo vai com o perfil genérico do Ghostscript, e isso está declarado no rodapé da página |
| PDF/X-1a ou PDF/X-4? | `--versao`. X-4 permite transparência, X-1a não |
| Sangria de 3 mm serve, ou preferem 5 mm? | `--sangria` |
| As marcas a 3 mm do corte, 5 mm de comprimento, 0,25 pt em registro, estão como vocês esperam? | `offset_marca_mm`, `comprimento_marca_mm` e `espessura_marca_pt` no formato |
| Que formato de corte aproveita melhor o papel de vocês? | `--formato`. O padrão de 160 × 230 mm é escolha nossa, não restrição |
| Qual o limite de cobertura total de tinta? | O preto composto da página está em 240%. O patch CMY 100 está em 300% de propósito, para achar o teto |
| Texto preto deve ser K puro ou composto, e a partir de que corpo? | Regra de cor do renderizador, no S2 |
| Qual a resolução mínima de imagem? | `DPI_IMAGEM`. A página vai em 300 dpi |
| Qual o fio mínimo que vocês garantem? | Espessura mínima de filete e régua no tema do S2 |
| Aceitam fontes embutidas em subconjunto, ou querem tudo em curvas? | Opções de embutimento na conversão |
| Como querem receber o miolo: arquivo único ou páginas separadas, com ou sem marcas? | Saída do S3b |
| Vocês fazem prova digital calibrada? Prazo e custo? | Quantas rodadas de S3b cabem no cronograma |

## O que fazer com a resposta

Anotar cada valor confirmado na seção "Parecer da gráfica" abaixo, com a data e quem respondeu.
Depois passar os valores aos parâmetros e regerar a prova antes de abrir o S3b.

Se o parecer exigir mudança no esquema do documento, o plano manda parar e reabrir o S1 antes de
o S2 avançar.

## Parecer da gráfica

Ainda não recebido. Enviado em: ____ . Respondido por: ____ .
