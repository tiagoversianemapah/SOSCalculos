import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .base import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from .parcela import Parcela
    from .processo import Processo


class ParadaExtraordinaria(UUIDPk, TimestampMixin, Base):
    __tablename__ = "parada_extraordinaria"
    __table_args__ = (
        CheckConstraint(
            "(processo_id IS NOT NULL AND parcela_id IS NULL) OR "
            "(processo_id IS NULL AND parcela_id IS NOT NULL)",
            name="ck_parada_dono_exclusivo",
        ),
        CheckConstraint("data_fim >= data_inicio", name="ck_parada_data_fim_apos_inicio"),
    )

    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=True, index=True
    )
    parcela_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parcela.id", ondelete="CASCADE"), nullable=True, index=True
    )
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(String, nullable=False)
    suspende_correcao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suspende_juros: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    processo: Mapped["Processo | None"] = relationship(back_populates="paradas")
    parcela: Mapped["Parcela | None"] = relationship(back_populates="paradas")
