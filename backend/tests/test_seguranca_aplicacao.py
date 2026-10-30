"""Configuração de segurança da aplicação: cabeçalhos, exposição, CORS e abuso de custo.

Referência: OWASP Top 10 — A01 (controle de acesso), A03 (injeção), A05 (configuração
incorreta de segurança) e A04 (projeto inseguro, no caso do consumo sem limite de um
recurso pago).
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app.core import config as modulo_config

CABECALHOS_ESPERADOS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "x-permitted-cross-domain-policies": "none",
}


# --- A05: cabeçalhos ------------------------------------------------------


@pytest.mark.parametrize(("cabecalho", "valor"), CABECALHOS_ESPERADOS.items())
def test_cabecalhos_de_seguranca_presentes(cliente_http: TestClient, cabecalho, valor):
    resposta = cliente_http.get("/api/v1/catalogo")
    assert resposta.status_code == 200
    assert resposta.headers.get(cabecalho) == valor


def test_cabecalhos_tambem_nas_respostas_de_erro(cliente_http: TestClient):
    """De nada serve proteger o caminho feliz e deixar o erro descoberto."""
    resposta = cliente_http.get("/api/v1/clientes")
    assert resposta.status_code == 401
    assert resposta.headers.get("x-content-type-options") == "nosniff"
    assert resposta.headers.get("x-frame-options") == "DENY"


def test_servidor_nao_anuncia_a_propria_versao(cliente_http: TestClient):
    """`Server: uvicorn` só interessa a quem procura vulnerabilidade conhecida."""
    resposta = cliente_http.get("/api/v1/catalogo")
    assert resposta.headers.get("server") == "espelho"
    assert "uvicorn" not in resposta.headers.get("server", "").lower()


def test_hsts_so_em_producao(cliente_http: TestClient):
    """Em desenvolvimento o servidor roda em HTTP; fixar HTTPS atrapalharia o trabalho."""
    resposta = cliente_http.get("/api/v1/catalogo")
    assert "strict-transport-security" not in resposta.headers


# --- A05: exposição da documentação ---------------------------------------


def test_documentacao_disponivel_fora_de_producao(cliente_http: TestClient):
    assert cliente_http.get("/docs").status_code == 200
    assert cliente_http.get("/openapi.json").status_code == 200


def test_documentacao_fechada_em_producao(monkeypatch: pytest.MonkeyPatch):
    """Com AMBIENTE=producao, a API deixa de publicar a própria superfície.

    A aplicação é remontada dentro do teste porque as rotas de documentação são
    definidas na construção do FastAPI, e não por requisição.
    """
    monkeypatch.setenv("AMBIENTE", "producao")
    # Produção não sobe com os atalhos de demonstração ligados.
    monkeypatch.setenv("MODO_DEMO", "false")
    monkeypatch.setenv("URL_PUBLICA", "https://api.exemplo.com.br")
    modulo_config.obter_config.cache_clear()
    try:
        from app import main as modulo_main

        recarregado = importlib.reload(modulo_main)
        with TestClient(recarregado.app) as cliente:
            assert cliente.get("/docs").status_code == 404
            assert cliente.get("/redoc").status_code == 404
            assert cliente.get("/openapi.json").status_code == 404
            # E o HSTS, que só existe em produção, aparece.
            resposta = cliente.get("/api/v1/catalogo")
            assert "max-age=" in resposta.headers.get("strict-transport-security", "")
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()
        from app import main as modulo_main

        importlib.reload(modulo_main)


# --- A05: CORS ------------------------------------------------------------


def test_cors_libera_a_origem_autorizada(cliente_http: TestClient):
    resposta = cliente_http.get(
        "/api/v1/catalogo", headers={"Origin": "http://localhost:8081"}
    )
    assert resposta.headers.get("access-control-allow-origin") == "http://localhost:8081"


def test_cors_nao_libera_origem_estranha(cliente_http: TestClient):
    """Sem o cabeçalho de liberação, o navegador recusa a resposta por conta própria."""
    resposta = cliente_http.get(
        "/api/v1/catalogo", headers={"Origin": "https://site-de-outra-pessoa.example"}
    )
    assert "access-control-allow-origin" not in resposta.headers


def test_cors_responde_a_requisicao_previa(cliente_http: TestClient):
    resposta = cliente_http.options(
        "/api/v1/clientes",
        headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert resposta.status_code == 200
    assert resposta.headers.get("access-control-allow-origin") == "http://localhost:8081"


def test_cors_nunca_combina_curinga_com_credenciais():
    """A combinação proibida: `*` com `allow_credentials=True` anula a proteção."""
    from app.main import app as aplicacao

    for camada in aplicacao.user_middleware:
        if camada.cls.__name__ == "CORSMiddleware":
            opcoes = camada.kwargs
            assert "*" not in opcoes.get("allow_origins", []), "origem curinga liberada"
            assert opcoes.get("allow_credentials") is False
            break
    else:
        raise AssertionError("o middleware de CORS não está montado")


# --- A04: consumo sem limite de um recurso pago ---------------------------


def test_teto_de_simulacoes_por_conta(cliente_http: TestClient, conta, monkeypatch):
    """Cada simulação é uma chamada paga: sem teto, um laço esvazia o crédito.

    O teto é baixado a 3 no teste. O que se verifica é a existência da barreira e o
    código devolvido, não o valor configurado.
    """
    from tests.fabricas import arquivo_de_foto

    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "3")
    modulo_config.obter_config.cache_clear()
    try:
        cabecalhos, _ = conta()
        cliente = cliente_http.post(
            "/api/v1/clientes",
            headers=cabecalhos,
            json={"nome": "Marina Alves", "telefone": "1"},
        ).json()
        cliente_http.post(
            f"/api/v1/clientes/{cliente['id']}/consentimentos",
            headers=cabecalhos,
            json={
                "decisao": "aceito",
                "formaObtencao": "tela_dispositivo",
                "confirmadoPor": "Marina Alves",
                "observacao": "",
            },
        )

        dados = {
            "clienteId": cliente["id"],
            "corte": "Bob curto",
            "cor": "Ruivo intenso",
            "observacoes": "",
        }
        aceitas = recusadas = 0
        for _ in range(5):
            resposta = cliente_http.post(
                "/api/v1/simulacoes",
                headers=cabecalhos,
                data=dados,
                files=arquivo_de_foto(),
            )
            if resposta.status_code == 202:
                aceitas += 1
            else:
                assert resposta.status_code == 429, resposta.text
                assert resposta.json()["erro"]["codigo"] == "limite_de_simulacoes"
                recusadas += 1

        assert aceitas == 3, f"o teto não foi respeitado: {aceitas} aceitas"
        assert recusadas == 2
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_teto_e_por_conta_e_nao_global(cliente_http: TestClient, conta, monkeypatch):
    """O teto de uma conta não pode bloquear outra: seria negação de serviço de graça."""
    from tests.fabricas import arquivo_de_foto

    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "1")
    modulo_config.obter_config.cache_clear()
    try:
        def cliente_pronto(cabecalhos):
            cliente = cliente_http.post(
                "/api/v1/clientes",
                headers=cabecalhos,
                json={"nome": "Cliente Teste", "telefone": "1"},
            ).json()
            cliente_http.post(
                f"/api/v1/clientes/{cliente['id']}/consentimentos",
                headers=cabecalhos,
                json={
                    "decisao": "aceito",
                    "formaObtencao": "tela_dispositivo",
                    "confirmadoPor": "Cliente Teste",
                    "observacao": "",
                },
            )
            return cliente

        def gerar(cabecalhos, cliente):
            return cliente_http.post(
                "/api/v1/simulacoes",
                headers=cabecalhos,
                data={
                    "clienteId": cliente["id"],
                    "corte": "Bob curto",
                    "cor": "Ruivo intenso",
                    "observacoes": "",
                },
                files=arquivo_de_foto(),
            )

        cabecalhos_a, _ = conta()
        cabecalhos_b, _ = conta()
        cliente_a = cliente_pronto(cabecalhos_a)
        cliente_b = cliente_pronto(cabecalhos_b)

        assert gerar(cabecalhos_a, cliente_a).status_code == 202
        assert gerar(cabecalhos_a, cliente_a).status_code == 429
        # A conta B não foi afetada pelo consumo da conta A.
        assert gerar(cabecalhos_b, cliente_b).status_code == 202
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_teto_age_antes_de_processar_a_foto(cliente_http: TestClient, conta, monkeypatch):
    """Teto depois do processamento não contém custo nenhum — só desperdiça trabalho.

    Aqui a foto enviada é inválida de propósito. Se o teto agir primeiro, a resposta é
    429; se agir depois da validação, viria 422 — o que provaria que a imagem foi
    decodificada antes da barreira.
    """
    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "0")
    modulo_config.obter_config.cache_clear()
    try:
        cabecalhos, _ = conta()
        cliente = cliente_http.post(
            "/api/v1/clientes",
            headers=cabecalhos,
            json={"nome": "Marina Alves", "telefone": "1"},
        ).json()
        resposta = cliente_http.post(
            "/api/v1/simulacoes",
            headers=cabecalhos,
            data={
                "clienteId": cliente["id"],
                "corte": "Bob curto",
                "cor": "Ruivo intenso",
                "observacoes": "",
            },
            files={"foto": ("nao-e-imagem.jpg", b"isto nao e uma imagem", "image/jpeg")},
        )
        assert resposta.status_code == 429, (
            f"esperado 429 do teto, veio {resposta.status_code}: a barreira está depois "
            "do processamento da imagem"
        )
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_bomba_de_descompressao_vira_422_e_nao_erro_interno(cliente_http: TestClient, conta):
    """Um arquivo de 68 bytes não pode derrubar o tratamento de erro da API."""
    from tests.test_validacao_foto import png_que_declara_dimensoes_enormes

    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Cliente Teste", "telefone": "1"}
    ).json()

    bomba = png_que_declara_dimensoes_enormes(30_000, 30_000)
    resposta = cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("inocente.png", bomba, "image/png")},
    )

    assert resposta.status_code == 422, resposta.text
    corpo = resposta.text.lower()
    assert "traceback" not in corpo and "pil" not in corpo


# --- Preparo da integração externa ----------------------------------------


def test_saude_informa_se_a_credencial_do_provedor_existe(cliente_http: TestClient, monkeypatch):
    """Permite conferir que a chave chegou ao servidor sem gastar uma simulação.

    O que sai é booleano. A chave em si nunca aparece em resposta alguma — é o que o
    teste abaixo confirma.
    """
    resposta = cliente_http.get("/api/v1/saude").json()
    assert resposta["provedorIa"] == "fake"
    assert resposta["credencialIa"] is False

    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "chave-que-nao-pode-vazar-r8-123456")
    modulo_config.obter_config.cache_clear()
    try:
        corpo = cliente_http.get("/api/v1/saude").json()
        assert corpo["provedorIa"] == "replicate"
        assert corpo["credencialIa"] is True, "a credencial configurada não foi detectada"
        assert corpo["modeloIa"] == "flux-kontext-apps/change-haircut"
        assert "chave-que-nao-pode-vazar" not in cliente_http.get("/api/v1/saude").text
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_saude_em_producao_nao_descreve_a_infraestrutura(cliente_http: TestClient, monkeypatch):
    monkeypatch.setenv("AMBIENTE", "producao")
    # Produção não sobe com os atalhos de demonstração ligados.
    monkeypatch.setenv("MODO_DEMO", "false")
    monkeypatch.setenv("URL_PUBLICA", "https://api.exemplo.com.br")
    modulo_config.obter_config.cache_clear()
    try:
        corpo = cliente_http.get("/api/v1/saude").json()
        assert set(corpo) == {"ok", "ambiente"}, f"vazou detalhe de infraestrutura: {corpo}"
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def _cliente_autorizado(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos",
        headers=cabecalhos,
        json={
            "decisao": "aceito",
            "formaObtencao": "tela_dispositivo",
            "confirmadoPor": "Marina Alves",
            "observacao": "",
        },
    )
    return cliente


def _gerar(cliente_http: TestClient, cabecalhos, cliente, foto=None):
    from tests.fabricas import arquivo_de_foto

    return cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Bob curto", "cor": "Ruivo intenso", "observacoes": ""},
        files=arquivo_de_foto(foto) if foto else arquivo_de_foto(),
    )


def test_foto_recusada_nao_gasta_a_cota(cliente_http: TestClient, conta, monkeypatch):
    """Só o que vai ao provedor (e custa) conta. Foto escura recusada não consome a cota."""
    from tests.fabricas import imagem_lisa

    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "1")
    modulo_config.obter_config.cache_clear()
    try:
        cabecalhos, _ = conta()
        cliente = _cliente_autorizado(cliente_http, cabecalhos)
        recusada = _gerar(cliente_http, cabecalhos, cliente, foto=imagem_lisa(tom=10))
        assert recusada.status_code == 422, recusada.text
        assert _gerar(cliente_http, cabecalhos, cliente).status_code == 202
        assert _gerar(cliente_http, cabecalhos, cliente).status_code == 429
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_cota_sobrevive_ao_reinicio_do_servidor(cliente_http: TestClient, conta, monkeypatch):
    """A contagem vem do banco: reiniciar o servidor não devolve a cota gasta."""
    from app.core import protecoes

    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "1")
    modulo_config.obter_config.cache_clear()
    try:
        cabecalhos, _ = conta()
        cliente = _cliente_autorizado(cliente_http, cabecalhos)
        assert _gerar(cliente_http, cabecalhos, cliente).status_code == 202
        # Nenhum registro em memória: o que barra a próxima é a contagem no banco, que um
        # reinício do processo não apaga.
        assert not hasattr(protecoes, "_simulacoes")
        assert _gerar(cliente_http, cabecalhos, cliente).status_code == 429
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_padrao_de_producao_e_tres_por_hora(monkeypatch):
    monkeypatch.delenv("SIMULACAO_MAX_POR_HORA", raising=False)
    modulo_config.obter_config.cache_clear()
    try:
        assert modulo_config.obter_config().simulacao_max_por_hora == 3
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()
