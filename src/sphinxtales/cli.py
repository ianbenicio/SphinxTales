"""Interface de linha de comando.

Toda capacidade do SphinxTales e alcancavel pela CLI antes de ser alcancavel por
qualquer outra coisa. Saida 0 significa aceito; saida 1 significa rejeitado com
os problemas listados em stderr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sphinxtales.ir import percorrer_blocos
from sphinxtales.prepress import (
    ConversaoFalhou,
    Formato,
    GhostscriptAusente,
    OpcoesDaProva,
    PerfilDeSaida,
    converter,
    gerar_postscript,
    perfil_padrao_do_ghostscript,
)
from sphinxtales.prepress.verificacao import conferir, tudo_passou
from sphinxtales.render import CompilacaoFalhou, Tema, contar_paginas, renderizar
from sphinxtales.schema import CAMINHO_PADRAO, escrever_json_schema
from sphinxtales.tags import (
    Acervo,
    EstadoDaTag,
    Tag,
    TagNaoEncontrada,
    TipoDeTag,
    materializar,
)
from sphinxtales.validation import ErroDeValidacao, carregar

ACERVO_PADRAO = Path("tags.json")


def _comando_render(args: argparse.Namespace) -> int:
    """Diagrama o livro. Valida antes, porque IR invalido nao vira PDF."""
    try:
        livro = carregar(args.arquivo)
    except ErroDeValidacao as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except OSError as erro:
        print(f"nao foi possivel ler {args.arquivo}: {erro}", file=sys.stderr)
        return 1

    tema = Tema(largura_mm=args.largura, altura_mm=args.altura, corpo_pt=args.corpo)

    try:
        pdf, typst = renderizar(livro, args.saida, tema)
    except CompilacaoFalhou as erro:
        print(str(erro), file=sys.stderr)
        return 1

    print(
        f"diagramado: {livro.meta.titulo} - {contar_paginas(typst)} pagina(s) em "
        f"{tema.largura_mm:g} x {tema.altura_mm:g} mm"
    )
    print(f"PDF: {pdf}")
    print(f"Typst: {typst}")
    return 0


def _comando_validate(args: argparse.Namespace) -> int:
    try:
        livro = carregar(args.arquivo)
    except ErroDeValidacao as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except OSError as erro:
        print(f"nao foi possivel ler {args.arquivo}: {erro}", file=sys.stderr)
        return 1

    total_blocos = sum(
        1 for capitulo in livro.capitulos for _ in percorrer_blocos(capitulo.blocos)
    )
    print(
        f"aceito: {livro.meta.titulo} - "
        f"{len(livro.capitulos)} capitulo(s), {total_blocos} bloco(s)"
    )
    return 0


def _comando_schema(args: argparse.Namespace) -> int:
    destino = escrever_json_schema(args.saida)
    print(f"JSON Schema escrito em {destino}")
    return 0


def _comando_prova(args: argparse.Namespace) -> int:
    """Gera a prova de prensa e confere o arquivo antes de ele sair daqui."""
    try:
        formato = Formato.de_texto(args.formato, sangria_mm=args.sangria)
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    perfil_icc = args.perfil or perfil_padrao_do_ghostscript()
    if perfil_icc is None:
        print(
            "nenhum perfil ICC informado e o perfil padrao do Ghostscript "
            "nao foi encontrado. Use --perfil.",
            file=sys.stderr,
        )
        return 1

    perfil = PerfilDeSaida(
        caminho_icc=perfil_icc,
        condicao=args.condicao,
        identificador=args.identificador,
    )
    opcoes = OpcoesDaProva(
        condicao_impressao=args.condicao,
        perfil=perfil_icc.name,
        data=date.today().isoformat(),
    )

    saida = args.saida
    postscript = saida.with_suffix(".ps")
    postscript.parent.mkdir(parents=True, exist_ok=True)
    postscript.write_bytes(gerar_postscript(formato, opcoes))

    try:
        pdf = converter(postscript, saida, opcoes.titulo, perfil, versao=args.versao)
    except GhostscriptAusente as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except ConversaoFalhou as erro:
        print(str(erro), file=sys.stderr)
        return 1

    checagens = conferir(pdf, formato, versao=args.versao)
    for checagem in checagens:
        destino = sys.stdout if checagem.passou else sys.stderr
        print(checagem, file=destino)

    if not tudo_passou(checagens):
        print("arquivo reprovado na conferencia, nao envie", file=sys.stderr)
        return 1

    print()
    print(f"PDF/{args.versao} pronto para a grafica: {pdf}")
    return 0


def _acervo_de(args: argparse.Namespace) -> Acervo:
    return Acervo.carregar(args.acervo)


def _linha_da_tag(tag: Tag) -> str:
    # Marca sempre visivel: uma coluna em branco desalinharia o resto da linha.
    marca = {"proposta": "·", "confirmada": "✓", "recusada": "×"}[tag.estado.value]
    quem = f" · {tag.confirmacao.autor}" if tag.confirmacao else ""
    return f"{marca} {tag.id}  c{tag.camada}  {tag.tipo.value:<18} {tag.conteudo}{quem}"


def _comando_tags_propor(args: argparse.Namespace) -> int:
    acervo = _acervo_de(args)
    tag = acervo.propor(TipoDeTag(args.tipo), args.conteudo, args.camada, args.origem)
    acervo.salvar(args.acervo)
    print(_linha_da_tag(tag))
    if tag.estado is not EstadoDaTag.PROPOSTA:
        print(f"(ja existia, estado {tag.estado.value})")
    return 0


def _comando_tags_confirmar(args: argparse.Namespace) -> int:
    acervo = _acervo_de(args)
    try:
        tag = acervo.confirmar(args.id, args.autor, datetime.now(timezone.utc))
    except TagNaoEncontrada:
        print(f"tag nao encontrada: {args.id}", file=sys.stderr)
        return 1
    acervo.salvar(args.acervo)
    print(_linha_da_tag(tag))
    return 0


def _comando_tags_recusar(args: argparse.Namespace) -> int:
    acervo = _acervo_de(args)
    try:
        tag = acervo.recusar(args.id)
    except TagNaoEncontrada:
        print(f"tag nao encontrada: {args.id}", file=sys.stderr)
        return 1
    acervo.salvar(args.acervo)
    print(_linha_da_tag(tag))
    return 0


def _comando_tags_listar(args: argparse.Namespace) -> int:
    acervo = _acervo_de(args)
    tags = acervo.tags
    if args.tipo:
        tags = [t for t in tags if t.tipo is TipoDeTag(args.tipo)]
    if args.camada is not None:
        tags = [t for t in tags if t.camada == args.camada]
    if args.estado:
        tags = [t for t in tags if t.estado is EstadoDaTag(args.estado)]

    for tag in sorted(tags, key=lambda t: (t.camada, t.tipo.value, t.conteudo)):
        print(_linha_da_tag(tag))
    print(f"{len(tags)} tag(s) · {len(acervo.confirmadas())} confirmada(s) no acervo")
    return 0


def _comando_tags_materializar(args: argparse.Namespace) -> int:
    """Mostra exatamente o que chegaria ao gerador, e nada alem disso."""
    acervo = _acervo_de(args)
    camadas = set(args.camada) if args.camada else None
    texto = materializar(acervo, camadas)
    if not texto:
        print("nenhuma tag confirmada, nada a materializar", file=sys.stderr)
        return 1
    print(texto, end="")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sphinxtales",
        description="Producao editorial assistida: IR, diagramacao e prepress.",
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    validate = subcomandos.add_parser(
        "validate", help="valida um documento IR em JSON"
    )
    validate.add_argument("arquivo", type=Path)
    validate.set_defaults(funcao=_comando_validate)

    schema = subcomandos.add_parser(
        "schema", help="exporta o JSON Schema derivado do esquema Pydantic"
    )
    schema.add_argument("-o", "--saida", type=Path, default=CAMINHO_PADRAO)
    schema.set_defaults(funcao=_comando_schema)

    prova = subcomandos.add_parser(
        "prova",
        help="gera a prova de prensa minima em PDF/X e confere o arquivo",
    )
    prova.add_argument(
        "-o", "--saida", type=Path, default=Path("out/prova-de-prensa.pdf")
    )
    prova.add_argument(
        "--formato", default="160x230", help="corte em mm, por exemplo 160x230"
    )
    prova.add_argument("--sangria", type=float, default=3.0, help="sangria em mm")
    prova.add_argument(
        "--versao", default="X-1a", choices=("X-1a", "X-3", "X-4"), help="versao PDF/X"
    )
    prova.add_argument(
        "--perfil", type=Path, default=None, help="perfil ICC CMYK de saida"
    )
    prova.add_argument(
        "--condicao",
        default="Commercial and specialty printing",
        help="condicao de impressao declarada no OutputIntent",
    )
    prova.add_argument(
        "--identificador",
        default="Custom",
        help="OutputConditionIdentifier declarado no OutputIntent",
    )
    prova.set_defaults(funcao=_comando_prova)

    render = subcomandos.add_parser(
        "render", help="diagrama um documento IR em PDF, via Typst"
    )
    render.add_argument("arquivo", type=Path)
    render.add_argument("-o", "--saida", type=Path, default=Path("out/livro.pdf"))
    render.add_argument(
        "--largura", type=float, default=160.0, help="largura do corte em mm"
    )
    render.add_argument(
        "--altura", type=float, default=230.0, help="altura do corte em mm"
    )
    render.add_argument(
        "--corpo", type=float, default=10.5, help="corpo do texto em pontos"
    )
    render.set_defaults(funcao=_comando_render)

    tags = subcomandos.add_parser(
        "tags", help="propoe, confirma e consulta as tags do projeto"
    )
    tags.add_argument(
        "--acervo", type=Path, default=ACERVO_PADRAO, help="arquivo do acervo"
    )
    acoes = tags.add_subparsers(dest="acao", required=True)

    tipos = [tipo.value for tipo in TipoDeTag]
    estados = [estado.value for estado in EstadoDaTag]

    propor = acoes.add_parser("propor", help="propoe uma tag, sem confirma-la")
    propor.add_argument("--tipo", required=True, choices=tipos)
    propor.add_argument("--conteudo", required=True)
    propor.add_argument("--camada", type=int, default=1)
    propor.add_argument("--origem", default="entrevista")
    propor.set_defaults(funcao=_comando_tags_propor)

    confirmar = acoes.add_parser(
        "confirmar", help="registra quem confirmou a tag e quando"
    )
    confirmar.add_argument("id")
    confirmar.add_argument("--autor", required=True)
    confirmar.set_defaults(funcao=_comando_tags_confirmar)

    recusar = acoes.add_parser("recusar", help="marca a tag como recusada")
    recusar.add_argument("id")
    recusar.set_defaults(funcao=_comando_tags_recusar)

    listar = acoes.add_parser("listar", help="lista as tags, com filtros")
    listar.add_argument("--tipo", choices=tipos)
    listar.add_argument("--camada", type=int)
    listar.add_argument("--estado", choices=estados)
    listar.set_defaults(funcao=_comando_tags_listar)

    mat = acoes.add_parser(
        "materializar", help="mostra o contexto que chegaria ao gerador"
    )
    mat.add_argument("--camada", type=int, action="append")
    mat.set_defaults(funcao=_comando_tags_materializar)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    raise SystemExit(main())
