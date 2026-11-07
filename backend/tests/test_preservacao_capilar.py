"""Preservação do cabelo natural na instrução do Nano Banana, e a curvatura informada.

Motivo: nos testes com usuários, a simulação "abriu os cachos" e "aumentou o comprimento".
A instrução passou a ser organizada por prioridade (pessoa, cabelo natural, mudança pedida,
naturalidade), com regras que dependem do pedido. Estes testes conferem essas regras e o
caminho da curvatura, do formulário à instrução gerada em segundo plano. Nenhum deles mede
qualidade de imagem: isso é com `scripts/comparar_simulacoes.py`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.erros import ValidacaoFalhou
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.instrucoes import (
    CURVATURA_EM_INGLES,
    prompt_detalhado,
    prompt_detalhado_original,
    prompt_edicao,
)
from app.services.ai.pedido import CURVATURAS, PedidoCapilar, interpretar, validar_curvatura
from app.services.ai.planos import Configuracao, montar_entrada, planejar
from tests import mock_provedor_ia
from tests.test_nano_banana import (  # noqa: F401 - fixtures usadas por nome
    NANO,
    api_com_nano,
    esquema_nano,
    provedor_de_mentira,
    simular_no_nano,
)
from tests.test_simulacao_com_mock_ia import cliente_com_aceite, gerar_pedido

CONFIG_NANO = Configuracao("flux-kontext-apps/change-haircut", NANO, caminho="instrucao")


def prompt(*args, **kwargs) -> str:
    return prompt_detalhado(interpretar(*args, **kwargs))


# --- Regras condicionais ---------------------------------------------------


def test_prioridades_na_ordem():
    texto = prompt("Pixie", "Loiro")
    posicoes = [texto.index(f"Priority {n}") for n in (1, 2, 3, 4)]
    assert posicoes == sorted(posicoes)
    assert texto.startswith("Using the provided photo of a real person, change only the hair")


def test_textura_natural_e_preservada_em_todo_pedido():
    for pedido in (prompt("Pixie", "Loiro"), prompt(None, "Loiro", manter_corte=True), prompt("Pixie", None, manter_cor=True)):
        assert "same curl pattern" in pedido
        assert "Do not loosen, open up, stretch, relax or straighten curls or coils" in pedido
        assert "same density, the same volume" in pedido


def test_sem_corte_o_comprimento_fica_exato():
    texto = prompt(None, "Ruivo", manter_corte=True)
    assert "Keep the current length exactly" in texto
    assert "Keep the current haircut exactly as it is" in texto
    assert "New haircut" not in texto
    # A exceção de textura só existe quando há corte pedido.
    assert "different texture" not in texto


def test_com_corte_o_comprimento_so_muda_o_que_o_corte_pede():
    texto = prompt("Long bob estruturado", None, manter_cor=True)
    assert "never make the hair longer than in the photo" in texto
    assert "Keep the current length exactly" not in texto
    assert "natural shrinkage, not by its stretched length" in texto
    assert "do not turn volume into length" in texto


def test_pedido_de_outra_textura_e_a_unica_excecao():
    texto = prompt("escova lisa com pontas para dentro", None, manter_cor=True)
    assert "explicitly asks for a different texture" in texto


def test_sem_cor_a_cor_fica_e_com_cor_a_textura_nao_muda():
    assert "Keep the current hair color exactly as it is" in prompt("Pixie", None, manter_cor=True)
    com_cor = prompt(None, "Loiro mel", manter_corte=True)
    assert "New hair color: honey blonde" in com_cor
    assert "without changing the curl pattern or the texture" in com_cor


def test_curvatura_entra_como_apoio_a_leitura_da_foto():
    texto = prompt("Pixie", "Loiro", curvatura="3C")
    assert CURVATURA_EM_INGLES["3C"] in texto
    assert "the photo remains the main reference" in texto


def test_sem_curvatura_a_foto_e_a_unica_referencia():
    texto = prompt("Pixie", "Loiro")
    assert "describes their natural hair" not in texto


@pytest.mark.parametrize("curvatura", CURVATURAS)
def test_toda_curvatura_tem_descricao(curvatura):
    assert curvatura in CURVATURA_EM_INGLES
    assert CURVATURA_EM_INGLES[curvatura] in prompt("Pixie", "Loiro", curvatura=curvatura)


def test_instrucao_sem_travessao():
    """A instrução aparece no aplicativo ("Ver o que foi pedido ao modelo")."""
    for curvatura in (None, "4C"):
        texto = prompt("Pixie", "Loiro", curvatura=curvatura)
        assert "—" not in texto and "–" not in texto


def test_variante_original_continua_disponivel_para_comparacao():
    pedido = interpretar("Chanel", "Ruivo")
    original = Configuracao("x/y", NANO, caminho="instrucao", variante_instrucao="original")
    assert planejar(pedido, original).campos["prompt"] == prompt_detalhado_original(pedido)
    assert planejar(pedido, CONFIG_NANO).campos["prompt"] == prompt_detalhado(pedido)


def test_kontext_nao_muda_com_a_curvatura():
    """O caminho especializado fica como estava: a curvatura é só do Nano Banana."""
    sem = interpretar("Butterfly", "Ruivo")
    com = interpretar("Butterfly", "Ruivo", curvatura="3C")
    assert prompt_edicao(sem) == prompt_edicao(com)


# --- Validação da curvatura ------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [(None, None), ("", None), ("  ", None), ("3c", "3C"), ("Cacheado", "cacheado"), ("4A", "4A")],
)
def test_curvatura_aceita(entrada, esperado):
    assert validar_curvatura(entrada) == esperado


@pytest.mark.parametrize("entrada", ["5A", "3D", "afro", "1", "lisinho"])
def test_curvatura_recusada(entrada):
    with pytest.raises(ValidacaoFalhou) as erro:
        validar_curvatura(entrada)
    assert erro.value.codigo == "curvatura_invalida"


# --- Referências (experimento) ---------------------------------------------


def test_referencias_tem_papel_dito_na_instrucao_e_vao_depois_da_foto():
    base = interpretar("corte da referência", None, manter_cor=True)
    pedido = PedidoCapilar(corte=base.corte, cor=None, referencias=("corte", "textura"))
    plano = planejar(pedido, CONFIG_NANO)
    texto = plano.campos["prompt"]
    assert "Image 1 is the client" in texto
    assert "Image 2 is only a haircut reference" in texto
    assert "Do not take that person's face" in texto
    assert "Image 3 is a close-up of the client's own natural hair" in texto
    entrada = montar_entrada(plano, "data:foto", esquema_nano(), ["data:ref1", "data:ref2"])
    assert entrada["image_input"] == ["data:foto", "data:ref1", "data:ref2"]


def test_modelo_de_uma_imagem_recusa_referencias():
    atual = Configuracao("flux-kontext-apps/change-haircut", "black-forest-labs/flux-kontext-pro")
    plano = planejar(interpretar("Butterfly", "Ruivo"), atual)
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, "data:foto", None, ["data:ref"])
    assert erro.value.codigo == "modelo_incompativel"


# --- Do formulário à instrução gerada em segundo plano ---------------------


def test_curvatura_e_gravada_e_chega_a_instrucao(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro", curvatura="4B")

    assert estado["status"] == "concluida"
    assert estado["parametros"]["curvatura"] == "4B"
    assert CURVATURA_EM_INGLES["4B"] in estado["instrucaoIa"]
    # A geração em segundo plano remonta o pedido a partir da linha gravada.
    (predicao,) = [c for c in mock_provedor_ia.chamadas if "input" in c]
    assert CURVATURA_EM_INGLES["4B"] in predicao["input"]["prompt"]
    # A curvatura não é parâmetro do modelo.
    assert "curvatura" not in predicao["input"] and "curl_pattern" not in predicao["input"]


def test_sem_curvatura_fica_nulo(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro")
    assert estado["parametros"]["curvatura"] is None


def test_curvatura_invalida_e_recusada_sem_chamar_o_provedor(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Pixie", cor="Loiro", curvatura="9Z")
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "curvatura_invalida"
    assert not [c for c in mock_provedor_ia.chamadas if "input" in c]


def test_previa_do_plano_considera_a_curvatura(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/simulacoes/plano",
        headers=cabecalhos,
        json={"corte": "Pixie", "cor": "Loiro", "curvatura": "2B"},
    )
    assert resposta.status_code == 200, resposta.text
    assert CURVATURA_EM_INGLES["2B"] in resposta.json()["instrucao"]
