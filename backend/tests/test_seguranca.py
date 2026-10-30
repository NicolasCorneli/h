"""Senhas, tokens e assinatura de imagem."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import obter_config
from app.core.security import (
    MAX_BYTES_SENHA,
    TokenInvalido,
    assinar_imagem,
    assinar_imagem_em,
    criar_token,
    gerar_hash_senha,
    ler_token,
    verificar_assinatura_imagem,
    verificar_senha,
)


def test_hash_nao_guarda_a_senha():
    hash_gerado = gerar_hash_senha("minha-senha-secreta")
    assert "minha-senha-secreta" not in hash_gerado
    assert hash_gerado.startswith("$2b$12$")  # bcrypt, custo 12
    assert verificar_senha("minha-senha-secreta", hash_gerado) is True
    assert verificar_senha("outra-senha", hash_gerado) is False


def test_hashes_do_mesmo_texto_sao_diferentes():
    assert gerar_hash_senha("igual") != gerar_hash_senha("igual")


def test_senha_longa_e_recusada_em_vez_de_truncada():
    with pytest.raises(ValueError):
        gerar_hash_senha("a" * (MAX_BYTES_SENHA + 1))


def test_hash_corrompido_nao_autentica():
    assert verificar_senha("qualquer", "nao-e-um-hash") is False


def test_token_de_acesso_e_lido():
    identificador = uuid.uuid4()
    assert ler_token(criar_token(identificador, "access"), "access") == identificador


def test_refresh_nao_vale_como_acesso():
    token = criar_token(uuid.uuid4(), "refresh")
    with pytest.raises(TokenInvalido):
        ler_token(token, "access")


def test_token_assinado_com_outro_segredo_e_recusado():
    forjado = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "tipo": "access",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        "outro-segredo-qualquer",
        algorithm="HS256",
    )
    with pytest.raises(TokenInvalido):
        ler_token(forjado, "access")


def test_token_expirado_e_recusado():
    config = obter_config()
    expirado = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "tipo": "access",
            "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        },
        config.jwt_secret,
        algorithm=config.jwt_algoritmo,
    )
    with pytest.raises(TokenInvalido):
        ler_token(expirado, "access")


def test_assinatura_de_imagem_vale_para_um_par_so():
    imagem, dono, outro = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    token = assinar_imagem(imagem, dono)
    assert verificar_assinatura_imagem(token, imagem, dono) is True
    assert verificar_assinatura_imagem(token, imagem, outro) is False
    assert verificar_assinatura_imagem(token, uuid.uuid4(), dono) is False
    assert verificar_assinatura_imagem("lixo", imagem, dono) is False


def test_assinatura_expirada():
    imagem, dono = uuid.uuid4(), uuid.uuid4()
    passado = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
    token = assinar_imagem_em(imagem, dono, passado)
    assert verificar_assinatura_imagem(token, imagem, dono) is False
