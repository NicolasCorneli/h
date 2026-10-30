"""Regras da personalização, sem rede e sem banco: pedido, catálogo de exemplos,
instruções, escolha do modelo e conferência no schema.

São as funções que decidem o que sai para o provedor. Cada teste usa o schema de mentira
de `mock_provedor_ia` (uma hipótese do schema real, ver o aviso lá) ou nenhum schema.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.erros import ValidacaoFalhou
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.esquema import Campo, EsquemaModelo, ler_esquema
from app.services.ai.glossario import termos_em_ingles
from app.services.ai.instrucoes import descrever, prompt_edicao
from app.services.ai.pedido import (
    COR_MANTIDA,
    CORTE_MANTIDO,
    GENEROS,
    Alteracao,
    interpretar,
    pedido_registrado,
)
from app.services.ai.planos import Configuracao, Modo, montar_entrada, planejar
from app.services.catalogo import (
    CORES_CLASSICAS,
    CORES_EM_ALTA,
    CORTES_CLASSICOS,
    CORTES_EM_ALTA,
    opcao_de_cor,
    opcao_de_corte,
)
from tests import mock_provedor_ia

PRINCIPAL = "flux-kontext-apps/change-haircut"
TEXTO = "black-forest-labs/flux-kontext-pro"
CONFIG = Configuracao(modelo_principal=PRINCIPAL, modelo_texto=TEXTO)
FOTO = "data:image/jpeg;base64,"


def esquema(modelo: str, cenario: str = "sucesso") -> EsquemaModelo:
    mock_provedor_ia.cenario = cenario
    try:
        dados = {"latest_version": {"id": "v1", "openapi_schema": mock_provedor_ia._schema_do_modelo(modelo)}}
    finally:
        mock_provedor_ia.cenario = "sucesso"
    resultado = ler_esquema(modelo, dados)
    assert resultado is not None
    return resultado


# --- Pedido ---------------------------------------------------------------


def test_corte_e_cor_livres_seguem_como_foram_escritos():
    pedido = interpretar("Bob na altura do queixo, com camadas suaves.", "castanho chocolate com reflexos caramelo")
    assert pedido.corte == Alteracao("Bob na altura do queixo, com camadas suaves.")
    assert pedido.cor == Alteracao("castanho chocolate com reflexos caramelo")
    assert not pedido.corte.do_catalogo


def test_exemplo_do_catalogo_e_reconhecido_sem_diferenciar_caixa_ou_acento():
    pedido = interpretar("degrade", "castanho escuro")
    assert pedido.corte.texto == "Degradê"
    assert pedido.corte.do_catalogo
    assert pedido.cor.texto == "Castanho-escuro"
    assert pedido.cor.opcoes_do_modelo == ("Dark Brown",)


def test_manter_o_corte_e_mudar_a_cor():
    pedido = interpretar("qualquer coisa", "Loiro", manter_corte=True)
    assert pedido.corte is None
    assert pedido.rotulo_corte == CORTE_MANTIDO
    assert pedido.rotulo_cor == "Loiro"


def test_manter_a_cor_e_mudar_o_corte():
    pedido = interpretar("Pixie", "", manter_cor=True)
    assert pedido.cor is None
    assert pedido.rotulo_cor == COR_MANTIDA


@pytest.mark.parametrize(
    ("corte", "cor", "opcoes", "codigo"),
    [
        ("", "Loiro", {}, "corte_vazio"),
        ("Chanel", "  ", {}, "cor_vazia"),
        ("x", "y", {"manter_corte": True, "manter_cor": True}, "pedido_vazio"),
        ("<script>alert(1)</script>", "Loiro", {}, "descricao_invalida"),
        ("Chanel", "{{prompt}}", {}, "descricao_invalida"),
        ("12345", "Loiro", {}, "descricao_invalida"),
        ("Chanel", "a" * 301, {}, "descricao_longa"),
    ],
)
def test_pedidos_invalidos(corte, cor, opcoes, codigo):
    with pytest.raises(ValidacaoFalhou) as erro:
        interpretar(corte, cor, **opcoes)
    assert erro.value.codigo == codigo


def test_descricao_vazia_nao_vira_escolha_padrao():
    """Campo em branco não é "manter" nem "No change": é pedido incompleto."""
    with pytest.raises(ValidacaoFalhou) as erro:
        interpretar("", "")
    assert erro.value.codigo == "corte_vazio"


def test_espacos_e_caracteres_de_controle_sao_limpos():
    pedido = interpretar("  Bob \n\n com   franja\t", "Loiro\x00")
    assert pedido.corte.texto == "Bob com franja"
    assert pedido.cor.texto == "Loiro"


def test_pedido_registrado_reconstroi_o_que_foi_gravado():
    assert pedido_registrado(CORTE_MANTIDO, "Loiro").corte is None
    assert pedido_registrado("Pixie", COR_MANTIDA).cor is None
    gravado = pedido_registrado("Chanel", "Ruivo")
    assert gravado.corte.opcoes_do_modelo == ("Bob",)
    assert gravado.cor.opcoes_do_modelo == ("Copper",)


# --- Catálogo de exemplos ---------------------------------------------------


def test_exemplos_do_aplicativo_e_do_servidor_nao_divergem():
    """Os exemplos que a tela mostra são exatamente os que o servidor reconhece."""
    catalogo_ts = (Path(__file__).resolve().parents[2] / "espelho" / "src" / "data" / "catalogo.ts").read_text(
        encoding="utf-8"
    )

    def lista(nome: str, grupo: str) -> list[str]:
        bloco = re.search(rf"{nome} = \{{(.*?)\}} as const", catalogo_ts, re.S).group(1)
        itens = re.search(rf"{grupo}: \[(.*?)\]", bloco, re.S).group(1)
        return re.findall(r"'([^']+)'", itens)

    assert lista("EXEMPLOS_DE_CORTE", "emAlta") == [o.rotulo for o in CORTES_EM_ALTA]
    assert lista("EXEMPLOS_DE_CORTE", "classicos") == [o.rotulo for o in CORTES_CLASSICOS]
    assert lista("EXEMPLOS_DE_COR", "emAlta") == [o.rotulo for o in CORES_EM_ALTA]
    assert lista("EXEMPLOS_DE_COR", "classicos") == [o.rotulo for o in CORES_CLASSICAS]


def test_cada_exemplo_tem_descricao_em_ingles():
    for opcao in (*CORTES_EM_ALTA, *CORTES_CLASSICOS, *CORES_EM_ALTA, *CORES_CLASSICAS):
        assert opcao.ingles and opcao.ingles.isascii(), opcao.rotulo
    for opcao in (*CORES_EM_ALTA, *CORES_CLASSICAS):
        assert opcao.amostra, f"{opcao.rotulo} sem amostra para o provedor local"


def test_cada_exemplo_e_um_pedido_aceito():
    for opcao in (*CORTES_EM_ALTA, *CORTES_CLASSICOS):
        assert interpretar(opcao.rotulo, "", manter_cor=True).corte.do_catalogo, opcao.rotulo
    for opcao in (*CORES_EM_ALTA, *CORES_CLASSICAS):
        assert interpretar("", opcao.rotulo, manter_corte=True).cor.do_catalogo, opcao.rotulo


def test_texto_que_nao_e_exemplo_nao_e_reconhecido():
    assert opcao_de_corte("Chanel na altura do queixo") is None
    assert opcao_de_cor("Loiro com raiz esfumada") is None


# --- Glossário e instruções -----------------------------------------------


def test_termos_em_ingles_na_ordem_e_sem_repetir():
    assert termos_em_ingles("Corte degradê baixo nas laterais, com topo médio e textura natural.") == [
        "low fade",
        "sides",
        "top",
        "medium-length",
        "natural texture",
    ]
    assert termos_em_ingles("Cabelo longo com franja cortininha e camadas ao redor do rosto") == [
        "long",
        "curtain bangs",
        "layers",
    ]
    assert termos_em_ingles("castanho escuro") == ["dark brown"]
    assert termos_em_ingles("loiro manteiga com raiz esfumada") == ["blonde", "butter", "roots"]
    assert termos_em_ingles("sem nada técnico aqui") == []


def test_descricao_livre_preserva_o_portugues_e_acrescenta_termos():
    trecho = descrever(Alteracao('Bob na altura do queixo, "bem" leve'))
    assert trecho.startswith("\"Bob na altura do queixo, 'bem' leve\"")
    assert "key terms: bob, chin-length" in trecho
    assert descrever(Alteracao("Bob na altura do queixo"), "pt") == (
        '"Bob na altura do queixo" (described in Brazilian Portuguese)'
    )


def test_prompt_de_edicao_preserva_identidade_e_diz_o_que_fica():
    prompt = prompt_edicao(interpretar("Butterfly", "", manter_cor=True))
    assert "Edit only the hair" in prompt
    assert "butterfly haircut" in prompt
    assert "Keep the current hair color exactly as it is" in prompt
    assert "face, identity" in prompt


# --- Escolha do modelo ----------------------------------------------------


def test_exemplos_com_equivalente_vao_ao_modelo_principal():
    plano = planejar(interpretar("Pixie", "Loiro mel"), CONFIG, esquema(PRINCIPAL))
    assert plano.modo is Modo.opcoes
    assert plano.modelo == PRINCIPAL
    assert plano.campos["haircut"] == "Pixie Cut"
    assert plano.campos["hair_color"] == "Honey Blonde"
    assert "prompt" not in plano.campos


def test_manter_vira_no_change_no_modelo_principal():
    plano = planejar(interpretar("", "Vermelho bordô", manter_corte=True), CONFIG, esquema(PRINCIPAL))
    assert plano.campos["haircut"] == "No change"
    assert plano.campos["hair_color"] == "Burgundy"
    assert plano.essenciais == {"input_image", "hair_color"}


def test_descricao_livre_vai_ao_modelo_de_texto():
    plano = planejar(interpretar("Bob na altura do queixo, com camadas suaves", "Loiro"), CONFIG, esquema(PRINCIPAL))
    assert plano.modo is Modo.descricao
    assert plano.modelo == TEXTO
    assert set(plano.campos) == {"prompt", "aspect_ratio", "output_format"}
    assert "Bob na altura do queixo" in plano.campos["prompt"]
    assert "New hair color: blonde" in plano.campos["prompt"]


def test_exemplo_sem_equivalente_vai_ao_modelo_de_texto_com_a_descricao_em_ingles():
    plano = planejar(interpretar("Butterfly", "Loiro manteiga"), CONFIG, esquema(PRINCIPAL))
    assert plano.modelo == TEXTO
    assert "butterfly haircut" in plano.campos["prompt"]
    assert "butter blonde" in plano.campos["prompt"]


def test_opcoes_publicadas_diferentes_mandam_para_o_texto():
    """Se a Replicate publicar opções diferentes das esperadas, nada inválido sai."""
    plano = planejar(interpretar("Chanel", "Loiro"), CONFIG, esquema(PRINCIPAL, "opcoes_diferentes"))
    assert plano.modelo == TEXTO


def test_principal_que_aceita_texto_recebe_a_descricao():
    plano = planejar(interpretar("Bob com franja", "", manter_cor=True), CONFIG, esquema(PRINCIPAL, "principal_texto_livre"))
    assert plano.modelo == PRINCIPAL
    assert plano.modo is Modo.descricao
    assert plano.campos["haircut"].startswith('"Bob com franja"')
    assert plano.campos["hair_color"] == "No change"


def test_descricao_livre_desligada_recusa_com_motivo():
    sem_texto = Configuracao(PRINCIPAL, "")
    with pytest.raises(ValidacaoFalhou) as erro:
        planejar(interpretar("corte assimétrico", "Loiro"), sem_texto)
    assert erro.value.codigo == "descricao_livre_indisponivel"
    # Com o texto desligado, os exemplos com equivalente continuam funcionando.
    assert planejar(interpretar("Chanel", "Loiro"), sem_texto).modelo == PRINCIPAL


# --- Conferência no schema ------------------------------------------------


def test_cada_modelo_recebe_so_os_campos_que_aceita():
    for pedido, modelo in (
        (interpretar("Chanel", "Loiro"), PRINCIPAL),
        (interpretar("corte assimétrico", "Loiro"), TEXTO),
    ):
        plano = planejar(pedido, CONFIG, esquema(PRINCIPAL))
        assert plano.modelo == modelo
        publicado = esquema(modelo)
        entrada = montar_entrada(plano, FOTO, publicado)
        assert set(entrada) <= set(publicado.campos), f"{modelo}: {set(entrada) - set(publicado.campos)}"
        for nome, valor in entrada.items():
            assert publicado.campos[nome].aceita(valor), f"{modelo}.{nome}={valor!r}"


def test_campo_acessorio_fora_do_schema_sai_do_envio():
    plano = planejar(interpretar("Chanel", "Loiro"), CONFIG)
    minimo = EsquemaModelo(
        PRINCIPAL,
        "v1",
        {
            "input_image": Campo("input_image", "string", obrigatorio=True),
            "haircut": Campo("haircut", opcoes=("No change", "Bob")),
            "hair_color": Campo("hair_color", opcoes=("No change", "Blonde")),
        },
    )
    entrada = montar_entrada(plano, FOTO, minimo)
    assert set(entrada) == {"input_image", "haircut", "hair_color"}


def test_campo_essencial_fora_do_schema_para_antes_de_gastar():
    plano = planejar(interpretar("corte assimétrico", "Loiro"), CONFIG)
    sem_prompt = EsquemaModelo(TEXTO, "v1", {"input_image": Campo("input_image", "string")})
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, FOTO, sem_prompt)
    assert erro.value.codigo == "modelo_incompativel"


def test_valor_essencial_fora_das_opcoes_para_antes_de_gastar():
    plano = planejar(interpretar("Chanel", "Loiro"), CONFIG)  # sem schema: supõe "Bob"
    outras_opcoes = EsquemaModelo(
        PRINCIPAL,
        "v1",
        {
            "input_image": Campo("input_image", "string"),
            "haircut": Campo("haircut", opcoes=("No change", "Short")),
            "hair_color": Campo("hair_color", opcoes=("No change", "Blonde")),
        },
    )
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, FOTO, outras_opcoes)
    assert erro.value.codigo == "parametro_fora_do_schema"


def test_campo_obrigatorio_que_o_sistema_nao_envia():
    plano = planejar(interpretar("Chanel", "Loiro"), CONFIG)
    exige_mais = esquema(PRINCIPAL)
    exige_mais.campos["seed"] = Campo("seed", "integer", obrigatorio=True)
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, FOTO, exige_mais)
    assert erro.value.codigo == "modelo_incompativel"


def test_leitura_do_schema_resolve_referencias_de_opcoes():
    publicado = esquema(PRINCIPAL)
    assert publicado.versao == "v1"
    assert publicado.campos["input_image"].obrigatorio
    assert "Pixie Cut" in publicado.campos["haircut"].opcoes
    assert publicado.campos["gender"].opcoes == ("none", "male", "female")
    assert ler_esquema(PRINCIPAL, {"latest_version": None}) is None


# --- Gênero do corte (campo `gender` do change-haircut) ----------------------


def test_genero_aceita_so_os_valores_do_modelo():
    assert GENEROS == ("none", "male", "female")
    for valor in GENEROS:
        assert interpretar("Chanel", "Loiro", genero=valor).genero == valor
    # Ausente ou vazio: o padrão do modelo, como antes de a opção existir.
    assert interpretar("Chanel", "Loiro").genero == "none"
    assert interpretar("Chanel", "Loiro", genero="").genero == "none"
    assert interpretar("Chanel", "Loiro", genero=None).genero == "none"


@pytest.mark.parametrize("invalido", ["Feminino", "FEMALE", "masculino", "other", "female "])
def test_genero_fora_dos_valores_e_recusado(invalido):
    with pytest.raises(ValidacaoFalhou) as erro:
        interpretar("Chanel", "Loiro", genero=invalido)
    assert erro.value.codigo == "genero_invalido"


def test_genero_sobrevive_a_reconstrucao_do_pedido():
    """A geração roda em segundo plano e remonta o pedido do que foi gravado."""
    for valor in GENEROS:
        original = interpretar("Pixie", "Loiro mel", genero=valor)
        assert pedido_registrado(original.rotulo_corte, original.rotulo_cor, valor) == original
    assert pedido_registrado("Pixie", "Loiro mel").genero == "none"


@pytest.mark.parametrize("valor", ["none", "male", "female"])
def test_genero_vai_ao_principal_junto_dos_outros_parametros(valor):
    publicado = esquema(PRINCIPAL)
    plano = planejar(interpretar("Pixie", "Loiro mel", genero=valor), CONFIG, publicado)
    assert plano.modelo == PRINCIPAL
    entrada = montar_entrada(plano, FOTO, publicado)
    assert entrada == {
        "input_image": FOTO,
        "haircut": "Pixie Cut",
        "hair_color": "Honey Blonde",
        "gender": valor,
        "aspect_ratio": "match_input_image",
        "output_format": "jpg",
    }


def test_genero_escolhido_e_essencial_e_nao_especificado_nao():
    assert "gender" in planejar(interpretar("Chanel", "Loiro", genero="female"), CONFIG).essenciais
    assert "gender" in planejar(interpretar("Chanel", "Loiro", genero="male"), CONFIG).essenciais
    assert "gender" not in planejar(interpretar("Chanel", "Loiro"), CONFIG).essenciais


def test_genero_vai_tambem_quando_so_a_cor_muda():
    plano = planejar(interpretar("", "Ruivo", manter_corte=True, genero="male"), CONFIG, esquema(PRINCIPAL))
    assert plano.campos["haircut"] == "No change"
    assert plano.campos["gender"] == "male"


def test_genero_vai_ao_principal_que_aceita_texto():
    plano = planejar(
        interpretar("Bob com franja", "", manter_cor=True, genero="female"),
        CONFIG,
        esquema(PRINCIPAL, "principal_texto_livre"),
    )
    assert plano.modelo == PRINCIPAL and plano.modo is Modo.descricao
    assert plano.campos["gender"] == "female"


def test_instrucao_registrada_mostra_o_genero_escolhido():
    assert planejar(interpretar("Pixie", "Ruivo"), CONFIG).instrucao == "haircut=Pixie Cut; hair_color=Copper"
    assert (
        planejar(interpretar("Pixie", "Ruivo", genero="female"), CONFIG).instrucao
        == "haircut=Pixie Cut; hair_color=Copper; gender=female"
    )


def test_modelo_sem_campo_de_genero_para_se_o_genero_foi_escolhido():
    """O valor escolhido não pode ser trocado em silêncio pelo padrão do modelo."""
    sem_genero = esquema(PRINCIPAL)
    del sem_genero.campos["gender"]
    escolhido = planejar(interpretar("Chanel", "Loiro", genero="male"), CONFIG, sem_genero)
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(escolhido, FOTO, sem_genero)
    assert erro.value.codigo == "modelo_incompativel"
    # "Não especificar" é o padrão do modelo: sem o campo, sai do envio e nada muda.
    neutro = planejar(interpretar("Chanel", "Loiro"), CONFIG, sem_genero)
    assert "gender" not in montar_entrada(neutro, FOTO, sem_genero)


def test_valor_de_genero_fora_das_opcoes_publicadas_para_antes_de_gastar():
    publicado = esquema(PRINCIPAL)
    publicado.campos["gender"] = Campo("gender", "string", opcoes=("none", "female"))
    plano = planejar(interpretar("Chanel", "Loiro", genero="male"), CONFIG, publicado)
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, FOTO, publicado)
    assert erro.value.codigo == "parametro_fora_do_schema"


def test_modelo_de_texto_recebe_o_genero_na_instrucao_e_nao_como_campo():
    publicado = esquema(TEXTO)
    for valor, frase in (("female", "It is a women's haircut."), ("male", "It is a men's haircut.")):
        plano = planejar(interpretar("corte assimétrico", "Loiro", genero=valor), CONFIG, esquema(PRINCIPAL))
        assert plano.modelo == TEXTO
        assert "gender" not in plano.campos
        assert frase in plano.campos["prompt"]
        assert set(montar_entrada(plano, FOTO, publicado)) == {"input_image", "prompt", "aspect_ratio", "output_format"}
    # Sem gênero escolhido, a instrução é a mesma de antes da opção existir.
    sem = planejar(interpretar("corte assimétrico", "Loiro"), CONFIG, esquema(PRINCIPAL))
    assert "It is a" not in sem.campos["prompt"]
    # Corte mantido: não há corte novo a que o gênero se refira.
    so_cor = planejar(interpretar("", "loiro com raiz esfumada", manter_corte=True, genero="female"), CONFIG, esquema(PRINCIPAL))
    assert so_cor.modelo == TEXTO and "women's haircut" not in so_cor.campos["prompt"]
