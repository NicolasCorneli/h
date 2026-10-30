"""Provedor Replicate: simulação capilar (FLUX.1 Kontext).

Ciclo de cada geração, todo no servidor (a chave `AI_API_KEY` nunca vai ao aplicativo):

1. **schema**: `GET /models/{dono}/{nome}` traz o schema de entrada publicado do modelo
   (guardado por `AI_CACHE_ESQUEMA_MIN`). É ele que diz quais campos existem e quais
   valores as opções fechadas aceitam;
2. **plano**: `planos.planejar` escolhe o modelo para o pedido e `montar_entrada` confere
   cada campo contra o schema. Campo inexistente ou valor fora das opções para aqui,
   antes de gastar;
3. **arquivo**: a foto até `AI_LIMITE_DATA_URI_KB` vai como *data URI* no
   corpo; acima disso, pela API de arquivos (`POST /files`), e o arquivo é apagado da
   Replicate ao fim, com sucesso ou falha. Nenhum dos dois caminhos expõe a foto em URL
   pública;
4. **predição**: `POST /models/{dono}/{nome}/predictions` (modelos oficiais). Se o modelo
   não for oficial (404), repete em `POST /predictions` com a versão lida do schema;
5. **espera**: consulta `urls.get` até concluir. Passado o tempo limite, pede o
   cancelamento (`urls.cancel`) para não pagar por um resultado que ninguém vai ver.

Os corpos de erro do provedor vão para o log só resumidos e sem imagem embutida.
"""

from __future__ import annotations

import base64
import io
import logging
import re
import threading
import time
from typing import Any

import httpx
from PIL import Image

from app.core.config import obter_config
from app.services.ai.base import EntradaSimulacao, FalhaDoProvedor, ProvedorIA, SaidaSimulacao
from app.services.ai.esquema import EsquemaModelo, ler_esquema
from app.services.ai.pedido import PedidoCapilar
from app.services.ai.planos import Plano, configuracao_de, montar_entrada, planejar

log = logging.getLogger(__name__)

#: Schemas lidos, por (endereço do provedor, modelo): (validade, schema).
_esquemas: dict[tuple[str, str], tuple[float, EsquemaModelo | None]] = {}
_trava_esquemas = threading.Lock()

_DATA_URI = re.compile(r"data:[^\"'\s,]*;base64,[A-Za-z0-9+/=]*")

#: Leituras idempotentes (consulta do estado, download do resultado) repetidas diante de
#: falha transitória. Quando elas acontecem a predição já foi criada e cobrada: perder o
#: resultado por um soluço de rede é pagar por nada. A criação da predição nunca é
#: repetida, porque um erro na resposta não garante que ela não foi criada.
TENTATIVAS_DE_LEITURA = 3
_SINAIS_DE_BLOQUEIO = ("nsfw", "moderat", "safety", "flagged", "sensitive")


def limpar_cache_de_esquemas() -> None:
    with _trava_esquemas:
        _esquemas.clear()


def _resumo_seguro(texto: str) -> str:
    """Trecho de corpo de erro para o log, sem imagem embutida."""
    return _DATA_URI.sub("data:…", texto or "")[:500]


def _reduzir(conteudo: bytes, lado_maximo: int) -> bytes:
    """Reduz a imagem ao lado máximo de envio, regravando em JPEG. Menores seguem iguais."""
    with Image.open(io.BytesIO(conteudo)) as imagem:
        if max(imagem.size) <= lado_maximo:
            return conteudo
        copia = imagem.convert("RGB")
    copia.thumbnail((lado_maximo, lado_maximo))
    saida = io.BytesIO()
    copia.save(saida, format="JPEG", quality=90)
    return saida.getvalue()


class ProvedorReplicate(ProvedorIA):
    nome = "replicate"

    def __init__(self) -> None:
        config = obter_config()
        if not config.ai_api_key:
            raise FalhaDoProvedor(
                "AI_API_KEY não configurada: defina a credencial do provedor ou use AI_PROVIDER=fake",
                codigo="credencial_ausente",
            )
        self.config = config
        self.token = config.ai_api_key
        self.modelo = config.ai_modelo
        self.timeout_s = config.ai_timeout_s
        # Lido da configuração, e não de uma constante de módulo: é o que permite os
        # testes exercitarem este cliente contra um servidor local, sem rede nem custo.
        self.base = config.ai_base_url.rstrip("/")
        self.intervalo_consulta_s = config.ai_intervalo_consulta_s

    def _cabecalhos(self, json: bool = True) -> dict[str, str]:
        cabecalhos = {"Authorization": f"Bearer {self.token}"}
        if json:
            cabecalhos["Content-Type"] = "application/json"
        return cabecalhos

    # --- Respostas de erro ---------------------------------------------------

    def _conferir(self, resposta: httpx.Response, acao: str, modelo: str | None = None) -> None:
        situacao = resposta.status_code
        if situacao < 400:
            return
        if situacao == 401:
            raise FalhaDoProvedor("Credencial do provedor de IA recusada.", codigo="credencial_invalida")
        if situacao == 402:
            raise FalhaDoProvedor("Sem crédito no provedor de IA.", codigo="sem_credito")
        if situacao == 404 and modelo:
            log.error("modelo não encontrado no provedor ao %s: %s", acao, modelo)
            raise FalhaDoProvedor(
                f"O modelo {modelo} não foi encontrado no provedor. Confira a configuração.",
                codigo="modelo_inexistente",
            )
        if situacao == 429:
            # Teto do próprio provedor, diferente do nosso: aqui não adianta crédito nem
            # credencial, é só esperar.
            log.warning(
                "provedor recusou por limite de requisições: retry_after=%s",
                resposta.headers.get("retry-after", "não informado"),
            )
            raise FalhaDoProvedor(
                "O serviço de simulação está recebendo pedidos demais agora.",
                codigo="limite_do_provedor",
            )
        if situacao == 422:
            log.error("o provedor recusou a entrada ao %s: %s", acao, _resumo_seguro(resposta.text))
            raise FalhaDoProvedor(
                "O serviço de simulação recusou os parâmetros enviados.", codigo="entrada_recusada"
            )
        log.error("replicate respondeu %s ao %s: %s", situacao, acao, _resumo_seguro(resposta.text))
        raise FalhaDoProvedor("O serviço de simulação recusou a requisição.")

    # --- Schema e plano ------------------------------------------------------

    def esquema(self, cliente: httpx.Client, modelo: str) -> EsquemaModelo | None:
        chave = (self.base, modelo)
        agora = time.monotonic()
        with _trava_esquemas:
            guardado = _esquemas.get(chave)
        if guardado and guardado[0] > agora:
            return guardado[1]

        resposta = cliente.get(f"{self.base}/models/{modelo}", headers=self._cabecalhos(False))
        self._conferir(resposta, "consultar o modelo", modelo)
        esquema = ler_esquema(modelo, _como_json(resposta))
        if esquema is None:
            log.warning(
                "o modelo %s não publicou schema de entrada: o envio segue sem conferência", modelo
            )
        with _trava_esquemas:
            _esquemas[chave] = (agora + self.config.ai_cache_esquema_min * 60, esquema)
        return esquema

    def _plano(self, cliente: httpx.Client, pedido: PedidoCapilar) -> tuple[Plano, EsquemaModelo | None]:
        configuracao = configuracao_de(self.config)
        principal = self.esquema(cliente, configuracao.modelo_principal)
        plano = planejar(pedido, configuracao, principal)
        if plano.modelo == configuracao.modelo_principal:
            return plano, principal
        return plano, self.esquema(cliente, plano.modelo)

    def preparar(self, pedido: PedidoCapilar) -> Plano:
        try:
            with httpx.Client(timeout=min(self.timeout_s, 20.0)) as cliente:
                plano, esquema = self._plano(cliente, pedido)
        except httpx.TimeoutException as erro:
            raise FalhaDoProvedor(
                "O serviço de simulação não respondeu no tempo esperado.", codigo="timeout"
            ) from erro
        except httpx.HTTPError as erro:
            log.warning("falha de rede ao consultar o provedor: %s", type(erro).__name__)
            raise FalhaDoProvedor("O serviço de simulação não respondeu.") from erro
        # A conferência olha nomes e opções; no lugar da foto, uma marcação.
        montar_entrada(plano, "data:image/jpeg;base64,", esquema)
        return plano

    # --- Arquivos ------------------------------------------------------------

    def _como_entrada(
        self, cliente: httpx.Client, conteudo: bytes, mime: str, enviados: list[str]
    ) -> str:
        """Data URI para arquivos pequenos; API de arquivos para os maiores."""
        if len(conteudo) <= self.config.ai_limite_data_uri_kb * 1024:
            return f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"
        extensao = mime.split("/")[-1].replace("jpeg", "jpg")
        resposta = cliente.post(
            f"{self.base}/files",
            headers=self._cabecalhos(False),
            files={"content": (f"entrada.{extensao}", conteudo, mime)},
        )
        self._conferir(resposta, "enviar o arquivo")
        dados = _como_json(resposta)
        url = (dados.get("urls") or {}).get("get")
        if isinstance(dados.get("id"), str):
            enviados.append(dados["id"])
        if not isinstance(url, str) or not url:
            raise FalhaDoProvedor(
                "O serviço de simulação devolveu uma resposta inesperada.", codigo="resposta_invalida"
            )
        return url

    def _apagar_arquivos(self, identificadores: list[str]) -> None:
        """A foto não fica na conta da Replicate depois do uso, mesmo se a geração falhar."""
        for identificador in identificadores:
            try:
                with httpx.Client(timeout=10.0) as cliente:
                    resposta = cliente.delete(
                        f"{self.base}/files/{identificador}", headers=self._cabecalhos(False)
                    )
                if resposta.status_code >= 400 and resposta.status_code != 404:
                    log.warning("não foi possível apagar o arquivo %s: status=%s", identificador, resposta.status_code)
            except httpx.HTTPError:
                log.warning("não foi possível apagar o arquivo %s no provedor", identificador)

    # --- Predição ------------------------------------------------------------

    def _criar_predicao(
        self, cliente: httpx.Client, modelo: str, esquema: EsquemaModelo | None, entrada: dict[str, Any]
    ) -> dict:
        resposta = cliente.post(
            f"{self.base}/models/{modelo}/predictions",
            headers=self._cabecalhos(),
            json={"input": entrada},
        )
        if resposta.status_code == 404 and esquema is not None and esquema.versao:
            # Modelo que não é "oficial" na Replicate: só aceita a versão explícita.
            resposta = cliente.post(
                f"{self.base}/predictions",
                headers=self._cabecalhos(),
                json={"version": esquema.versao, "input": entrada},
            )
        self._conferir(resposta, "criar a predição", modelo)
        return _como_json(resposta)

    def _aguardar(self, cliente: httpx.Client, predicao: dict, limite_s: float) -> object:
        """Consulta a predição até concluir e devolve o `output` dela."""
        limite = time.monotonic() + limite_s
        urls = predicao.get("urls") or {}
        url_consulta = urls.get("get")
        estado = predicao

        while True:
            situacao = estado.get("status")
            if situacao == "succeeded":
                return estado.get("output")
            if situacao in {"failed", "canceled"}:
                motivo = str(estado.get("error") or "")
                log.error("predição %s: %s", situacao, _resumo_seguro(motivo)[:300])
                if any(sinal in motivo.lower() for sinal in _SINAIS_DE_BLOQUEIO):
                    raise FalhaDoProvedor(
                        "O filtro de segurança do serviço recusou a imagem.",
                        codigo="conteudo_bloqueado",
                    )
                raise FalhaDoProvedor(
                    "O serviço de simulação não conseguiu gerar a imagem.",
                    codigo="falha_na_geracao",
                )
            if not url_consulta:
                # O provedor respondeu, e rápido: só não respondeu o que o contrato diz.
                log.error(
                    "resposta fora do contrato do provedor: status=%r chaves=%s",
                    situacao,
                    sorted(estado) if isinstance(estado, dict) else type(estado).__name__,
                )
                raise FalhaDoProvedor(
                    "O serviço de simulação devolveu uma resposta inesperada.",
                    codigo="resposta_invalida",
                )
            if time.monotonic() > limite:
                self._cancelar(cliente, urls.get("cancel"))
                raise FalhaDoProvedor(
                    "O serviço de simulação não respondeu no tempo esperado.", codigo="timeout"
                )
            time.sleep(self.intervalo_consulta_s)
            resposta = self._ler(cliente, url_consulta, headers=self._cabecalhos(False))
            self._conferir(resposta, "consultar a predição")
            estado = _como_json(resposta)

    def _ler(self, cliente: httpx.Client, url: str, **opcoes: Any) -> httpx.Response:
        """GET com até `TENTATIVAS_DE_LEITURA` tentativas para falhas transitórias.

        Repete erro de rede e respostas 5xx ou 429; um 4xx de verdade (credencial, não
        encontrado) volta na hora, para `_conferir` explicar.
        """
        for tentativa in range(1, TENTATIVAS_DE_LEITURA + 1):
            try:
                resposta = cliente.get(url, **opcoes)
            except httpx.TransportError as erro:
                if tentativa == TENTATIVAS_DE_LEITURA:
                    raise
                log.warning(
                    "leitura no provedor falhou (%s), tentativa %s de %s",
                    type(erro).__name__,
                    tentativa,
                    TENTATIVAS_DE_LEITURA,
                )
            else:
                transitoria = resposta.status_code >= 500 or resposta.status_code == 429
                if not transitoria or tentativa == TENTATIVAS_DE_LEITURA:
                    return resposta
                log.warning(
                    "provedor respondeu %s a uma leitura, tentativa %s de %s",
                    resposta.status_code,
                    tentativa,
                    TENTATIVAS_DE_LEITURA,
                )
            time.sleep(self.intervalo_consulta_s * tentativa)
        raise AssertionError("inalcançável")  # pragma: no cover

    def _cancelar(self, cliente: httpx.Client, url: str | None) -> None:
        if not url:
            return
        try:
            cliente.post(url, headers=self._cabecalhos(False), timeout=10.0)
            log.info("predição cancelada por tempo esgotado")
        except httpx.HTTPError:
            log.warning("não foi possível cancelar a predição por tempo esgotado")

    # --- Simulação -----------------------------------------------------------

    def gerar(self, entrada: EntradaSimulacao) -> SaidaSimulacao:
        inicio = time.monotonic()
        lado = self.config.ai_lado_maximo_envio
        enviados: list[str] = []
        try:
            with httpx.Client(timeout=self.timeout_s) as cliente:
                plano, esquema = self._plano(cliente, entrada.pedido)
                foto = self._como_entrada(cliente, _reduzir(entrada.imagem, lado), "image/jpeg", enviados)
                corpo = montar_entrada(plano, foto, esquema)
                predicao = self._criar_predicao(cliente, plano.modelo, esquema, corpo)
                url_saida = _url_da_saida(self._aguardar(cliente, predicao, self.timeout_s))
                imagem = self._ler(cliente, url_saida, timeout=self.timeout_s)
                imagem.raise_for_status()
        except httpx.TimeoutException as erro:
            raise FalhaDoProvedor(
                "O serviço de simulação não respondeu no tempo esperado.", codigo="timeout"
            ) from erro
        except httpx.HTTPError as erro:
            log.warning("falha de rede ao falar com o provedor: %s", type(erro).__name__)
            raise FalhaDoProvedor("O serviço de simulação não respondeu.") from erro
        finally:
            self._apagar_arquivos(enviados)

        return SaidaSimulacao(
            imagem=imagem.content,
            mime=imagem.headers.get("content-type", "image/jpeg").split(";")[0],
            modelo=plano.modelo,
            tempo_ms=int((time.monotonic() - inicio) * 1000),
            instrucao=plano.instrucao,
        )


def _como_json(resposta: httpx.Response) -> dict:
    """Lê o corpo como JSON, tratando corpo vazio ou inválido como falha do provedor.

    Sem isso, um corpo vazio levanta erro de decodificação que sobe até o tratamento
    genérico e é registrado como `erro_interno`, atribuindo ao sistema um problema que
    é do terceiro.
    """
    try:
        corpo = resposta.json()
    except ValueError as erro:
        log.error(
            "corpo não é JSON: status=%s bytes=%s", resposta.status_code, len(resposta.content)
        )
        raise FalhaDoProvedor(
            "O serviço de simulação devolveu uma resposta inesperada.",
            codigo="resposta_invalida",
        ) from erro
    if not isinstance(corpo, dict):
        raise FalhaDoProvedor(
            "O serviço de simulação devolveu uma resposta inesperada.",
            codigo="resposta_invalida",
        )
    return corpo


def _url_da_saida(saida: object) -> str:
    """O modelo pode devolver uma string ou uma lista de URLs."""
    if isinstance(saida, str) and saida:
        return saida
    if isinstance(saida, list) and saida and isinstance(saida[0], str):
        return saida[0]
    raise FalhaDoProvedor(
        "O serviço de simulação devolveu uma resposta inesperada.", codigo="resposta_invalida"
    )
