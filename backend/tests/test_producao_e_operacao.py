"""Regressões da revisão de prontidão para produção.

Configuração de produção, sondas de saúde, identificação das requisições, log de acesso,
encerramento de sessões no servidor, falhas de storage, simulações presas e limites de
memória. Quase todos falham no código anterior a esta revisão; os que passam nele são de
compatibilidade (token emitido antes da versão da sessão) ou de controle (prontidão com o
banco em dia).
"""

from __future__ import annotations

import io
import logging
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text

from app.core import config as modulo_config
from app.core import protecoes
from app.core.security import criar_token
from app.db.session import engine
from app.models import Simulacao, StatusSimulacao, Usuario
from tests.conftest import SENHA
from tests.fabricas import retrato_valido

RAIZ = Path(__file__).resolve().parents[1]

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "a própria cliente",
    "responsavel": None,
    "observacao": "",
}


@pytest.fixture
def config_limpa(monkeypatch: pytest.MonkeyPatch):
    """Ambiente de produção mínimo e válido; cada teste estraga uma parte."""
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("MODO_DEMO", "false")
    monkeypatch.setenv("URL_PUBLICA", "https://api.exemplo.com.br")
    monkeypatch.setenv("CORS_ORIGENS", "https://app.exemplo.com.br")
    modulo_config.obter_config.cache_clear()
    yield monkeypatch
    monkeypatch.undo()
    modulo_config.obter_config.cache_clear()


# --- Configuração de produção ------------------------------------------------------


def test_producao_valida_sobe(config_limpa):
    config = modulo_config.Configuracao()
    assert config.producao
    assert config.url_publica == "https://api.exemplo.com.br"


def test_producao_exige_url_publica_com_https(config_limpa):
    config_limpa.delenv("URL_PUBLICA")
    with pytest.raises(ValueError, match="URL_PUBLICA"):
        modulo_config.Configuracao()
    config_limpa.setenv("URL_PUBLICA", "http://api.exemplo.com.br")
    with pytest.raises(ValueError, match="URL_PUBLICA"):
        modulo_config.Configuracao()


def test_producao_recusa_o_banco_de_desenvolvimento(config_limpa):
    config_limpa.setenv("DATABASE_URL", modulo_config.URL_BANCO_DESENVOLVIMENTO)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        modulo_config.Configuracao()


def test_producao_recusa_cors_aberto(config_limpa):
    config_limpa.setenv("CORS_ORIGENS", "*")
    with pytest.raises(ValueError, match="CORS_ORIGENS"):
        modulo_config.Configuracao()


def test_url_publica_malformada_e_recusada_em_qualquer_ambiente(monkeypatch):
    monkeypatch.setenv("URL_PUBLICA", "api.exemplo.com.br")
    with pytest.raises(ValueError, match="URL_PUBLICA"):
        modulo_config.Configuracao()


def test_avisos_de_producao_apontam_escolhas_arriscadas(config_limpa):
    config_limpa.setenv("AI_PROVIDER", "fake")
    config_limpa.setenv("CORS_ORIGENS", "https://app.exemplo.com.br,http://antigo.exemplo.com.br")
    avisos = " ".join(modulo_config.Configuracao().avisos_de_producao())
    assert "AI_PROVIDER=fake" in avisos
    assert "http://antigo.exemplo.com.br" in avisos
    assert "STORAGE_DRIVER=local" in avisos


def test_testes_se_recusam_a_rodar_fora_de_um_banco_de_teste():
    """A suíte apaga o banco que recebe: só aceita um cujo nome termine em `_test`."""
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_protecoes.py"],
        cwd=RAIZ,
        env={
            "PATH": "/usr/bin:/bin",
            "TEST_DATABASE_URL": "postgresql+psycopg://espelho:espelho@localhost:5432/espelho",
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert resultado.returncode != 0
    assert "_test" in resultado.stdout + resultado.stderr


# --- URL pública das imagens -------------------------------------------------------


def test_url_da_imagem_usa_a_url_publica(cliente_http: TestClient, conta, monkeypatch):
    """Atrás de proxy, o endereço da requisição é o interno (http://api:8000)."""
    cabecalhos, _ = conta()
    monkeypatch.setenv("URL_PUBLICA", "https://api.exemplo.com.br")
    modulo_config.obter_config.cache_clear()
    try:
        resposta = cliente_http.post(
            "/api/v1/usuarios/me/foto",
            headers=cabecalhos,
            files={"arquivo": ("foto.jpg", retrato_valido(), "image/jpeg")},
        )
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["fotoUri"].startswith("https://api.exemplo.com.br/api/v1/imagens/")
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


# --- Sondas de saúde ---------------------------------------------------------------


def test_sonda_de_vida_nao_depende_do_banco(cliente_http: TestClient, monkeypatch):
    def banco_fora(*_args, **_kwargs):
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr("app.main.versoes", banco_fora)
    assert cliente_http.get("/api/v1/saude/vivo").json() == {"ok": True}
    assert cliente_http.get("/api/v1/saude").status_code == 503


def test_prontidao_responde_503_com_migrations_pendentes(cliente_http: TestClient, monkeypatch):
    monkeypatch.setattr("app.main.versoes", lambda _engine: ("versao-antiga", "versao-nova"))
    resposta = cliente_http.get("/api/v1/saude")
    assert resposta.status_code == 503
    assert resposta.json()["ok"] is False


def test_prontidao_responde_200_com_o_banco_em_dia(cliente_http: TestClient):
    resposta = cliente_http.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True


# --- Identificação das requisições e log de acesso -----------------------------------


def test_toda_resposta_leva_um_identificador(cliente_http: TestClient):
    resposta = cliente_http.get("/api/v1/catalogo")
    assert len(resposta.headers["x-request-id"]) >= 8
    # Também nas respostas que os middlewares dão sozinhos.
    preflight = cliente_http.options(
        "/api/v1/clientes",
        headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "GET"},
    )
    assert preflight.headers.get("x-request-id")


def test_identificador_recebido_e_reaproveitado_so_se_for_seguro(cliente_http: TestClient):
    vindo_do_proxy = "abc123-def456"
    resposta = cliente_http.get("/api/v1/catalogo", headers={"X-Request-ID": vindo_do_proxy})
    assert resposta.headers["x-request-id"] == vindo_do_proxy

    malicioso = "x" * 10 + " injetado no log"
    resposta = cliente_http.get("/api/v1/catalogo", headers={"X-Request-ID": malicioso})
    assert resposta.headers["x-request-id"] != malicioso


def test_log_de_acesso_nao_registra_a_assinatura_da_imagem(
    cliente_http: TestClient, conta, caplog: pytest.LogCaptureFixture
):
    """A query das imagens é a credencial que abre a foto: não pode ir para o log."""
    cabecalhos, _ = conta()
    foto = cliente_http.post(
        "/api/v1/usuarios/me/foto",
        headers=cabecalhos,
        files={"arquivo": ("foto.jpg", retrato_valido(), "image/jpeg")},
    ).json()["fotoUri"]
    caminho = foto.replace("http://testserver", "")
    assinatura = caminho.split("?t=")[1]

    with caplog.at_level(logging.INFO, logger="espelho.acesso"):
        assert cliente_http.get(caminho).status_code == 200

    linhas = [r.getMessage() for r in caplog.records if r.name == "espelho.acesso"]
    assert any("/api/v1/imagens/" in linha and " 200 " in linha for linha in linhas), linhas
    assert not any(assinatura in linha or "?t=" in linha for linha in linhas)


# --- Sessões encerradas no servidor ------------------------------------------------


def _renovacao(cliente_http: TestClient, email: str) -> tuple[dict, str]:
    sessao = cliente_http.post("/api/v1/auth/login", json={"email": email, "senha": SENHA}).json()
    return (
        {"Authorization": f"Bearer {sessao['tokens']['accessToken']}"},
        sessao["tokens"]["refreshToken"],
    )


def test_trocar_senha_encerra_as_outras_sessoes(cliente_http: TestClient, conta):
    _, usuario = conta()
    outro_aparelho, renovacao_antiga = _renovacao(cliente_http, usuario["email"])
    este_aparelho, _ = _renovacao(cliente_http, usuario["email"])

    resposta = cliente_http.post(
        "/api/v1/usuarios/me/senha",
        headers=este_aparelho,
        json={"senhaAtual": SENHA, "novaSenha": "uma-senha-nova-e-longa"},
    )
    assert resposta.status_code == 200, resposta.text
    novos = {"Authorization": f"Bearer {resposta.json()['tokens']['accessToken']}"}

    # O aparelho que trocou segue com os tokens novos.
    assert cliente_http.get("/api/v1/usuarios/me", headers=novos).status_code == 200
    # O outro aparelho, e o token de renovação copiado, não valem mais.
    recusada = cliente_http.get("/api/v1/usuarios/me", headers=outro_aparelho)
    assert recusada.status_code == 401
    assert recusada.json()["erro"]["codigo"] == "sessao_encerrada"
    assert (
        cliente_http.post("/api/v1/auth/renovar", json={"refreshToken": renovacao_antiga}).status_code
        == 401
    )
    # A senha antiga não entra; a nova, sim.
    assert (
        cliente_http.post(
            "/api/v1/auth/login", json={"email": usuario["email"], "senha": SENHA}
        ).status_code
        == 401
    )
    assert (
        cliente_http.post(
            "/api/v1/auth/login",
            json={"email": usuario["email"], "senha": "uma-senha-nova-e-longa"},
        ).status_code
        == 200
    )


def test_trocar_senha_exige_a_senha_atual(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/senha",
        headers=cabecalhos,
        json={"senhaAtual": "nao-e-esta", "novaSenha": "uma-senha-nova-e-longa"},
    )
    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "senha_incorreta"
    # Nada mudou: o token continua valendo.
    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos).status_code == 200


@pytest.mark.parametrize(
    ("nova", "codigo"),
    [(SENHA, "senha_repetida"), ("curta", "validacao")],
)
def test_nova_senha_invalida_e_recusada(cliente_http: TestClient, conta, nova, codigo):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/senha",
        headers=cabecalhos,
        json={"senhaAtual": SENHA, "novaSenha": nova},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == codigo


def test_conta_do_google_nao_tem_senha_para_trocar(cliente_http: TestClient, sessao):
    usuario = Usuario(nome="Conta Google", email=f"g-{uuid.uuid4().hex[:8]}@exemplo.com", senha_hash=None)
    sessao.add(usuario)
    sessao.commit()
    cabecalhos = {"Authorization": f"Bearer {criar_token(usuario.id, 'access')}"}
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/senha",
        headers=cabecalhos,
        json={"senhaAtual": "qualquer", "novaSenha": "uma-senha-nova-e-longa"},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "conta_sem_senha"


def test_sair_de_todos_os_aparelhos(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    outro, renovacao = _renovacao(cliente_http, usuario["email"])

    assert cliente_http.delete("/api/v1/usuarios/me/sessoes", headers=cabecalhos).status_code == 204

    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos).status_code == 401
    assert cliente_http.get("/api/v1/usuarios/me", headers=outro).status_code == 401
    assert cliente_http.post("/api/v1/auth/renovar", json={"refreshToken": renovacao}).status_code == 401
    # Entrar de novo funciona normalmente.
    novo, _ = _renovacao(cliente_http, usuario["email"])
    assert cliente_http.get("/api/v1/usuarios/me", headers=novo).status_code == 200


def test_token_anterior_a_versao_da_sessao_continua_valendo(cliente_http: TestClient, conta):
    """Tokens emitidos antes desta mudança não têm `sv`: a atualização não desconecta ninguém."""
    import jwt

    _, usuario = conta()
    config = modulo_config.obter_config()
    agora = datetime.now(UTC)
    antigo = jwt.encode(
        {
            "sub": usuario["id"],
            "tipo": "access",
            "iat": int(agora.timestamp()),
            "exp": int((agora + timedelta(minutes=5)).timestamp()),
            "jti": uuid.uuid4().hex,
        },
        config.jwt_secret,
        algorithm="HS256",
    )
    resposta = cliente_http.get("/api/v1/usuarios/me", headers={"Authorization": f"Bearer {antigo}"})
    assert resposta.status_code == 200


def test_troca_de_senha_tem_freio_de_tentativas(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    for _ in range(protecoes.MAX_TENTATIVAS):
        cliente_http.post(
            "/api/v1/usuarios/me/senha",
            headers=cabecalhos,
            json={"senhaAtual": "chute-errado", "novaSenha": "uma-senha-nova-e-longa"},
        )
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/senha",
        headers=cabecalhos,
        json={"senhaAtual": SENHA, "novaSenha": "uma-senha-nova-e-longa"},
    )
    assert resposta.status_code == 429


# --- Freio de tentativas: memória limitada -----------------------------------------


def test_freio_de_tentativas_nao_guarda_origens_para_sempre(cliente_http: TestClient, monkeypatch):
    monkeypatch.setattr(protecoes, "MAX_ORIGENS_GUARDADAS", 5)
    antigo = -protecoes.JANELA_S * 2
    for indice in range(50):
        protecoes._tentativas[f"10.0.0.{indice}"].append(antigo)

    cliente_http.post("/api/v1/auth/login", json={"email": "x@exemplo.com", "senha": "errada"})

    assert len(protecoes._tentativas) <= 5


def test_login_correto_nao_deixa_registro_em_memoria(cliente_http: TestClient, conta):
    _, usuario = conta()
    protecoes.limpar_tentativas()
    cliente_http.post("/api/v1/auth/login", json={"email": usuario["email"], "senha": SENHA})
    assert len(protecoes._tentativas) == 0


# --- Storage fora do ar ------------------------------------------------------------


class _StorageForaDoAr:
    def __getattr__(self, _nome):
        from app.services.storage import ErroDeArmazenamento

        def falhar(*_args, **_kwargs):
            raise ErroDeArmazenamento("S3 indisponível ao apagar: EndpointConnectionError")

        return falhar


def test_storage_fora_do_ar_responde_503_e_nao_apaga_o_registro(
    cliente_http: TestClient, conta, monkeypatch
):
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves"}
    ).json()
    monkeypatch.setattr("app.services.clientes.obter_armazenamento", lambda: _StorageForaDoAr())

    resposta = cliente_http.delete(f"/api/v1/clientes/{cliente['id']}", headers=cabecalhos)

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "armazenamento_indisponivel"
    monkeypatch.undo()
    assert cliente_http.get(f"/api/v1/clientes/{cliente['id']}", headers=cabecalhos).status_code == 200


def test_driver_s3_nao_ignora_falha_parcial_ao_apagar():
    """`delete_objects` responde 200 com a lista de falhas no corpo."""
    from app.services.storage import ErroDeArmazenamento
    from app.services.storage.s3 import ArmazenamentoS3

    class Paginador:
        def paginate(self, **_kwargs):
            return [{"Contents": [{"Key": "usuarios/u/clientes/c/a.jpg"}]}]

    class ClienteS3:
        def get_paginator(self, _nome):
            return Paginador()

        def delete_objects(self, **_kwargs):
            return {"Errors": [{"Key": "usuarios/u/clientes/c/a.jpg", "Code": "AccessDenied"}]}

    driver = ArmazenamentoS3.__new__(ArmazenamentoS3)
    driver.bucket = "espelho"
    driver.cliente = ClienteS3()
    with pytest.raises(ErroDeArmazenamento):
        driver.excluir_prefixo("usuarios/u/clientes/c/")


def test_driver_s3_traduz_falha_de_rede():
    from botocore.exceptions import EndpointConnectionError

    from app.services.storage import ErroDeArmazenamento
    from app.services.storage.s3 import ArmazenamentoS3

    class ClienteS3:
        def put_object(self, **_kwargs):
            raise EndpointConnectionError(endpoint_url="https://s3.exemplo.com")

    driver = ArmazenamentoS3.__new__(ArmazenamentoS3)
    driver.bucket = "espelho"
    driver.cliente = ClienteS3()
    with pytest.raises(ErroDeArmazenamento):
        driver.salvar("usuarios/u/a.jpg", b"x", "image/jpeg")


# --- Simulações presas ---------------------------------------------------------------


def test_simulacao_presa_por_reinicio_pode_ser_vista_e_excluida(
    cliente_http: TestClient, conta, sessao
):
    """Interrompida por um reinício, ela tinha menos de 5 minutos na inicialização e
    escapava da expiração: ficava "processando" para sempre e a exclusão dava 409."""
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves"}
    ).json()
    cliente_http.post(f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    criada = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Chanel", "cor": "Ruivo"},
        files={"foto": ("foto.jpg", retrato_valido(), "image/jpeg")},
    ).json()

    # Simula a geração interrompida há 10 minutos.
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "UPDATE simulacoes SET status = 'processando', img_saida_id = NULL, "
                "criado_em = now() - interval '10 minutes' WHERE id = :id"
            ),
            {"id": criada["id"]},
        )

    estado = cliente_http.get(f"/api/v1/simulacoes/{criada['id']}", headers=cabecalhos).json()
    assert estado["status"] == "falhou"
    assert estado["erroCodigo"] == "interrompida"
    assert cliente_http.delete(f"/api/v1/simulacoes/{criada['id']}", headers=cabecalhos).status_code == 204


def test_expiracao_por_conta_nao_mexe_nas_simulacoes_de_outra(
    cliente_http: TestClient, conta, sessao
):
    from app.services.simulacao import expirar_processando

    cabecalhos, usuario = conta()
    _, outro = conta()
    cliente = cliente_http.post("/api/v1/clientes", headers=cabecalhos, json={"nome": "Ana Lima"}).json()
    cliente_http.post(f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    criada = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Chanel", "cor": "Ruivo"},
        files={"foto": ("foto.jpg", retrato_valido(), "image/jpeg")},
    ).json()
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "UPDATE simulacoes SET status = 'processando', img_saida_id = NULL, "
                "criado_em = now() - interval '10 minutes' WHERE id = :id"
            ),
            {"id": criada["id"]},
        )

    assert expirar_processando(sessao, uuid.UUID(outro["id"])) == 0
    assert expirar_processando(sessao, uuid.UUID(usuario["id"])) == 1
    simulacao = sessao.scalar(select(Simulacao).where(Simulacao.id == uuid.UUID(criada["id"])))
    sessao.refresh(simulacao)
    assert simulacao.status is StatusSimulacao.falhou


# --- Imagens enormes recusadas sem decodificar ---------------------------------------


def test_imagem_com_lado_acima_do_limite_e_recusada_pelo_cabecalho(
    cliente_http: TestClient, conta, monkeypatch
):
    cabecalhos, _ = conta()
    buffer = io.BytesIO()
    # Poucos bytes (cor única), muitos pixels.
    Image.new("RGB", (5000, 6000), (128, 128, 128)).save(buffer, format="PNG")

    decodificou = []
    original = Image.Image.convert

    def espiao(self, *args, **kwargs):
        decodificou.append(self.size)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "convert", espiao)
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/foto",
        headers=cabecalhos,
        files={"arquivo": ("foto.png", buffer.getvalue(), "image/png")},
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["mensagem"] == "Imagem muito grande"
    assert (5000, 6000) not in decodificou, "a imagem foi decodificada inteira antes da recusa"
