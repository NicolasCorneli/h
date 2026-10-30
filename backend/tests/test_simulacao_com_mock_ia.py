"""Fluxo da simulação contra o mock do provedor, nos sete cenários pedidos.

Aqui o cliente real (`ProvedorReplicate`) fala com um servidor HTTP de mentira, levantado
em uma porta local. Não há substituição do provedor: `AI_PROVIDER=replicate` e
`AI_BASE_URL` apontando para o mock. O que se testa é o código que rodará em produção.

Nenhuma chamada a serviço externo acontece em nenhum destes testes.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.core import config as modulo_config
from tests import mock_provedor_ia
from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def provedor_de_mentira() -> Iterator[str]:
    """Sobe o mock em uma thread e devolve o endereço base dele."""
    porta = porta_livre()
    configuracao = uvicorn.Config(
        mock_provedor_ia.app, host="127.0.0.1", port=porta, log_level="warning"
    )
    servidor = uvicorn.Server(configuracao)
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()

    limite = time.monotonic() + 15
    while not servidor.started:
        if time.monotonic() > limite:  # pragma: no cover - ambiente muito lento
            raise RuntimeError("o mock do provedor não subiu")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{porta}"

    servidor.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def api_com_provedor(
    provedor_de_mentira: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Aponta a aplicação para o mock, com tempo limite curto e sem espera entre consultas."""
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "token-de-teste-que-nao-existe-de-verdade")
    monkeypatch.setenv("AI_BASE_URL", provedor_de_mentira)
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0")
    monkeypatch.setenv("AI_TIMEOUT_S", "3")
    modulo_config.obter_config.cache_clear()
    mock_provedor_ia.reiniciar()
    yield
    monkeypatch.undo()
    modulo_config.obter_config.cache_clear()


def cliente_com_aceite(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    return cliente


def gerar(cliente_http: TestClient, cabecalhos, cliente_id: str, foto=None):
    return cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={
            "clienteId": cliente_id,
            "corte": "Chanel",
            "cor": "Ruivo",
            "observacoes": "",
        },
        files=arquivo_de_foto(foto),
    )


def aguardar_desfecho(cliente_http: TestClient, cabecalhos, simulacao_id: str) -> dict:
    """Consulta até a simulação sair de `processando`.

    O processamento roda em segundo plano; o TestClient executa a tarefa ao fim da
    requisição, então na prática o primeiro GET já encontra o desfecho.
    """
    for _ in range(80):
        estado = cliente_http.get(
            f"/api/v1/simulacoes/{simulacao_id}", headers=cabecalhos
        ).json()
        if estado["status"] != "processando":
            return estado
        time.sleep(0.1)
    raise AssertionError("a simulação ficou presa em processando")


def simular(cliente_http: TestClient, cabecalhos, cenario: str) -> dict:
    mock_provedor_ia.reiniciar(cenario)
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar(cliente_http, cabecalhos, cliente["id"])
    assert resposta.status_code == 202, resposta.text
    return aguardar_desfecho(cliente_http, cabecalhos, resposta.json()["id"])


# --- Cenário 1: sucesso ---------------------------------------------------


def test_sucesso(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "sucesso")

    assert estado["status"] == "concluida"
    assert estado["imgSaidaUri"], "a simulação concluiu sem imagem de saída"
    assert estado["provedor"] == "replicate"
    assert mock_provedor_ia.chamadas, "o provedor não foi chamado"


def test_a_imagem_gerada_e_servida_ao_aplicativo(cliente_http: TestClient, conta, api_com_provedor):
    """O resultado tem de chegar à tela: URL assinada que devolve imagem de verdade."""
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "sucesso")

    caminho = estado["imgSaidaUri"].replace("http://testserver", "")
    imagem = cliente_http.get(caminho)
    assert imagem.status_code == 200
    assert imagem.headers["content-type"] == "image/jpeg"
    assert imagem.content[:2] == b"\xff\xd8", "o que chega à tela não é JPEG"


# --- Cenários 2 a 7: as falhas -------------------------------------------


@pytest.mark.parametrize(
    ("cenario", "codigo_esperado"),
    [
        ("erro_4xx", "credencial_invalida"),
        ("sem_credito", "sem_credito"),
        ("erro_5xx", None),
        ("limite", "limite_do_provedor"),
        ("timeout", "timeout"),
        ("malformada", "resposta_invalida"),
        ("vazia", "resposta_invalida"),
        ("predicao_falhou", "falha_na_geracao"),
        ("bloqueio_de_seguranca", "conteudo_bloqueado"),
        ("imagem_invalida", "resposta_invalida"),
        ("sem_saida", "resposta_invalida"),
        ("entrada_recusada", "entrada_recusada"),
    ],
)
def test_falhas_do_provedor(
    cliente_http: TestClient, conta, api_com_provedor, cenario, codigo_esperado
):
    """Toda falha do provedor termina em `falhou` com motivo registrado — nunca presa.

    O código exato importa menos que a garantia: a simulação não fica em processando
    para sempre, e o motivo registrado permite distinguir o que aconteceu.
    """
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, cenario)

    assert estado["status"] == "falhou", f"cenário {cenario} não terminou em falhou"
    assert estado["erroCodigo"], f"cenário {cenario} falhou sem registrar motivo"
    if codigo_esperado:
        assert estado["erroCodigo"] == codigo_esperado, (
            f"cenário {cenario}: motivo {estado['erroCodigo']}, esperado {codigo_esperado}"
        )
    assert not estado["imgSaidaUri"], "falhou, mas registrou imagem de saída"


def test_resposta_lenta_conclui_dentro_do_tempo(cliente_http: TestClient, conta, api_com_provedor):
    """Lento não é falha: enquanto estiver dentro do tempo limite, tem de concluir."""
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "lento")

    assert estado["status"] == "concluida", "uma resposta lenta foi tratada como falha"
    assert estado["tempoMs"] >= 1000, "o tempo medido não reflete a demora real"


def test_conteudo_que_nao_e_imagem_culpa_o_provedor(
    cliente_http: TestClient, conta, api_com_provedor
):
    """O provedor responde 200 com tipo de imagem, mas devolve HTML.

    O motivo registrado tem de apontar o provedor, não o armazenamento: culpar o
    componente errado manda a investigação para o lado oposto do problema.
    """
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "imagem_invalida")

    assert estado["status"] == "falhou"
    assert estado["erroCodigo"] == "resposta_invalida"
    assert estado["erroCodigo"] != "falha_no_armazenamento"


# --- O que não deve chegar ao provedor -----------------------------------


def test_sem_consentimento_o_provedor_nao_e_chamado(
    cliente_http: TestClient, conta, api_com_provedor
):
    """A verificação mais importante do sistema, do ponto de vista da LGPD.

    Não basta a API recusar: nenhum byte da fotografia pode sair para o terceiro. A
    lista de chamadas recebidas pelo mock prova isso diretamente.
    """
    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar("sucesso")
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Sem Aceite", "telefone": "1"}
    ).json()

    resposta = gerar(cliente_http, cabecalhos, cliente["id"])

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["erro"]["codigo"] == "consentimento_invalido"
    assert mock_provedor_ia.chamadas == [], (
        "a foto foi enviada ao provedor sem consentimento registrado"
    )
    assert mock_provedor_ia.consultas_de_esquema == [], "o provedor foi consultado sem consentimento"


def test_foto_invalida_nao_chega_ao_provedor(cliente_http: TestClient, conta, api_com_provedor):
    """A validação da foto é a barreira que antecede a chamada paga."""
    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar("sucesso")
    cliente = cliente_com_aceite(cliente_http, cabecalhos)

    resposta = gerar(cliente_http, cabecalhos, cliente["id"], foto=b"isto nao e uma imagem")

    assert resposta.status_code == 422
    assert mock_provedor_ia.chamadas == [], "uma foto recusada chegou a custar dinheiro"


def test_credencial_vai_ao_provedor_e_nao_volta_ao_aplicativo(
    cliente_http: TestClient, conta, api_com_provedor
):
    """A chave existe só no servidor: vai no cabeçalho para o provedor e em nenhuma resposta."""
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "erro_4xx")

    assert mock_provedor_ia.chamadas[0]["tem_credencial"] is True, (
        "a requisição saiu sem credencial"
    )
    # Mesmo no cenário em que o provedor devolve erro de autenticação, a resposta ao
    # aplicativo não pode conter a chave nem o corpo de erro do terceiro.
    corpo = str(estado)
    assert "token-de-teste" not in corpo
    assert "Invalid token" not in corpo


def test_so_a_imagem_e_os_parametros_saem_do_sistema(
    cliente_http: TestClient, conta, api_com_provedor
):
    """Minimização (art. 6º III): o terceiro recebe a foto e o penteado, nada mais."""
    cabecalhos, _ = conta()
    simular(cliente_http, cabecalhos, "sucesso")

    predicoes = [c for c in mock_provedor_ia.chamadas if "input" in c]
    enviado = predicoes[0]["input"]
    assert set(enviado) <= {
        "input_image",
        "haircut",
        "hair_color",
        "gender",
        "aspect_ratio",
        "output_format",
    }, f"campo inesperado enviado ao provedor: {sorted(enviado)}"

    como_texto = str(enviado)
    for proibido in ("Marina", "Alves", "telefone", "@", "nascimento"):
        assert proibido not in como_texto, f"dado do cliente vazou para o provedor: {proibido}"


# --- Personalização: cada modelo recebe o que aceita ---------------------


def gerar_pedido(cliente_http: TestClient, cabecalhos, cliente_id: str, **campos):
    dados = {"clienteId": cliente_id, "observacoes": "", **campos}
    return cliente_http.post("/api/v1/simulacoes", headers=cabecalhos, data=dados, files=arquivo_de_foto())


def simular_pedido(cliente_http: TestClient, cabecalhos, cenario: str = "sucesso", **campos) -> dict:
    mock_provedor_ia.reiniciar(cenario)
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], **campos)
    assert resposta.status_code == 202, resposta.text
    return aguardar_desfecho(cliente_http, cabecalhos, resposta.json()["id"])


def predicoes() -> list[dict]:
    return [c for c in mock_provedor_ia.chamadas if "input" in c]


def test_exemplos_vao_ao_principal_com_os_valores_das_opcoes(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, corte="Pixie", cor="Loiro mel")
    assert estado["status"] == "concluida"
    (predicao,) = predicoes()
    assert predicao["modelo"] == "flux-kontext-apps/change-haircut"
    assert predicao["input"]["haircut"] == "Pixie Cut"
    assert predicao["input"]["hair_color"] == "Honey Blonde"
    assert "prompt" not in predicao["input"], "o principal não tem campo prompt"
    assert estado["modeloIa"] == "flux-kontext-apps/change-haircut"
    assert estado["instrucaoIa"] == "haircut=Pixie Cut; hair_color=Honey Blonde"


@pytest.mark.parametrize("genero", ["female", "male", "none"])
def test_genero_escolhido_chega_ao_modelo_com_os_outros_parametros(
    cliente_http: TestClient, conta, api_com_provedor, genero
):
    """Do formulário até o corpo da predição: o valor escolhido, sem troca pelo padrão."""
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, corte="Pixie", cor="Loiro mel", genero=genero)
    assert estado["status"] == "concluida", estado
    assert estado["parametros"]["genero"] == genero
    (predicao,) = predicoes()
    assert predicao["modelo"] == "flux-kontext-apps/change-haircut"
    entrada = predicao["input"]
    assert entrada["gender"] == genero
    assert entrada["haircut"] == "Pixie Cut"
    assert entrada["hair_color"] == "Honey Blonde"
    assert entrada["aspect_ratio"] == "match_input_image"
    assert entrada["output_format"] == "jpg"
    assert entrada["input_image"].startswith("data:image/jpeg;base64,")


def test_sem_genero_no_envio_vale_o_padrao_do_modelo(cliente_http: TestClient, conta, api_com_provedor):
    """Aplicativo de versão anterior, que não manda o campo: segue como antes."""
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, corte="Pixie", cor="Loiro mel")
    assert estado["parametros"]["genero"] == "none"
    assert estado["instrucaoIa"] == "haircut=Pixie Cut; hair_color=Honey Blonde"
    (predicao,) = predicoes()
    assert predicao["input"]["gender"] == "none"


def test_genero_invalido_e_recusado_sem_chamar_o_provedor(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar("sucesso")
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Pixie", cor="Loiro", genero="feminino")
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "genero_invalido"
    assert mock_provedor_ia.chamadas == []


def test_genero_chega_ao_modelo_de_texto_pela_instrucao(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(
        cliente_http, cabecalhos, corte="Corte degradê baixo nas laterais", cor="", manterCor="true", genero="male"
    )
    assert estado["status"] == "concluida"
    (predicao,) = predicoes()
    assert predicao["modelo"] == "black-forest-labs/flux-kontext-pro"
    assert "gender" not in predicao["input"], "o modelo de texto não tem esse campo"
    assert "It is a men's haircut." in predicao["input"]["prompt"]


def test_manter_corte_vai_como_no_change(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    simular_pedido(cliente_http, cabecalhos, corte="", manterCorte="true", cor="Castanho-escuro")
    (predicao,) = predicoes()
    assert predicao["input"]["haircut"] == "No change"
    assert predicao["input"]["hair_color"] == "Dark Brown"


def test_descricao_livre_vai_ao_modelo_de_texto_so_com_campos_dele(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(
        cliente_http,
        cabecalhos,
        corte="Corte degradê baixo nas laterais, com topo médio e textura natural.",
        cor="",
        manterCor="true",
    )
    assert estado["status"] == "concluida"
    (predicao,) = predicoes()
    assert predicao["modelo"] == "black-forest-labs/flux-kontext-pro"
    assert set(predicao["input"]) == {"prompt", "input_image", "aspect_ratio", "output_format"}
    prompt = predicao["input"]["prompt"]
    assert "Corte degradê baixo nas laterais, com topo médio e textura natural." in prompt
    assert "low fade" in prompt and "Keep the current hair color" in prompt
    assert predicao["input"]["input_image"].startswith("data:image/jpeg;base64,")
    assert estado["modeloIa"] == "black-forest-labs/flux-kontext-pro"
    assert estado["instrucaoIa"] == prompt


def test_opcoes_publicadas_diferentes_nao_enviam_valor_invalido(cliente_http: TestClient, conta, api_com_provedor):
    """O schema ao vivo manda: se as opções forem outras, o exemplo vai pela descrição."""
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "opcoes_diferentes", corte="Chanel", cor="Loiro")
    assert estado["status"] == "concluida"
    (predicao,) = predicoes()
    assert predicao["modelo"] == "black-forest-labs/flux-kontext-pro"
    assert "classic chin-length bob" in predicao["input"]["prompt"]


def test_principal_que_aceita_texto_recebe_a_descricao(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    simular_pedido(cliente_http, cabecalhos, "principal_texto_livre", corte="Bob com franja", cor="", manterCor="true")
    (predicao,) = predicoes()
    assert predicao["modelo"] == "flux-kontext-apps/change-haircut"
    assert predicao["input"]["haircut"].startswith('"Bob com franja"')


def test_modelo_nao_oficial_usa_a_versao_publicada(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "nao_oficial", corte="Chanel", cor="Loiro")
    assert estado["status"] == "concluida", estado
    (predicao,) = predicoes()
    assert predicao["rota"] == "/predictions"
    assert predicao["versao"] == "versao-change-haircut"


def test_imagem_grande_vai_pela_api_de_arquivos_e_e_apagada(
    cliente_http: TestClient, conta, api_com_provedor, monkeypatch
):
    monkeypatch.setenv("AI_LIMITE_DATA_URI_KB", "1")
    modulo_config.obter_config.cache_clear()
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, corte="Chanel", cor="Loiro")
    assert estado["status"] == "concluida"
    envios = [c for c in mock_provedor_ia.chamadas if c["rota"] == "/files"]
    assert len(envios) == 1 and envios[0]["tem_credencial"]
    (predicao,) = predicoes()
    assert predicao["input"]["input_image"].startswith("http://"), "a imagem deveria ir por arquivo"
    assert len(mock_provedor_ia.apagados) == 1, "o arquivo ficou na conta do provedor"


def test_arquivo_enviado_e_apagado_mesmo_quando_a_geracao_falha(
    cliente_http: TestClient, conta, api_com_provedor, monkeypatch
):
    monkeypatch.setenv("AI_LIMITE_DATA_URI_KB", "1")
    modulo_config.obter_config.cache_clear()
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "predicao_falhou", corte="Chanel", cor="Loiro")
    assert estado["status"] == "falhou"
    assert len(mock_provedor_ia.apagados) == 1


def test_predicao_em_andamento_e_acompanhada_ate_concluir(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "processando", corte="Chanel", cor="Loiro")
    assert estado["status"] == "concluida"
    consultas = [c for c in mock_provedor_ia.chamadas if c["rota"].startswith("/predictions/")]
    assert len(consultas) >= 3


def test_predicao_que_nao_termina_e_cancelada(cliente_http: TestClient, conta, api_com_provedor, monkeypatch):
    monkeypatch.setenv("AI_TIMEOUT_S", "1")
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0.05")
    modulo_config.obter_config.cache_clear()
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "nunca_termina", corte="Chanel", cor="Loiro")
    assert estado["status"] == "falhou"
    assert estado["erroCodigo"] == "timeout"
    assert len(mock_provedor_ia.cancelamentos) == 1, "a predição esgotada não foi cancelada"


def test_modelo_sem_schema_segue_sem_conferencia(cliente_http: TestClient, conta, api_com_provedor):
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "sem_schema", corte="Chanel", cor="Loiro")
    assert estado["status"] == "concluida"


@pytest.mark.parametrize(
    ("cenario", "codigo"),
    [
        ("esquema_401", "credencial_invalida"),
        ("modelo_inexistente", "modelo_inexistente"),
        ("principal_sem_haircut", None),
    ],
)
def test_problemas_no_schema_param_antes_de_gastar(
    cliente_http: TestClient, conta, api_com_provedor, cenario, codigo
):
    """Credencial recusada ou modelo errado aparecem na hora, sem simulação nem cota gasta."""
    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar(cenario)
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Chanel", cor="Loiro")
    if codigo is None:
        # Sem o campo haircut, o exemplo vai pelo modelo de texto: nada inválido sai.
        assert resposta.status_code == 202
        aguardar_desfecho(cliente_http, cabecalhos, resposta.json()["id"])
        assert predicoes()[0]["modelo"] == "black-forest-labs/flux-kontext-pro"
        return
    assert resposta.status_code == 502, resposta.text
    assert resposta.json()["erro"]["codigo"] == codigo
    assert predicoes() == [], "uma predição foi criada apesar do problema no schema"
    lista = cliente_http.get(f"/api/v1/simulacoes?clienteId={cliente['id']}", headers=cabecalhos).json()
    assert lista == [], "nada deveria ter sido gravado"


def test_envio_repetido_gera_uma_predicao_so(cliente_http: TestClient, conta, api_com_provedor):
    import uuid

    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar("sucesso")
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    chave = str(uuid.uuid4())
    primeira = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Chanel", cor="Loiro", chaveEnvio=chave)
    segunda = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Chanel", cor="Loiro", chaveEnvio=chave)
    assert primeira.json()["id"] == segunda.json()["id"]
    aguardar_desfecho(cliente_http, cabecalhos, primeira.json()["id"])
    assert len(predicoes()) == 1, "o reenvio pagou outra geração"


def test_log_nao_registra_imagem_nem_credencial(cliente_http: TestClient, conta, api_com_provedor, caplog):
    """O 422 do provedor pode ecoar a entrada: o log fica sem a imagem embutida."""
    import logging

    caplog.set_level(logging.DEBUG)
    cabecalhos, _ = conta()
    estado = simular_pedido(cliente_http, cabecalhos, "entrada_recusada", corte="Chanel", cor="Loiro")
    assert estado["erroCodigo"] == "entrada_recusada"
    texto = caplog.text
    assert "entrada_recusada" in texto or "recusou a entrada" in texto
    # JPEG em base64 sempre começa com "/9j/": se aparecer, a foto foi parar no log.
    assert "/9j/" not in texto, "a imagem foi parar no log"
    assert "token-de-teste-que-nao-existe-de-verdade" not in texto


# --- Leituras repetidas diante de falha transitória ---------------------------------


def test_consulta_instavel_nao_perde_a_geracao_ja_paga(
    cliente_http: TestClient, conta, api_com_provedor
):
    """Um 503 ao consultar o estado não derruba uma predição que já foi criada e cobrada."""
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "consulta_instavel")

    assert estado["status"] == "concluida", estado
    criacoes = [c for c in mock_provedor_ia.chamadas if c["rota"].endswith("/predictions")]
    assert len(criacoes) == 1, "a predição foi criada de novo, e cobrada duas vezes"


def test_download_instavel_do_resultado_e_repetido(
    cliente_http: TestClient, conta, api_com_provedor
):
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "saida_instavel")

    assert estado["status"] == "concluida", estado
    assert len(mock_provedor_ia.downloads) == 2


def test_consulta_fora_do_ar_termina_em_falha_depois_das_tentativas(
    cliente_http: TestClient, conta, api_com_provedor
):
    """A repetição é limitada: com o provedor fora do ar, a simulação falha, não trava."""
    from app.services.ai.replicate import TENTATIVAS_DE_LEITURA

    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "consulta_fora_do_ar")

    assert estado["status"] == "falhou"
    consultas = [c for c in mock_provedor_ia.chamadas if c["rota"].startswith("/predictions/")]
    assert len(consultas) == TENTATIVAS_DE_LEITURA


def test_criacao_da_predicao_com_erro_5xx_nao_e_repetida(
    cliente_http: TestClient, conta, api_com_provedor
):
    """Um 500 na criação não garante que nada foi criado: repetir poderia cobrar duas vezes."""
    cabecalhos, _ = conta()
    estado = simular(cliente_http, cabecalhos, "erro_5xx")

    assert estado["status"] == "falhou"
    criacoes = [c for c in mock_provedor_ia.chamadas if c["rota"].endswith("/predictions")]
    assert len(criacoes) == 1
