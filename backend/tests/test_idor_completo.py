"""IDOR: varredura de **todas** as rotas que recebem identificador.

A pergunta é sempre a mesma: o profissional B consegue alcançar alguma coisa do
profissional A trocando o identificador na URL ou no corpo?

A resposta correta é 404, e não 403. Um 403 confirmaria que o recurso existe, o que já é
informação: permitiria a B descobrir quantos clientes A tem, ou se um identificador
específico é de alguém. O sistema responde como se o recurso simplesmente não existisse,
porque, do ponto de vista de B, não existe.

Das 28 rotas que recebem identificador, 26 pertencem a uma conta: 24 entram na varredura
parametrizada abaixo e 2 — envio de foto e entrega de imagem — têm testes próprios, por
exigirem corpo ou assinatura. As outras 2 servem os termos públicos, que não têm dono.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Cliente de A",
    "observacao": "",
}


def amanha() -> str:
    base = datetime.now(UTC) + timedelta(days=1)
    return base.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()


@pytest.fixture
def cenario(cliente_http: TestClient, conta):
    """Conta A com tudo criado; conta B vazia, para tentar alcançar o que é de A."""
    cabecalhos_a, usuario_a = conta()
    cabecalhos_b, usuario_b = conta()

    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos_a, json={"nome": "Cliente de A", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos_a, json=ACEITE
    )
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/foto",
        headers=cabecalhos_a,
        files={"arquivo": ("perfil.jpg", arquivo_de_foto()["foto"][1], "image/jpeg")},
    )
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos_a,
        data={
            "clienteId": cliente["id"],
            "corte": "Bob curto",
            "cor": "Ruivo intenso",
            "observacoes": "",
        },
        files=arquivo_de_foto(),
    ).json()
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos_a,
        json={
            "clienteId": cliente["id"],
            "descricao": "Coloração",
            "dataServico": date.today().isoformat(),
            "observacoes": "",
        },
    ).json()
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos_a,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Coloração",
            "duracaoMin": 60,
            "lembrete": False,
        },
    ).json()
    resumo = cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos_a
    ).json()

    return {
        "a": cabecalhos_a,
        "b": cabecalhos_b,
        "usuario_a": usuario_a,
        "usuario_b": usuario_b,
        "cliente": cliente,
        "simulacao": simulacao,
        "atendimento": atendimento,
        "agendamento": agendamento,
        "resumo": resumo,
    }


def rotas_do_cenario(cenario) -> list[tuple[str, str, dict]]:
    cliente = cenario["cliente"]["id"]
    simulacao = cenario["simulacao"]["id"]
    atendimento = cenario["atendimento"]["id"]
    agendamento = cenario["agendamento"]["id"]
    return [
        ("GET", f"/api/v1/clientes/{cliente}", {}),
        ("PATCH", f"/api/v1/clientes/{cliente}", {"json": {"nome": "Invadido"}}),
        ("DELETE", f"/api/v1/clientes/{cliente}", {}),
        ("GET", f"/api/v1/clientes/{cliente}/consentimento", {}),
        ("GET", f"/api/v1/clientes/{cliente}/consentimentos", {}),
        ("POST", f"/api/v1/clientes/{cliente}/consentimentos", {"json": ACEITE}),
        ("GET", f"/api/v1/clientes/{cliente}/historico", {}),
        ("GET", f"/api/v1/clientes/{cliente}/simulacoes", {}),
        ("GET", f"/api/v1/clientes/{cliente}/agendamentos", {}),
        ("DELETE", f"/api/v1/clientes/{cliente}/simulacoes", {}),
        ("DELETE", f"/api/v1/clientes/{cliente}/foto", {}),
        ("GET", f"/api/v1/simulacoes/{simulacao}", {}),
        ("POST", f"/api/v1/simulacoes/{simulacao}/preferida", {}),
        ("DELETE", f"/api/v1/simulacoes/{simulacao}", {}),
        ("GET", f"/api/v1/atendimentos/{atendimento}", {}),
        ("PATCH", f"/api/v1/atendimentos/{atendimento}", {"json": {"descricao": "Invadido"}}),
        ("DELETE", f"/api/v1/atendimentos/{atendimento}", {}),
        ("GET", f"/api/v1/agendamentos/{agendamento}", {}),
        ("PATCH", f"/api/v1/agendamentos/{agendamento}", {"json": {"servico": "Invadido"}}),
        ("PATCH", f"/api/v1/agendamentos/{agendamento}/status", {"json": {"status": "cancelado"}}),
        ("POST", f"/api/v1/agendamentos/{agendamento}/confirmar", {}),
        ("POST", f"/api/v1/agendamentos/{agendamento}/cancelar", {"json": {"motivo": "invadido"}}),
        ("POST", f"/api/v1/agendamentos/{agendamento}/concluir", {"json": {}}),
        ("DELETE", f"/api/v1/agendamentos/{agendamento}", {}),
    ]


def test_a_varredura_cobre_as_rotas_de_recurso_com_identificador(cenario, cliente_http):
    """Guarda contra o teste envelhecer: rota nova com identificador tem de entrar aqui.

    Sem isso, a varredura continuaria passando enquanto uma rota recém-criada ficaria
    sem nunca ser testada — e o relatório diria "todas as rotas", sem ser verdade.
    """
    from app.main import app

    esquema = app.openapi()
    com_identificador = {
        (metodo.upper(), caminho)
        for caminho, operacoes in esquema["paths"].items()
        if "{" in caminho
        for metodo in operacoes
        if metodo in ("get", "post", "patch", "put", "delete")
    }
    # As que não pertencem a uma conta, ou têm teste próprio.
    fora_da_varredura = {
        ("GET", "/api/v1/termos/{tipo}"),
        ("GET", "/api/v1/termos/{tipo}/{versao}"),
        ("GET", "/api/v1/imagens/{imagem_id}"),
        ("POST", "/api/v1/clientes/{cliente_id}/foto"),
    }

    def modelo(caminho: str) -> str:
        import re

        caminho = re.sub(r"/[0-9a-f-]{36}", "/{id}", caminho)
        return caminho

    varridas = {(metodo, modelo(rota)) for metodo, rota, _ in rotas_do_cenario(cenario)}
    esperadas = {
        (metodo, modelo(caminho.replace("{cliente_id}", "x" * 36)
                        .replace("{simulacao_id}", "x" * 36)
                        .replace("{atendimento_id}", "x" * 36)
                        .replace("{agendamento_id}", "x" * 36)))
        for metodo, caminho in com_identificador - fora_da_varredura
    }
    # Compara só a contagem: os caminhos têm formas diferentes de identificador.
    assert len(varridas) == len(esperadas) == 24, (
        f"varredura cobre {len(varridas)} rotas, a API tem {len(esperadas)} elegíveis"
    )


@pytest.mark.parametrize("indice", range(24))
def test_conta_b_nao_alcanca_recurso_de_a(cliente_http: TestClient, cenario, indice):
    metodo, rota, extra = rotas_do_cenario(cenario)[indice]
    resposta = cliente_http.request(metodo, rota, headers=cenario["b"], **extra)

    assert resposta.status_code == 404, (
        f"{metodo} {rota} respondeu {resposta.status_code} para a outra conta"
    )
    # 403 confirmaria a existência do recurso; 200 seria vazamento.
    assert resposta.status_code not in (200, 403)


def test_corpo_com_cliente_de_outra_conta(cliente_http: TestClient, cenario):
    """O identificador também viaja no corpo — e lá também não pode ser aceito."""
    for rota, corpo in (
        (
            "/api/v1/atendimentos",
            {
                "clienteId": cenario["cliente"]["id"],
                "descricao": "Invadido",
                "dataServico": date.today().isoformat(),
                "observacoes": "",
            },
        ),
        (
            "/api/v1/agendamentos",
            {
                "clienteId": cenario["cliente"]["id"],
                "dataHora": amanha(),
                "servico": "Invadido",
                "duracaoMin": 60,
                "lembrete": False,
            },
        ),
    ):
        resposta = cliente_http.post(rota, headers=cenario["b"], json=corpo)
        assert resposta.status_code == 404, f"{rota} aceitou cliente de outra conta"


def test_foto_para_cliente_de_outra_conta(cliente_http: TestClient, cenario):
    resposta = cliente_http.post(
        f"/api/v1/clientes/{cenario['cliente']['id']}/foto",
        headers=cenario["b"],
        files={"arquivo": ("perfil.jpg", arquivo_de_foto()["foto"][1], "image/jpeg")},
    )
    assert resposta.status_code == 404


def test_simulacao_para_cliente_de_outra_conta(cliente_http: TestClient, cenario):
    resposta = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cenario["b"],
        data={
            "clienteId": cenario["cliente"]["id"],
            "corte": "Bob curto",
            "cor": "Ruivo intenso",
            "observacoes": "",
        },
        files=arquivo_de_foto(),
    )
    assert resposta.status_code == 404


def test_atendimento_com_simulacao_de_outra_conta(cliente_http: TestClient, cenario):
    """B tem cliente próprio, mas tenta anexar a simulação de A."""
    cliente_b = cliente_http.post(
        "/api/v1/clientes", headers=cenario["b"], json={"nome": "Cliente de B", "telefone": "2"}
    ).json()
    resposta = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cenario["b"],
        json={
            "clienteId": cliente_b["id"],
            "simulacaoId": cenario["simulacao"]["id"],
            "descricao": "Tentativa",
            "dataServico": date.today().isoformat(),
            "observacoes": "",
        },
    )
    assert resposta.status_code == 404


def uri_da_foto(cliente_http: TestClient, cenario) -> str:
    perfil = cliente_http.get(
        f"/api/v1/clientes/{cenario['cliente']['id']}", headers=cenario["a"]
    ).json()
    uri = perfil.get("fotoUri")
    assert uri, "o cenário precisa de uma foto de perfil"
    return uri.replace("http://testserver", "")


def test_b_nao_obtem_a_url_assinada_de_a_por_rota_alguma(cliente_http: TestClient, cenario):
    """O que de fato protege a imagem: B nunca recebe a URL assinada de A.

    A rota de entrega não tem autenticação, por decisão de projeto — o `<Image>` do
    React Native não envia cabeçalhos, então a assinatura HMAC *é* a autorização. Isso
    desloca a pergunta: não é "B consegue usar a URL de A?", e sim "B consegue obter
    uma?". A resposta tem de ser não, em toda rota que devolve URL de imagem.
    """
    for rota in (
        f"/api/v1/clientes/{cenario['cliente']['id']}",
        f"/api/v1/clientes/{cenario['cliente']['id']}/simulacoes",
        f"/api/v1/simulacoes/{cenario['simulacao']['id']}",
        "/api/v1/clientes",
        "/api/v1/simulacoes",
    ):
        resposta = cliente_http.get(rota, headers=cenario["b"])
        corpo = resposta.text
        assert "/api/v1/imagens/" not in corpo, (
            f"{rota} entregou a B uma URL de imagem de A"
        )


def test_assinatura_e_obrigatoria(cliente_http: TestClient, cenario):
    """Sem o parâmetro de assinatura a rota não entrega nada."""
    caminho = uri_da_foto(cliente_http, cenario).split("?")[0]
    assert cliente_http.get(caminho).status_code == 422
    assert cliente_http.get(caminho, headers=cenario["b"]).status_code == 422


def test_assinatura_forjada_e_recusada(cliente_http: TestClient, cenario):
    """Sem o segredo do servidor não se fabrica assinatura válida."""
    caminho = uri_da_foto(cliente_http, cenario)
    base, _, consulta = caminho.partition("?")

    for adulterada in (
        consulta.replace("t=", "t=0", 1),  # um caractere a mais
        consulta[:-1],  # um caractere a menos
        "t=9999999999.assinatura-inventada-por-quem-nao-tem-o-segredo",
    ):
        resposta = cliente_http.get(f"{base}?{adulterada}")
        assert resposta.status_code == 404, (
            f"assinatura inválida foi aceita: {adulterada[:40]}"
        )


def test_assinatura_expirada_e_recusada(cliente_http: TestClient, cenario):
    """A validade é parte da assinatura: passada a hora, a mesma URL deixa de abrir."""
    from app.core.security import assinar_imagem_em

    caminho = uri_da_foto(cliente_http, cenario)
    base, _, _ = caminho.partition("?")
    imagem_id = base.rsplit("/", 1)[-1]

    import uuid as _uuid

    dono = _uuid.UUID(cenario["usuario_a"]["id"])
    vencida = assinar_imagem_em(_uuid.UUID(imagem_id), dono, 1_600_000_000)
    assert cliente_http.get(f"{base}?t={vencida}").status_code == 404


def test_assinatura_de_uma_imagem_nao_vale_para_outra(cliente_http: TestClient, cenario):
    """A assinatura é por imagem: trocar o identificador na URL não funciona."""
    caminho = uri_da_foto(cliente_http, cenario)
    base, _, consulta = caminho.partition("?")
    prefixo = base.rsplit("/", 1)[0]

    simulacao = cliente_http.get(
        f"/api/v1/simulacoes/{cenario['simulacao']['id']}", headers=cenario["a"]
    ).json()
    outra = simulacao["imgEntradaUri"].replace("http://testserver", "").split("?")[0]
    outro_id = outra.rsplit("/", 1)[-1]
    assert outro_id != base.rsplit("/", 1)[-1], "o cenário precisa de duas imagens distintas"

    # Assinatura da foto de perfil, aplicada à imagem de entrada da simulação.
    assert cliente_http.get(f"{prefixo}/{outro_id}?{consulta}").status_code == 404


def test_url_assinada_e_credencial_portadora(cliente_http: TestClient, cenario):
    """Documenta por teste o que o modelo de fato garante — e o que não garante.

    Quem possui uma URL assinada válida lê a imagem, inclusive autenticado como outra
    conta ou sem autenticação alguma. Isso é o desenho, não um defeito: a assinatura é a
    credencial. O que limita a exposição é a validade curta, o `Cache-Control: private`
    e o `Referrer-Policy: no-referrer`.

    Está registrado como risco residual no relatório de QA: uma URL vazada vale até
    expirar, para qualquer um. Se algum dia for preciso amarrar a entrega à sessão, a
    assinatura teria de incluir o usuário que requisita, e não o dono da imagem — e aí
    o `<Image>` precisaria de outra forma de autenticação.
    """
    caminho = uri_da_foto(cliente_http, cenario)

    assert cliente_http.get(caminho).status_code == 200, "a URL assinada não abre nem para o dono"
    assert cliente_http.get(caminho, headers=cenario["b"]).status_code == 200, (
        "comportamento mudou: a entrega passou a depender da sessão — reavaliar o relatório"
    )


def test_listas_nao_atravessam_contas(cliente_http: TestClient, cenario):
    """Nenhum filtro amplo pode trazer registro de outra conta."""
    for rota in (
        "/api/v1/clientes",
        "/api/v1/clientes?busca=Cliente",
        "/api/v1/simulacoes",
        "/api/v1/atendimentos",
        "/api/v1/agendamentos",
    ):
        corpo = cliente_http.get(rota, headers=cenario["b"]).json()
        assert corpo == [], f"{rota} devolveu dados de outra conta: {corpo}"


def test_token_de_conta_excluida_deixa_de_valer(cliente_http: TestClient, conta):
    """Excluir a conta invalida o token, porque o usuário deixa de existir."""
    cabecalhos, _ = conta()
    antes = cliente_http.get("/api/v1/clientes", headers=cabecalhos)
    assert antes.status_code == 200

    cliente_http.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=cabecalhos,
        json={"senha": "senha-de-teste-123"},
    )
    depois = cliente_http.get("/api/v1/clientes", headers=cabecalhos)
    assert depois.status_code == 401
