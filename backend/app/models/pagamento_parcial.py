import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .base import UUIDPk
from .enums import TipoPagamentoParcial
from .tipos import DecimalText

if TYPE_CHECKING:
    from .parcela import Parcela


class PagamentoParcial(UUIDPk, Base):
    """Dedução da parcela — pagamento, depósito judicial, compensação ou
    outro (seção 2/3.6). Várias por parcela; o abatimento no motor é
    idêntico para todos, `tipo` só rotula a linha na memória/PDF.
    """

    __tablename__ = "pagamento_parcial"

    parcela_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parcela.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(DecimalText(18, 2), nullable=False)
    tipo: Mapped[TipoPagamentoParcial] = mapped_column(
        Enum(TipoPagamentoParcial, name="tipo_pagamento_parcial"), nullable=False
    )
    descricao: Mapped[str | None] = mapped_column(String, nullable=True)
    fonte_criterio: Mapped[str | None] = mapped_column(String, nullable=True)

    parcela: Mapped["Parcela"] = relationship(back_populates="pagamentos")
