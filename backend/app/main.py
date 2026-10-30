"""Aplicação FastAPI do Salão em Dia.

Monta a API, o CORS, o tratamento global de erros e as rotinas de inicialização.
"""

from __future__ import annotations

import logging
import time
from http import HTTPStatus
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.v1 import router as router_v1
from app.core.config import obter_config
from app.core.contexto import definir_base_url
from app.core.erros import ErroDeNegocio
from app.core.protecoes import CabecalhosDeSeguranca, LimiteDeCorpo, LimiteDeTentativas
from app.core.registro import configurar_logs, definir_id_requisicao, novo_id_requisicao
from app.db.session import FabricaSessao, engine
from app.db.versao import versoes
from app.services.simulacao import expirar_processando
from app.services.storage import ErroDeArmazenamento

_config = obter_config()
configurar_logs(_config.log_formato, _config.log_nivel)
log = logging.getLogger("espelho")
log_acesso = logging.getLogger("espelho.acesso")

#: Sondas chamadas a cada poucos segundos pelo orquestrador: registrar cada uma afogaria
#: o log. Saem só em nível DEBUG, a menos que falhem.
SONDAS = {"/api/v1/saude", "/api/v1/saude/vivo"}


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    config = obter_config()
    log.info(
        "iniciando: ambiente=%s storage=%s provedor_ia=%s modo_demo=%s url_publica=%s",
        config.ambiente,
        config.storage_driver,
        config.ai_provider,
        config.modo_demo,
        config.url_publica or "(da requisição)",
    )
    for aviso in config.avisos_de_producao():
        log.warning("produção: %s", aviso)
    _avisar_se_banco_desatualizado()
    # Simulações interrompidas por um reinício não podem ficar "processando" para sempre.
    with FabricaSessao() as sessao:
        expirar_processando(sessao)
    yield


def _avisar_se_banco_desatualizado() -> None:
    """Código novo com banco antigo: avisa no terminal o comando que resolve."""
    try:
        aplicada, mais_recente = versoes(engine)
    except Exception:  # pragma: no cover - sem banco, o /saude já acusa
        log.exception("não foi possível conferir a versão do banco")
        return
    if aplicada != mais_recente:
        log.error(
            "BANCO DESATUALIZADO: o banco está na versão %s e o código espera %s. "
            "Rode 'alembic upgrade head' na pasta backend e reinicie a API. Até lá, "
            "login e outras rotas vão responder com erro 500.",
            aplicada,
            mais_recente,
        )


class IdentificaERegistra:
    """Dá um identificador a cada requisição e registra o acesso quando a resposta sai.

    É o middleware mais externo: até a resposta de um preflight de CORS ou um 413 leva
    o `X-Request-ID`. A linha de acesso é escrita quando o corpo da resposta termina de
    sair, e não quando a chamada termina: as tarefas em segundo plano (a geração de uma
    simulação) rodam depois da resposta e inflariam a duração.

    O caminho vai sem a query string: nas imagens ela é a assinatura que abre a foto.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        recebido = dict(scope.get("headers") or []).get(b"x-request-id", b"")
        identificador = novo_id_requisicao(recebido.decode("latin-1"))
        definir_id_requisicao(identificador)
        inicio = time.perf_counter()
        situacao = 500
        registrado = False

        def registrar() -> None:
            nonlocal registrado
            registrado = True
            caminho = scope.get("path", "")
            nivel = logging.DEBUG if caminho in SONDAS and situacao < 400 else logging.INFO
            log_acesso.log(
                nivel,
                "%s %s %s %.0fms",
                scope.get("method", "-"),
                caminho,
                situacao,
                (time.perf_counter() - inicio) * 1000,
            )

        async def enviar(mensagem: Message) -> None:
            nonlocal situacao
            if mensagem["type"] == "http.response.start":
                situacao = mensagem["status"]
                mensagem["headers"] = [
                    *mensagem.get("headers", []),
                    (b"x-request-id", identificador.encode()),
                ]
            await send(mensagem)
            if (
                mensagem["type"] == "http.response.body"
                and not mensagem.get("more_body", False)
                and not registrado
            ):
                registrar()

        try:
            await self.app(scope, receive, enviar)
        finally:
            if not registrado:
                registrar()


# Em produção a API não publica a própria superfície: nomes de campos internos, formatos
# aceitos e rotas completas são exatamente o material de reconhecimento de quem procura
# brecha. Em desenvolvimento e teste a documentação continua disponível.
_documentacao_aberta = not _config.producao

app = FastAPI(
    title="Salão em Dia: API",
    version="1.0.0",
    summary="Simulação capilar por IA e gestão de clientes para profissionais de beleza.",
    description=(
        "Back-end do aplicativo Salão em Dia (TCC em Sistemas de Informação). "
        "Toda rota de dados exige `Authorization: Bearer <token>` e devolve apenas o que "
        "pertence ao profissional autenticado."
    ),
    lifespan=ciclo_de_vida,
    docs_url="/docs" if _documentacao_aberta else None,
    redoc_url="/redoc" if _documentacao_aberta else None,
    openapi_url="/openapi.json" if _documentacao_aberta else None,
)

# Ordem importa: o limite de corpo roda antes de qualquer leitura da requisição, e os
# cabeçalhos são aplicados por último, para valerem também nas respostas de erro.
app.add_middleware(LimiteDeTentativas)
app.add_middleware(LimiteDeCorpo)
app.add_middleware(CabecalhosDeSeguranca)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.origens_cors,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    # O aplicativo na web lê o identificador para mostrar no suporte.
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def registrar_base_url(request: Request, proximo):
    """Guarda o endereço público da requisição para montar as URLs de imagem."""
    definir_base_url(str(request.base_url))
    return await proximo(request)


# Por último: o mais externo de todos, para identificar e registrar até as respostas que
# os outros middlewares dão sozinhos (preflight de CORS, 413, 429).
app.add_middleware(IdentificaERegistra)


@app.exception_handler(ErroDeNegocio)
async def tratar_erro_de_negocio(request: Request, erro: ErroDeNegocio) -> JSONResponse:
    return JSONResponse(status_code=erro.status, content=erro.como_json())


@app.exception_handler(ErroDeArmazenamento)
async def tratar_armazenamento(request: Request, erro: ErroDeArmazenamento) -> JSONResponse:
    """Storage fora do ar não é erro do sistema nem de quem pediu: 503, tente de novo."""
    log.error("storage indisponível em %s %s: %s", request.method, request.url.path, erro)
    return JSONResponse(
        status_code=503,
        content={
            "erro": {
                "codigo": "armazenamento_indisponivel",
                "mensagem": "O armazenamento de imagens não respondeu. Tente de novo em instantes.",
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def tratar_validacao(request: Request, erro: RequestValidationError) -> JSONResponse:
    """Mesma forma dos erros de negócio, para o aplicativo ter um só caminho de leitura."""
    detalhes = [
        {
            "campo": ".".join(str(parte) for parte in item.get("loc", [])[1:]) or "corpo",
            "mensagem": item.get("msg", "valor inválido"),
        }
        for item in erro.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "erro": {
                "codigo": "validacao",
                "mensagem": "Confira os dados enviados.",
                "detalhes": detalhes,
            }
        },
    )


#: Erros HTTP que não passam pelas regras de negócio (rota inexistente, método errado). O
#: texto padrão do Starlette vem em inglês ("Method Not Allowed") e chegava assim à tela.
MENSAGENS_HTTP = {
    404: "Endereço não encontrado.",
    405: "Esta operação não está disponível nesta versão do servidor.",
}


@app.exception_handler(StarletteHTTPException)
async def tratar_http(request: Request, erro: StarletteHTTPException) -> JSONResponse:
    mensagem = MENSAGENS_HTTP.get(erro.status_code)
    if mensagem is None:
        detalhe = str(erro.detail)
        # O detalhe padrão é o nome do status em inglês; um detalhe próprio passa como veio.
        padrao = erro.status_code >= 400 and detalhe == HTTPStatus(erro.status_code).phrase
        mensagem = "Não foi possível concluir a ação." if padrao else detalhe
    return JSONResponse(
        status_code=erro.status_code,
        content={"erro": {"codigo": "http_%s" % erro.status_code, "mensagem": mensagem}},
        headers=getattr(erro, "headers", None),
    )


@app.exception_handler(Exception)
async def tratar_inesperado(request: Request, erro: Exception) -> JSONResponse:
    """Erro não previsto: detalhe vai para o log, nunca para a resposta."""
    log.exception("erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "erro": {
                "codigo": "erro_interno",
                "mensagem": "Algo deu errado aqui no servidor. Tente de novo em instantes.",
            }
        },
    )


app.include_router(router_v1)


@app.get("/api/v1/saude/vivo", tags=["diagnóstico"])
def vivo() -> dict[str, bool]:
    """Sonda de vida: o processo responde. Não toca no banco.

    Para o orquestrador decidir se reinicia o contêiner. Um banco fora do ar não se
    resolve reiniciando a API, por isso ele fica de fora desta sonda (e entra na de
    prontidão, `/api/v1/saude`).
    """
    return {"ok": True}


@app.get("/api/v1/saude", tags=["diagnóstico"])
def saude(resposta: Response) -> dict[str, object]:
    """Sonda de prontidão e diagnóstico: banco acessível e com as migrations aplicadas.

    Responde 503 quando não está pronta, para o orquestrador ou o balanceador não mandar
    tráfego a uma instância que só devolveria erro 500.
    """
    from sqlalchemy import text

    config = obter_config()
    banco_ok = True
    banco_atualizado = False
    try:
        with FabricaSessao() as sessao:
            sessao.execute(text("SELECT 1"))
        aplicada, mais_recente = versoes(engine)
        banco_atualizado = aplicada == mais_recente
    except Exception:  # pragma: no cover - depende de falha de infraestrutura
        log.exception("banco indisponível")
        banco_ok = False

    if not (banco_ok and banco_atualizado):
        resposta.status_code = 503

    if config.producao:
        # Em produção a rota não descreve a infraestrutura.
        return {"ok": banco_ok and banco_atualizado, "ambiente": config.ambiente}

    return {
        "ok": banco_ok and banco_atualizado,
        "ambiente": config.ambiente,
        "banco": banco_ok,
        # Falso quando faltam migrations: rode `alembic upgrade head`.
        "bancoAtualizado": banco_atualizado,
        "storage": config.storage_driver,
        "provedorIa": config.ai_provider,
        # Booleano, nunca a chave: é o que permite conferir, antes de gastar uma
        # simulação, se a credencial do provedor externo chegou ao servidor.
        "credencialIa": bool(config.ai_api_key),
        "modeloIa": config.ai_modelo if config.ai_provider == "replicate" else None,
        # Os dois modelos da simulação (texto vazio = descrição livre desligada).
        "modelosIa": (
            {"principal": config.ai_modelo, "texto": config.ai_modelo_texto or None}
            if config.ai_provider == "replicate"
            else None
        ),
        "modoDemo": config.modo_demo,
    }
