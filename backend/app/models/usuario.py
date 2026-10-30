from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdUUID, Timestamps

if TYPE_CHECKING:
    from app.models.agendamento import Agendamento
    from app.models.atendimento import Atendimento
    from app.models.ciencia import Ciencia
    from app.models.cliente import Cliente
    from app.models.identidade_externa import IdentidadeExterna
    from app.models.imagem import Imagem
    from app.models.simulacao import Simulacao


class Usuario(IdUUID, Timestamps, Base):
    """Profissional de beleza. É o titular da conta e o controlador dos dados (LGPD)."""

    __tablename__ = "usuarios"

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # Guardado sempre em minúsculas pelo serviço de autenticação, o que torna a
    # unicidade insensível a caixa sem depender da extensão citext.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    # Vazio nas contas criadas pelo Google, que não têm senha. Uma conta sem senha só
    # entra pelo Google; o login por senha a recusa como a qualquer senha errada.
    senha_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    atuacao: Mapped[str] = mapped_column(String(60), nullable=False, default="autônomo")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Vai em todo token emitido (`sv`). Trocar a senha ou "sair de todos os aparelhos"
    #: incrementa o valor, e os tokens anteriores deixam de valer.
    versao_sessao: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    clientes: Mapped[list["Cliente"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    ciencias: Mapped[list["Ciencia"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    imagens: Mapped[list["Imagem"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    simulacoes: Mapped[list["Simulacao"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    atendimentos: Mapped[list["Atendimento"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    agendamentos: Mapped[list["Agendamento"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    identidades: Mapped[list["IdentidadeExterna"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def tem_senha(self) -> bool:
        return self.senha_hash is not None

    @property
    def google_vinculado(self) -> bool:
        return any(i.provedor == "google" for i in self.identidades)
