"""Interface de linha de comando.

Toda capacidade do BookShelf e alcancavel pela CLI antes de ser alcancavel por
qualquer outra coisa. Saida 0 significa aceito; saida 1 significa rejeitado com
os problemas listados em stderr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from bookshelf.ir import percorrer_blocos
from bookshelf.prepress import (
    ConversaoFalhou,
    Formato,
    GhostscriptAusente,
    OpcoesDaProva,
    PerfilDeSaida,
    converter,
    gerar_postscript,
    perfil_padrao_do_ghostscript,
)
from bookshelf.prepress.verificacao import conferir, tudo_passou
from bookshelf.schema import CAMINHO_PADRAO, escrever_json_schema
from bookshelf.validation import ErroDeValidacao, carregar


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


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bookshelf",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    raise SystemExit(main())
