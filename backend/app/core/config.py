"""Configuração da aplicação, lida de variáveis de ambiente (seção 18 da especificação).

Nenhum segredo tem valor padrão: `JWT_SECRET` ausente derruba a inicialização em vez de
deixar a aplicação subir com uma chave previsível.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]

#: Banco local de desenvolvimento, com a senha publicada na documentação. Serve de padrão
#: fora de produção; em produção a API se recusa a subir com ele.
URL_BANCO_DESENVOLVIMENTO = "postgresql+psycopg://espelho:espelho@localhost:5432/espelho"


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RAIZ / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ambiente: Literal["desenvolvimento", "teste", "producao"] = "desenvolvimento"

    #: Fuso do salão. Usado para saber em que DIA um atendimento aconteceu: 23h em
    #: Brasília já é o dia seguinte em UTC, e o histórico do cliente não pode registrar
    #: o serviço na data errada. Comparações de instante (passado x futuro) não dependem
    #: dele, porque instantes com fuso são comparáveis entre si.
    fuso_horario: str = "America/Sao_Paulo"

    database_url: str = URL_BANCO_DESENVOLVIMENTO
    #: Conexões mantidas pelo pool, por processo. Cada processo do uvicorn tem o seu: com
    #: N processos, o banco recebe até N x (pool + excedente) conexões.
    banco_pool: int = 5
    banco_pool_excedente: int = 10
    #: Quanto uma requisição espera por uma conexão livre do pool antes de desistir.
    banco_pool_espera_s: int = 10

    #: Endereço público da API, como o aplicativo a enxerga (ex.: https://api.exemplo.com).
    #: As URLs assinadas das imagens são montadas a partir dele. Vazio: usa o endereço da
    #: própria requisição, o que serve no desenvolvimento (o celular chega pelo IP da rede
    #: local) mas, atrás de um proxy, sairia com o host e o esquema internos. Obrigatório
    #: em produção.
    url_publica: str = ""

    #: `texto` para ler no terminal; `json` (uma linha por evento) para coletores de log.
    log_formato: Literal["texto", "json"] = "texto"
    log_nivel: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    jwt_secret: str
    jwt_minutos_access: int = 30
    jwt_dias_refresh: int = 30
    jwt_algoritmo: str = "HS256"

    cors_origens: str = "http://localhost:8081,http://localhost:19006"

    storage_driver: Literal["local", "s3"] = "local"
    storage_dir: Path = RAIZ / "dados" / "imagens"
    storage_url: str = ""
    storage_bucket: str = "espelho"
    storage_key: str = ""
    storage_secret: str = ""
    storage_regiao: str = "us-east-1"
    url_imagem_minutos: int = 10

    # Entrar com Google. Os IDs de cliente OAuth (web, Android, iOS) criados no Google
    # Cloud, separados por vírgula. São públicos (vão também no aplicativo); o servidor
    # usa a lista para aceitar só tokens emitidos para este aplicativo. Vazio: o login
    # com Google fica desligado e o botão não aparece.
    google_client_ids: str = ""

    ai_provider: Literal["fake", "replicate"] = "fake"
    ai_api_key: str = ""
    #: Modelo principal: troca de corte e cor com opções fechadas (`haircut`, `hair_color`).
    ai_modelo: str = "flux-kontext-apps/change-haircut"
    #: Edição por descrição livre (`prompt` + `input_image`), para o que não cabe nas
    #: opções do principal. Vazio: só as sugestões da lista são aceitas.
    ai_modelo_texto: str = "black-forest-labs/flux-kontext-pro"
    #: Como a descrição em português vai nos `prompt`s (ver `services/ai/instrucoes.py`).
    ai_instrucao_idioma: Literal["pt_com_termos", "pt"] = "pt_com_termos"
    ai_timeout_s: float = 60.0
    #: Fotos até este tamanho vão como data URI no corpo; acima, pela API de arquivos
    #: da Replicate (e são apagados de lá ao fim). A documentação dela recomenda data URI
    #: só abaixo de 1 MB.
    ai_limite_data_uri_kb: int = 1024
    #: Lado maior das imagens enviadas ao modelo. Os modelos geram por volta de 1 megapixel:
    #: mandar a foto inteira só aumenta o envio.
    ai_lado_maximo_envio: int = 1536
    #: Por quanto tempo o schema publicado de cada modelo é reaproveitado.
    ai_cache_esquema_min: int = 60
    #: Endereço do provedor. Configurável para que os testes possam apontar para um
    #: servidor de mentira e exercitar o cliente real sem chamar o serviço externo.
    ai_base_url: str = "https://api.replicate.com/v1"
    #: Intervalo entre consultas ao estado da predição.
    ai_intervalo_consulta_s: float = 1.0

    imagem_max_bytes: int = 8 * 1024 * 1024
    imagem_min_lado: int = 480
    imagem_max_lado: int = 4096
    imagem_proporcao_max: float = 1.35
    imagem_luminancia_min: float = 40.0
    imagem_luminancia_max: float = 230.0
    validar_rosto: bool = True

    modo_demo: bool = False

    #: Teto de simulações por conta a cada hora. Cada geração custa dinheiro no provedor:
    #: sem um teto, uma conta (ou um token roubado) esvazia o crédito.
    simulacao_max_por_hora: int = 3

    simulacao_expira_min: int = 5

    @field_validator("ai_modelo", "ai_modelo_texto")
    @classmethod
    def _identificador_de_modelo(cls, valor: str, informacao) -> str:
        # O identificador entra no caminho da URL do provedor: só "dono/nome". Vazio é
        # aceito no modelo de texto e desliga a descrição livre.
        valor = valor.strip()
        if not valor and informacao.field_name != "ai_modelo":
            return ""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", valor):
            raise ValueError(
                f"{informacao.field_name.upper()} deve ser 'dono/nome' de um modelo da Replicate"
            )
        return valor

    @field_validator("jwt_secret")
    @classmethod
    def _segredo_forte(cls, valor: str) -> str:
        if len(valor) < 32:
            raise ValueError("JWT_SECRET precisa ter ao menos 32 caracteres")
        return valor

    @field_validator("storage_dir")
    @classmethod
    def _storage_relativo_ao_backend(cls, valor: Path) -> Path:
        # `STORAGE_DIR=./dados/imagens` (o valor do .env.example) era resolvido a partir da
        # pasta de onde a API foi iniciada. Subir o servidor de outra pasta, ou extrair o
        # projeto em outro lugar, fazia as imagens já gravadas "sumirem" (404) e as novas
        # irem para um lugar diferente. Relativo, agora, é sempre à pasta `backend`.
        return valor if valor.is_absolute() else (RAIZ / valor).resolve()

    @field_validator("fuso_horario")
    @classmethod
    def _fuso_existe(cls, valor: str) -> str:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(valor)
        except (ZoneInfoNotFoundError, ValueError) as erro:
            raise ValueError(
                f"FUSO_HORARIO desconhecido: {valor!r}. Use um nome como America/Sao_Paulo."
            ) from erro
        return valor

    @field_validator("url_publica")
    @classmethod
    def _url_publica_valida(cls, valor: str) -> str:
        valor = valor.strip().rstrip("/")
        if valor and not re.fullmatch(r"https?://[^\s/?#]+(/[^\s?#]*)?", valor):
            raise ValueError("URL_PUBLICA deve ser um endereço como https://api.exemplo.com")
        return valor

    @model_validator(mode="after")
    def _producao_segura(self) -> "Configuracao":
        """Combinações que não podem chegar a produção: melhor não subir do que subir assim.

        Cada uma já aconteceu ou é fácil de acontecer ao copiar o `.env` do desenvolvimento.
        """
        if not self.producao:
            return self
        # Os atalhos de demonstração forçam foto recusada e falha do provedor. Em produção
        # eles seriam uma porta para enganar o profissional, e um `MODO_DEMO=true` herdado
        # do ambiente de desenvolvimento passaria despercebido.
        if self.modo_demo:
            raise ValueError("MODO_DEMO=true não é permitido com AMBIENTE=producao")
        # A senha deste banco está publicada na documentação.
        if self.database_url == URL_BANCO_DESENVOLVIMENTO:
            raise ValueError(
                "DATABASE_URL precisa ser definida em produção (o padrão é o banco local "
                "de desenvolvimento, com senha publicada)"
            )
        # Sem endereço público, as URLs de imagem saem com o host e o esquema que o proxy
        # usa por dentro (http://api:8000): o navegador bloqueia e o celular não alcança.
        if not self.url_publica.startswith("https://"):
            raise ValueError("URL_PUBLICA com https:// é obrigatória em produção")
        if "*" in self.origens_cors:
            raise ValueError("CORS_ORIGENS não pode ser '*' em produção: liste as origens")
        return self

    def avisos_de_producao(self) -> list[str]:
        """Escolhas permitidas em produção, mas que merecem uma linha no log ao subir."""
        if not self.producao:
            return []
        avisos = []
        if self.ai_provider == "fake":
            avisos.append(
                "AI_PROVIDER=fake: as simulações são geradas localmente, sem IA (só "
                "recoloração com aviso na imagem)"
            )
        inseguras = [o for o in self.origens_cors if o.startswith("http://")]
        if inseguras:
            avisos.append(f"CORS_ORIGENS com origens sem https: {', '.join(inseguras)}")
        if self.storage_driver == "local":
            avisos.append(
                f"STORAGE_DRIVER=local: as imagens ficam em {self.storage_dir}; esse "
                "diretório precisa estar num volume persistente e entrar no backup"
            )
        return avisos

    @property
    def fuso(self):
        from zoneinfo import ZoneInfo

        return ZoneInfo(self.fuso_horario)

    @property
    def ids_google(self) -> list[str]:
        return [i.strip() for i in self.google_client_ids.split(",") if i.strip()]

    @property
    def origens_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origens.split(",") if o.strip()]

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"


@lru_cache
def obter_config() -> Configuracao:
    return Configuracao()  # type: ignore[call-arg]
