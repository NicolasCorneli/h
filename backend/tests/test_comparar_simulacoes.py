"""Ferramenta de comparação de qualidade (`scripts/comparar_simulacoes.py`).

O que importa garantir: sem `--confirmar-custo` nenhuma chamada sai da máquina, e com ela
a geração usa o mesmo cliente da produção e entrega o CSV e a página de avaliação.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.core import config as modulo_config
from app.services.ai.replicate import limpar_cache_de_esquemas
from tests import mock_provedor_ia
from tests.fabricas import retrato_valido

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "comparar_simulacoes.py"
EXEMPLO = SCRIPT.parent / "pedidos_exemplo.json"


def carregar_script():
    especificacao = importlib.util.spec_from_file_location("comparar_simulacoes", SCRIPT)
    modulo = importlib.util.module_from_spec(especificacao)
    # Os dataclasses do script procuram o próprio módulo em sys.modules ao serem criados.
    sys.modules["comparar_simulacoes"] = modulo
    especificacao.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def pasta_de_fotos(tmp_path: Path) -> Path:
    pasta = tmp_path / "fotos"
    pasta.mkdir()
    (pasta / "pessoa-a.jpg").write_bytes(retrato_valido())
    (pasta / "leia-me.txt").write_text("ignorado")
    return pasta


def proibir_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    def recusar(*args, **kwargs):
        raise AssertionError("o ensaio tentou falar com a rede")

    monkeypatch.setattr(httpx, "Client", recusar)


def test_exemplo_tem_os_seis_tipos_de_pedido():
    pedidos = carregar_script().ler_pedidos(EXEMPLO)
    assert len(pedidos) == 6
    tipos = {(p.pedido.corte is None, p.pedido.cor is None) for p in pedidos}
    assert tipos == {(False, False), (True, False), (False, True)}, "faltam só corte, só cor ou os dois"
    assert any(p.pedido.corte and not p.pedido.corte.do_catalogo for p in pedidos), "falta texto livre"


def test_sem_confirmar_custo_nenhuma_chamada_e_feita(monkeypatch, pasta_de_fotos, tmp_path, capsys):
    proibir_rede(monkeypatch)
    script = carregar_script()

    codigo = script.main(
        ["--fotos", str(pasta_de_fotos), "--pedidos", str(EXEMPLO), "--estrategias", "nano,atual",
         "--saida", str(tmp_path / "saida")]
    )

    assert codigo == 0
    texto = capsys.readouterr().out
    assert "12 chamada(s)" in texto
    # 6 no Nano (1K) + 6 no caminho atual, a US$ 0,04.
    assert "US$ 0.44" in texto
    assert "nenhuma chamada foi feita" in texto
    assert not (tmp_path / "saida").exists()


def test_teto_de_chamadas_impede_execucao_cara(monkeypatch, pasta_de_fotos):
    proibir_rede(monkeypatch)
    codigo = carregar_script().main(
        ["--fotos", str(pasta_de_fotos), "--pedidos", str(EXEMPLO), "--estrategias", "nano,atual",
         "--maximo", "5", "--confirmar-custo"]
    )
    assert codigo == 1


def test_geracao_confirmada_entrega_csv_e_pagina(monkeypatch, pasta_de_fotos, tmp_path):
    monkeypatch.setenv("AI_API_KEY", "token-de-teste")
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0")
    modulo_config.obter_config.cache_clear()
    limpar_cache_de_esquemas()
    mock_provedor_ia.reiniciar()
    criadas: list[str] = []

    def replicate(requisicao: httpx.Request) -> httpx.Response:
        caminho = requisicao.url.path
        if requisicao.method == "GET" and caminho.startswith("/v1/models/"):
            schema = mock_provedor_ia._schema_do_modelo(caminho.removeprefix("/v1/models/"))
            return httpx.Response(200, json={"latest_version": {"id": "v", "openapi_schema": schema}})
        if requisicao.method == "POST" and caminho.endswith("/predictions"):
            criadas.append(caminho)
            if "flux-kontext-pro" in caminho:
                return httpx.Response(201, json={"id": "p", "status": "failed", "error": "NSFW content detected"})
            return httpx.Response(
                201,
                json={"id": "p", "status": "succeeded", "output": "https://replicate.delivery/s.png", "urls": {"get": "x"}},
            )
        buffer = io.BytesIO()
        Image.new("RGB", (64, 80), (90, 50, 30)).save(buffer, format="PNG")
        return httpx.Response(200, content=buffer.getvalue(), headers={"content-type": "image/png"})

    transporte = httpx.MockTransport(replicate)
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: original(*a, **{**k, "transport": transporte}))

    pedidos = tmp_path / "pedidos.json"
    pedidos.write_text(json.dumps([{"id": "p1", "corte": "Butterfly", "cor": "Ruivo"}]), encoding="utf-8")
    saida = tmp_path / "saida"
    try:
        codigo = carregar_script().main(
            ["--fotos", str(pasta_de_fotos), "--pedidos", str(pedidos), "--estrategias", "nano,atual",
             "--saida", str(saida), "--confirmar-custo"]
        )
    finally:
        modulo_config.obter_config.cache_clear()
        limpar_cache_de_esquemas()

    assert codigo == 0
    assert criadas == [
        "/v1/models/google/nano-banana-2.1/predictions",
        "/v1/models/black-forest-labs/flux-kontext-pro/predictions",
    ]
    with (saida / "resultado.csv").open(encoding="utf-8-sig") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert [(l["caminho"], l["sucesso"], l["codigo_erro"]) for l in linhas] == [
        ("nano", "sim", ""),
        ("atual", "nao", "conteudo_bloqueado"),
    ]
    assert linhas[0]["modelo"] == "google/nano-banana-2.1"
    assert linhas[0]["instrucao"].startswith("Edit this photograph")
    gerada = saida / linhas[0]["arquivo"]
    assert gerada.read_bytes()[:2] == b"\xff\xd8", "a saída em PNG foi gravada como JPEG"
    assert (saida / "originais" / "pessoa-a.jpg").exists()
    pagina = (saida / "comparacao.html").read_text(encoding="utf-8")
    for trecho in ("Naturalidade", "Fidelidade da cor", "Preservação do rosto", "Falhou: conteudo_bloqueado"):
        assert trecho in pagina
