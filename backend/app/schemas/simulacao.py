from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import StatusSimulacao
from app.schemas.base import ModeloBase
from app.services.ai.pedido import Genero


class ParametrosSimulacao(ModeloBase):
    #: Corte pedido: a descrição ou "Corte atual".
    estilo: str = Field(max_length=300)
    #: Cor pedida: a descrição ou "Cor atual".
    cor: str = Field(max_length=300)
    #: Gênero do corte enviado ao modelo: "none" (não especificado), "male" ou "female".
    genero: Genero = "none"
    observacoes: str = Field(default="", max_length=2000)


class ProblemaFoto(ModeloBase):
    """Mesma forma que a tela `simulacao/recusada.tsx` já exibe."""

    titulo: str
    detalhe: str


class SimulacaoOut(ModeloBase):
    id: uuid.UUID
    cliente_id: uuid.UUID
    usuario_id: uuid.UUID
    parametros: ParametrosSimulacao
    status: StatusSimulacao
    #: URLs assinadas de curta duração (`null` enquanto a geração não terminou).
    img_entrada_uri: str | None
    img_saida_uri: str | None
    modelo_ia: str
    provedor: str
    #: O que foi pedido ao modelo (opções ou instrução em texto), sem a imagem.
    instrucao_ia: str | None
    tempo_ms: int | None
    preferida: bool
    erro_codigo: str | None
    criado_em: datetime
    concluida_em: datetime | None


class CatalogoOut(ModeloBase):
    estilos: list[str]
    cores: list[str]
    servicos: list[str]


class EnquadramentoOut(ModeloBase):
    """Resposta da conferência ao vivo da câmera."""

    rosto_no_guia: bool


class PedidoIn(ModeloBase):
    """O pedido da etapa "Estilo e cor", para a prévia do plano (sem a foto)."""

    corte: str = Field(default="", max_length=2000)
    manter_corte: bool = False
    cor: str = Field(default="", max_length=2000)
    manter_cor: bool = False
    #: "none", "male" ou "female". Validado em `interpretar`, com a mesma mensagem do envio.
    genero: str = Field(default="none", max_length=20)


class PlanoOut(ModeloBase):
    """Como o pedido será gerado: modo, modelo e o que vai ao modelo (sem a foto)."""

    #: "fake" no provedor local de desenvolvimento, que não usa IA (a revisão avisa).
    provedor: str
    modo: str
    descricao_modo: str
    modelo: str
    instrucao: str
    estilo: str
    cor: str
