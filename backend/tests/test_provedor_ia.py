"""Provedores de IA.

O provedor local é exercitado de verdade. O da Replicate é exercitado com HTTP simulado:
assim o código da integração real fica coberto sem chamada paga, sem credencial e sem
depender de rede — e o que não foi executado contra o serviço real está dito na
documentação, não escondido aqui.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx
import pytest
from PIL import Image

from app.core import config as modulo_config
from app.services.ai import obter_provedor
from app.services.ai.base import EntradaSimulacao, FalhaDoProvedor
from app.services.ai.fake import ProvedorLocal
from app.services.ai.pedido import interpretar
from tests import mock_provedor_ia
from tests.fabricas import retrato_valido

MODELO = "flux-kontext-apps/change-haircut"


def entrada() -> EntradaSimulacao:
    # "Chanel" e "Ruivo" são exemplos do catálogo com equivalente nas opções do modelo
    # principal: o pedido vai ao change-haircut.
    return EntradaSimulacao(
        imagem=retrato_valido(), mime="image/jpeg", pedido=interpretar("Chanel", "Ruivo")
    )


def resposta_do_schema(requisicao: httpx.Request) -> httpx.Response | None:
    """Responde à consulta do schema (`GET /v1/models/dono/nome`) como a Replicate."""
    partes = requisicao.url.path.strip("/").split("/")
    if requisicao.method == "GET" and len(partes) == 4 and partes[1] == "models":
        modelo = f"{partes[2]}/{partes[3]}"
        return httpx.Response(
            200,
            json={
                "latest_version": {
                    "id": "v1",
                    "openapi_schema": mock_provedor_ia._schema_do_modelo(modelo),
                }
            },
        )
    return None


def jpeg_de_teste() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), (120, 60, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


# --- Provedor local -------------------------------------------------------


def test_provedor_local_gera_imagem_valida():
    resultado = ProvedorLocal().gerar(entrada())
    assert resultado.mime == "image/jpeg"
    assert resultado.tempo_ms >= 0
    assert "sem IA" in resultado.modelo
    with Image.open(io.BytesIO(resultado.imagem)) as imagem:
        assert imagem.size == (720, 960)


def test_provedor_local_altera_a_imagem():
    original = entrada()
    resultado = ProvedorLocal().gerar(original)
    assert resultado.imagem != original.imagem


def test_fabrica_devolve_o_local_por_padrao():
    assert obter_provedor().nome == "fake"


# --- Provedor Replicate (HTTP simulado) ----------------------------------


@pytest.fixture
def replicate_configurado(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "token-de-teste")
    monkeypatch.setenv("AI_MODELO", MODELO)
    # Sem espera entre consultas: o intervalo agora vem da configuração, não de uma
    # constante de módulo, justamente para poder ser ajustado assim.
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0")
    modulo_config.obter_config.cache_clear()
    yield
    monkeypatch.undo()
    modulo_config.obter_config.cache_clear()


def usar_transporte(monkeypatch: pytest.MonkeyPatch, manipulador) -> None:
    """Faz todo `httpx.Client` desta execução falar com o manipulador, e não com a rede."""
    transporte = httpx.MockTransport(manipulador)
    original = httpx.Client

    def fabrica(*args, **kwargs):
        kwargs["transport"] = transporte
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fabrica)


def test_replicate_fluxo_de_sucesso(monkeypatch: pytest.MonkeyPatch, replicate_configurado):
    chamadas: list[str] = []

    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        chamadas.append(f"{requisicao.method} {requisicao.url.path}")
        if (schema := resposta_do_schema(requisicao)) is not None:
            return schema
        if requisicao.url.path == f"/v1/models/{MODELO}/predictions":
            corpo = requisicao.read().decode()
            # A foto vai no corpo como data URI: nenhuma URL pública é criada.
            assert "data:image/jpeg;base64," in corpo
            # Os valores exatos das opções publicadas, e não descrições em inglês.
            assert '"haircut":"Bob"' in corpo.replace(" ", "")
            assert '"hair_color":"Copper"' in corpo.replace(" ", "")
            assert requisicao.headers["authorization"] == "Bearer token-de-teste"
            return httpx.Response(
                201,
                json={
                    "id": "pred-1",
                    "status": "processing",
                    "urls": {"get": "https://api.replicate.com/v1/predictions/pred-1"},
                },
            )
        if requisicao.url.path == "/v1/predictions/pred-1":
            return httpx.Response(
                200,
                json={
                    "id": "pred-1",
                    "status": "succeeded",
                    "output": "https://replicate.delivery/saida.jpg",
                },
            )
        return httpx.Response(
            200, content=jpeg_de_teste(), headers={"content-type": "image/jpeg"}
        )

    usar_transporte(monkeypatch, manipulador)

    from app.services.ai.replicate import ProvedorReplicate

    provedor = ProvedorReplicate()
    assert provedor.nome == "replicate"
    resultado = provedor.gerar(entrada())

    assert resultado.imagem[:2] == b"\xff\xd8"
    assert resultado.modelo == MODELO
    assert resultado.instrucao == "haircut=Bob; hair_color=Copper"
    # Primeiro o schema (sem custo), depois a predição.
    assert chamadas[0] == f"GET /v1/models/{MODELO}"
    assert chamadas[1] == f"POST /v1/models/{MODELO}/predictions"
    assert "GET /v1/predictions/pred-1" in chamadas


def test_replicate_saida_em_lista(monkeypatch: pytest.MonkeyPatch, replicate_configurado):
    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        if (schema := resposta_do_schema(requisicao)) is not None:
            return schema
        if requisicao.url.path.endswith("/predictions"):
            return httpx.Response(
                201,
                json={
                    "status": "succeeded",
                    "output": ["https://replicate.delivery/a.jpg"],
                    "urls": {"get": "https://api.replicate.com/v1/predictions/x"},
                },
            )
        return httpx.Response(200, content=jpeg_de_teste(), headers={"content-type": "image/jpeg"})

    usar_transporte(monkeypatch, manipulador)
    from app.services.ai.replicate import ProvedorReplicate

    assert ProvedorReplicate().gerar(entrada()).imagem[:2] == b"\xff\xd8"


@pytest.mark.parametrize(
    ("status_http", "codigo"),
    [(401, "credencial_invalida"), (402, "sem_credito"), (500, "provedor_indisponivel")],
)
def test_replicate_erros_http(
    monkeypatch: pytest.MonkeyPatch, replicate_configurado, status_http, codigo
):
    usar_transporte(
        monkeypatch,
        lambda requisicao: resposta_do_schema(requisicao)
        or httpx.Response(status_http, json={"detail": "erro"}),
    )
    from app.services.ai.replicate import ProvedorReplicate

    with pytest.raises(FalhaDoProvedor) as erro:
        ProvedorReplicate().gerar(entrada())
    assert erro.value.codigo == codigo


def test_replicate_predicao_falhada(monkeypatch: pytest.MonkeyPatch, replicate_configurado):
    usar_transporte(
        monkeypatch,
        lambda requisicao: resposta_do_schema(requisicao)
        or httpx.Response(201, json={"status": "failed", "error": "modelo recusou a imagem"}),
    )
    from app.services.ai.replicate import ProvedorReplicate

    with pytest.raises(FalhaDoProvedor) as erro:
        ProvedorReplicate().gerar(entrada())
    assert erro.value.codigo == "falha_na_geracao"


def test_replicate_resposta_sem_saida(monkeypatch: pytest.MonkeyPatch, replicate_configurado):
    usar_transporte(
        monkeypatch,
        lambda requisicao: resposta_do_schema(requisicao)
        or httpx.Response(201, json={"status": "succeeded"}),
    )
    from app.services.ai.replicate import ProvedorReplicate

    with pytest.raises(FalhaDoProvedor) as erro:
        ProvedorReplicate().gerar(entrada())
    assert erro.value.codigo == "resposta_invalida"


def test_replicate_timeout(monkeypatch: pytest.MonkeyPatch, replicate_configurado):
    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("demorou", request=requisicao)

    usar_transporte(monkeypatch, manipulador)
    from app.services.ai.replicate import ProvedorReplicate

    with pytest.raises(FalhaDoProvedor) as erro:
        ProvedorReplicate().gerar(entrada())
    assert erro.value.codigo == "timeout"


def test_replicate_sem_credencial_falha_claro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "")
    modulo_config.obter_config.cache_clear()
    try:
        from app.services.ai.replicate import ProvedorReplicate

        with pytest.raises(FalhaDoProvedor) as erro:
            ProvedorReplicate()
        assert erro.value.codigo == "credencial_ausente"
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()
