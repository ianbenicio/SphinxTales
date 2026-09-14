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
from sphinxtales.referencias import (
    AcervoDeReferencias,
    Referencia,
    ReferenciaNaoEncontrada,
    SemDecomposicao,
    TipoDeContribuicao,
    checklist_do_acervo,
)
from sphinxtales.referencias import materializar as materializar_referencias
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
REFERENCIAS_PADRAO = Path("referencias.json")
RAIZ_DE_REFERENCIAS = Path("referencias")


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


def _acervo_de_referencias(args: argparse.Namespace) -> AcervoDeReferencias:
    return AcervoDeReferencias.carregar(args.acervo)


def _linha_da_referencia(referencia: Referencia) -> str:
    marca = {"proposta": "·", "confirmada": "✓", "recusada": "×"}[
        referencia.estado.value
    ]
    if referencia.decomposicao is None:
        situacao = "sem decomposição"
    else:
        editados = len(referencia.decomposicao.itens_editados)
        situacao = f"{len(referencia.decomposicao.itens)} item(ns)"
        if editados:
            situacao += f", {editados} reescrito(s)"
    return (
        f"{marca} {referencia.id}  {referencia.contribuicao.value:<15} "
        f"{referencia.nome}  ({situacao})"
    )


def _comando_ref_subir(args: argparse.Namespace) -> int:
    if not args.arquivo.exists():
        print(f"arquivo nao encontrado: {args.arquivo}", file=sys.stderr)
        return 1
    acervo = _acervo_de_referencias(args)
    referencia = acervo.subir(
        args.arquivo, TipoDeContribuicao(args.contribuicao), args.raiz
    )
    acervo.salvar(args.acervo)
    print(_linha_da_referencia(referencia))
    return 0


def _comando_ref_decompor(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    try:
        referencia = acervo.decompor(args.id, args.item)
    except ReferenciaNaoEncontrada:
        print(f"referencia nao encontrada: {args.id}", file=sys.stderr)
        return 1
    acervo.salvar(args.acervo)
    print(_linha_da_referencia(referencia))
    return 0


def _edicoes_de(pares: list[str] | None) -> dict[int, str]:
    """Interpreta `--editar 2=novo texto` como {2: "novo texto"}."""
    edicoes: dict[int, str] = {}
    for par in pares or []:
        ordem, _, texto = par.partition("=")
        if not texto:
            raise ValueError(f"edicao sem texto: {par!r}. Use ORDEM=texto novo")
        edicoes[int(ordem)] = texto
    return edicoes


def _comando_ref_confirmar(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    try:
        edicoes = _edicoes_de(args.editar)
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    try:
        referencia = acervo.confirmar(
            args.id, args.autor, datetime.now(timezone.utc), edicoes
        )
    except ReferenciaNaoEncontrada:
        print(f"referencia nao encontrada: {args.id}", file=sys.stderr)
        return 1
    except SemDecomposicao as erro:
        print(str(erro), file=sys.stderr)
        return 1

    acervo.salvar(args.acervo)
    print(_linha_da_referencia(referencia))
    if referencia.decomposicao is not None:
        print(f"taxa de reescrita: {referencia.decomposicao.taxa_de_edicao:.0%}")
    return 0


def _comando_ref_recusar(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    try:
        referencia = acervo.recusar(args.id)
    except ReferenciaNaoEncontrada:
        print(f"referencia nao encontrada: {args.id}", file=sys.stderr)
        return 1
    acervo.salvar(args.acervo)
    print(_linha_da_referencia(referencia))
    return 0


def _comando_ref_listar(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    for referencia in acervo.referencias:
        print(_linha_da_referencia(referencia))
        if referencia.arquivo_mudou(args.raiz):
            print(
                f"  aviso: o arquivo de {referencia.id} mudou desde a decomposicao",
                file=sys.stderr,
            )
    print(
        f"{len(acervo.referencias)} referencia(s) · "
        f"{len(acervo.confirmadas())} confirmada(s)"
    )
    return 0


def _comando_ref_checklist(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    itens = checklist_do_acervo(acervo)
    if not itens:
        print(
            "nenhum checklist: so referencia de estrutura confirmada gera itens",
            file=sys.stderr,
        )
        return 1
    for item in itens:
        print(f"{item.referencia}  {item}")
    return 0


def _comando_ref_materializar(args: argparse.Namespace) -> int:
    acervo = _acervo_de_referencias(args)
    texto = materializar_referencias(acervo)
    if not texto:
        print("nenhuma referencia confirmada, nada a materializar", file=sys.stderr)
        return 1
    print(texto, end="")
    return 0


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

    referencias = subcomandos.add_parser(
        "referencias", help="sobe, decompoe e confirma as referencias do autor"
    )
    referencias.add_argument(
        "--acervo", type=Path, default=REFERENCIAS_PADRAO, help="arquivo do acervo"
    )
    referencias.add_argument(
        "--raiz", type=Path, default=RAIZ_DE_REFERENCIAS, help="onde os arquivos ficam"
    )
    ref_acoes = referencias.add_subparsers(dest="acao", required=True)

    contribuicoes = [tipo.value for tipo in TipoDeContribuicao]

    subir = ref_acoes.add_parser("subir", help="copia um arquivo para o acervo")
    subir.add_argument("arquivo", type=Path)
    subir.add_argument("--contribuicao", required=True, choices=contribuicoes)
    subir.set_defaults(funcao=_comando_ref_subir)

    decompor = ref_acoes.add_parser(
        "decompor", help="grava a decomposicao proposta, sem confirma-la"
    )
    decompor.add_argument("id")
    decompor.add_argument(
        "--item", action="append", required=True, help="um item, na ordem"
    )
    decompor.set_defaults(funcao=_comando_ref_decompor)

    ref_confirmar = ref_acoes.add_parser(
        "confirmar", help="confirma a decomposicao, registrando o que foi reescrito"
    )
    ref_confirmar.add_argument("id")
    ref_confirmar.add_argument("--autor", required=True)
    ref_confirmar.add_argument(
        "--editar", action="append", metavar="ORDEM=TEXTO", help="reescreve um item"
    )
    ref_confirmar.set_defaults(funcao=_comando_ref_confirmar)

    ref_recusar = ref_acoes.add_parser("recusar", help="marca a referencia recusada")
    ref_recusar.add_argument("id")
    ref_recusar.set_defaults(funcao=_comando_ref_recusar)

    ref_listar = ref_acoes.add_parser("listar", help="lista as referencias")
    ref_listar.set_defaults(funcao=_comando_ref_listar)

    ref_checklist = ref_acoes.add_parser(
        "checklist", help="itens cobraveis pelo loop, vindos das referencias de estrutura"
    )
    ref_checklist.set_defaults(funcao=_comando_ref_checklist)

    ref_mat = ref_acoes.add_parser(
        "materializar", help="mostra o contexto que chegaria ao gerador"
    )
    ref_mat.set_defaults(funcao=_comando_ref_materializar)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    raise SystemExit(main())
