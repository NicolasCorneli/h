"""Caminho `instrucao` (AI_ESTRATEGIA=instrucao) com o `google/nano-banana-2.1`.

Três camadas, como no resto da suíte:

1. a escolha e a montagem (`planos`, `instrucoes`), sem rede;
2. o cliente real da Replicate (`ProvedorReplicate`) contra HTTP simulado
   (`httpx.MockTransport`), para inspecionar byte a byte o que sai do sistema;
3. a API inteira contra o servidor que imita a Replicate (`mock_provedor_ia`), do envio da
   foto ao registro da simulação.

O schema usado é cópia do publicado pela Replicate em 2026-11-05 (ver o mock). Nenhum teste
chama o serviço real: a qualidade das imagens se mede com `scripts/comparar_simulacoes.py`.
"""

from __future__ import annotations

import base64
import io
import json
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from app.core import config as modulo_config
from app.services.ai.base import EntradaSimulacao, FalhaDoProvedor
from app.services.ai.esquema import ler_esquema
from app.services.ai.instrucoes import PESSOA
from app.services.ai.pedido import interpretar
from app.services.ai.planos import Configuracao, Modo, montar_entrada, planejar
from app.services.ai.replicate import ProvedorReplicate, limpar_cache_de_esquemas
from app.services.catalogo import opcao_de_corte
from app.services.validacao_foto import validar_e_normalizar
from tests import mock_provedor_ia
from tests.fabricas import retrato_valido
from tests.test_simulacao_com_mock_ia import (  # noqa: F401 - fixture usada por nome
    aguardar_desfecho,
    cliente_com_aceite,
    gerar_pedido,
    provedor_de_mentira,
)

NANO = "google/nano-banana-2.1"
CONFIG_NANO = Configuracao(
    modelo_principal="flux-kontext-apps/change-haircut",
    modelo_texto=NANO,
    caminho="instrucao",
)
#: Tudo o que pode sair para o Nano Banana. Qualquer outra chave é vazamento.
CAMPOS_PERMITIDOS = {
    "prompt",
    "image_input",
    "aspect_ratio",
    "resolution",
    "output_format",
    "google_search",
    "image_search",
}


def esquema_nano():
    schema = mock_provedor_ia._schema_do_modelo(NANO)
    return ler_esquema(NANO, {"latest_version": {"id": "v-nano", "openapi_schema": schema}})


# --- 1. Escolha e montagem -------------------------------------------------


def test_exemplo_do_catalogo_vai_ao_nano_com_a_descricao_completa():
    """No caminho `instrucao`, nem os exemplos com opção no change-haircut vão a ele."""
    plano = planejar(interpretar("Chanel", "Ruivo"), CONFIG_NANO)

    assert plano.modo == Modo.instrucao
    assert plano.modelo == NANO
    prompt = plano.campos["prompt"]
    assert opcao_de_corte("Chanel").detalhe in prompt
    assert "natural ginger red" in prompt
    assert "haircut" not in plano.campos and "hair_color" not in plano.campos
    assert plano.instrucao == prompt, "a instrução gravada é a que vai ao modelo"


def test_texto_livre_segue_como_foi_escrito_com_os_termos():
    plano = planejar(interpretar("franja cortininha e camadas", "loiro com mechas finas"), CONFIG_NANO)
    prompt = plano.campos["prompt"]
    assert '"franja cortininha e camadas"' in prompt
    assert "curtain bangs" in prompt
    assert '"loiro com mechas finas"' in prompt


def test_manter_corte_e_manter_cor_viram_frases_explicitas():
    so_cor = planejar(interpretar(None, "Loiro mel", manter_corte=True), CONFIG_NANO).campos["prompt"]
    assert "Keep the current haircut exactly as it is" in so_cor
    assert "New haircut" not in so_cor
    assert "honey blonde" in so_cor

    so_corte = planejar(interpretar("Pixie", None, manter_cor=True), CONFIG_NANO).campos["prompt"]
    assert "Keep the current hair color exactly as it is" in so_corte
    assert "New hair color" not in so_corte


@pytest.mark.parametrize(
    ("genero", "frase"),
    [
        ("female", "It is a women's haircut."),
        ("male", "It is a men's haircut."),
        ("none", "It is a gender-neutral haircut"),
    ],
)
def test_genero_do_corte_vira_frase_da_instrucao(genero, frase):
    """"Neutro" (none) é uma escolha, e não ausência: vira frase própria."""
    prompt = planejar(interpretar("Pixie", "Loiro", genero=genero), CONFIG_NANO).campos["prompt"]
    assert frase in prompt
    outras = {"It is a women's haircut.", "It is a men's haircut.", "It is a gender-neutral haircut"} - {frase}
    assert not any(outra in prompt for outra in outras)


def test_genero_nao_aparece_quando_o_corte_e_mantido():
    """O gênero descreve o corte novo: sem corte novo, não há o que qualificar."""
    prompt = planejar(
        interpretar(None, "Loiro", manter_corte=True, genero="female"), CONFIG_NANO
    ).campos["prompt"]
    assert "women's" not in prompt


def test_instrucao_manda_preservar_tudo_alem_do_cabelo():
    prompt = planejar(interpretar("Pixie", "Loiro"), CONFIG_NANO).campos["prompt"]
    assert "change only the hair" in prompt
    assert PESSOA in prompt
    for elemento in ("face", "identity", "expression", "skin tone", "clothing", "background", "lighting", "framing"):
        assert elemento in prompt, f"a instrução não manda preservar: {elemento}"


def test_montagem_confere_contra_o_schema_publicado():
    plano = planejar(interpretar("Chanel", "Ruivo"), CONFIG_NANO)
    entrada = montar_entrada(plano, "data:image/jpeg;base64,AAAA", esquema_nano())

    assert entrada["image_input"] == ["data:image/jpeg;base64,AAAA"], "a foto vai numa lista"
    assert entrada["aspect_ratio"] == "match_input_image"
    assert entrada["resolution"] == "1K"
    assert entrada["output_format"] == "jpg"
    assert entrada["google_search"] is False and entrada["image_search"] is False
    assert set(entrada) == CAMPOS_PERMITIDOS


def test_resolucao_vem_da_configuracao():
    config = Configuracao("x/y", NANO, caminho="instrucao", resolucao="2K")
    plano = planejar(interpretar("Chanel", "Ruivo"), config)
    assert montar_entrada(plano, "data:,", esquema_nano())["resolution"] == "2K"


def test_schema_sem_image_input_para_antes_de_gastar(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mock_provedor_ia, "cenario", "nano_sem_image_input")
    plano = planejar(interpretar("Chanel", "Ruivo"), CONFIG_NANO)
    with pytest.raises(FalhaDoProvedor) as erro:
        montar_entrada(plano, "data:,", esquema_nano())
    assert erro.value.codigo == "modelo_incompativel"


def test_nano_como_modelo_de_texto_no_caminho_especializado_recebe_o_formato_dele():
    """Descrição livre no caminho especializado com o Nano no AI_MODELO_TEXTO: o perfil
    segue o modelo, não o caminho."""
    config = Configuracao("flux-kontext-apps/change-haircut", NANO)
    plano = planejar(interpretar("Butterfly", "Ruivo"), config)
    assert plano.modo == Modo.descricao
    assert plano.campo_imagem == "image_input" and plano.imagem_em_lista


def test_caminho_atual_continua_igual():
    """A configuração antiga produz exatamente o envio de antes."""
    atual = Configuracao("flux-kontext-apps/change-haircut", "black-forest-labs/flux-kontext-pro")
    opcoes = planejar(interpretar("Chanel", "Ruivo"), atual)
    assert opcoes.modo == Modo.opcoes
    assert opcoes.modelo == "flux-kontext-apps/change-haircut"
    assert opcoes.instrucao == "haircut=Bob; hair_color=Copper"

    livre = planejar(interpretar("Butterfly", "Ruivo"), atual)
    assert livre.modelo == "black-forest-labs/flux-kontext-pro"
    assert set(livre.campos) == {"prompt", "aspect_ratio", "output_format"}
    assert livre.campos["prompt"].startswith("Edit only the hair of the person in this photo.")
    assert montar_entrada(livre, "data:,", None)["input_image"] == "data:,"


# --- Configuração ----------------------------------------------------------


def test_caminho_instrucao_exige_modelo_de_texto(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_ESTRATEGIA", "instrucao")
    monkeypatch.setenv("AI_MODELO_TEXTO", "")
    with pytest.raises(ValidationError, match="AI_MODELO_TEXTO"):
        modulo_config.Configuracao()


def test_expiracao_precisa_passar_do_tempo_limite(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_TIMEOUT_S", "300")
    monkeypatch.setenv("SIMULACAO_EXPIRA_MIN", "5")
    with pytest.raises(ValidationError, match="SIMULACAO_EXPIRA_MIN"):
        modulo_config.Configuracao()


def test_resolucao_fora_das_opcoes_e_recusada(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_RESOLUCAO", "8K")
    with pytest.raises(ValidationError):
        modulo_config.Configuracao()


# --- 2. Cliente da Replicate, HTTP simulado --------------------------------


@pytest.fixture
def nano_configurado(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "token-de-teste")
    monkeypatch.setenv("AI_ESTRATEGIA", "instrucao")
    monkeypatch.setenv("AI_MODELO_TEXTO", NANO)
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0")
    modulo_config.obter_config.cache_clear()
    limpar_cache_de_esquemas()
    mock_provedor_ia.reiniciar()
    yield
    monkeypatch.undo()
    modulo_config.obter_config.cache_clear()
    limpar_cache_de_esquemas()


def usar_transporte(monkeypatch: pytest.MonkeyPatch, manipulador) -> None:
    transporte = httpx.MockTransport(manipulador)
    original = httpx.Client

    def fabrica(*args, **kwargs):
        kwargs["transport"] = transporte
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fabrica)


def jpeg(cor=(120, 60, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), cor).save(buffer, format="JPEG")
    return buffer.getvalue()


class ReplicateDeMentira:
    """Responde como a Replicate e guarda cada requisição para inspeção."""

    def __init__(self, predicao: dict | None = None, status_criacao: int = 201):
        self.requisicoes: list[httpx.Request] = []
        self.corpos: list[dict] = []
        self.predicao = predicao or {
            "id": "p1",
            "status": "succeeded",
            "output": "https://replicate.delivery/saida.jpg",
            "urls": {"get": "https://api.replicate.com/v1/predictions/p1"},
        }
        self.status_criacao = status_criacao

    def __call__(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        caminho = requisicao.url.path
        if requisicao.method == "GET" and caminho.startswith("/v1/models/"):
            modelo = caminho.removeprefix("/v1/models/")
            schema = mock_provedor_ia._schema_do_modelo(modelo)
            return httpx.Response(200, json={"latest_version": {"id": "v1", "openapi_schema": schema}})
        if caminho == f"/v1/models/{NANO}/predictions":
            self.corpos.append(json.loads(requisicao.read()))
            return httpx.Response(self.status_criacao, json=self.predicao)
        if caminho == "/saida.jpg":
            return httpx.Response(200, content=jpeg((90, 50, 30)), headers={"content-type": "image/jpeg"})
        return httpx.Response(404, json={"detail": "rota inesperada"})


def gerar_no_nano(foto: bytes | None = None, corte="Chanel", cor="Ruivo"):
    return ProvedorReplicate().gerar(
        EntradaSimulacao(imagem=foto or retrato_valido(), mime="image/jpeg", pedido=interpretar(corte, cor))
    )


def test_sucesso_registra_o_modelo_e_a_instrucao(monkeypatch, nano_configurado):
    replicate = ReplicateDeMentira()
    usar_transporte(monkeypatch, replicate)

    saida = gerar_no_nano()

    assert saida.modelo == NANO
    assert saida.instrucao.startswith("Using the provided photo of a real person")
    consultados = [r.url.path for r in replicate.requisicoes if r.method == "GET" and "/models/" in r.url.path]
    assert consultados == [f"/v1/models/{NANO}"], "no caminho instrucao, o AI_MODELO não é consultado"


def test_so_a_foto_e_a_instrucao_saem_do_sistema(monkeypatch, nano_configurado):
    """Minimização: o corpo da predição tem só `input`, e nele só os campos do modelo."""
    replicate = ReplicateDeMentira()
    usar_transporte(monkeypatch, replicate)

    gerar_no_nano()

    (corpo,) = replicate.corpos
    assert set(corpo) == {"input"}, f"o corpo leva mais que a entrada: {sorted(corpo)}"
    assert set(corpo["input"]) == CAMPOS_PERMITIDOS
    (foto,) = corpo["input"]["image_input"]
    assert foto.startswith("data:image/jpeg;base64,"), "a foto vai embutida, sem URL pública"
    assert corpo["input"]["google_search"] is False
    assert corpo["input"]["image_search"] is False


def test_foto_sai_sem_exif(monkeypatch, nano_configurado):
    """Mesmo que chegue aqui uma foto com EXIF, ela sai sem ele."""
    exif = Image.Exif()
    exif[0x010F] = "Fabricante do celular"  # Make
    exif[0x0132] = "2026:11:05 10:00:00"  # DateTime
    buffer = io.BytesIO()
    Image.open(io.BytesIO(retrato_valido())).save(buffer, format="JPEG", exif=exif)
    com_exif = buffer.getvalue()
    assert Image.open(io.BytesIO(com_exif)).getexif(), "a foto de teste precisa ter EXIF"

    replicate = ReplicateDeMentira()
    usar_transporte(monkeypatch, replicate)
    gerar_no_nano(com_exif)

    (corpo,) = replicate.corpos
    (foto,) = corpo["input"]["image_input"]
    enviada = Image.open(io.BytesIO(base64.b64decode(foto.split(",", 1)[1])))
    assert not enviada.getexif(), "a foto saiu com EXIF"


def test_validacao_tambem_remove_o_exif():
    """A primeira barreira: a foto guardada (e depois enviada) já não tem EXIF."""
    exif = Image.Exif()
    exif[0x010F] = "Fabricante do celular"
    buffer = io.BytesIO()
    Image.open(io.BytesIO(retrato_valido())).save(buffer, format="JPEG", exif=exif)

    validada = validar_e_normalizar(buffer.getvalue(), validar_rosto=False)

    assert not Image.open(io.BytesIO(validada.conteudo)).getexif()


@pytest.mark.parametrize(
    ("predicao", "codigo"),
    [
        (
            {"id": "p", "status": "failed", "error": "Image generation blocked: finish_reason=IMAGE_SAFETY"},
            "conteudo_bloqueado",
        ),
        (
            {"id": "p", "status": "failed", "error": "The request was rejected: PROHIBITED_CONTENT"},
            "conteudo_bloqueado",
        ),
        (
            {"id": "p", "status": "failed", "error": "Google API error: 500 INTERNAL"},
            "falha_na_geracao",
        ),
        ({"id": "p", "status": "succeeded", "output": None, "urls": {"get": "x"}}, "resposta_invalida"),
        ({"id": "p", "status": "succeeded", "output": [], "urls": {"get": "x"}}, "resposta_invalida"),
    ],
)
def test_falhas_do_nano_caem_nos_codigos_tratados_pelo_app(monkeypatch, nano_configurado, predicao, codigo):
    usar_transporte(monkeypatch, ReplicateDeMentira(predicao))
    with pytest.raises(FalhaDoProvedor) as erro:
        gerar_no_nano()
    assert erro.value.codigo == codigo


def test_parametro_recusado_pelo_provedor(monkeypatch, nano_configurado):
    usar_transporte(monkeypatch, ReplicateDeMentira({"detail": "invalid"}, status_criacao=422))
    with pytest.raises(FalhaDoProvedor) as erro:
        gerar_no_nano()
    assert erro.value.codigo == "entrada_recusada"


def test_tempo_esgotado(monkeypatch, nano_configurado):
    def lento(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.method == "POST":
            raise httpx.ReadTimeout("tempo esgotado", request=requisicao)
        return ReplicateDeMentira()(requisicao)

    usar_transporte(monkeypatch, lento)
    with pytest.raises(FalhaDoProvedor) as erro:
        gerar_no_nano()
    assert erro.value.codigo == "timeout"


def test_configuracao_explicita_permite_comparar_os_caminhos(monkeypatch, nano_configurado):
    """O script de comparação gera pelo caminho atual com o mesmo servidor configurado."""
    atual = Configuracao("flux-kontext-apps/change-haircut", "black-forest-labs/flux-kontext-pro")
    criadas: list[str] = []
    replicate = ReplicateDeMentira()

    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.method == "POST" and requisicao.url.path.endswith("/predictions"):
            criadas.append(requisicao.url.path)
            return httpx.Response(201, json=replicate.predicao)
        return replicate(requisicao)

    usar_transporte(monkeypatch, manipulador)
    saida = ProvedorReplicate(atual).gerar(
        EntradaSimulacao(imagem=retrato_valido(), mime="image/jpeg", pedido=interpretar("Chanel", "Ruivo"))
    )
    assert saida.modelo == "flux-kontext-apps/change-haircut"
    assert criadas == ["/v1/models/flux-kontext-apps/change-haircut/predictions"]


# --- 3. A API inteira contra o servidor que imita a Replicate --------------


@pytest.fixture
def api_com_nano(provedor_de_mentira: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "token-de-teste-que-nao-existe-de-verdade")
    monkeypatch.setenv("AI_BASE_URL", provedor_de_mentira)
    monkeypatch.setenv("AI_ESTRATEGIA", "instrucao")
    monkeypatch.setenv("AI_MODELO_TEXTO", NANO)
    monkeypatch.setenv("AI_INTERVALO_CONSULTA_S", "0")
    monkeypatch.setenv("AI_TIMEOUT_S", "3")
    modulo_config.obter_config.cache_clear()
    limpar_cache_de_esquemas()
    mock_provedor_ia.reiniciar()
    yield
    monkeypatch.undo()
    modulo_config.obter_config.cache_clear()
    limpar_cache_de_esquemas()


def simular_no_nano(cliente_http: TestClient, cabecalhos, cenario="sucesso", **campos) -> dict:
    mock_provedor_ia.reiniciar(cenario)
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], **campos)
    assert resposta.status_code == 202, resposta.text
    return aguardar_desfecho(cliente_http, cabecalhos, resposta.json()["id"])


def test_simulacao_registra_o_nano_como_modelo(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    estado = simular_no_nano(cliente_http, cabecalhos, corte="Pixie", cor="Loiro mel", genero="female")

    assert estado["status"] == "concluida"
    assert estado["modeloIa"] == NANO
    assert "pixie cut" in estado["instrucaoIa"] and "It is a women's haircut." in estado["instrucaoIa"]
    (predicao,) = [c for c in mock_provedor_ia.chamadas if "input" in c]
    assert predicao["modelo"] == NANO
    assert set(predicao["input"]) == CAMPOS_PERMITIDOS
    assert len(predicao["input"]["image_input"]) == 1
    assert mock_provedor_ia.consultas_de_esquema == [NANO]


def test_dados_do_cliente_nao_vao_ao_nano(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    simular_no_nano(cliente_http, cabecalhos, corte="Chanel", cor="Ruivo", observacoes="alergia a amônia")

    (predicao,) = [c for c in mock_provedor_ia.chamadas if "input" in c]
    como_texto = json.dumps(predicao, ensure_ascii=False)
    for proibido in ("Marina", "Alves", "alergia", "amônia", "telefone"):
        assert proibido not in como_texto, f"dado do cliente vazou para o provedor: {proibido}"


@pytest.mark.parametrize(
    ("cenario", "codigo"),
    [
        ("bloqueio_do_google", "conteudo_bloqueado"),
        ("erro_do_google", "falha_na_geracao"),
        ("sem_saida", "resposta_invalida"),
        ("entrada_recusada", "entrada_recusada"),
        ("timeout", "timeout"),
        ("nano_sem_image_input", "modelo_incompativel"),
    ],
)
def test_falhas_terminam_com_codigo_que_a_tela_explica(
    cliente_http: TestClient, conta, api_com_nano, cenario, codigo
):
    cabecalhos, _ = conta()
    mock_provedor_ia.reiniciar(cenario)
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = gerar_pedido(cliente_http, cabecalhos, cliente["id"], corte="Chanel", cor="Ruivo")
    if cenario == "nano_sem_image_input":
        # Schema incompatível para antes de criar a simulação: nada é cobrado.
        assert resposta.status_code == 502, resposta.text
        assert resposta.json()["erro"]["codigo"] == codigo
        assert not [c for c in mock_provedor_ia.chamadas if "input" in c]
        return
    assert resposta.status_code == 202, resposta.text
    estado = aguardar_desfecho(cliente_http, cabecalhos, resposta.json()["id"])
    assert estado["status"] == "falhou"
    assert estado["erroCodigo"] == codigo


def test_previa_do_pedido_mostra_o_caminho_instrucao(cliente_http: TestClient, conta, api_com_nano):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/simulacoes/plano", headers=cabecalhos, json={"corte": "Chanel", "cor": "Ruivo"}
    )
    assert resposta.status_code == 200, resposta.text
    plano = resposta.json()
    assert plano["modo"] == "instrucao"
    assert plano["modelo"] == NANO
    assert plano["descricaoModo"]


def test_saude_informa_o_caminho_em_vigor(cliente_http: TestClient, api_com_nano):
    estado = cliente_http.get("/api/v1/saude").json()
    assert estado["modeloIa"] == NANO
    assert estado["modelosIa"] == {
        "estrategia": "instrucao",
        "principal": None,
        "texto": NANO,
        "resolucao": "1K",
    }
