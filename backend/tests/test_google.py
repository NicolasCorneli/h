"""Entrar com Google: verificação do token no servidor e vínculo seguro de contas.

Nenhuma credencial real é usada. O teste gera um par de chaves RSA e um certificado, assina
os tokens com a chave privada e entrega o certificado à biblioteca oficial (`google-auth`)
no lugar do endereço de chaves do Google. Tudo o mais é a verificação de verdade:
assinatura, validade, emissor e público. Um token assinado por outra chave, vencido, de
outro emissor ou emitido para outro aplicativo é recusado pela mesma rotina que roda em
produção.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt
from google.auth import exceptions as erros_google
from google.auth import jwt as jwt_google

from app.core import config as modulo_config
from app.services import google as modulo_google
from tests.conftest import SENHA

CLIENTE_WEB = "123-web.apps.googleusercontent.com"
CLIENTE_ANDROID = "123-android.apps.googleusercontent.com"
KID = "chave-de-teste"


def _par_de_chaves() -> tuple[bytes, bytes]:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "teste")])
    agora = datetime.now(UTC)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=1))
        .sign(chave, hashes.SHA256())
    )
    privada = chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return privada, certificado.public_bytes(serialization.Encoding.PEM)


PRIVADA, CERTIFICADO = _par_de_chaves()
PRIVADA_INTRUSA, _ = _par_de_chaves()


class _Resposta:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self, corpo: dict) -> None:
        self.data = json.dumps(corpo).encode()


def _requisicao_falsa(url, method="GET", **_):
    # Única substituição: em vez de buscar as chaves no Google, entrega o certificado
    # gerado aqui, no mesmo formato do endereço oficial (kid -> certificado PEM).
    assert "googleapis.com" in url
    return _Resposta({KID: CERTIFICADO.decode()})


@pytest.fixture(autouse=True)
def google_configurado(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_IDS", f"{CLIENTE_WEB}, {CLIENTE_ANDROID}")
    modulo_config.obter_config.cache_clear()
    monkeypatch.setattr(modulo_google, "_requisicao", lambda: _requisicao_falsa)
    yield
    modulo_config.obter_config.cache_clear()


def token(
    *,
    sub: str | None = None,
    email: str = "ana@gmail.com",
    verificado: bool | str = True,
    aud: str = CLIENTE_WEB,
    iss: str = "https://accounts.google.com",
    expira_em: int = 3600,
    chave: bytes = PRIVADA,
    nome: str = "Ana Souza",
    nonce: str | None = None,
) -> str:
    agora = int(time.time())
    carga = {
        "iss": iss,
        "aud": aud,
        "sub": sub or str(uuid.uuid4().int)[:21],
        "email": email,
        "email_verified": verificado,
        "name": nome,
        "iat": agora - 10,
        "exp": agora + expira_em,
    }
    if nonce is not None:
        carga["nonce"] = nonce
    assinador = crypt.RSASigner.from_string(chave, key_id=KID)
    return jwt_google.encode(assinador, carga).decode()


def entrar(cliente_http, id_token: str, **extra):
    return cliente_http.post("/api/v1/auth/google", json={"idToken": id_token, **extra})


# --- configuração ------------------------------------------------------------


def test_provedores_informa_se_o_google_esta_ligado(cliente_http, monkeypatch):
    assert cliente_http.get("/api/v1/auth/provedores").json() == {"google": True}
    monkeypatch.setenv("GOOGLE_CLIENT_IDS", "")
    modulo_config.obter_config.cache_clear()
    assert cliente_http.get("/api/v1/auth/provedores").json() == {"google": False}


def test_sem_configuracao_a_rota_responde_indisponivel(cliente_http, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_IDS", "")
    modulo_config.obter_config.cache_clear()
    resposta = entrar(cliente_http, token())
    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "google_nao_configurado"


# --- primeiro acesso e login -------------------------------------------------


def test_primeiro_acesso_cria_conta_sem_senha(cliente_http):
    resposta = entrar(cliente_http, token(sub="111", email="Ana@Gmail.com"))
    assert resposta.status_code == 200, resposta.text
    usuario = resposta.json()["usuario"]
    assert usuario["email"] == "ana@gmail.com"
    assert usuario["nome"] == "Ana Souza"
    assert usuario["temSenha"] is False
    assert usuario["googleVinculado"] is True

    acesso = resposta.json()["tokens"]["accessToken"]
    eu = cliente_http.get("/api/v1/usuarios/me", headers={"Authorization": f"Bearer {acesso}"})
    assert eu.status_code == 200 and eu.json()["id"] == usuario["id"]


def test_segundo_acesso_entra_na_mesma_conta_sem_duplicar(cliente_http, sessao):
    primeiro = entrar(cliente_http, token(sub="222")).json()["usuario"]["id"]
    segundo = entrar(cliente_http, token(sub="222")).json()["usuario"]["id"]
    assert primeiro == segundo
    from app.models import IdentidadeExterna, Usuario

    assert sessao.query(Usuario).count() == 1
    assert sessao.query(IdentidadeExterna).count() == 1


def test_a_conta_e_achada_pelo_sub_e_nao_pelo_email(cliente_http):
    """Quem troca o e-mail no Google continua entrando na mesma conta."""
    antes = entrar(cliente_http, token(sub="333", email="velho@gmail.com")).json()["usuario"]
    depois = entrar(cliente_http, token(sub="333", email="novo@gmail.com")).json()["usuario"]
    assert antes["id"] == depois["id"]


def test_conta_sem_senha_nao_entra_pelo_login_de_senha(cliente_http):
    entrar(cliente_http, token(sub="444", email="semsenha@gmail.com"))
    for senha in ("", "qualquer-coisa", "None"):
        resposta = cliente_http.post(
            "/api/v1/auth/login", json={"email": "semsenha@gmail.com", "senha": senha or "x"}
        )
        assert resposta.status_code == 401
        assert resposta.json()["erro"]["codigo"] == "credenciais_invalidas"


# --- tokens recusados ---------------------------------------------------------


@pytest.mark.parametrize(
    ("descricao", "parametros"),
    [
        ("assinado por outra chave", {"chave": PRIVADA_INTRUSA}),
        ("vencido", {"expira_em": -3600}),
        ("emitido para outro aplicativo", {"aud": "outro-app.apps.googleusercontent.com"}),
        ("de outro emissor", {"iss": "https://falso.example.com"}),
    ],
)
def test_token_invalido_e_recusado(cliente_http, sessao, descricao, parametros):
    resposta = entrar(cliente_http, token(**parametros))
    assert resposta.status_code == 401, descricao
    assert resposta.json()["erro"]["codigo"] == "google_token_invalido"
    from app.models import Usuario

    assert sessao.query(Usuario).count() == 0, f"{descricao}: nenhuma conta pode ser criada"


def test_token_adulterado_e_recusado(cliente_http):
    cabeca, carga, assinatura = token().split(".")
    import base64

    dados = json.loads(base64.urlsafe_b64decode(carga + "=="))
    dados["email"] = "outra.pessoa@gmail.com"
    carga_falsa = base64.urlsafe_b64encode(json.dumps(dados).encode()).decode().rstrip("=")
    resposta = entrar(cliente_http, f"{cabeca}.{carga_falsa}.{assinatura}")
    assert resposta.status_code == 401


def test_token_de_outro_cliente_configurado_e_aceito(cliente_http):
    """O aplicativo Android tem ID de cliente próprio; também é deste aplicativo."""
    assert entrar(cliente_http, token(aud=CLIENTE_ANDROID)).status_code == 200


def test_email_nao_verificado_e_recusado(cliente_http):
    resposta = entrar(cliente_http, token(verificado=False))
    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "google_email_nao_verificado"


def test_nonce_diferente_do_pedido_e_recusado(cliente_http):
    assert entrar(cliente_http, token(nonce="abc"), nonce="abc").status_code == 200
    resposta = entrar(cliente_http, token(nonce="abc"), nonce="outro")
    assert resposta.status_code == 401


def test_falha_ao_buscar_as_chaves_responde_indisponivel(cliente_http, monkeypatch):
    def sem_rede(*_a, **_k):
        raise erros_google.TransportError("sem rede")

    monkeypatch.setattr(modulo_google, "_requisicao", lambda: sem_rede)
    resposta = entrar(cliente_http, token())
    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "google_indisponivel"


def test_o_token_nao_aparece_no_log(cliente_http, caplog):
    id_token = token(chave=PRIVADA_INTRUSA)
    with caplog.at_level("DEBUG"):
        entrar(cliente_http, id_token)
    assert id_token not in caplog.text
    assert id_token.split(".")[1] not in caplog.text


# --- contas existentes: nada de vínculo automático pelo e-mail ----------------


def test_mesmo_email_de_conta_com_senha_nao_e_vinculado_automaticamente(cliente_http, conta, sessao):
    _, usuario = conta("carla@gmail.com")
    resposta = entrar(cliente_http, token(sub="555", email="carla@gmail.com"))
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "google_email_em_uso"
    assert "tokens" not in resposta.json()
    from app.models import IdentidadeExterna, Usuario

    assert sessao.query(IdentidadeExterna).count() == 0
    assert sessao.query(Usuario).count() == 1


def test_conta_com_senha_liga_o_google_pelo_perfil(cliente_http, conta):
    cabecalhos, usuario = conta("bia@gmail.com")
    ligado = cliente_http.post(
        "/api/v1/usuarios/me/google", json={"idToken": token(sub="666", email="bia@gmail.com")},
        headers=cabecalhos,
    )
    assert ligado.status_code == 200, ligado.text
    assert ligado.json()["googleVinculado"] is True
    assert ligado.json()["temSenha"] is True

    # Daí em diante, o Google entra na mesma conta; a senha continua valendo.
    pelo_google = entrar(cliente_http, token(sub="666", email="bia@gmail.com")).json()
    assert pelo_google["usuario"]["id"] == usuario["id"]
    pela_senha = cliente_http.post("/api/v1/auth/login", json={"email": "bia@gmail.com", "senha": SENHA})
    assert pela_senha.status_code == 200


def test_ligar_exige_estar_autenticado(cliente_http):
    resposta = cliente_http.post("/api/v1/usuarios/me/google", json={"idToken": token()})
    assert resposta.status_code == 401


def test_conta_google_de_outra_pessoa_nao_pode_ser_ligada(cliente_http, conta):
    entrar(cliente_http, token(sub="777", email="dona@gmail.com"))
    cabecalhos, _ = conta("intrusa@exemplo.com.br")
    resposta = cliente_http.post(
        "/api/v1/usuarios/me/google", json={"idToken": token(sub="777", email="dona@gmail.com")},
        headers=cabecalhos,
    )
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "google_ja_vinculado"


def test_uma_conta_tem_no_maximo_uma_conta_google(cliente_http, conta):
    cabecalhos, _ = conta()
    primeira = cliente_http.post(
        "/api/v1/usuarios/me/google", json={"idToken": token(sub="801")}, headers=cabecalhos
    )
    assert primeira.status_code == 200
    segunda = cliente_http.post(
        "/api/v1/usuarios/me/google", json={"idToken": token(sub="802")}, headers=cabecalhos
    )
    assert segunda.status_code == 409
    assert segunda.json()["erro"]["codigo"] == "google_outra_conta"
    # Repetir a mesma é inofensivo.
    repetida = cliente_http.post(
        "/api/v1/usuarios/me/google", json={"idToken": token(sub="801")}, headers=cabecalhos
    )
    assert repetida.status_code == 200


def test_banco_impede_a_mesma_conta_google_em_duas_contas(sessao, conta):
    from sqlalchemy.exc import IntegrityError

    from app.models import IdentidadeExterna

    _, u1 = conta()
    _, u2 = conta()
    sessao.add(IdentidadeExterna(usuario_id=u1["id"], provedor="google", sujeito="9", email="a@b.c"))
    sessao.commit()
    sessao.add(IdentidadeExterna(usuario_id=u2["id"], provedor="google", sujeito="9", email="a@b.c"))
    with pytest.raises(IntegrityError):
        sessao.commit()
    sessao.rollback()


def test_desconectar_so_quando_ha_senha(cliente_http, conta):
    cabecalhos, _ = conta()
    cliente_http.post("/api/v1/usuarios/me/google", json={"idToken": token(sub="901")}, headers=cabecalhos)
    resposta = cliente_http.delete("/api/v1/usuarios/me/google", headers=cabecalhos)
    assert resposta.status_code == 200 and resposta.json()["googleVinculado"] is False

    so_google = entrar(cliente_http, token(sub="902")).json()
    acesso = {"Authorization": f"Bearer {so_google['tokens']['accessToken']}"}
    recusa = cliente_http.delete("/api/v1/usuarios/me/google", headers=acesso)
    assert recusa.status_code == 422
    assert recusa.json()["erro"]["codigo"] == "google_unica_forma_de_entrar"


# --- exclusão de conta sem senha ----------------------------------------------


def test_conta_sem_senha_exclui_confirmando_com_o_google(cliente_http, sessao):
    criada = entrar(cliente_http, token(sub="1001")).json()
    acesso = {"Authorization": f"Bearer {criada['tokens']['accessToken']}"}

    sem_confirmacao = cliente_http.request("DELETE", "/api/v1/usuarios/me", json={}, headers=acesso)
    assert sem_confirmacao.status_code == 403

    outra_conta = cliente_http.request(
        "DELETE", "/api/v1/usuarios/me", json={"idTokenGoogle": token(sub="9999")}, headers=acesso
    )
    assert outra_conta.status_code == 403

    certa = cliente_http.request(
        "DELETE", "/api/v1/usuarios/me", json={"idTokenGoogle": token(sub="1001")}, headers=acesso
    )
    assert certa.status_code == 204
    from app.models import IdentidadeExterna, Usuario

    assert sessao.query(Usuario).count() == 0
    assert sessao.query(IdentidadeExterna).count() == 0


def test_conta_com_senha_continua_exigindo_a_senha_para_excluir(cliente_http, conta):
    cabecalhos, _ = conta()
    cliente_http.post("/api/v1/usuarios/me/google", json={"idToken": token(sub="1101")}, headers=cabecalhos)
    so_google = cliente_http.request(
        "DELETE", "/api/v1/usuarios/me", json={"idTokenGoogle": token(sub="1101")}, headers=cabecalhos
    )
    assert so_google.status_code == 403
    com_senha = cliente_http.request("DELETE", "/api/v1/usuarios/me", json={"senha": SENHA}, headers=cabecalhos)
    assert com_senha.status_code == 204


def test_tentativas_seguidas_no_google_sao_freadas(cliente_http):
    codigos = [entrar(cliente_http, token(chave=PRIVADA_INTRUSA)).status_code for _ in range(12)]
    assert 429 in codigos


# --- migration ------------------------------------------------------------------


def test_volta_da_migration_recusa_apagar_contas_sem_senha(cliente_http):
    """Desfazer a migration exigiria senha em todas as contas. Com conta criada pelo
    Google, a volta se recusa e o banco fica como estava, em vez de apagar a conta."""
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    entrar(cliente_http, token(sub="5001", email="semsenha@gmail.com"))
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    with pytest.raises(RuntimeError, match="sem senha"):
        command.downgrade(configuracao, "d7b2e9c41a03")
    # Continua na versão atual, com a conta intacta e entrando pelo Google.
    assert entrar(cliente_http, token(sub="5001", email="semsenha@gmail.com")).status_code == 200


def test_ida_e_volta_da_migration_sem_contas_google():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    from app.db.session import engine
    from tests.conftest import RAIZ

    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    command.downgrade(configuracao, "d7b2e9c41a03")
    assert "identidades_externas" not in inspect(engine).get_table_names()
    command.upgrade(configuracao, "head")
    assert "identidades_externas" in inspect(engine).get_table_names()


def test_saude_acusa_banco_desatualizado():
    """Código novo com migrations pendentes: o /saude diz isso em vez de só falhar depois."""
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.conftest import RAIZ

    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    with TestClient(app) as cliente:
        assert cliente.get("/api/v1/saude").json()["bancoAtualizado"] is True
        command.downgrade(configuracao, "d7b2e9c41a03")
        try:
            corpo = cliente.get("/api/v1/saude").json()
            assert corpo["bancoAtualizado"] is False
            assert corpo["ok"] is False
        finally:
            command.upgrade(configuracao, "head")
