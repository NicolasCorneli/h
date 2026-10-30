"""RF04, RF05 e RF07 — geração, estado, comparação e falhas controladas."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from tests.fabricas import arquivo_de_foto, imagem_lisa, retrato_valido

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def cliente_com_aceite(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    return cliente


def gerar(cliente_http: TestClient, cabecalhos, cliente_id, **extra):
    dados = {
        "clienteId": cliente_id,
        "corte": "Bob curto",
        "cor": "Ruivo intenso",
        "observacoes": "",
        **extra,
    }
    foto = dados.pop("foto", None)
    return cliente_http.post(
        "/api/v1/simulacoes", headers=cabecalhos, data=dados, files=arquivo_de_foto(foto)
    )


def aguardar(cliente_http: TestClient, cabecalhos, simulacao_id: str, tentativas: int = 60) -> dict:
    for _ in range(tentativas):
        estado = cliente_http.get(f"/api/v1/simulacoes/{simulacao_id}", headers=cabecalhos).json()
        if estado["status"] != "processando":
            return estado
        time.sleep(0.2)
    raise AssertionError("a simulação não saiu de processando")


def test_fluxo_completo_da_simulacao(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)

    criada = gerar(cliente_http, cabecalhos, cliente["id"])
    assert criada.status_code == 202
    corpo = criada.json()
    assert corpo["status"] == "processando"
    assert corpo["usuarioId"] == usuario["id"]
    assert corpo["imgEntradaUri"] and corpo["imgSaidaUri"] is None
    assert corpo["parametros"] == {
        "estilo": "Bob curto",
        "cor": "Ruivo intenso",
        # Envio sem o campo: vale o padrão do modelo, como antes de a opção existir.
        "genero": "none",
        "observacoes": "",
    }

    final = aguardar(cliente_http, cabecalhos, corpo["id"])
    assert final["status"] == "concluida"
    assert final["imgSaidaUri"]
    assert final["tempoMs"] >= 0
    assert final["concluidaEm"]
    assert final["provedor"] == "fake"

    imagem = cliente_http.get(final["imgSaidaUri"].replace("http://testserver", ""))
    assert imagem.status_code == 200
    assert imagem.content[:2] == b"\xff\xd8"


def test_imagem_exige_assinatura_valida(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    final = aguardar(
        cliente_http, cabecalhos, gerar(cliente_http, cabecalhos, cliente["id"]).json()["id"]
    )
    caminho = final["imgSaidaUri"].replace("http://testserver", "")
    sem_assinatura = caminho.split("?")[0]

    assert cliente_http.get(sem_assinatura).status_code == 422  # falta o parâmetro t
    assert cliente_http.get(f"{sem_assinatura}?t=assinatura.invalida").status_code == 404


def test_descricao_livre_e_aceita_e_texto_invalido_recusado(cliente_http: TestClient, conta):
    """Corte e cor deixaram de ser uma lista fechada (etapa "Estilo e cor" redesenhada).

    Antes, "Moicano fluorescente" era recusado com `estilo_invalido`. Agora é uma descrição
    válida e segue como foi escrita; o que continua recusado é o que não é descrição.
    """
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)

    livre = gerar(cliente_http, cabecalhos, cliente["id"], corte="Moicano fluorescente", cor="Verde neon")
    assert livre.status_code == 202, livre.text
    assert livre.json()["parametros"]["estilo"] == "Moicano fluorescente"
    assert livre.json()["parametros"]["cor"] == "Verde neon"

    marcacao = gerar(cliente_http, cabecalhos, cliente["id"], corte="<b>bob</b>")
    assert marcacao.status_code == 422
    assert marcacao.json()["erro"]["codigo"] == "descricao_invalida"

    longa = gerar(cliente_http, cabecalhos, cliente["id"], cor="castanho " * 40)
    assert longa.status_code == 422
    assert longa.json()["erro"]["codigo"] == "descricao_longa"


def test_foto_ruim_nao_chega_ao_provedor(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar(cliente_http, cabecalhos, cliente["id"], foto=imagem_lisa(300, 300))
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "foto_recusada"

    # Nenhuma simulação foi criada, nem mesmo com falha.
    assert cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/simulacoes", headers=cabecalhos
    ).json() == []


def test_falha_do_provedor_nao_gera_simulacao_concluida(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    criada = gerar(cliente_http, cabecalhos, cliente["id"], demoFalharIa="true")
    assert criada.status_code == 202

    final = aguardar(cliente_http, cabecalhos, criada.json()["id"])
    assert final["status"] == "falhou"
    assert final["imgSaidaUri"] is None
    assert final["erroCodigo"] == "demonstracao"


def test_demo_de_foto_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar(cliente_http, cabecalhos, cliente["id"], demoRecusarFoto="true")
    assert resposta.status_code == 422
    assert len(resposta.json()["erro"]["detalhes"]) == 2


def test_preferida_e_unica_por_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    primeira = aguardar(
        cliente_http, cabecalhos, gerar(cliente_http, cabecalhos, cliente["id"]).json()["id"]
    )
    segunda = aguardar(
        cliente_http,
        cabecalhos,
        gerar(cliente_http, cabecalhos, cliente["id"], cor="Loiro mel").json()["id"],
    )

    assert cliente_http.post(
        f"/api/v1/simulacoes/{primeira['id']}/preferida", headers=cabecalhos
    ).json()["preferida"] is True
    assert cliente_http.post(
        f"/api/v1/simulacoes/{segunda['id']}/preferida", headers=cabecalhos
    ).json()["preferida"] is True

    lista = cliente_http.get(
        "/api/v1/simulacoes", headers=cabecalhos, params={"clienteId": cliente["id"]}
    ).json()
    assert [s["id"] for s in lista if s["preferida"]] == [segunda["id"]]


def test_simulacao_em_falha_nao_pode_ser_preferida(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    falha = aguardar(
        cliente_http,
        cabecalhos,
        gerar(cliente_http, cabecalhos, cliente["id"], demoFalharIa="true").json()["id"],
    )
    resposta = cliente_http.post(f"/api/v1/simulacoes/{falha['id']}/preferida", headers=cabecalhos)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "simulacao_incompleta"


def test_catalogo_publicado(cliente_http: TestClient):
    catalogo = cliente_http.get("/api/v1/catalogo").json()
    # Os exemplos da tela "Estilo e cor": tendências e clássicos.
    assert {"Butterfly", "Long bob estruturado", "Chanel", "Pixie"} <= set(catalogo["estilos"])
    assert {"Loiro manteiga", "Vermelho bordô", "Castanho-escuro", "Ruivo"} <= set(catalogo["cores"])
    assert "Coloração" in catalogo["servicos"]


def test_simulacao_guarda_o_consentimento_que_autorizou(cliente_http: TestClient, conta, sessao):
    from app.models import Simulacao

    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    criada = gerar(cliente_http, cabecalhos, cliente["id"]).json()

    registro = cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos
    ).json()["registro"]
    guardada = sessao.get(Simulacao, criada["id"])
    assert guardada is not None
    assert str(guardada.consentimento_id) == registro["id"]


def test_foto_grande_demais_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    gigante = retrato_valido() + b"\x00" * (9 * 1024 * 1024)
    resposta = gerar(cliente_http, cabecalhos, cliente["id"], foto=gigante)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["detalhes"][0]["titulo"] == "Arquivo muito grande"


def test_preferida_vem_primeiro_e_o_resto_por_data(cliente_http: TestClient, conta):
    """A preferida abre a lista mesmo sendo a mais antiga; as demais seguem por data."""
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    ids = [
        aguardar(
            cliente_http,
            cabecalhos,
            gerar(cliente_http, cabecalhos, cliente["id"], cor=cor).json()["id"],
        )["id"]
        for cor in ("Loiro mel", "Castanho escuro", "Platinado")
    ]
    antiga, meio, nova = ids
    cliente_http.post(f"/api/v1/simulacoes/{antiga}/preferida", headers=cabecalhos)

    for rota in ("/api/v1/simulacoes", f"/api/v1/clientes/{cliente['id']}/simulacoes"):
        lista = cliente_http.get(rota, headers=cabecalhos, params={"clienteId": cliente["id"]}).json()
        assert [s["id"] for s in lista] == [antiga, nova, meio], rota
