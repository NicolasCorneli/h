"""Conferência ao vivo do enquadramento: o rosto está dentro do guia da câmera?"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from tests.fabricas import imagem_lisa, retrato_valido
from tests.test_seguranca_aplicacao import _cliente_autorizado


def conferir(cliente_http, cabecalhos, cliente_id, conteudo):
    return cliente_http.post(
        "/api/v1/simulacoes/enquadramento",
        headers=cabecalhos,
        data={"clienteId": cliente_id},
        files={"foto": ("quadro.jpg", conteudo, "image/jpeg")},
    )


def miniatura(conteudo: bytes, largura: int = 360) -> bytes:
    imagem = Image.open(io.BytesIO(conteudo))
    imagem = imagem.resize((largura, int(imagem.height * largura / imagem.width)))
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=70)
    return saida.getvalue()


def rosto_no_canto() -> bytes:
    """O mesmo retrato, pequeno e encostado no canto de um quadro maior."""
    rosto = Image.open(io.BytesIO(retrato_valido())).resize((360, 480))
    quadro = Image.new("RGB", (1080, 1440), (205, 196, 188))
    quadro.paste(rosto, (0, 0))
    saida = io.BytesIO()
    quadro.save(saida, format="JPEG", quality=90)
    return saida.getvalue()


def test_rosto_centralizado_esta_no_guia(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = _cliente_autorizado(cliente_http, cabecalhos)
    resposta = conferir(cliente_http, cabecalhos, cliente["id"], miniatura(retrato_valido()))
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"rostoNoGuia": True}


def test_sem_rosto_nao_esta_no_guia(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = _cliente_autorizado(cliente_http, cabecalhos)
    assert conferir(cliente_http, cabecalhos, cliente["id"], miniatura(imagem_lisa())).json() == {"rostoNoGuia": False}


def test_rosto_fora_do_centro_nao_esta_no_guia(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = _cliente_autorizado(cliente_http, cabecalhos)
    assert conferir(cliente_http, cabecalhos, cliente["id"], miniatura(rosto_no_canto())).json() == {"rostoNoGuia": False}


def test_arquivo_ilegivel_e_so_sem_rosto(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = _cliente_autorizado(cliente_http, cabecalhos)
    resposta = conferir(cliente_http, cabecalhos, cliente["id"], b"nao e imagem")
    assert resposta.status_code == 200 and resposta.json() == {"rostoNoGuia": False}


def test_exige_autorizacao_de_imagem_do_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    sem_termo = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Sem termo", "telefone": "1"}
    ).json()
    resposta = conferir(cliente_http, cabecalhos, sem_termo["id"], miniatura(retrato_valido()))
    assert resposta.status_code == 403


def test_cliente_de_outra_conta_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    outra, _ = conta()
    alheio = _cliente_autorizado(cliente_http, outra)
    assert conferir(cliente_http, cabecalhos, alheio["id"], miniatura(retrato_valido())).status_code == 404


def test_nao_guarda_nada_nem_gasta_a_cota(cliente_http: TestClient, conta, sessao):
    from sqlalchemy import func, select

    from app.models import Imagem, Simulacao

    cabecalhos, _ = conta()
    cliente = _cliente_autorizado(cliente_http, cabecalhos)
    for _ in range(5):
        conferir(cliente_http, cabecalhos, cliente["id"], miniatura(retrato_valido()))
    assert sessao.scalar(select(func.count()).select_from(Imagem)) == 0
    assert sessao.scalar(select(func.count()).select_from(Simulacao)) == 0
