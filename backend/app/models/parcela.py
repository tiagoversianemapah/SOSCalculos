import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .base import TimestampMixin, UUIDPk
from .tipos import DecimalText

if TYPE_CHECKING:
    from .pagamento_parcial import PagamentoParcial
    from .parada import ParadaExtraordinaria
    from .processo import Processo
    from .segmento import CorrecaoSegmento, JurosSegmento


class Parcela(UUIDPk, TimestampMixin, Base):
    __tablename__ = "parcela"

    processo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    historico: Mapped[str] = mapped_column(String, nullable=False)
    valor_bruto: Mapped[Decimal] = mapped_column(DecimalText(18, 2), nullable=False)
    valor_apurado: Mapped[Decimal | None] = mapped_column(DecimalText(18, 2), nullable=True)
    usa_correcao_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    usa_juros_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Coluna "Multa %" do passo 2 (paridade SOSCálculos) — percentual
    # simples sobre o valor_apurado da própria parcela, calculado só na
    # exibição (não passa pela linha do tempo do motor, seção 3).
    multa_percentual: Mapped[Decimal | None] = mapped_column(DecimalText(9, 4), nullable=True)

    processo: Mapped["Processo"] = relationship(back_populates="parcelas")
    pagamentos: Mapped[list["PagamentoParcial"]] = relationship(
        back_populates="parcela", cascade="all, delete-orphan", order_by="PagamentoParcial.data"
    )
    correcao_segmentos_override: Mapped[list["CorrecaoSegmento"]] = relationship(
        back_populates="parcela",
        cascade="all, delete-orphan",
        primaryjoin="and_(Parcela.id==CorrecaoSegmento.parcela_id)",
    )
    juros_segmentos_override: Mapped[list["JurosSegmento"]] = relationship(
        back_populates="parcela",
        cascade="all, delete-orphan",
        primaryjoin="and_(Parcela.id==JurosSegmento.parcela_id)",
    )
    paradas: Mapped[list["ParadaExtraordinaria"]] = relationship(
        back_populates="parcela", cascade="all, delete-orphan"
    )
