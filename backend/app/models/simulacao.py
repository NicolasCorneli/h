from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CriadoEm, IdUUID
from app.models.enums import StatusSimulacao
from app.models.tipos_sql import enum_pg

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.consentimento import Consentimento
    from app.models.imagem import Imagem
    from app.models.usuario import Usuario


class Simulacao(IdUUID, CriadoEm, Base):
    """Simulação capilar gerada pelo provedor de IA (RF04/RF05).

    `consentimento_id` é obrigatório: cada imagem gerada aponta para a decisão de
    consentimento que a autorizou. É a prova, no próprio banco, de que nenhuma simulação
    existiu sem base legal.
    """

    __tablename__ = "simulacoes"
    __table_args__ = (
        Index("ix_simulacoes_cliente_id_criado_em", "cliente_id", "criado_em"),
        # Cota por hora e expiração das presas, ambas por conta.
        Index("ix_simulacoes_usuario_id_criado_em", "usuario_id", "criado_em"),
        # Conferidas pelo banco ao apagar uma imagem (cascata).
        Index("ix_simulacoes_img_entrada_id", "img_entrada_id"),
        Index("ix_simulacoes_img_saida_id", "img_saida_id"),
        # Apenas uma simulação preferida por cliente (RF07).
        Index(
            "uq_simulacoes_preferida_por_cliente",
            "cliente_id",
            unique=True,
            postgresql_where=text("preferida"),
        ),
        CheckConstraint(
            "(status = 'concluida') = (img_saida_id IS NOT NULL)",
            name="saida_coerente_com_status",
        ),
        CheckConstraint("NOT (preferida AND status <> 'concluida')", name="preferida_concluida"),
        CheckConstraint("tempo_ms IS NULL OR tempo_ms >= 0", name="tempo_nao_negativo"),
        CheckConstraint("genero IN ('none', 'male', 'female')", name="genero_valido"),
        # O mesmo envio repetido devolve a simulação já criada (ver `chave_envio`).
        Index(
            "uq_simulacoes_chave_envio_por_usuario",
            "usuario_id",
            "chave_envio",
            unique=True,
            postgresql_where=text("chave_envio IS NOT NULL"),
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    # Em cascata: a simulação não faz sentido sem a decisão que a autorizou nem sem as
    # imagens. Cascata também evita ordem de exclusão indefinida quando o cliente é
    # apagado — com RESTRICT, a cascata do cliente poderia falhar.
    consentimento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("consentimentos.id", ondelete="CASCADE"), nullable=False
    )
    img_entrada_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("imagens.id", ondelete="CASCADE"), nullable=False
    )
    img_saida_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("imagens.id", ondelete="CASCADE"), nullable=True
    )

    #: Corte pedido: a descrição ou "Corte atual".
    estilo: Mapped[str] = mapped_column(String(300), nullable=False)
    #: Cor pedida: a descrição ou "Cor atual".
    cor: Mapped[str] = mapped_column(String(300), nullable=False)
    #: Gênero do corte, com o valor do campo `gender` do modelo: "none", "male" ou "female".
    #: Gravado porque a geração roda em segundo plano e remonta o pedido a partir daqui.
    genero: Mapped[str] = mapped_column(
        String(10), nullable=False, default="none", server_default="none"
    )
    observacoes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: O que foi pedido ao modelo (opções ou instrução em texto), sem a imagem.
    instrucao_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Identificador do envio, gerado pelo aplicativo: o mesmo envio não gera duas vezes.
    chave_envio: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    status: Mapped[StatusSimulacao] = mapped_column(
        enum_pg(StatusSimulacao, "status_simulacao"),
        nullable=False,
        default=StatusSimulacao.processando,
    )
    provedor: Mapped[str] = mapped_column(String(40), nullable=False)
    modelo_ia: Mapped[str] = mapped_column(String(120), nullable=False)
    tempo_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    erro_codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    erro_detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cliente: Mapped["Cliente"] = relationship(back_populates="simulacoes")
    usuario: Mapped["Usuario"] = relationship(back_populates="simulacoes")
    consentimento: Mapped["Consentimento"] = relationship()
    img_entrada: Mapped["Imagem"] = relationship(foreign_keys=[img_entrada_id])
    img_saida: Mapped["Imagem | None"] = relationship(foreign_keys=[img_saida_id])
