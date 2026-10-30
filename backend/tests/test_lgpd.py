"""Verificação dos pontos de LGPD que o sistema afirma cumprir.

Cada teste aqui corresponde a uma afirmação da documentação. A intenção é justamente
desconfiar dela: o que vale é o comportamento observado, não o texto.

Sobre a captura de log: estes testes usam um coletor próprio em vez do `caplog` do
pytest, e cada um deles afirma primeiro que **recebeu log**. Sem essa asserção-canário o
teste passaria de graça se o log estivesse desligado — foi exatamente o que acontecia
enquanto as migrations chamavam `fileConfig` com `disable_existing_loggers` no padrão.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}

#: Dado fictício, mas do tipo que não pode aparecer em log.
NOME = "Marina Alves de Souza"
TELEFONE = "55999887766"
OBSERVACAO = "alergia a amônia, couro cabeludo sensível"
SENHA = "senha-de-teste-123"


class ColetorDeLog(logging.Handler):
    """Guarda as linhas formatadas de todos os loggers da aplicação."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.linhas: list[str] = []

    def emit(self, registro: logging.LogRecord) -> None:
        try:
            self.linhas.append(self.format(registro))
        except Exception:  # pragma: no cover - formatação de log não pode quebrar teste
            self.linhas.append(str(registro.msg))

    @property
    def texto(self) -> str:
        return "\n".join(self.linhas)


@pytest.fixture
def log_capturado() -> Iterator[ColetorDeLog]:
    coletor = ColetorDeLog()
    coletor.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
    raiz = logging.getLogger()
    nivel_anterior = raiz.level
    raiz.addHandler(coletor)
    raiz.setLevel(logging.DEBUG)
    # Os loggers da aplicação precisam estar habilitados e propagando até a raiz.
    for nome in ("app", "espelho", "app.services", "app.api"):
        logger = logging.getLogger(nome)
        logger.disabled = False
        logger.propagate = True
    try:
        yield coletor
    finally:
        raiz.removeHandler(coletor)
        raiz.setLevel(nivel_anterior)


def test_o_coletor_de_log_realmente_funciona(log_capturado: ColetorDeLog):
    """Canário do próprio instrumento.

    Se este teste falhar, nenhum dos seguintes prova coisa alguma: significa que o log
    da aplicação está desligado e os testes de vazamento estariam passando no vácuo.
    """
    logging.getLogger("app.servico_de_teste").info("linha de controle")
    assert "linha de controle" in log_capturado.texto, (
        "o coletor não recebeu log nenhum — os testes de vazamento não verificariam nada"
    )


def cliente_completo(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes",
        headers=cabecalhos,
        json={"nome": NOME, "telefone": TELEFONE, "observacoes": OBSERVACAO},
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    return cliente


def test_dados_pessoais_nao_aparecem_no_log(
    cliente_http: TestClient, conta, log_capturado: ColetorDeLog
):
    """Art. 46 e art. 6º VIII: o registro operacional não é lugar de dado pessoal."""
    cabecalhos, _ = conta()
    cliente = cliente_completo(cliente_http, cabecalhos)
    cliente_http.post(
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
    cliente_http.delete(f"/api/v1/clientes/{cliente['id']}", headers=cabecalhos)

    registrado = log_capturado.texto
    assert registrado, "o coletor não recebeu log nenhum — o teste não verificaria nada"

    for proibido, rotulo in (
        (NOME, "nome do cliente"),
        (TELEFONE, "telefone"),
        (OBSERVACAO, "observação clínica"),
    ):
        assert proibido not in registrado, f"{rotulo} apareceu no log"

    # O identificador registrado é UUID, que não revela dado pessoal por si.
    assert cliente["id"] in registrado or "cliente=" in registrado


def test_senha_nunca_aparece_no_log(cliente_http: TestClient, log_capturado: ColetorDeLog):
    email = "prof-log@exemplo.com.br"
    cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Profissional Teste", "email": email, "senha": SENHA},
    )
    cliente_http.post("/api/v1/auth/login", json={"email": email, "senha": "senha-errada-123"})

    registrado = log_capturado.texto
    assert registrado, "o coletor não recebeu log nenhum — o teste não verificaria nada"
    assert SENHA not in registrado, "a senha apareceu no log"
    assert "senha-errada-123" not in registrado


def test_conteudo_de_imagem_nao_aparece_no_log(
    cliente_http: TestClient, conta, log_capturado: ColetorDeLog
):
    """Nem a imagem, nem a sua versão em base64, nem o data URI enviado ao provedor."""
    cabecalhos, _ = conta()
    cliente = cliente_completo(cliente_http, cabecalhos)
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("retrato-da-marina.jpg", arquivo_de_foto()["foto"][1], "image/jpeg")},
    )

    registrado = log_capturado.texto
    assert registrado, "o coletor não recebeu log nenhum — o teste não verificaria nada"
    assert "data:image" not in registrado
    assert "base64" not in registrado
    assert "retrato-da-marina" not in registrado, "nome do arquivo enviado apareceu no log"
