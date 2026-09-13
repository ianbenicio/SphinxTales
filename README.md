# SphinxTales

Produção editorial assistida: da entrevista com o autor ao arquivo que a gráfica aceita.

Este repositório segue a ordem de construção do plano de MVP: primeiro sem IA
(esquema, diagramação, prepress), depois conhecimento, depois geração.

Plano vigente: [docs/plano-mvp-v0.2.md](docs/plano-mvp-v0.2.md).
Arquitetura: [ADR-001](docs/ADR-001-nucleo-casca-e-interface.md) separa o que é núcleo do que é
casca, e decide quando a interface aparece.

| Spec | Estado |
|---|---|
| S1 — Esquema IR | construído |
| S2 — Renderizador Typst | construído |
| S3a — Prova de prensa mínima | arquivo pronto, aguardando parecer da gráfica |
| S3b — Prepress do livro | bloqueado pelo gate G1 |
| S4 a S11 | não iniciadas |

Três gates bloqueiam trabalho a jusante: parecer da gráfica antes do prepress do livro,
ficha de pré-registro congelada antes do escritor com estado, e volume real antes de
declarar a consolidação de tags pronta. Os três estão descritos no plano.

## Rodar

```bash
uv venv
uv pip install -e ".[dev]"
```

Validar um documento IR:

```bash
python -m sphinxtales.cli validate examples/livro-exemplo.json
```

Exportar o JSON Schema derivado do esquema Pydantic:

```bash
python -m sphinxtales.cli schema
```

Diagramar o livro em PDF:

```bash
python -m sphinxtales.cli render examples/livro-exemplo.json
```

Gerar a prova de prensa para a gráfica, já conferida:

```bash
python -m sphinxtales.cli prova
```

Suíte de testes:

```bash
python -m pytest
```

## Estrutura

| Caminho | Papel |
|---|---|
| `src/sphinxtales/ir/` | Esquema do IR: inline, blocos, documento, percursos |
| `src/sphinxtales/render/` | Tema, emissor de Typst e compilação do miolo em PDF |
| `src/sphinxtales/prepress/` | Geometria, prova de prensa, conversão PDF/X e conferência |
| `src/sphinxtales/validation.py` | Porta de entrada: valida e nomeia todo defeito |
| `src/sphinxtales/schema.py` | Exporta o JSON Schema a partir do Pydantic |
| `src/sphinxtales/cli.py` | Interface de linha de comando |
| `examples/livro-exemplo.json` | Livro escrito à mão que exercita o esquema inteiro |
| `schemas/book.schema.json` | JSON Schema gerado, nunca editado à mão |
| `docs/` | Registro por spec: o que foi decidido e como verificar |
