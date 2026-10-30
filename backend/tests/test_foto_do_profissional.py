"""Foto do próprio profissional (Meus dados): enviar, trocar, remover.

A foto é uma imagem de tipo `perfil` sem cliente, guardada no storage e entregue por URL
assinada, como as fotos de cliente. Cada conta tem no máximo uma.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Imagem
from tests.conftest import SENHA
from tests.fabricas import imagem_lisa, retrato_valido


def enviar(cliente_http: TestClient, cabecalhos, conteudo: bytes | None = None):
    return cliente_http.post(
        "/api/v1/usuarios/me/foto",
        headers=cabecalhos,
        files={"arquivo": ("eu.jpg", conteudo or retrato_valido(), "image/jpeg")},
    )


def caminho(url: str) -> str:
    return url.replace("http://testserver", "")


def test_envia_e_a_foto_aparece_na_conta(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    assert usuario["fotoUri"] is None

    resposta = enviar(cliente_http, cabecalhos)
    assert resposta.status_code == 200, resposta.text
    url = resposta.json()["fotoUri"]
    assert url and "/api/v1/imagens/" in url and "t=" in url

    # A imagem abre pela URL assinada, e /me e o login devolvem a foto.
    assert cliente_http.get(caminho(url)).status_code == 200
    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos).json()["fotoUri"]
    login = cliente_http.post(
        "/api/v1/auth/login", json={"email": usuario["email"], "senha": SENHA}
    ).json()
    assert login["usuario"]["fotoUri"]


def test_trocar_mantem_uma_so_e_apaga_a_anterior(cliente_http: TestClient, conta, sessao):
    cabecalhos, usuario = conta()
    primeira = enviar(cliente_http, cabecalhos).json()["fotoUri"]
    segunda = enviar(cliente_http, cabecalhos, imagem_lisa(800, 800)).json()["fotoUri"]
    assert primeira != segunda
    fotos = sessao.scalars(
        select(Imagem).where(Imagem.usuario_id == usuario["id"], Imagem.cliente_id.is_(None))
    ).all()
    assert len(fotos) == 1
    assert cliente_http.get(caminho(primeira)).status_code == 404
    assert cliente_http.get(caminho(segunda)).status_code == 200


def test_remover(cliente_http: TestClient, conta, sessao):
    cabecalhos, usuario = conta()
    url = enviar(cliente_http, cabecalhos).json()["fotoUri"]
    resposta = cliente_http.delete("/api/v1/usuarios/me/foto", headers=cabecalhos)
    assert resposta.status_code == 200 and resposta.json()["fotoUri"] is None
    assert cliente_http.get(caminho(url)).status_code == 404
    assert sessao.scalars(select(Imagem).where(Imagem.usuario_id == usuario["id"])).all() == []
    # Remover sem foto é inofensivo.
    assert cliente_http.delete("/api/v1/usuarios/me/foto", headers=cabecalhos).status_code == 200


def test_arquivo_que_nao_e_imagem_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = enviar(cliente_http, cabecalhos, b"isto nao e uma imagem")
    assert resposta.status_code == 422


def test_exige_autenticacao(cliente_http: TestClient):
    assert enviar(cliente_http, {}).status_code == 401
    assert cliente_http.delete("/api/v1/usuarios/me/foto").status_code == 401


def test_foto_de_um_nao_aparece_para_outro(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    enviar(cliente_http, cabecalhos_a)
    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos_b).json()["fotoUri"] is None


def test_apagar_imagens_dos_clientes_preserva_a_foto_do_profissional(cliente_http: TestClient, conta):
    """A exclusão da Privacidade é das imagens dos clientes (LGPD), não da foto da conta."""
    cabecalhos, _ = conta()
    url = enviar(cliente_http, cabecalhos).json()["fotoUri"]
    assert cliente_http.delete("/api/v1/usuarios/me/imagens", headers=cabecalhos).status_code == 204
    assert cliente_http.get(caminho(url)).status_code == 200


def test_excluir_a_conta_apaga_a_foto(cliente_http: TestClient, conta, sessao):
    cabecalhos, usuario = conta()
    enviar(cliente_http, cabecalhos)
    resposta = cliente_http.request("DELETE", "/api/v1/usuarios/me", headers=cabecalhos, json={"senha": SENHA})
    assert resposta.status_code == 204
    assert sessao.scalars(select(Imagem).where(Imagem.usuario_id == usuario["id"])).all() == []


def test_banco_impede_duas_fotos_do_profissional(cliente_http: TestClient, conta, sessao):
    from sqlalchemy.exc import IntegrityError

    from app.models import TipoImagem

    cabecalhos, usuario = conta()
    enviar(cliente_http, cabecalhos)
    sessao.add(
        Imagem(
            usuario_id=usuario["id"],
            cliente_id=None,
            tipo=TipoImagem.perfil,
            chave_objeto="usuarios/x/perfil-duplicada.jpg",
            mime="image/jpeg",
            bytes=1,
            largura=1,
            altura=1,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.commit()
    sessao.rollback()
