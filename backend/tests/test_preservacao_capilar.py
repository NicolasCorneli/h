"""Tipo de cabelo desejado, preservação da textura e descrições livres na instrução.

Motivo: nos testes com usuários, a simulação "abriu os cachos" e "aumentou o comprimento".
A instrução é organizada por prioridade (pessoa, textura, mudança pedida, naturalidade),
com regras que dependem do pedido. Desde 2026-11-10 a pergunta da textura é "Qual tipo de
cabelo você deseja na simulação?": o tipo escolhido é aplicado, e "Manter meu tipo de
cabelo atual" é a instrução positiva de preservar a textura da foto.

Estes testes conferem as regras, os cenários A a E do pedido de reestruturação e o caminho
do tipo de cabelo, do formulário à instrução gerada em segundo plano. Nenhum deles mede
qualidade de imagem: isso é com `scripts/comparar_simulacoes.py`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.erros import ValidacaoFalhou
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.glossario import termos_em_ingles
from app.services.ai.instrucoes import (
    TEXTURA_EM_INGLES,
    prompt_detalhado,
    prompt_detalhado_original,
    prompt_edicao,
)
from app.services.ai.pedido import TEXTURAS, PedidoCapilar, interpretar, validar_textura
from app.services.ai.planos import Configuracao, Modo, montar_entrada, planejar
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
MANTER_TEXTURA = "keep the client's natural hair texture exactly as in the photo"
TROCAR_TEXTURA = "change the hair texture to"


def prompt(*args, **kwargs) -> str:
    return prompt_detalhado(interpretar(*args, **kwargs))


# --- Regras condicionais ---------------------------------------------------


def test_prioridades_na_ordem():
    texto = prompt("Pixie", "Loiro")
    posicoes = [texto.index(f"Priority {n}") for n in (1, 2, 3, 4)]
    assert posicoes == sorted(posicoes)
    assert texto.startswith("Using the provided photo of a real person, change only the hair")
    assert "This is an edit of an existing photograph, not a new image." in texto


def test_manter_o_tipo_atual_e_instrucao_positiva_de_preservar():
    """"Manter meu tipo de cabelo atual" não é ausência: diz o que preservar e o que não fazer."""
    for pedido in (prompt("Pixie", "Loiro"), prompt(None, "Loiro", manter_corte=True), prompt("Pixie", None, manter_cor=True)):
        assert MANTER_TEXTURA in pedido
        assert "same curl pattern" in pedido
        assert "Do not loosen, open up, stretch, relax or straighten curls or coils" in pedido
        assert "same density, the same volume" in pedido
        assert TROCAR_TEXTURA not in pedido


def test_manter_vence_textura_citada_na_descricao():
    """Preservação tem prioridade sobre uma descrição incompatível ("liso" num corte)."""
    texto = prompt("Chanel liso e alinhado", None, manter_cor=True)
    assert MANTER_TEXTURA in texto
    assert "This takes priority over any texture mentioned in the descriptions below." in texto
    # A exceção antiga ("a não ser que o corte peça outra textura") não existe mais.
    assert "explicitly asks for a different texture" not in texto


def test_tipo_escolhido_e_aplicado_e_vence_a_descricao():
    texto = prompt("Pixie", "Loiro", textura="3C")
    assert f"{TROCAR_TEXTURA} {TEXTURA_EM_INGLES['3C']}" in texto
    assert "Apply this texture to all of the hair" in texto
    assert "keep the same hair density as in the photo" in texto
    assert "This chosen texture takes priority over any texture mentioned" in texto
    assert MANTER_TEXTURA not in texto
    assert "Shape this haircut with the chosen texture" in texto


@pytest.mark.parametrize("textura", TEXTURAS)
def test_todo_tipo_tem_descricao_propria(textura):
    assert textura in TEXTURA_EM_INGLES
    assert TEXTURA_EM_INGLES[textura] in prompt("Pixie", "Loiro", textura=textura)


def test_descricoes_dos_tipos_sao_distintas():
    assert len(set(TEXTURA_EM_INGLES.values())) == len(TEXTURA_EM_INGLES)


def test_sem_corte_o_comprimento_fica_exato():
    texto = prompt(None, "Ruivo", manter_corte=True)
    assert "Keep the current length exactly" in texto
    assert "Keep the current haircut exactly as it is" in texto
    assert "New haircut" not in texto


def test_com_corte_o_comprimento_so_muda_o_que_o_corte_pede():
    texto = prompt("Long bob estruturado", None, manter_cor=True)
    assert "never make the hair longer than in the photo" in texto
    assert "Keep the current length exactly" not in texto
    assert "natural shrinkage, not by its stretched length" in texto
    assert "do not turn volume into length" in texto


def test_sem_cor_a_cor_fica_e_com_cor_a_textura_nao_muda():
    assert "Keep the current hair color exactly as it is" in prompt("Pixie", None, manter_cor=True)
    com_cor = prompt(None, "Loiro mel", manter_corte=True)
    assert "New hair color: honey blonde" in com_cor
    assert "Coloring does not change the curl pattern or the texture set in priority 2." in com_cor


def test_instrucao_sem_travessao():
    """A instrução aparece no aplicativo ("Ver o que foi pedido ao modelo")."""
    for textura in (None, "4C", "liso"):
        texto = prompt("Pixie", "Loiro", textura=textura)
        assert "—" not in texto and "–" not in texto


def test_variante_original_continua_disponivel_para_comparacao():
    pedido = interpretar("Chanel", "Ruivo")
    original = Configuracao("x/y", NANO, caminho="instrucao", variante_instrucao="original")
    assert planejar(pedido, original).campos["prompt"] == prompt_detalhado_original(pedido)
    assert planejar(pedido, CONFIG_NANO).campos["prompt"] == prompt_detalhado(pedido)


# --- Descrição livre --------------------------------------------------------


def test_descricao_livre_de_corte_vai_inteira_e_com_ordem_de_fidelidade():
    descricao = (
        "Quero manter o comprimento, adicionar camadas longas, uma franja cortininha e "
        "deixar as pontas mais leves"
    )
    texto = prompt(descricao, None, manter_cor=True)
    assert descricao in texto, "a descrição não pode ser resumida nem trocada por um nome de corte"
    assert "Follow every detail of this description" in texto
    assert "Do not add details that were not asked for." in texto
    for termo in ("keep the current length", "long layers", "curtain bangs", "lighter, softly thinned ends"):
        assert termo in texto


def test_descricao_livre_de_cor_mantem_regioes_e_fica_local():
    descricao = (
        "Quero manter a raiz castanho escuro, com mechas caramelo suaves no comprimento e "
        "pontas um pouco mais claras"
    )
    texto = prompt(None, descricao, manter_corte=True)
    assert descricao in texto
    assert "Keep localized changes local: do not spread them to the whole hair" in texto
    for termo in ("roots", "dark brown", "highlights", "caramel", "lengths", "ends"):
        assert termo in texto


def test_exemplo_do_catalogo_usa_a_descricao_do_catalogo_sem_a_frase_de_fidelidade():
    texto = prompt("Pixie", "Loiro mel")
    assert "Follow every detail of this description" not in texto


def test_degrade_muda_de_sentido_conforme_o_campo():
    assert "low fade" in termos_em_ingles("degradê baixo nas laterais", "corte")
    assert "ombre gradient, blended from roots to ends" in termos_em_ingles("degradê do castanho ao loiro", "cor")
    assert "ombre gradient, blended from roots to ends" not in termos_em_ingles("degradê", "corte")


# --- Gênero neutro ----------------------------------------------------------


def test_neutro_vira_frase_de_corte_neutro_so_com_corte_novo():
    com_corte = prompt("Corte curto texturizado", None, manter_cor=True, genero="none")
    assert "It is a gender-neutral haircut" in com_corte
    so_cor = prompt(None, "Ruivo", manter_corte=True, genero="none")
    assert "gender-neutral" not in so_cor


def test_neutro_no_kontext_continua_sem_frase():
    """No caminho especializado, "none" é o padrão do modelo (campo `gender`)."""
    assert "gender-neutral" not in prompt_edicao(interpretar("Butterfly", "Ruivo"))


# --- Cenários A a E ---------------------------------------------------------


def test_cenario_a_corte_cor_e_textura():
    texto = prompt("camadas longas com franja cortininha", "mechas caramelo nas pontas", textura="2B", genero="female")
    assert f"{TROCAR_TEXTURA} {TEXTURA_EM_INGLES['2B']}" in texto
    assert "New haircut:" in texto and "New hair color:" in texto
    assert "It is a women's haircut." in texto


def test_cenario_b_so_cor_mantem_corte_comprimento_e_textura():
    texto = prompt(None, "mechas caramelo só nas pontas", manter_corte=True)
    assert MANTER_TEXTURA in texto
    assert "Keep the current haircut exactly as it is" in texto
    assert "Keep the current length exactly" in texto
    assert "New hair color:" in texto


def test_cenario_c_so_corte_mantem_cor_e_textura():
    texto = prompt("Corte curto texturizado", None, manter_cor=True)
    assert MANTER_TEXTURA in texto
    assert "Keep the current hair color exactly as it is" in texto
    assert "Shape this haircut with the client's own hair texture" in texto


def test_cenario_d_corte_com_textura_mantida():
    texto = prompt("Chanel na altura do queixo, liso e alinhado", None, manter_cor=True)
    assert MANTER_TEXTURA in texto
    assert "This takes priority over any texture mentioned in the descriptions below." in texto


def test_cenario_e_so_textura_mantem_corte_cor_e_comprimento():
    pedido = interpretar(None, None, manter_corte=True, manter_cor=True, textura="4A")
    texto = prompt_detalhado(pedido)
    assert f"{TROCAR_TEXTURA} {TEXTURA_EM_INGLES['4A']}" in texto
    assert "Keep the current haircut exactly as it is" in texto
    assert "Keep the current hair color exactly as it is" in texto
    assert "the hair is not cut or lengthened" in texto
    assert "shrinkage, and that is expected" in texto


def test_manter_tudo_sem_tipo_novo_nao_e_pedido():
    with pytest.raises(ValidacaoFalhou) as erro:
        interpretar(None, None, manter_corte=True, manter_cor=True)
    assert erro.value.codigo == "pedido_vazio"
    assert "tipo de cabelo" in str(erro.value)


# --- Roteamento -------------------------------------------------------------


def test_especializado_com_tipo_escolhido_vai_ao_modelo_de_texto():
    """O change-haircut não tem campo de textura: com tipo escolhido, vai ao de texto."""
    atual = Configuracao("flux-kontext-apps/change-haircut", "black-forest-labs/flux-kontext-pro")
    sem = planejar(interpretar("Pixie", "Loiro mel"), atual)
    com = planejar(interpretar("Pixie", "Loiro mel", textura="3A"), atual)
    assert sem.modo is Modo.opcoes and sem.modelo == "flux-kontext-apps/change-haircut"
    assert com.modo is Modo.descricao and com.modelo == "black-forest-labs/flux-kontext-pro"
    assert f"New hair texture: {TEXTURA_EM_INGLES['3A']}." in com.campos["prompt"]


def test_kontext_sem_tipo_escolhido_fica_como_antes():
    texto = prompt_edicao(interpretar("Butterfly", "Ruivo"))
    assert "New hair texture" not in texto


# --- Validação ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [(None, None), ("", None), ("  ", None), ("3c", "3C"), ("Cacheado", "cacheado"), ("4A", "4A")],
)
def test_textura_aceita(entrada, esperado):
    assert validar_textura(entrada) == esperado


@pytest.mark.parametrize("entrada", ["5A", "3D", "afro", "1", "lisinho"])
def test_textura_recusada(entrada):
    with pytest.raises(ValidacaoFalhou) as erro:
        validar_textura(entrada)
    assert erro.value.codigo == "textura_invalida"


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


def test_tipo_escolhido_e_gravado_e_chega_a_instrucao(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro", textura="4B")

    assert estado["status"] == "concluida"
    assert estado["parametros"]["textura"] == "4B"
    assert TEXTURA_EM_INGLES["4B"] in estado["instrucaoIa"]
    # A geração em segundo plano remonta o pedido a partir da linha gravada.
    (predicao,) = [c for c in mock_provedor_ia.chamadas if "input" in c]
    assert TEXTURA_EM_INGLES["4B"] in predicao["input"]["prompt"]
    # O tipo de cabelo não é parâmetro do modelo.
    for campo in ("textura", "hair_texture", "curl_pattern", "curvatura"):
        assert campo not in predicao["input"]


def test_so_o_tipo_de_cabelo_e_um_pedido_valido(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(
        cliente_http, cabecalhos, manterCorte="true", manterCor="true", textura="ondulado"
    )
    assert estado["status"] == "concluida"
    assert estado["parametros"]["estilo"] == "Corte atual"
    assert estado["parametros"]["cor"] == "Cor atual"
    assert estado["parametros"]["textura"] == "ondulado"


def test_sem_tipo_escolhido_fica_nulo_e_mantem(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro")
    assert estado["parametros"]["textura"] is None
    assert MANTER_TEXTURA in estado["instrucaoIa"]


def test_campo_antigo_curvatura_nao_vira_troca_de_textura(cliente_http: TestClient, conta, api_com_nano):
    """Versões anteriores do aplicativo mandam `curvatura` (o cabelo natural). Ele é ignorado:
    sem `textura`, a textura da foto é mantida, que é o que aquele pedido queria."""
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro", curvatura="3C")
    assert estado["status"] == "concluida"
    assert estado["parametros"]["textura"] is None
    assert "curvatura" not in estado["parametros"]
    assert MANTER_TEXTURA in estado["instrucaoIa"]


def test_textura_invalida_e_recusada_sem_chamar_o_provedor(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Pixie", cor="Loiro", textura="9Z")
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "textura_invalida"
    assert not [c for c in mock_provedor_ia.chamadas if "input" in c]


def test_previa_do_plano_considera_o_tipo_de_cabelo(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/simulacoes/plano",
        headers=cabecalhos,
        json={"corte": "Pixie", "cor": "Loiro", "textura": "2B"},
    )
    assert resposta.status_code == 200, resposta.text
    assert TEXTURA_EM_INGLES["2B"] in resposta.json()["instrucao"]
