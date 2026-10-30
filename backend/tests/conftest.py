"""Infraestrutura dos testes.

O banco de testes é um PostgreSQL de verdade (`espelho_test`, ou o de
`TEST_DATABASE_URL`, cujo nome precisa terminar em `_test`), criado pelas **mesmas
migrations** da aplicação — inclusive os gatilhos de imutabilidade, que são parte da
regra de negócio e precisam ser exercitados. Entre os testes as tabelas são truncadas,
menos `termos`, que é dado de sistema vindo da migration.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parents[1]

#: A suíte desfaz todas as migrations (`downgrade base`) e trunca as tabelas. Por isso o
#: banco vem de uma variável só dos testes, e nunca do `DATABASE_URL` herdado do terminal:
#: antes, com `DATABASE_URL` exportado apontando para o banco de desenvolvimento (ou de
#: produção), rodar o pytest apagava o banco inteiro.
URL_TESTE = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://espelho:espelho@localhost:5432/espelho_test"
)
if not (make_url(URL_TESTE).database or "").endswith("_test"):
    raise pytest.UsageError(
        "TEST_DATABASE_URL precisa apontar para um banco cujo nome termine em '_test': a "
        f"suíte apaga todas as tabelas dele. Recebido: {make_url(URL_TESTE).database!r}."
    )
os.environ["DATABASE_URL"] = URL_TESTE
os.environ["JWT_SECRET"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["AI_PROVIDER"] = "fake"
os.environ["STORAGE_DRIVER"] = "local"
os.environ["STORAGE_DIR"] = str(RAIZ / "dados" / "testes")
os.environ["MODO_DEMO"] = "true"
os.environ["AMBIENTE"] = "teste"
# O padrão de produção é 3 por hora; os testes que geram várias simulações não testam o
# teto. Os que testam o teto baixam o valor por conta própria.
os.environ.setdefault("SIMULACAO_MAX_POR_HORA", "20")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.protecoes import limpar_tentativas  # noqa: E402
from app.services.ai.replicate import limpar_cache_de_esquemas  # noqa: E402
from app.core.security import gerar_hash_senha  # noqa: E402
from app.db.session import FabricaSessao, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Cliente, Usuario  # noqa: E402

TABELAS_VOLATEIS = (
    "atendimentos",
    "agendamentos",
    "simulacoes",
    "imagens",
    "consentimentos",
    "ciencias",
    "clientes",
    "identidades_externas",
    "usuarios",
)


@pytest.fixture(scope="session", autouse=True)
def banco_migrado() -> Iterator[None]:
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    command.downgrade(configuracao, "base")
    command.upgrade(configuracao, "head")
    yield


@pytest.fixture(autouse=True)
def limpar_tabelas() -> Iterator[None]:
    limpar_tentativas()
    # Cada teste monta o próprio provedor de mentira; o schema guardado não atravessa.
    limpar_cache_de_esquemas()
    _limpar_storage()
    yield
    with engine.begin() as conexao:
        # TRUNCATE não dispara os gatilhos de imutabilidade — é limpeza de teste, não
        # exclusão de dados do domínio.
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS_VOLATEIS)} CASCADE"))
    # O banco é truncado, mas os objetos ficavam no disco entre os testes. Sem esta
    # limpeza, um teste que afirma "não sobrou arquivo" encontra os arquivos dos testes
    # anteriores e não consegue distinguir herança de vazamento.
    _limpar_storage()


def _limpar_storage() -> None:
    import shutil

    pasta = Path(os.environ["STORAGE_DIR"])
    if pasta.exists():
        shutil.rmtree(pasta, ignore_errors=True)


@pytest.fixture
def sessao() -> Iterator[Session]:
    with FabricaSessao() as s:
        yield s


@pytest.fixture
def versao_vigente():
    """Versão vigente de um tipo de termo, lida do banco.

    Os testes não devem fixar "1.0" no código: publicar uma versão nova do termo é parte
    prevista do sistema, e um teste que quebra por isso estaria medindo o calendário, não
    o comportamento.
    """

    def consultar(tipo: str = "cliente") -> str:
        with engine.begin() as conexao:
            return conexao.execute(
                text("SELECT versao FROM termos WHERE tipo = :tipo AND vigente = true"),
                {"tipo": tipo},
            ).scalar_one()

    return consultar


@pytest.fixture
def cliente_http() -> Iterator[TestClient]:
    with TestClient(app, base_url="http://testserver") as c:
        yield c


SENHA = "senha-de-teste-123"


@pytest.fixture
def conta(cliente_http: TestClient):
    """Cria uma conta e devolve `(cabecalhos, usuario)`."""

    def criar(email: str | None = None):
        email = email or f"prof-{uuid.uuid4().hex[:8]}@exemplo.com.br"
        resposta = cliente_http.post(
            "/api/v1/auth/registrar",
            json={"nome": "Profissional Teste", "email": email, "senha": SENHA},
        )
        assert resposta.status_code == 201, resposta.text
        corpo = resposta.json()
        return (
            {"Authorization": f"Bearer {corpo['tokens']['accessToken']}"},
            corpo["usuario"],
        )

    return criar


@pytest.fixture
def usuario_direto(sessao: Session):
    """Usuário inserido direto no banco, para testes de regra que não passam pela API."""

    def criar(email: str | None = None) -> Usuario:
        usuario = Usuario(
            nome="Profissional",
            email=email or f"u-{uuid.uuid4().hex[:8]}@exemplo.com.br",
            senha_hash=gerar_hash_senha(SENHA),
            atuacao="autônomo",
        )
        sessao.add(usuario)
        sessao.commit()
        sessao.refresh(usuario)
        return usuario

    return criar


@pytest.fixture
def cliente_direto(sessao: Session):
    def criar(usuario: Usuario, nome: str = "Cliente Teste", nascimento=None) -> Cliente:
        registro = Cliente(
            usuario_id=usuario.id,
            nome=nome,
            telefone="(55) 90000-0000",
            observacoes="",
            data_nascimento=nascimento,
        )
        sessao.add(registro)
        sessao.commit()
        sessao.refresh(registro)
        return registro

    return criar
