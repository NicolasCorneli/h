"""O aplicativo consome exatamente o que a API devolve?

Este teste compara, campo a campo, os tipos TypeScript de `espelho/src/data/tipos.ts` com
os schemas publicados no OpenAPI. Um campo renomeado no servidor e esquecido no
aplicativo passaria despercebido até alguém abrir a tela; aqui ele falha na suíte.

Não é checagem de tipo — é de nome e presença, que é onde a divergência costuma nascer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.main import app

TIPOS_TS = Path(__file__).resolve().parents[2] / "espelho" / "src" / "data" / "tipos.ts"

#: tipo no aplicativo → schema na API
PARES = {
    "Usuario": "UsuarioOut",
    "Cliente": "ClienteOut",
    "Simulacao": "SimulacaoOut",
    "HistoricoServico": "AtendimentoOut",
    "Agendamento": "AgendamentoOut",
    "RegistroConsentimento": "ConsentimentoOut",
    "ResumoConsentimento": "ResumoConsentimentoOut",
    "BloqueioCaptura": "BloqueioOut",
    "CienciaProfissional": "CienciaOut",
    "Termo": "TermoOut",
    "SecaoTermo": "SecaoTermoOut",
    "Catalogo": "CatalogoOut",
    "ParametrosSimulacao": "ParametrosSimulacao",
    "PlanoSimulacao": "PlanoOut",
    "ResponsavelLegal": "ResponsavelLegal",
    "Tokens": "TokensOut",
}


def campos_do_tipo_ts(nome: str) -> set[str]:
    """Nomes das propriedades declaradas no tipo, em uma linha ou em várias."""
    texto = TIPOS_TS.read_text(encoding="utf-8")
    achado = re.search(rf"export type {nome} = \{{(.*?)\}};", texto, re.S)
    assert achado, f"tipo {nome} não encontrado em tipos.ts"

    corpo = re.sub(r"/\*.*?\*/", " ", achado.group(1), flags=re.S)
    corpo = re.sub(r"//[^\n]*", " ", corpo)

    campos = set()
    profundidade = 0
    atual = ""
    for caractere in corpo:
        if caractere in "{<([":
            profundidade += 1
        elif caractere in "}>)]":
            profundidade -= 1
        if caractere in ";\n" and profundidade == 0:
            propriedade = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", atual)
            if propriedade:
                campos.add(propriedade.group(1))
            atual = ""
        else:
            atual += caractere
    propriedade = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", atual)
    if propriedade:
        campos.add(propriedade.group(1))
    return campos


def campos_do_schema(nome: str) -> set[str]:
    esquema = app.openapi()["components"]["schemas"]
    assert nome in esquema, f"schema {nome} não existe na API"
    return set(esquema[nome].get("properties", {}))


def test_o_arquivo_de_tipos_existe():
    """Canário: sem o arquivo, todos os testes abaixo seriam vacuamente verdadeiros."""
    assert TIPOS_TS.exists(), f"tipos.ts não encontrado em {TIPOS_TS}"
    assert "export type Cliente" in TIPOS_TS.read_text(encoding="utf-8")


@pytest.mark.parametrize(("tipo_ts", "schema"), PARES.items())
def test_tipo_do_aplicativo_cobre_o_schema_da_api(tipo_ts: str, schema: str):
    do_app = campos_do_tipo_ts(tipo_ts)
    da_api = campos_do_schema(schema)

    faltando_no_app = da_api - do_app
    assert not faltando_no_app, (
        f"a API devolve campos que {tipo_ts} não declara: {sorted(faltando_no_app)}"
    )

    sobrando_no_app = do_app - da_api
    assert not sobrando_no_app, (
        f"{tipo_ts} declara campos que a API não devolve: {sorted(sobrando_no_app)}"
    )


def test_api_responde_em_camel_case():
    """O contrato combinado: nada de snake_case no JSON."""
    esquema = app.openapi()["components"]["schemas"]
    com_underline = {
        f"{nome}.{campo}"
        for nome, corpo in esquema.items()
        for campo in corpo.get("properties", {})
        # Os schemas de corpo multipart são gerados pelo FastAPI a partir dos nomes dos
        # parâmetros; o alias camelCase está no parâmetro, não no schema gerado.
        if "_" in campo and not nome.startswith("Body_")
    }
    assert not com_underline, sorted(com_underline)


def test_listas_nao_prometem_paginacao_que_nao_existe():
    """As rotas de lista devolvem array puro — e o aplicativo trata como array.

    Registrado de propósito: não há paginação. Com carteiras grandes isso vira um limite
    real, e está anotado como risco residual no relatório de QA.
    """
    caminhos = app.openapi()["paths"]
    for rota in ("/api/v1/clientes", "/api/v1/agendamentos", "/api/v1/atendimentos"):
        resposta = caminhos[rota]["get"]["responses"]["200"]["content"]["application/json"]
        assert resposta["schema"]["type"] == "array", rota


def test_enumeracoes_batem_com_as_do_aplicativo():
    """Status e enumerações são usados em `switch` no aplicativo: divergir quebra tela."""
    esquema = app.openapi()["components"]["schemas"]
    texto = TIPOS_TS.read_text(encoding="utf-8")

    for nome_api, tipo_ts in (
        ("StatusSimulacao", "StatusSimulacao"),
        ("StatusAgendamento", "StatusAgendamento"),
        ("FormaObtencao", "FormaObtencao"),
        ("FaixaEtaria", "FaixaEtaria"),
        ("TipoTermo", "TipoTermo"),
    ):
        valores_api = set(esquema[nome_api]["enum"])
        achado = re.search(rf"export type {tipo_ts} =(.*?);", texto, re.S)
        assert achado, f"{tipo_ts} não encontrado em tipos.ts"
        valores_app = set(re.findall(r"'([^']+)'", achado.group(1)))
        assert valores_api == valores_app, (
            f"{nome_api}: API tem {sorted(valores_api)}, aplicativo tem {sorted(valores_app)}"
        )
